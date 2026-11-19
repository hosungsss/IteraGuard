"""Train the on-device NLP heads on frozen KoELECTRA-small int8 features and evaluate them.

Pipeline: tokenizer.json (WordPiece) -> encoder with the exported int8 weights (run in ONNX
Runtime by substituting the dequantized tensors into the original graph, so features equal the
NumPy/JS reference math) -> [CLS; mean] 512-d -> standardize -> multinomial logistic regression
heads (speech act, action) -> temperature scaling on the calibration split.

Writes: heads JSON (weights + provenance) and an evaluation report with baselines/ablations.
Usage: python tools/nlp/train_heads.py --enc enc_fp32.onnx --bin weights.bin --tok tokenizer.json
        --data ds/ --locked tools/nlp/locked_handwritten.jsonl --out out/
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys, time
from pathlib import Path
import numpy as np
import re, zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(ROOT / 'dmsg'))
import electra_ref as R  # noqa: E402

SPEECH = ['DIRECT_REQUEST', 'INDIRECT_REQUEST', 'WARNING', 'QUOTATION', 'INFORMATION']
ACTION = ['transfer', 'otp', 'remote_install', 'personal_data', 'link', 'secrecy', 'none']
MAX_LEN = 128
DANGEROUS = {'transfer', 'otp', 'remote_install', 'personal_data'}
NGRAM_BUCKETS, NGRAM_N, NGRAM_W_SPEECH = 2048, (1, 2, 3), 0.5


def ngram_vec(text):
    """Hashed character n-grams over the whitespace-removed, lower-cased text; log1p counts.
    CRC-32 (IEEE) of the UTF-8 bytes of each n-gram (code points), mod NGRAM_BUCKETS."""
    t = ' ' + ''.join(text.lower().split()) + ' '
    cp = list(t); v = np.zeros(NGRAM_BUCKETS, np.float32)
    for n in NGRAM_N:
        for i in range(len(cp) - n + 1):
            v[zlib.crc32(''.join(cp[i:i + n]).encode('utf8')) % NGRAM_BUCKETS] += 1
    return np.log1p(v)


def speech_x(Z, G):
    return np.concatenate([Z, G * NGRAM_W_SPEECH], 1)


def eojeol_spans(text):
    """(start, end) code-point spans of whitespace-delimited words."""
    return [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]


def occlusion_anchor(head, text, action):
    """Word whose removal most lowers the action head's probability for `action`.
    Attribution of this linear n-gram model only; not proof of meaning."""
    if action not in head['classes'] or action == 'none': return None
    k = head['classes'].index(action); sp = eojeol_spans(text)
    if not sp: return None
    base = predict(head, ngram_vec(text)[None])[0, k]; best = None
    for s0, e0 in sp:
        q = predict(head, ngram_vec(text[:s0] + text[e0:])[None])[0, k]
        if best is None or base - q > best[0]: best = (base - q, s0, e0)
    if best is None or best[0] <= 0.0: return None
    return (best[1], best[2], text[best[1]:best[2]])


def dequant_session(enc_path, bin_path):
    import onnx, onnxruntime as ort
    from onnx import numpy_helper
    m = onnx.load(enc_path)
    q = R.read_bin(Path(bin_path)); W = {k: R.dequant(v, k) for k, v in q.items()}
    # role name -> initializer name (same discovery as electra_ref.load_onnx_weights)
    role = {'/embeddings_project/MatMul': 'embeddings_project.weight'}
    for i in range(R.LAYERS):
        p = f'/encoder/layer.{i}/'
        for a, b in (('attention/self/query', 'attention.self.query'), ('attention/self/key', 'attention.self.key'), ('attention/self/value', 'attention.self.value'),
                     ('attention/output/dense', 'attention.output.dense'), ('intermediate/dense', 'intermediate.dense'), ('output/dense', 'output.dense')):
            role[f'{p}{a}/MatMul'] = f'encoder.layer.{i}.{b}.weight'
    init_names = {t.name for t in m.graph.initializer}
    src = {}
    for nd in m.graph.node:
        if nd.op_type == 'MatMul' and nd.name in role:
            src[[x for x in nd.input if x in init_names][0]] = role[nd.name]
    for t in m.graph.initializer:
        key = src.get(t.name, t.name)
        if key in W:
            t.CopyFrom(numpy_helper.from_array(W[key].astype(np.float32), t.name))
    return ort.InferenceSession(m.SerializeToString())


def featurize(sess, tok, texts, bs=32):
    out = np.zeros((len(texts), 512), np.float32)
    for i in range(0, len(texts), bs):
        enc = [tok.encode(t).ids[:MAX_LEN - 1] for t in texts[i:i + bs]]
        enc = [e if e[-1] == 3 else e + [3] for e in enc]          # keep [SEP] after truncation
        L = max(len(e) for e in enc)
        ids = np.zeros((len(enc), L), np.int64); mask = np.zeros_like(ids)
        for j, e in enumerate(enc): ids[j, :len(e)] = e; mask[j, :len(e)] = 1
        h = sess.run(None, {'input_ids': ids, 'attention_mask': mask, 'token_type_ids': np.zeros_like(ids)})[0]
        cls = h[:, 0]; mean = (h * mask[..., None]).sum(1) / mask.sum(1, keepdims=True)
        out[i:i + len(enc)] = np.concatenate([cls, mean], 1)
    return out


def softmax(z):
    z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)


def fit_head(Xtr, ytr, Xca, yca, classes):
    from sklearn.linear_model import LogisticRegression
    best = None
    for C in (0.05, 0.1, 0.3, 1.0, 3.0):
        clf = LogisticRegression(C=C, max_iter=3000, class_weight='balanced')
        clf.fit(Xtr, ytr)
        p = clf.predict_proba(Xca); nll = -np.mean(np.log(p[np.arange(len(yca)), [list(clf.classes_).index(c) for c in yca]] + 1e-12))
        if best is None or nll < best[0]: best = (nll, C, clf)
    _, C, clf = best
    order = [list(clf.classes_).index(c) for c in classes]
    Wt, b = clf.coef_[order], clf.intercept_[order]
    z = Xca @ Wt.T + b; yi = np.array([classes.index(c) for c in yca])
    temps = np.exp(np.linspace(np.log(0.3), np.log(5), 60))
    T = min(temps, key=lambda t: -np.mean(np.log(softmax(z / t)[np.arange(len(yi)), yi] + 1e-12)))
    return {'classes': classes, 'W': Wt.astype(np.float32), 'b': b.astype(np.float32), 'T': float(T), 'C': C}


def predict(head, X):
    return softmax((X @ head['W'].T + head['b']) / head['T'])


def ece(p, y, bins=10):
    conf = p.max(1); pred = p.argmax(1); acc = (pred == y).astype(float); e = 0.0
    for lo in np.linspace(0, 1, bins, endpoint=False):
        m = (conf > lo) & (conf <= lo + 1 / bins)
        if m.any(): e += m.mean() * abs(acc[m].mean() - conf[m].mean())
    return float(e)


def wilson(k, n, z=1.96):
    if n == 0: return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def typed_raw(ps, pa):
    """Map head probabilities to the System One typed contract used by model_bridge.advisory().
    q_speech is defined relative to the *apparent action*; with no action candidate a request is not a
    request for a risky action, so the request mass is split by P(action present)."""
    s = dict(zip(SPEECH, map(float, ps))); a = dict(zip(ACTION, map(float, pa)))
    act = {k: a[k] for k in ACTION}; act['unclear'] = 0.0
    present = 1.0 - a['none']; req = s['DIRECT_REQUEST'] + s['INDIRECT_REQUEST']
    sp = {'direct_request': req * present, 'reported_or_quoted': s['QUOTATION'], 'negated_or_warning': s['WARNING'],
          'unclear': 0.0, 'informational': s['INFORMATION'] + req * a['none']}
    risky = req * present
    return {'answers': {'q_action': {'type': 'choice', 'probabilities': act}, 'q_speech': {'type': 'choice', 'probabilities': sp},
                        'q_scam': {'type': 'noul', 'noul': risky}, 'q_pressure': {'type': 'noul', 'noul': risky}}}


def policy_b2(text, ps, pa, anchor=None, threshold=0.70):
    from prototype.model_bridge import advisory
    from prototype.typed_contract import ContractError
    try:
        r = advisory(text, typed_raw(ps, pa), source='ON_DEVICE_NLP', threshold=threshold, model_anchor=anchor)
        return r['action'], r['reason']
    except ContractError as e:
        return 'ASK_HUMAN', 'ContractError:' + str(e)


def gold_action(r):
    if r['action'] == 'none' or r['speech'] in ('WARNING', 'INFORMATION'): return 'NO_STRONG_SIGNAL'
    if r['speech'] == 'QUOTATION': return 'CAUTION'
    return 'PAUSE_AND_VERIFY' if r['action'] in DANGEROUS else 'CAUTION'


def policy_b1(ps, pa):
    sp, ac = SPEECH[int(np.argmax(ps))], ACTION[int(np.argmax(pa))]
    if ac != 'none' and sp in ('DIRECT_REQUEST', 'INDIRECT_REQUEST'):
        return 'PAUSE_AND_VERIFY' if ac in DANGEROUS else 'CAUTION'
    if ac != 'none' and sp == 'QUOTATION': return 'CAUTION'
    return 'NO_STRONG_SIGNAL'


def policy_rule(text):
    from prototype.context_guard import clause_profile, ACTION_TOKENS
    prof = clause_profile(text)
    danger = ('송금', '이체', '입금', '돈을 보내', '인증번호', 'otp', '비밀번호', '주민등록번호', '신분증', '원격', '팀뷰어', '애니데스크')
    for c in prof:
        seg = text[c.start:c.end].casefold()
        if c.clean_imperative and any(d in seg for d in danger): return 'PAUSE_AND_VERIFY'
    if any(c.clean_imperative for c in prof): return 'CAUTION'
    if any(c.flags.report_cue and c.flags.action_mentioned for c in prof): return 'CAUTION'
    if any(c.flags.action_mentioned for c in prof) and not any(c.flags.warning_cue for c in prof): return 'ASK_HUMAN'
    return 'NO_STRONG_SIGNAL'


def score(rows, actions):
    n = len(rows); ok = sum(a in r['expect'] for r, a in zip(rows, actions))
    risky = [(r, a) for r, a in zip(rows, actions) if r['risky']]; benign = [(r, a) for r, a in zip(rows, actions) if not r['risky']]
    inter = sum(a in ('PAUSE_AND_VERIFY', 'CAUTION') for _, a in risky)
    nonclear = sum(a != 'NO_STRONG_SIGNAL' for _, a in risky)
    fa = sum(a in ('PAUSE_AND_VERIFY', 'CAUTION') for _, a in benign)
    ab = sum(a == 'ASK_HUMAN' for a in actions)
    return {'n': n, 'expected_action_rate': round(ok / n, 3), 'expected_ci95': wilson(ok, n),
            'risky_n': len(risky), 'risky_intervention_recall': round(inter / max(1, len(risky)), 3), 'risky_recall_ci95': wilson(inter, len(risky)),
            'risky_not_cleared_rate': round(nonclear / max(1, len(risky)), 3),
            'benign_n': len(benign), 'benign_false_alarm_rate': round(fa / max(1, len(benign)), 3), 'benign_fa_ci95': wilson(fa, len(benign)),
            'abstain_rate': round(ab / n, 3)}


def run_set(rows, ps, pa, ha, thr):
    acts = {'B0_v44_free_text': [], 'B_rule_lexical_only': [], 'B1_nlp_heads_only': [], 'B2_nlp_plus_policy': [],
            'B2_ablation_no_attribution_span': []}
    per = []
    for r, p1, p2 in zip(rows, ps, pa):
        top = ACTION[int(np.argmax(p2))]
        anc = occlusion_anchor(ha, r['text'], top) if r['text'].strip() else None
        b2, why = policy_b2(r['text'], p1, p2, anc, thr)
        acts['B0_v44_free_text'].append('ASK_HUMAN'); acts['B_rule_lexical_only'].append(policy_rule(r['text']) if r['text'].strip() else 'ASK_HUMAN')
        acts['B1_nlp_heads_only'].append(policy_b1(p1, p2)); acts['B2_nlp_plus_policy'].append(b2)
        acts['B2_ablation_no_attribution_span'].append(policy_b2(r['text'], p1, p2, None, thr)[0])
        per.append({'id': r.get('id'), 'cat': r.get('cat'), 'expect': r.get('expect'), 'B2': b2, 'reason': why, 'B1': acts['B1_nlp_heads_only'][-1],
                    'rule': acts['B_rule_lexical_only'][-1], 'speech_pred': SPEECH[int(p1.argmax())], 'speech_conf': round(float(p1.max()), 3),
                    'speech_gold': r['speech'], 'action_pred': top, 'action_conf': round(float(p2.max()), 3), 'action_gold': r['action'],
                    'anchor': anc})
    return acts, per


def main():
    ap = argparse.ArgumentParser()
    for k in ('enc', 'bin', 'tok', 'data', 'dev', 'locked', 'out'): ap.add_argument('--' + k, required=True)
    ap.add_argument('--final', action='store_true', help='also score the frozen locked set (run once, after design is fixed)')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    frz = json.loads(Path(a.locked).with_suffix('.freeze.json').read_text('utf8'))
    lk_sha = hashlib.sha256(Path(a.locked).read_bytes()).hexdigest()
    if lk_sha != frz['sha256']: raise SystemExit('LOCKED_SET_HASH_MISMATCH')
    from tokenizers import Tokenizer
    from sklearn.metrics import f1_score, confusion_matrix
    tok = Tokenizer.from_file(a.tok); sess = dequant_session(a.enc, a.bin)
    load = lambda p: [json.loads(l) for l in Path(p).read_text('utf8').splitlines() if l.strip()]
    S = {'tr': load(Path(a.data) / 'train.jsonl'), 'ca': load(Path(a.data) / 'calib.jsonl'), 'lk': load(Path(a.data) / 'locked.jsonl'),
         'dev': load(a.dev)}
    if a.final: S['hw'] = load(a.locked)
    t0 = time.time(); F = {k: featurize(sess, tok, [r['text'] if r['text'].strip() else '.' for r in v]) for k, v in S.items()}
    feat_s = time.time() - t0
    mu, sd = F['tr'].mean(0), F['tr'].std(0) + 1e-6
    G = {k: np.stack([ngram_vec(r['text']) for r in v]) for k, v in S.items()}
    XS = {k: speech_x((F[k] - mu) / sd, G[k]) for k in S}
    hs = fit_head(XS['tr'], [r['speech'] for r in S['tr']], XS['ca'], [r['speech'] for r in S['ca']], SPEECH)
    ha = fit_head(G['tr'], [r['action'] for r in S['tr']], G['ca'], [r['action'] for r in S['ca']], ACTION)
    P = {k: (predict(hs, XS[k]), predict(ha, G[k])) for k in S}
    # threshold chosen on the calibration split only (gold advisory derived from labels)
    cal = {}
    for thr in (0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8):
        acts, _ = run_set(S['ca'], *P['ca'], ha, thr)
        cal[thr] = round(float(np.mean([x == gold_action(r) for x, r in zip(acts['B2_nlp_plus_policy'], S['ca'])])), 4)
    thr = max(cal, key=lambda t: (cal[t], t))
    rep = {'feature_seconds': round(feat_s, 1), 'sizes': {k: len(v) for k, v in S.items()},
           'speech_head': {'features': 'KoELECTRA [CLS;mean] standardized + 0.5 x char-ngram', 'C': hs['C'], 'T': hs['T']},
           'action_head': {'features': 'char 1-3gram hashed 2048 (lexical, not deep semantic)', 'C': ha['C'], 'T': ha['T']},
           'threshold_selection_on_calib': cal, 'threshold': thr,
           'locked_sha256': lk_sha, 'locked_freeze': frz}
    for name in ('ca', 'lk'):
        rows = S[name]; ps, pa = P[name]
        ys = np.array([SPEECH.index(r['speech']) for r in rows]); ya = np.array([ACTION.index(r['action']) for r in rows])
        rep[{'ca': 'calib', 'lk': 'locked_frames'}[name]] = {
            'n': len(rows), 'speech_acc': round(float((ps.argmax(1) == ys).mean()), 3), 'speech_macro_f1': round(float(f1_score(ys, ps.argmax(1), average='macro')), 3),
            'speech_ece': round(ece(ps, ys), 3), 'action_acc': round(float((pa.argmax(1) == ya).mean()), 3),
            'action_macro_f1': round(float(f1_score(ya, pa.argmax(1), average='macro')), 3), 'action_ece': round(ece(pa, ya), 3),
            'speech_confusion': {'labels': SPEECH, 'matrix': confusion_matrix(ys, ps.argmax(1), labels=range(len(SPEECH))).tolist()}}
    for name, key in (('dev', 'dev_handwritten_v1_SEEN'), ('hw', 'locked_handwritten_v2')):
        if name not in S: rep[key] = 'NOT_SCORED_IN_DEV_RUN'; continue
        rows = S[name]; ps, pa = P[name]
        acts, per = run_set(rows, ps, pa, ha, thr)
        r2 = {k: score(rows, v) for k, v in acts.items()}; r2['B3_real_zoro'] = 'NOT_RUN'; r2['B4_rag_anomaly'] = 'NOT_IMPLEMENTED'
        sg = [r['speech'] if r['speech'] in SPEECH else 'INFORMATION' for r in rows]
        r2['speech_acc'] = round(float(np.mean([SPEECH[int(p.argmax())] == g for p, g in zip(ps, sg)])), 3)
        r2['action_acc'] = round(float(np.mean([ACTION[int(p.argmax())] == r['action'] for p, r in zip(pa, rows)])), 3)
        r2['per_item'] = per; rep[key] = r2
    heads = {'schema': 'dmsg-nlp-heads/2', 'max_len': MAX_LEN, 'pooling': 'concat(cls, mean)', 'threshold': thr,
             'ngram': {'buckets': NGRAM_BUCKETS, 'n': list(NGRAM_N), 'hash': 'crc32-ieee(utf8) mod buckets', 'prep': "' ' + lower(remove_whitespace(text)) + ' '",
                       'value': 'log1p(count)', 'speech_weight': NGRAM_W_SPEECH},
             'mu': mu.round(6).tolist(), 'sd': sd.round(6).tolist(),
             'speech': {'classes': SPEECH, 'features': 'electra512+ngram', 'W': hs['W'].round(6).tolist(), 'b': hs['b'].round(6).tolist(), 'T': hs['T']},
             'action': {'classes': ACTION, 'features': 'ngram', 'W': ha['W'].round(6).tolist(), 'b': ha['b'].round(6).tolist(), 'T': ha['T']},
             'provenance': {'encoder': 'monologg/koelectra-small-v3-discriminator (as claimed by npm kakaotalk-chat-analyzer-models@0.2.1; not attested)',
                            'encoder_weights_sha256': hashlib.sha256(Path(a.bin).read_bytes()).hexdigest(),
                            'train_sha256': hashlib.sha256((Path(a.data) / 'train.jsonl').read_bytes()).hexdigest(),
                            'data': ['3i4k (warnikchow/3i4k, CC BY-SA 4.0) commands/rhetorical commands/statements',
                                     'author-generated synthetic domain sentences (tools/nlp/make_dataset.py)'],
                            'license': 'Head weights: CC BY-SA 4.0 (trained in part on 3i4k). Encoder: Apache-2.0 (KoELECTRA).'}}
    (out / 'dmsg_nlp_heads.json').write_text(json.dumps(heads, separators=(',', ':')), 'utf8')
    (out / 'nlp_eval_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), 'utf8')
    summ = {k: v for k, v in rep.items() if k not in ('dev_handwritten_v1_SEEN', 'locked_handwritten_v2', 'locked_freeze')}
    for k in ('dev_handwritten_v1_SEEN', 'locked_handwritten_v2'):
        if not isinstance(rep[k], dict): summ[k] = rep[k]; continue
        summ[k] = {m: (v if not isinstance(v, dict) else {x: v[x] for x in ('expected_action_rate', 'risky_intervention_recall', 'benign_false_alarm_rate', 'abstain_rate')})
                   for m, v in rep[k].items() if m != 'per_item'}
    for k in ('calib', 'locked_frames'): summ[k].pop('speech_confusion', None)
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
