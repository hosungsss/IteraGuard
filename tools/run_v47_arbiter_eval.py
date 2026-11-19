"""v4.7 arbiter evaluation: rule vs on-device NLP with the v4.6 advisory vs the same NLP with DRA.

The protocol (sets, hashes, metrics, DRA source hash) is written before any engine runs.
All four sets were visible to the author before this run; none is an independent test.
usage: python tools/run_v47_arbiter_eval.py
"""
from __future__ import annotations
import datetime, hashlib, inspect, json, os, subprocess, sys
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dmsg')); sys.path.insert(0, str(ROOT / 'tools' / 'nlp'))
from prototype import model_bridge as mb  # noqa: E402

SETS = {'V2_48': ROOT / 'tools/nlp/locked_handwritten_v2.jsonl', 'TEAM_AI25': ROOT / 'tools/nlp/locked_team_ai25.jsonl',
        'W49': ROOT / 'tools/nlp/locked_v46_multitask.jsonl', 'C32_V47': ROOT / 'evaluation/v47_challenge/locked.jsonl'}
EVD = ROOT / 'internal/evidence/v47'
STRONG = {'CAUTION', 'PAUSE_AND_VERIFY'}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dra_hash():
    src = inspect.getsource(mb.decision_relevant_advisory) + repr(mb.DRA_COSTS) + repr((mb.DRA_UNGROUNDED_DISCOUNT, mb.DRA_IMPERATIVE_BOOST, mb.DRA_WARNING_BOOST))
    return hashlib.sha256(src.encode()).hexdigest()


def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def metrics(rows, outs):
    o = {x['id']: x['action'] for x in outs}
    risky = [r for r in rows if r['risky']]; benign = [r for r in rows if not r['risky']]
    def cnt(rs, f): return sum(1 for r in rs if f(o[r['id']], r))
    m = {'n': len(rows), 'expected_match': cnt(rows, lambda a, r: a in r['expect']),
         'abstain': cnt(rows, lambda a, r: a == 'ASK_HUMAN'),
         'risky_n': len(risky), 'risky_intervened': cnt(risky, lambda a, r: a in STRONG),
         'risky_cleared': cnt(risky, lambda a, r: a == 'NO_STRONG_SIGNAL'),
         'pause_expected_n': sum(1 for r in rows if r['expect'] == ['PAUSE_AND_VERIFY']),
         'pause_expected_hit': cnt(rows, lambda a, r: r['expect'] == ['PAUSE_AND_VERIFY'] and a == 'PAUSE_AND_VERIFY'),
         'benign_n': len(benign), 'benign_abstain': cnt(benign, lambda a, r: a == 'ASK_HUMAN'),
         'benign_pause': cnt(benign, lambda a, r: a == 'PAUSE_AND_VERIFY'),
         'benign_any_intervention': cnt(benign, lambda a, r: a in STRONG and a not in r['expect'])}
    return m


def run_nlp(path, arbiter):
    env = dict(os.environ, DMSG_ARBITER=arbiter)
    p = subprocess.run(['node', str(ROOT / 'tools/nlp/run_nlp_batch.js'), str(path)], capture_output=True, text=True, env=env, timeout=1800)
    if p.returncode: raise SystemExit(p.stderr[-800:])
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]


def run_rule(rows):
    from train_heads import policy_rule
    return [{'id': r['id'], 'action': policy_rule(r['text']) if r['text'].strip() else 'ASK_HUMAN'} for r in rows]


def main():
    EVD.mkdir(parents=True, exist_ok=True)
    proto = {'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'sets': {k: {'path': str(v.relative_to(ROOT)), 'sha256': sha(v)} for k, v in SETS.items()},
             'engines': ['rule', 'nlp_v46_advisory', 'nlp_dra'], 'dra_source_sha256': dra_hash(), 'dra_costs': {k: list(v) for k, v in mb.DRA_COSTS.items()},
             'primary': 'risky_cleared must not increase (safety); then abstain and benign_abstain', 'paired_test': 'exact McNemar on expected_match, v46 vs dra, pooled',
             'independence': 'NONE of the sets is independent: V2/W49/AI25 seen during v4.6, C32 written by the same AI after reading team reports'}
    body = json.dumps(proto, ensure_ascii=False, indent=1, sort_keys=True)
    (EVD / 'v47_arbiter_eval.protocol.json').write_text(body)
    res = {'protocol_sha256': hashlib.sha256(body.encode()).hexdigest(), 'protocol': proto, 'sets': {}}
    pooled_b = pooled_c = 0
    for name, path in SETS.items():
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        outs = {'rule': run_rule(rows), 'nlp_v46_advisory': run_nlp(path, 'v46'), 'nlp_dra': run_nlp(path, 'dra')}
        ok = {e: {x['id']: x['action'] in next(r for r in rows if r['id'] == x['id'])['expect'] for x in o} for e, o in outs.items()}
        b = sum(1 for i in ok['nlp_v46_advisory'] if ok['nlp_v46_advisory'][i] and not ok['nlp_dra'][i])
        c = sum(1 for i in ok['nlp_v46_advisory'] if not ok['nlp_v46_advisory'][i] and ok['nlp_dra'][i])
        pooled_b += b; pooled_c += c
        res['sets'][name] = {'metrics': {e: metrics(rows, o) for e, o in outs.items()},
                             'v46_vs_dra': {'v46_only_right': b, 'dra_only_right': c, 'mcnemar_exact_p': round(mcnemar(b, c), 4)},
                             'items': [{'id': r['id'], 'expect': r['expect'], 'risky': r['risky'], **{e: next(x for x in outs[e] if x['id'] == r['id'])['action'] for e in outs},
                                        'dra_reason': next(x for x in outs['nlp_dra'] if x['id'] == r['id']).get('reason')} for r in rows]}
    res['pooled_v46_vs_dra'] = {'v46_only_right': pooled_b, 'dra_only_right': pooled_c, 'mcnemar_exact_p': round(mcnemar(pooled_b, pooled_c), 4)}
    (EVD / 'v47_arbiter_eval.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for name, s in res['sets'].items():
        print(name, json.dumps(s['metrics'], ensure_ascii=False)); print('  ', s['v46_vs_dra'])
    print('POOLED', res['pooled_v46_vs_dra'])


if __name__ == '__main__':
    main()
