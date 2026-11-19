"""Zoro abstention audit — replays SAVED Zoro responses offline (no GPU, no network, no new inference).

Answers the team's question from 2026-11-02: when Zoro's path said ASK_HUMAN, was it the model or our code?
For every item it reports:
  * v45/v46 advisory result and its reason (the gate that fired),
  * cause bucket: GATE_* (model's answer was usable, our rule abstained) vs MODEL_* (the model itself was unsure/split),
  * whether the model's argmax reading would have produced the expected guidance ("model right / gate blocked"),
  * what the v4.7 decision-relevant arbiter (DRA) outputs on the very same response,
  * an exact temperature sweep (p' ∝ p^(T_server/T)) so threshold/temperature sensitivity is visible without re-running Zoro.

inputs (written by tools/compare_engines.py in the team's v4.5 folder):
  --raw      internal/evidence/v45_local_compare_20261102.zoro_raw.json   (list of {id, response})
  --labels   the locked .jsonl used for that run (id, text, expect, risky)
usage:
  python tools/zoro/abstention_audit.py --raw <zoro_raw.json> --labels <locked.jsonl> --out <report.json> [--t-server 1.52]
"""
from __future__ import annotations
import argparse, collections, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dmsg'))
from prototype import model_bridge as mb  # noqa: E402
from prototype.typed_contract import ContractError, normalize_response  # noqa: E402

SWEEP = (1.0, 1.52, 2.19, 3.0)


def argmax_guidance(n):
    """Guidance implied by the model's own top choices, without any threshold or lexical gate."""
    a = n['q_action']['choice']; s = n['q_speech']['choice']
    return mb._dra_truth(mb.DRA_ACTION_CLASS[a], mb.DRA_SPEECH_CLASS[s])


def audit(raw_items, labels, t_server=1.52):
    lab = {r['id']: r for r in labels}
    rows, causes, side = [], collections.Counter(), collections.Counter()
    for it in raw_items:
        r = lab.get(it['id'])
        if r is None or not r.get('text', '').strip(): continue
        resp, text = it['response'], r['text']
        row = {'id': it['id'], 'expect': r.get('expect'), 'risky': r.get('risky'), 'response_sha256': hashlib.sha256(
            json.dumps(resp, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        try:
            n = normalize_response(resp, mb.SPEC, optional=mb.OPTIONAL_QUESTIONS)
            base = mb.advisory(text, resp)
            cause = mb.abstention_cause(text, resp)
            dra = mb.decision_relevant_advisory(text, resp)
        except ContractError as e:
            row.update(error=str(e)); rows.append(row); causes['CONTRACT_ERROR'] += 1; continue
        mg = argmax_guidance(n)
        row.update(advisory=base['action'], advisory_reason=base['reason'], cause=cause.get('cause'), cause_side=cause.get('cause_side'),
                   top_action=n['q_action']['choice'], p_action=round(n['q_action']['probabilities'][n['q_action']['choice']], 4),
                   top_speech=n['q_speech']['choice'], p_speech=round(n['q_speech']['probabilities'][n['q_speech']['choice']], 4),
                   model_argmax_guidance=mg,
                   model_argmax_matches_expect=(mg in (r.get('expect') or [])) if mg != 'UNKNOWN' else None,
                   dra=dra['action'], dra_reason=dra['reason'], dra_margin=round(dra['margin'], 4), dra_trace=dra['trace'],
                   sweep={str(t): mb.advisory(text, mb.retemper(resp, t_server, t))['action'] for t in SWEEP})
        if base['action'] == 'ASK_HUMAN':
            causes[cause['cause']] += 1; side[cause['cause_side']] += 1
            if cause['cause_side'] == 'GATE' and row['model_argmax_matches_expect']: side['GATE_AND_MODEL_ARGMAX_RIGHT'] += 1
            if cause['cause_side'] == 'GATE' and row['model_argmax_matches_expect'] is False: side['GATE_BUT_MODEL_ARGMAX_WRONG'] += 1
        rows.append(row)
    ok = [x for x in rows if 'error' not in x]
    def rate(key): return sum(1 for x in ok if x.get(key) in (x.get('expect') or [])) if ok else 0
    summary = {
        'n': len(ok), 'advisory_abstain': sum(1 for x in ok if x['advisory'] == 'ASK_HUMAN'),
        'dra_abstain': sum(1 for x in ok if x['dra'] == 'ASK_HUMAN'),
        'advisory_expected_match': rate('advisory'), 'dra_expected_match': rate('dra'),
        'model_argmax_expected_match': sum(1 for x in ok if x['model_argmax_matches_expect']),
        'risky_cleared_advisory': sum(1 for x in ok if x['risky'] and x['advisory'] == 'NO_STRONG_SIGNAL'),
        'risky_cleared_dra': sum(1 for x in ok if x['risky'] and x['dra'] == 'NO_STRONG_SIGNAL'),
        'abstain_causes': dict(causes.most_common()), 'abstain_side': dict(side),
        'temperature_sweep_abstain': {str(t): sum(1 for x in ok if x['sweep'][str(t)] == 'ASK_HUMAN') for t in SWEEP},
        'reading': 'GATE_* = the model gave a usable answer and our code abstained; MODEL_* = the model itself was unsure or split. '
                   'model_argmax_matches_expect uses the item labels, which are developer/AI authored and not independent.'}
    return {'summary': summary, 'items': rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True); ap.add_argument('--labels', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--t-server', type=float, default=1.52)
    a = ap.parse_args()
    raw = json.loads(Path(a.raw).read_text(encoding='utf8'))
    raw = raw if isinstance(raw, list) else raw.get('items', [])
    labels = [json.loads(l) for l in Path(a.labels).read_text(encoding='utf8').splitlines() if l.strip()]
    rep = audit(raw, labels, a.t_server)
    rep['inputs'] = {'raw_sha256': hashlib.sha256(Path(a.raw).read_bytes()).hexdigest(), 'labels_sha256': hashlib.sha256(Path(a.labels).read_bytes()).hexdigest(),
                     't_server': a.t_server, 'note': 'offline replay of saved responses; no model was called'}
    Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf8')
    print(json.dumps(rep['summary'], ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
