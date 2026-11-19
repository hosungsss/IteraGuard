"""v4.6 multi-task fine-tuning of KoELECTRA-small-v3 (JAX, CPU) + export to the shipped int8 format.

Architecture
  frozen layers 0..(12-K-1)  ->  trainable top-K encoder layers  ->  pooled [CLS; masked mean] (512)
  -> per-task linear heads (optionally fused with hashed char n-grams, see --ngram):
       speech (softmax 5) | intent (softmax 7) | requested action (softmax 8) | topic (softmax 7, v4.5-compatible)
       indicators (9 independent sigmoids; multi-label)
  Missing labels are masked out of the loss (v4.5 rows have speech/topic only).
Loss: class-weighted CE (weights = 1/sqrt(freq), normalised) + positive-weighted BCE for indicators.
Calibration on the calib split: one temperature per softmax head, one per indicator; indicator decision
thresholds chosen on calib (max F1, clipped to [0.05, 0.95]). Model selection: best epoch on calib.

Usage:
  python tools/nlp/finetune_v46.py --onnx enc_fp32.onnx --tok tokenizer.json --v46 <dir with v46_*.jsonl>
     --v45 <dir with train/calib.jsonl> --out <dir> --top-k 4 [--ngram] [--epochs 3] [--seed 46]
Writes: <out>/weights_int8.bin (DMSGNLP1), <out>/heads.json (dmsg-nlp-heads/3), <out>/train_log.json
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import electra_ref as R  # noqa: E402
from train_heads import ngram_vec, NGRAM_BUCKETS  # noqa: E402

TASKS = {
    'speech': ['DIRECT_REQUEST', 'INDIRECT_REQUEST', 'INFORMATIONAL', 'WARNING_OR_NEGATION', 'QUOTATION_OR_REPORT'],
    'intent': ['ORDINARY_INFORMATION', 'LEGITIMATE_REQUEST', 'COMMERCIAL_PROMOTION', 'CONTACT_SOLICITATION',
               'PAYMENT_SOLICITATION', 'CREDENTIAL_SOLICITATION', 'IMPERSONATION_CLAIM'],
    'req_action': ['MONEY_TRANSFER', 'CREDENTIAL_DISCLOSURE', 'PERSONAL_DATA_DISCLOSURE', 'INSTALL_APPLICATION', 'CLICK_LINK',
                   'MOVE_TO_EXTERNAL_MESSENGER', 'CONTACT_UNKNOWN_PERSON', 'NO_EXPLICIT_ACTION'],
    'topic': ['transfer', 'otp', 'remote_install', 'personal_data', 'link', 'secrecy', 'none'],
}
INDICATORS = ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE', 'FINANCIAL_INDUCEMENT', 'CREDENTIAL_REQUEST',
              'ACCOUNT_CHANGE_REQUEST', 'IMPERSONATION_SIGNAL', 'MALICIOUS_LINK_SUSPICION', 'UNWANTED_SOLICITATION']
V45_SPEECH = {'DIRECT_REQUEST': 'DIRECT_REQUEST', 'INDIRECT_REQUEST': 'INDIRECT_REQUEST', 'WARNING': 'WARNING_OR_NEGATION',
              'QUOTATION': 'QUOTATION_OR_REPORT', 'INFORMATION': 'INFORMATIONAL'}
MAX_LEN = 128
BUCKETS = (16, 24, 32, 48, 64, 96, 128)


def load_rows(v46_dir, v45_dir, split):
    rows = [json.loads(l) for l in (Path(v46_dir) / f'v46_{split}.jsonl').read_text('utf8').splitlines() if l.strip()]
    v45f = Path(v45_dir) / f'{split}.jsonl'
    if split in ('train', 'calib') and v45f.is_file():
        for l in v45f.read_text('utf8').splitlines():
            if not l.strip(): continue
            r = json.loads(l)
            x = {'text': r['text'], 'speech': V45_SPEECH[r['speech']], 'topic': r['action'], 'intent': None, 'indicators': None,
                 'req_action': None, 'source': r['source'], 'family': 'v45:' + r.get('family', '')}
            if r['source'].startswith('3i4k'):          # everyday sentences: no risk indicator, no risky requested action
                x['indicators'] = []; x['req_action'] = 'NO_EXPLICIT_ACTION'
            rows.append(x)
    return rows


def encode(tok, texts):
    out = []
    for t in texts:
        ids = tok.encode(t if t.strip() else '.').ids[:MAX_LEN - 1]
        out.append(ids if ids[-1] == 3 else ids + [3])
    return out


def bucket(n):
    for b in BUCKETS:
        if n <= b: return b
    return MAX_LEN


def label_arrays(rows):
    Y = {}
    for t, cls in TASKS.items():
        Y[t] = np.array([cls.index(r[t]) if r.get(t) is not None else -1 for r in rows], np.int32)
    ind = np.zeros((len(rows), len(INDICATORS)), np.float32); m = np.zeros(len(rows), np.float32)
    for i, r in enumerate(rows):
        if r.get('indicators') is not None:
            m[i] = 1
            for k in r['indicators']: ind[i, INDICATORS.index(k)] = 1
    Y['indicators'] = ind; Y['ind_mask'] = m
    return Y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--onnx', required=True); ap.add_argument('--tok', required=True)
    ap.add_argument('--v46', required=True); ap.add_argument('--v45', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--top-k', type=int, default=4); ap.add_argument('--ngram', action='store_true')
    ap.add_argument('--epochs', type=int, default=3); ap.add_argument('--seed', type=int, default=46)
    ap.add_argument('--lr-enc', type=float, default=5e-5); ap.add_argument('--lr-head', type=float, default=2e-3)
    ap.add_argument('--batch', type=int, default=32)
    a = ap.parse_args()
    import jax, jax.numpy as jnp, optax
    from tokenizers import Tokenizer
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    tok = Tokenizer.from_file(a.tok)
    W = R.load_onnx_weights(a.onnx)                      # fp32 original (ONNX initialisers)
    K = a.top_k; FROZEN = R.LAYERS - K
    tr, ca = load_rows(a.v46, a.v45, 'train'), load_rows(a.v46, a.v45, 'calib')
    log = {'args': vars(a), 'sizes': {'train': len(tr), 'calib': len(ca)}, 'epochs': []}

    # ---------------- JAX model ----------------
    H, NH, DH = R.H, R.HEADS, R.H // R.HEADS
    def ln(x, g, b): mu = x.mean(-1, keepdims=True); v = ((x - mu) ** 2).mean(-1, keepdims=True); return (x - mu) / jnp.sqrt(v + R.EPS) * g + b
    def layer(p, x, mask):  # x [B,L,H], mask [B,L]
        B, L, _ = x.shape
        q = (x @ p['q_w'] + p['q_b']).reshape(B, L, NH, DH); k = (x @ p['k_w'] + p['k_b']).reshape(B, L, NH, DH); v = (x @ p['v_w'] + p['v_b']).reshape(B, L, NH, DH)
        s = jnp.einsum('blhd,bmhd->bhlm', q, k) / math.sqrt(DH) + (1.0 - mask[:, None, None, :]) * -1e9
        c = jnp.einsum('bhlm,bmhd->blhd', jax.nn.softmax(s, -1), v).reshape(B, L, H)
        x = ln(c @ p['o_w'] + p['o_b'] + x, p['ln1_g'], p['ln1_b'])
        f = jax.nn.gelu(x @ p['f1_w'] + p['f1_b'], approximate=False) @ p['f2_w'] + p['f2_b']
        return ln(f + x, p['ln2_g'], p['ln2_b'])
    def lp(i):
        g = lambda n: jnp.asarray(W[f'encoder.layer.{i}.{n}'])
        return {'q_w': g('attention.self.query.weight'), 'q_b': g('attention.self.query.bias'), 'k_w': g('attention.self.key.weight'), 'k_b': g('attention.self.key.bias'),
                'v_w': g('attention.self.value.weight'), 'v_b': g('attention.self.value.bias'), 'o_w': g('attention.output.dense.weight'), 'o_b': g('attention.output.dense.bias'),
                'ln1_g': g('attention.output.LayerNorm.weight'), 'ln1_b': g('attention.output.LayerNorm.bias'), 'f1_w': g('intermediate.dense.weight'), 'f1_b': g('intermediate.dense.bias'),
                'f2_w': g('output.dense.weight'), 'f2_b': g('output.dense.bias'), 'ln2_g': g('output.LayerNorm.weight'), 'ln2_b': g('output.LayerNorm.bias')}
    emb = {k: jnp.asarray(W[k]) for k in ('embeddings.word_embeddings.weight', 'embeddings.position_embeddings.weight', 'embeddings.token_type_embeddings.weight',
                                          'embeddings.LayerNorm.weight', 'embeddings.LayerNorm.bias', 'embeddings_project.weight', 'embeddings_project.bias')}
    frozen_layers = [lp(i) for i in range(FROZEN)]

    @jax.jit
    def bottom(ids, mask):
        L = ids.shape[1]
        x = emb['embeddings.word_embeddings.weight'][ids] + emb['embeddings.position_embeddings.weight'][:L][None] + emb['embeddings.token_type_embeddings.weight'][0]
        x = ln(x, emb['embeddings.LayerNorm.weight'], emb['embeddings.LayerNorm.bias']) @ emb['embeddings_project.weight'] + emb['embeddings_project.bias']
        for p in frozen_layers: x = layer(p, x, mask)
        return x

    def batches(rows, ids, order, bs):
        # length-bucketed batches; returns list of index arrays
        by = {}
        for i in order: by.setdefault(bucket(len(ids[i])), []).append(i)
        out = []
        for b, idx in by.items():
            for j in range(0, len(idx), bs): out.append((b, np.array(idx[j:j + bs])))
        return out

    def pack(ids, idx, L):
        X = np.zeros((len(idx), L), np.int32); M = np.zeros((len(idx), L), np.float32)
        for r, i in enumerate(idx): n = len(ids[i]); X[r, :n] = ids[i]; M[r, :n] = 1
        return X, M

    def cache(rows):
        ids = encode(tok, [r['text'] for r in rows]); hid = [None] * len(rows)
        for L, idx in batches(rows, ids, range(len(rows)), 64):
            X, M = pack(ids, idx, L); h = np.asarray(bottom(X, M))
            for r, i in enumerate(idx): hid[i] = h[r, :len(ids[i])]
        return ids, hid

    t0 = time.time()
    tr_ids, tr_h = cache(tr); ca_ids, ca_h = cache(ca)
    log['cache_seconds'] = round(time.time() - t0, 1)
    G_tr = np.stack([ngram_vec(r['text']) for r in tr]) if a.ngram else None
    G_ca = np.stack([ngram_vec(r['text']) for r in ca]) if a.ngram else None
    Ytr, Yca = label_arrays(tr), label_arrays(ca)

    # ---------------- trainable params ----------------
    key = jax.random.PRNGKey(a.seed)
    feat = 512 + (NGRAM_BUCKETS if a.ngram else 0)
    heads = {}
    for t, cls in list(TASKS.items()) + [('indicators', INDICATORS)]:
        key, k1 = jax.random.split(key)
        heads[t] = {'W': jax.random.normal(k1, (feat, len(cls))) * 0.02, 'b': jnp.zeros(len(cls))}
    params = {'top': [lp(i) for i in range(FROZEN, R.LAYERS)], 'heads': heads}
    cw = {}
    for t, cls in TASKS.items():
        y = Ytr[t][Ytr[t] >= 0]; c = np.bincount(y, minlength=len(cls)).astype(np.float64) + 1
        w = 1 / np.sqrt(c); cw[t] = jnp.asarray(w / (w * c).sum() * c.sum(), jnp.float32)
    pos = Ytr['indicators'][Ytr['ind_mask'] > 0].mean(0)
    posw = jnp.asarray(np.clip((1 - pos) / np.maximum(pos, 1e-3), 1, 20) ** 0.5, jnp.float32)

    def forward(params, h, mask, g):
        x = h
        for p in params['top']: x = layer(p, x, mask)
        cls = x[:, 0]; mean = (x * mask[..., None]).sum(1) / mask.sum(1, keepdims=True)
        f = jnp.concatenate([cls, mean], -1)
        if g is not None: f = jnp.concatenate([f, g * 0.5], -1)
        return {t: f @ hp['W'] + hp['b'] for t, hp in params['heads'].items()}, f

    def loss_fn(params, h, mask, g, y):
        logits, _ = forward(params, h, mask, g); tot = 0.0
        for t in TASKS:
            yy = y[t]; valid = (yy >= 0).astype(jnp.float32); yc = jnp.maximum(yy, 0)
            lsm = jax.nn.log_softmax(logits[t], -1); nll = -jnp.take_along_axis(lsm, yc[:, None], 1)[:, 0] * cw[t][yc]
            tot = tot + (nll * valid).sum() / jnp.maximum(valid.sum(), 1.0)
        z = logits['indicators']; yi = y['indicators']; m = y['ind_mask'][:, None]
        bce = posw * yi * jax.nn.softplus(-z) + (1 - yi) * jax.nn.softplus(z)
        tot = tot + (bce * m).sum() / jnp.maximum(m.sum() * len(INDICATORS), 1.0) * 3.0
        return tot

    steps_per_epoch = math.ceil(len(tr) / a.batch) + len(BUCKETS)
    total = steps_per_epoch * a.epochs
    sched = lambda base: optax.warmup_cosine_decay_schedule(0.0, base, max(1, total // 20), total, base * 0.05)
    label = lambda p: jax.tree_util.tree_map_with_path(lambda path, _: 'top' if str(path[0]).find('top') >= 0 else 'heads', p)
    opt = optax.multi_transform({'top': optax.adamw(sched(a.lr_enc), weight_decay=0.01), 'heads': optax.adamw(sched(a.lr_head), weight_decay=1e-4)}, label(params))
    if K == 0: opt = optax.multi_transform({'top': optax.set_to_zero(), 'heads': optax.adamw(sched(a.lr_head), weight_decay=1e-4)}, label(params))
    state = opt.init(params)

    @jax.jit
    def step(params, state, h, mask, g, y):
        l, gr = jax.value_and_grad(loss_fn)(params, h, mask, g, y)
        upd, state = opt.update(gr, state, params); return optax.apply_updates(params, upd), state, l

    infer = jax.jit(lambda params, h, mask, g: forward(params, h, mask, g)[0])

    def run_logits(params, ids, hid, G):
        outs = {t: np.zeros((len(ids), len(c)), np.float32) for t, c in list(TASKS.items()) + [('indicators', INDICATORS)]}
        for L, idx in batches(None, ids, range(len(ids)), 64):
            Hh = np.zeros((len(idx), L, H), np.float32); M = np.zeros((len(idx), L), np.float32)
            for r, i in enumerate(idx): n = len(ids[i]); Hh[r, :n] = hid[i]; M[r, :n] = 1
            lo = infer(params, Hh, M, None if G is None else G[idx])
            for t in outs: outs[t][idx] = np.asarray(lo[t])
        return outs

    def calib_score(lo, Y):
        from sklearn.metrics import f1_score
        s = {}
        for t in TASKS:
            v = Y[t] >= 0
            if v.any(): s[t] = f1_score(Y[t][v], lo[t][v].argmax(1), average='macro')
        m = Y['ind_mask'] > 0
        s['indicators'] = f1_score(Y['indicators'][m], (lo['indicators'][m] > 0).astype(int), average='micro', zero_division=0)
        s['mean'] = float(np.mean(list(s.values())))
        return {k: round(float(v), 4) for k, v in s.items()}

    best = None
    for ep in range(a.epochs):
        t1 = time.time(); order = rng.permutation(len(tr)); losses = []
        for L, idx in batches(tr, tr_ids, order, a.batch):
            Hh = np.zeros((len(idx), L, H), np.float32); M = np.zeros((len(idx), L), np.float32)
            for r, i in enumerate(idx): n = len(tr_ids[i]); Hh[r, :n] = tr_h[i]; M[r, :n] = 1
            y = {t: Ytr[t][idx] for t in TASKS}; y['indicators'] = Ytr['indicators'][idx]; y['ind_mask'] = Ytr['ind_mask'][idx]
            params, state, l = step(params, state, Hh, M, None if G_tr is None else G_tr[idx], y); losses.append(float(l))
        sc = calib_score(run_logits(params, ca_ids, ca_h, G_ca), Yca)
        log['epochs'].append({'epoch': ep + 1, 'loss': round(float(np.mean(losses)), 4), 'calib': sc, 'seconds': round(time.time() - t1, 1)})
        print(json.dumps(log['epochs'][-1]), flush=True)
        if best is None or sc['mean'] > best[0]:
            best = (sc['mean'], ep + 1, jax.tree_util.tree_map(np.asarray, params))
    params = best[2]; log['selected_epoch'] = best[1]

    # ---------------- calibration ----------------
    lo = run_logits(params, ca_ids, ca_h, G_ca)
    temps = np.exp(np.linspace(np.log(0.3), np.log(5), 60)); cal = {}
    for t in TASKS:
        v = Yca[t] >= 0; z = lo[t][v]; yy = Yca[t][v]
        nll = lambda T: -np.mean(np.log(np.exp(z / T - (z / T).max(1, keepdims=True))[np.arange(len(yy)), yy] / np.exp(z / T - (z / T).max(1, keepdims=True)).sum(1) + 1e-12))
        cal[t] = float(min(temps, key=nll))
    m = Yca['ind_mask'] > 0; z = lo['indicators'][m]; yi = Yca['indicators'][m]
    sig = lambda x: 1 / (1 + np.exp(-x))
    ind_T, ind_thr = [], []
    for j in range(len(INDICATORS)):
        bce = lambda T: -np.mean(yi[:, j] * np.log(sig(z[:, j] / T) + 1e-9) + (1 - yi[:, j]) * np.log(1 - sig(z[:, j] / T) + 1e-9))
        T = float(min(temps, key=bce)); p = sig(z[:, j] / T); ind_T.append(T)
        best_t, best_f = 0.5, -1
        for th in np.linspace(0.05, 0.95, 19):
            pr = p >= th; tp = (pr & (yi[:, j] > 0)).sum(); f = 2 * tp / max(1, pr.sum() + (yi[:, j] > 0).sum())
            if yi[:, j].sum() > 0 and f > best_f: best_f, best_t = f, float(round(th, 2))
        ind_thr.append(best_t)
    log['calibration'] = {'softmax_T': cal, 'indicator_T': dict(zip(INDICATORS, ind_T)), 'indicator_threshold': dict(zip(INDICATORS, ind_thr))}

    # ---------------- export: int8 encoder (same container as v4.5) + heads ----------------
    W2 = dict(W)
    names = {'q_w': 'attention.self.query.weight', 'q_b': 'attention.self.query.bias', 'k_w': 'attention.self.key.weight', 'k_b': 'attention.self.key.bias',
             'v_w': 'attention.self.value.weight', 'v_b': 'attention.self.value.bias', 'o_w': 'attention.output.dense.weight', 'o_b': 'attention.output.dense.bias',
             'ln1_g': 'attention.output.LayerNorm.weight', 'ln1_b': 'attention.output.LayerNorm.bias', 'f1_w': 'intermediate.dense.weight', 'f1_b': 'intermediate.dense.bias',
             'f2_w': 'output.dense.weight', 'f2_b': 'output.dense.bias', 'ln2_g': 'output.LayerNorm.weight', 'ln2_b': 'output.LayerNorm.bias'}
    for j, p in enumerate(params['top']):
        i = FROZEN + j
        for k, n in names.items(): W2[f'encoder.layer.{i}.{n}'] = np.asarray(p[k], np.float32)
    np.savez_compressed(out / 'encoder_fp32.npz', **W2)
    info = R.write_bin(R.quantize(W2), out / 'weights_int8.bin')
    hj = {'schema': 'dmsg-nlp-heads/3', 'max_len': MAX_LEN, 'pooling': 'concat(cls, masked mean)', 'encoder_trainable_top_layers': K,
          'ngram': ({'buckets': NGRAM_BUCKETS, 'n': [1, 2, 3], 'hash': 'crc32-ieee(utf8) mod buckets', 'prep': "' ' + lower(remove_whitespace(text)) + ' '",
                     'value': 'log1p(count)', 'fusion_weight': 0.5} if a.ngram else None),
          'tasks': {t: {'type': 'softmax', 'classes': c, 'W': np.asarray(params['heads'][t]['W']).T.round(6).tolist(),
                        'b': np.asarray(params['heads'][t]['b']).round(6).tolist(), 'T': cal[t]} for t, c in TASKS.items()},
          'indicators': {'type': 'sigmoid', 'classes': INDICATORS, 'W': np.asarray(params['heads']['indicators']['W']).T.round(6).tolist(),
                         'b': np.asarray(params['heads']['indicators']['b']).round(6).tolist(), 'T': ind_T, 'threshold': ind_thr},
          'provenance': {'encoder_init': 'ONNX fp32 initialisers of monologg/koelectra-small-v3-discriminator as shipped in npm kakaotalk-chat-analyzer-models@0.2.1 (not byte-verified against Hugging Face)',
                         'encoder_init_sha256': hashlib.sha256(Path(a.onnx).read_bytes()).hexdigest(),
                         'weights_int8_sha256': hashlib.sha256((out / 'weights_int8.bin').read_bytes()).hexdigest(),
                         'train_data': ['tools/nlp/make_dataset_v46.py (author synthetic, decontaminated vs locked sets)', 'tools/nlp/data (v4.5 authored synthetic + 3i4k CC BY-SA 4.0)'],
                         'license': 'Encoder Apache-2.0 (KoELECTRA); fine-tuned weights and heads trained in part on 3i4k -> CC BY-SA 4.0'}}
    (out / 'heads.json').write_text(json.dumps(hj, separators=(',', ':')), 'utf8')
    log['export'] = info; log['train_seconds_total'] = round(sum(e['seconds'] for e in log['epochs']), 1)
    (out / 'train_log.json').write_text(json.dumps(log, indent=1), 'utf8')
    print(json.dumps({'selected_epoch': best[1], 'calib': log['epochs'][best[1] - 1]['calib'], 'export': info}))


if __name__ == '__main__':
    main()
