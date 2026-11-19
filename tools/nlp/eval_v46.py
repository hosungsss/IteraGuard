"""v4.5 vs v4.6 evaluation on identical sets and an identical policy pipeline (nlp_v46.analyze).

Sets
  W  tools/nlp/locked_v46_multitask.jsonl  (49, hand-written, frozen before any v4.6 run; author-made)
  V2 tools/nlp/locked_handwritten_v2.jsonl (48, v4.5 final locked set; policy regression)
  G  generated v4.6 locked families        (author synthetic, held-out templates)
  F  v4.5 locked frames                    (speech/topic only)
Usage:
  python tools/nlp/eval_v46.py --onnx enc_fp32.onnx --tok tokenizer.json --system NAME=<bin>,<heads.json> [...]
     --gen <v46_locked.jsonl> --frames <v45 locked.jsonl> --out report.json [--sets W,V2,G,F] [--ablations NAME]
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nlp_v46 as N  # noqa: E402
from train_heads import score, wilson  # noqa: E402

V45S = {'WARNING': 'WARNING_OR_NEGATION', 'QUOTATION': 'QUOTATION_OR_REPORT', 'INFORMATION': 'INFORMATIONAL', 'REPORT': 'QUOTATION_OR_REPORT'}


def load(p): return [json.loads(l) for l in Path(p).read_text('utf8').splitlines() if l.strip()]


def check_frozen(p):
    p = Path(p); frz = json.loads(p.with_suffix('.freeze.json').read_text('utf8'))
    if hashlib.sha256(p.read_bytes()).hexdigest() != frz['sha256']: raise SystemExit('LOCKED_SET_HASH_MISMATCH ' + p.name)
    return frz['sha256']


def ece(conf, correct, bins=10):
    e = 0.0
    for lo in np.linspace(0, 1, bins, endpoint=False):
        m = (conf > lo) & (conf <= lo + 1 / bins)
        if m.any(): e += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(e)


def task_metrics(rows, outs, task, gold_key=None, gold_map=None):
    from sklearn.metrics import f1_score, precision_recall_fscore_support, confusion_matrix
    gk = gold_key or task; pairs = []
    for r, o in zip(rows, outs):
        if task not in o or r.get(gk) is None: continue
        g = r[gk]; g = gold_map.get(g, g) if gold_map else g
        pairs.append((g, o[task]))
    if not pairs: return 'NOT_AVAILABLE'
    cls = sorted(set(pairs[0][1]))
    gold = [g for g, _ in pairs]; pred = [max(p, key=p.get) for _, p in pairs]
    labels = sorted(set(gold) | set(pred))
    P, Rr, F, S = precision_recall_fscore_support(gold, pred, labels=labels, zero_division=0)
    conf = np.array([max(p.values()) for _, p in pairs]); corr = np.array([a == b for a, b in zip(gold, pred)], float)
    brier = float(np.mean([sum((p.get(c, 0) - (1.0 if c == g else 0.0)) ** 2 for c in set(p) | {g}) for g, p in pairs]))
    return {'n': len(pairs), 'accuracy': round(float(corr.mean()), 3), 'acc_ci95': wilson(int(corr.sum()), len(pairs)),
            'macro_f1': round(float(f1_score(gold, pred, labels=labels, average='macro', zero_division=0)), 3),
            'per_class': {l: {'p': round(float(a), 3), 'r': round(float(b), 3), 'f1': round(float(c), 3), 'n': int(d)} for l, a, b, c, d in zip(labels, P, Rr, F, S)},
            'ece': round(ece(conf, corr), 3), 'brier': round(brier, 3),
            'confusion': {'labels': labels, 'matrix': confusion_matrix(gold, pred, labels=labels).tolist()}}


def indicator_metrics(rows, outs, thresholds):
    from sklearn.metrics import average_precision_score, f1_score
    idx = [i for i, (r, o) in enumerate(zip(rows, outs)) if 'indicators' in o and r.get('indicators') is not None]
    if not idx: return 'NOT_AVAILABLE'
    labs = list(outs[idx[0]]['indicators'])
    Y = np.array([[1 if l in rows[i]['indicators'] else 0 for l in labs] for i in idx]); S = np.array([[outs[i]['indicators'][l] for l in labs] for i in idx])
    Pd = np.array([[outs[i]['indicators'][l] >= thresholds[l] for l in labs] for i in idx]).astype(int)
    per = {}
    for j, l in enumerate(labs):
        per[l] = {'support': int(Y[:, j].sum()), 'pr_auc': round(float(average_precision_score(Y[:, j], S[:, j])), 3) if Y[:, j].sum() else None,
                  'f1_at_threshold': round(float(f1_score(Y[:, j], Pd[:, j], zero_division=0)), 3)}
    none_gold = (Y.sum(1) == 0); none_pred = (Pd.sum(1) == 0)
    return {'n': len(idx), 'micro_pr_auc': round(float(average_precision_score(Y.ravel(), S.ravel())), 3), 'micro_f1': round(float(f1_score(Y.ravel(), Pd.ravel(), zero_division=0)), 3),
            'macro_f1': round(float(np.mean([v['f1_at_threshold'] for v in per.values() if v['support']])), 3),
            'none_observed_accuracy': round(float((none_gold == none_pred).mean()), 3), 'per_label': per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--onnx', required=True); ap.add_argument('--tok', required=True); ap.add_argument('--system', action='append', required=True)
    ap.add_argument('--gen'); ap.add_argument('--frames'); ap.add_argument('--calib'); ap.add_argument('--out', required=True)
    ap.add_argument('--sets', default='W,V2,G,F'); ap.add_argument('--ablations', default='')
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tok)
    sets = {}
    if 'W' in a.sets: sets['W'] = (load(HERE / 'locked_v46_multitask.jsonl'), check_frozen(HERE / 'locked_v46_multitask.jsonl'))
    if 'V2' in a.sets: sets['V2'] = (load(HERE / 'locked_handwritten_v2.jsonl'), check_frozen(HERE / 'locked_handwritten_v2.jsonl'))
    if 'G' in a.sets and a.gen: sets['G'] = (load(a.gen), hashlib.sha256(Path(a.gen).read_bytes()).hexdigest())
    if 'D1' in a.sets: sets['D1'] = (load(HERE / 'locked_handwritten.jsonl'), 'dev (v4.5 v1, seen)')
    if 'C' in a.sets and a.calib: sets['C'] = (load(a.calib), hashlib.sha256(Path(a.calib).read_bytes()).hexdigest())
    if 'F' in a.sets and a.frames: sets['F'] = (load(a.frames), hashlib.sha256(Path(a.frames).read_bytes()).hexdigest())
    rep = {'sets': {k: {'n': len(v[0]), 'sha256': v[1]} for k, v in sets.items()}, 'systems': {}}
    for spec in a.system:
        name, rest = spec.split('=', 1); binp, hp = rest.split(',')
        if binp.endswith('.npz'): W = dict(np.load(binp))
        else: W = N.int8_weights(binp)
        sess = N.session_from_weights(a.onnx, W); heads = N.Heads(hp)
        variants = [('full', {})]
        if name in a.ablations.split(','):
            variants += [('no_indicator_layer', {'use_indicators': False}), ('no_structural_grounds', {'use_structural': False}),
                         ('no_model_spans', {'use_spans': False}), ('no_cross_task_guard', {'use_guard': False})]
        sysrep = {'weights_sha256': hashlib.sha256(Path(binp).read_bytes()).hexdigest(), 'heads_sha256': hashlib.sha256(Path(hp).read_bytes()).hexdigest(),
                  'heads_schema': heads.v}
        for sname, (rows, _) in sets.items():
            t0 = time.time(); F = N.pooled(sess, tok, [r['text'] for r in rows]); feat_s = time.time() - t0
            for vname, kw in variants:
                outs = [N.analyze(r['text'], f, heads, **kw) if r['text'].strip() else {'action': 'ASK_HUMAN', 'reason': 'EMPTY'} for r, f in zip(rows, F)]
                key = f'{sname}' + ('' if vname == 'full' else '/' + vname)
                r_ = {}
                if 'expect' in rows[0]:
                    r_['policy'] = score(rows, [o['action'] for o in outs])
                    cats = sorted({r.get('cat', '') for r in rows})
                    r_['policy_by_category'] = {c: score([r for r in rows if r.get('cat') == c], [o['action'] for r, o in zip(rows, outs) if r.get('cat') == c]) for c in cats} if sname == 'W' and vname == 'full' else None
                if vname == 'full':
                    gm = V45S if sname in ('V2', 'F', 'D1') else None
                    r_['speech'] = task_metrics(rows, outs, 'speech', gold_map=gm if sname != 'F' else {**V45S})
                    tk = 'action' if sname in ('F', 'V2', 'D1') else 'topic'
                    r_['topic'] = task_metrics(rows, outs, 'topic', gold_key=tk)
                    for t in ('intent', 'req_action'): r_[t] = task_metrics(rows, outs, t)
                    thr = dict(zip(heads.j['indicators']['classes'], heads.j['indicators']['threshold'])) if heads.v != 'dmsg-nlp-heads/2' else {}
                    r_['indicators'] = indicator_metrics(rows, outs, thr) if thr else 'NOT_AVAILABLE'
                    r_['feature_seconds'] = round(feat_s, 2)
                    r_['per_item'] = [{'id': r.get('id'), 'cat': r.get('cat'), 'expect': r.get('expect'), 'action': o['action'], 'reason': o['reason'],
                                       'uncertainty': o.get('uncertainty'), 'speech_pred': max(o['speech'], key=o['speech'].get) if 'speech' in o else None,
                                       'intent_pred': max(o['intent'], key=o['intent'].get) if 'intent' in o else None,
                                       'fired': [x['label'] for x in o.get('indicator_report', [])]} for r, o in zip(rows, outs)] if sname in ('W', 'V2', 'D1') else None
                sysrep[key] = r_
        rep['systems'][name] = sysrep
    Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), 'utf8')
    # compact console summary
    for n, s in rep['systems'].items():
        for k, v in s.items():
            if not isinstance(v, dict): continue
            line = {'sys': n, 'set': k}
            if 'policy' in v: line.update({m: v['policy'][m] for m in ('expected_action_rate', 'risky_intervention_recall', 'benign_false_alarm_rate', 'abstain_rate')})
            for t in ('speech', 'intent', 'req_action', 'topic'):
                if isinstance(v.get(t), dict): line[t + '_mF1'] = v[t]['macro_f1']
            if isinstance(v.get('indicators'), dict): line['ind_microF1'] = v['indicators']['micro_f1']; line['ind_PRAUC'] = v['indicators']['micro_pr_auc']
            print(json.dumps(line, ensure_ascii=False))


if __name__ == '__main__':
    main()
