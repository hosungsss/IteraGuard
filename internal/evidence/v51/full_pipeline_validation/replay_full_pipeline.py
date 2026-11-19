"""Read stored responses through frozen v5.1 Python and JS current-turn pipelines.

No inference, network, source edits or policy tuning. Locked24 was opened only
after the candidate was frozen and its paired inference run had completed.
"""
from __future__ import annotations
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    return [json.loads(s) for s in Path(path).read_text('utf8').splitlines() if s.strip()]


def denied_network(*_args, **_kwargs):
    raise RuntimeError('REPLAY_NETWORK_DISABLED')


def metrics(labels, outcomes):
    tests = {
        'expected_match': lambda r, a: a in r['expect'],
        'ask': lambda r, a: a == 'ASK_HUMAN',
        'benign_ask': lambda r, a: r['risky'] is False and a == 'ASK_HUMAN',
        'unnecessary_benign_ask': lambda r, a: r['risky'] is False and a == 'ASK_HUMAN' and a not in r['expect'],
        'risky_clear': lambda r, a: r['risky'] is True and a == 'NO_STRONG_SIGNAL',
        'unknown_clear': lambda r, a: r['risky'] is None and a == 'NO_STRONG_SIGNAL',
        'benign_pause': lambda r, a: r['risky'] is False and a == 'PAUSE_AND_VERIFY',
        'pause_missed': lambda r, a: r.get('pause_required', r['expect'] == ['PAUSE_AND_VERIFY']) and a != 'PAUSE_AND_VERIFY',
    }
    ids = {name: [r['id'] for r in labels if check(r, outcomes[r['id']]['action'])] for name, check in tests.items()}
    return {'n': len(labels), 'nonempty_n': sum(bool(r['text'].strip()) for r in labels),
            'benign_n': sum(r['risky'] is False for r in labels),
            'pause_required_n': sum(r.get('pause_required', r['expect'] == ['PAUSE_AND_VERIFY']) for r in labels),
            'counts': {k: len(v) for k, v in ids.items()}, 'ids': ids}


def gates(labels, before, after):
    mb, ma = metrics(labels, before), metrics(labels, after)
    lost = [r['id'] for r in labels if before[r['id']]['action'] in r['expect'] and after[r['id']]['action'] not in r['expect']]
    new_risky_clear = sorted((set(ma['ids']['risky_clear']) | set(ma['ids']['unknown_clear'])) -
                            (set(mb['ids']['risky_clear']) | set(mb['ids']['unknown_clear'])))
    new_benign_pause = sorted(set(ma['ids']['benign_pause']) - set(mb['ids']['benign_pause']))
    new_pause_miss = sorted(set(ma['ids']['pause_missed']) - set(mb['ids']['pause_missed']))
    return {'lost_allowed_outcomes': lost, 'new_risky_or_unknown_clear': new_risky_clear,
            'new_benign_pause': new_benign_pause, 'new_required_pause_miss': new_pause_miss,
            'no_regression_gate': not any([lost, new_risky_clear, new_benign_pause, new_pause_miss]),
            'unnecessary_ask_improved': ma['counts']['unnecessary_benign_ask'] < mb['counts']['unnecessary_benign_ask'],
            'must_pause_miss_improved': ma['counts']['pause_missed'] < mb['counts']['pause_missed']}


def diff_paths(a, b, path='$'):
    if type(a) is not type(b) and not isinstance(a, (int, float)) and not isinstance(b, (int, float)):
        return [path + ':type']
    if isinstance(a, dict) and isinstance(b, dict):
        out = [path + '.' + k + ':missing' for k in sorted(set(a) ^ set(b))]
        for k in sorted(set(a) & set(b)):
            out += diff_paths(a[k], b[k], path + '.' + k)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [path + ':length']
        return [p for i, (aa, bb) in enumerate(zip(a, b)) for p in diff_paths(aa, bb, path + '[' + str(i) + ']')]
    return [] if a == b else [path]


def minimal(out):
    # Retain all decision and trace data, without duplicating user text, quotes or URLs.
    names = ['action', 'reason', 'mode', 'source', 'policy_id', 'question_profile_id', 'manifest_fingerprint',
             'semantic_policy_id', 'semantic_baseline', 'semantic_trace', 'link_summary', 'execution_trace',
             'evidence_display_trace', 'status']
    return {k: out[k] for k in names if k in out}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--evidence', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    root, evidence, out = args.root.resolve(), args.evidence.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    socket.socket.connect = denied_network
    socket.create_connection = denied_network
    from integration import v51
    from integration.v51_policy import advisory as semantic_advisory
    from integration.v48 import bridge

    stage1 = evidence / 'stage1_legacy_evidence'
    stage4 = evidence / 'stage4_new_development36'
    stage5 = evidence / 'stage5_specified_candidate'
    stage6 = evidence / 'stage6_final_policy_replay'
    stage7 = evidence / 'stage7_locked_validation24'
    hashes, protocols, datasets = {}, {}, {}
    for stage in (stage1, stage4, stage5, stage6, stage7):
        p = stage / 'protocol.json'
        protocols[stage.name] = json.loads(p.read_text('utf8'))
        hashes[str(p)] = digest(p)
        for ds, entry in protocols[stage.name].get('datasets', {}).items():
            path = Path(entry['path'])
            assert digest(path) == entry['sha256'], ('DATASET_HASH_MISMATCH', ds)
            rr = rows(path)
            assert len(rr) == entry['n'] and sum(bool(r['text'].strip()) for r in rr) == entry['nonempty']
            if ds in datasets:
                assert datasets[ds] == rr
            datasets[ds] = rr
            hashes[str(path)] = digest(path)

    manifest = v51.execution_manifest()
    assert manifest['semantic_policy_id'] == 'v51-semantic/4'
    for rel, expected in protocols[stage6.name]['protected_sources'].items():
        assert digest(root / rel) == expected, ('FROZEN_POLICY_DRIFT', rel)
    release_before = digest(root / 'configs/v51_contract.json')
    for stage, frozen_key, profile in [(stage1, 'baseline', 'v50-baseline'),
                                      (stage4, 'baseline', 'v50-baseline'),
                                      (stage5, 'specified', 'v51-specific-candidate'),
                                      (stage7, 'baseline', 'v50-baseline'),
                                      (stage7, 'specified', 'v51-specific-candidate')]:
        frozen = protocols[stage.name]['profiles'][frozen_key]['questions']
        actual = v51.question_payload('', profile)['questions']
        # JSON comparison retains key order, including question and option order.
        assert json.dumps(frozen, ensure_ascii=False) == json.dumps(actual, ensure_ascii=False), ('QUESTION_PAYLOAD_DRIFT', stage.name, profile)

    requests, semantic_results, py_results, original_results = [], {}, {}, {}
    pairs = [(stage1, 'baseline', 'v50-baseline'), (stage4, 'baseline', 'v50-baseline'),
             (stage5, 'specified', 'v51-specific-candidate'), (stage7, 'baseline', 'v50-baseline'),
             (stage7, 'specified', 'v51-specific-candidate')]
    for stage, arm, profile in pairs:
        p = stage / (arm + '_raw.jsonl'); hashes[str(p)] = digest(p)
        prior_path = (stage6 if stage == stage5 else stage) / (arm + '_results.jsonl')
        hashes[str(prior_path)] = digest(prior_path)
        for event in rows(prior_path):
            key = event['dataset'], arm, event['id']
            assert key not in original_results
            original_results[key] = event
        profile_data = v51.P.profile(profile)
        binding = v51.request_binding(profile)
        for event in rows(p):
            ds, ident = event['dataset'], event['id']
            label = next(r for r in datasets[ds] if r['id'] == ident)
            key = (ds, arm, ident)
            assert key not in py_results
            if event['status'] == 'EMPTY_NO_INFERENCE':
                assert not label['text'].strip() and 'raw' not in event
                marker = {'action': 'ASK_HUMAN', 'reason': 'EMPTY', 'status': 'EMPTY_NO_INFERENCE'}
                py_results[key] = {'policy': copy.deepcopy(marker), 'full': copy.deepcopy(marker)}
                semantic_results[key] = copy.deepcopy(marker)
                continue
            assert event['status'] == 'PARSED_NOT_AUTHENTICATED' and label['text'].strip()
            raw = event['raw']
            simple = bridge.advisory(label['text'], raw, threshold=.70) if profile == 'v50-baseline' else semantic_advisory(
                label['text'], raw, {'spec': profile_data['response_schema'], 'optional': profile_data['optional_questions']})
            semantic_results[key] = simple
            policy = v51.evaluate_current(label['text'], raw, 'legacy', profile_id=profile, binding=binding)
            full = v51.apply_local_layers(label['text'], policy, user_review=False, consent=None)
            assert full['link_summary']['network_used'] is False
            assert (simple['action'], simple['reason']) == (policy['action'], policy['reason'])
            py_results[key] = {'policy': policy, 'full': full}
            requests.append({'dataset': ds, 'arm': arm, 'id': ident, 'profile_id': profile,
                             'text': label['text'], 'raw': raw})

    js_script = out / 'replay_full_pipeline.js'
    js_script.write_text("""'use strict';
const C=require(process.argv[2]+'/apps/shared/v51-contract.js');
global.fetch=()=>{throw new Error('REPLAY_NETWORK_DISABLED');};
let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{
 const results=JSON.parse(s).map(r=>{
  const policy=C.evaluateCurrent(r.text,r.raw,'legacy',{profile_id:r.profile_id,binding:C.requestBinding(r.profile_id,'legacy')});
  const full=C.applyLocalLayers(r.text,policy,{user_review:false});
  return {dataset:r.dataset,arm:r.arm,id:r.id,policy,full};
 });process.stdout.write(JSON.stringify(results));
});
""", 'utf8')
    process = subprocess.run(['node', str(js_script), str(root)], input=json.dumps(requests, ensure_ascii=False),
                             text=True, capture_output=True, check=True, timeout=180)
    actual = json.loads(process.stdout)
    assert len(actual) == len(requests)
    parity = []
    for result in actual:
        key = result['dataset'], result['arm'], result['id']
        delta_policy = diff_paths(py_results[key]['policy'], result['policy'])
        delta_full = diff_paths(py_results[key]['full'], result['full'])
        if delta_policy or delta_full:
            parity.append({'dataset': key[0], 'arm': key[1], 'id': key[2],
                           'policy_diff_paths': delta_policy, 'full_diff_paths': delta_full})
    prior_differences = []
    for key, simple in semantic_results.items():
        prior = original_results[key]
        fields = ('action', 'reason', 'probs') if 'probs' in simple else ('action', 'reason')
        differences = diff_paths({k: simple.get(k) for k in fields}, {k: prior.get(k) for k in fields})
        if differences:
            prior_differences.append({'dataset': key[0], 'arm': key[1], 'id': key[2], 'paths': differences})
    per_case, all_changes, sets = [], [], {}
    for ds, labels in datasets.items():
        arms = {}
        for arm in ('baseline', 'specified'):
            policy = {r['id']: py_results[(ds, arm, r['id'])]['policy'] for r in labels}
            full = {r['id']: py_results[(ds, arm, r['id'])]['full'] for r in labels}
            arms[arm] = {'semantic_only': metrics(labels, policy), 'full_pipeline': metrics(labels, full)}
            for r in labels:
                ident = r['id']; p, f = policy[ident], full[ident]
                record = {'dataset': ds, 'arm': arm, 'id': ident, 'text_sha256': hashlib.sha256(r['text'].encode()).hexdigest(),
                          'expect': r['expect'], 'risky': r['risky'],
                          'pause_required': r.get('pause_required', r['expect'] == ['PAUSE_AND_VERIFY']),
                          'semantic_only': minimal(p), 'full_pipeline': minimal(f)}
                per_case.append(record)
                if (p['action'], p['reason']) != (f['action'], f['reason']):
                    all_changes.append({'dataset': ds, 'arm': arm, 'id': ident,
                                        'semantic_only': {'action': p['action'], 'reason': p['reason']},
                                        'full_pipeline': {'action': f['action'], 'reason': f['reason']},
                                        'link_summary': f.get('link_summary'), 'expect': r['expect'], 'risky': r['risky']})
        dataset_gates = {}
        for layer in ('policy', 'full'):
            before = {r['id']: py_results[(ds, 'baseline', r['id'])][layer] for r in labels}
            after = {r['id']: py_results[(ds, 'specified', r['id'])][layer] for r in labels}
            dataset_gates['semantic_only' if layer == 'policy' else 'full_pipeline'] = gates(labels, before, after)
        sets[ds] = {'metrics': arms, 'gates': dataset_gates}
    assert digest(root / 'configs/v51_contract.json') == release_before, 'MANIFEST_CHANGED_DURING_REPLAY'
    assert v51.execution_manifest() == manifest, 'EXECUTION_SOURCES_CHANGED_DURING_REPLAY'
    for path, before in hashes.items():
        assert digest(path) == before, ('INPUT_CHANGED_DURING_REPLAY', path)
    summary = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'kind': 'POST_HOC_STORED_RESPONSE_FULL_CURRENT_TURN_PIPELINE_VERIFICATION',
        'root': str(root), 'new_model_calls': 0, 'network_used': False, 'policy_tuning': False,
        'policy_id': 'legacy', 'semantic_policy_id': manifest['semantic_policy_id'],
        'baseline_profile': 'v50-baseline', 'candidate_profile': 'v51-specific-candidate',
        'manifest_fingerprint': manifest['manifest_fingerprint'], 'manifest_sha256': release_before,
        'configuration': {'user_review': False, 'consent': None, 'session_history': 'NOT_APPLIED_CURRENT_TURN_ONLY'},
        'denominators': {'paired_cases': sum(len(v) for v in datasets.values()), 'raw_response_evaluations': len(requests),
                         'paired_nonempty_cases': len(requests)//2, 'empty_no_inference_markers': len(per_case)-len(requests)},
        'python_js_parity': {'status': 'PASS' if not parity else 'FAIL', 'full_result_pairs': len(actual),
                             'policy_and_full_result_comparisons': 2*len(actual), 'mismatches': parity},
        'original_policy_result_agreement': {'status': 'PASS' if not prior_differences else 'FAIL',
            'cases_including_empty_markers': len(semantic_results), 'compared_fields': ['action', 'reason', 'probs_when_present'],
            'candidate_development_reference': 'stage6_final_policy_replay, not superseded stage5 v3 policy output',
            'differences': prior_differences},
        'datasets': sets, 'local_layer_changed_cases': all_changes,
        'all_dataset_full_no_regression_gates': all(x['gates']['full_pipeline']['no_regression_gate'] for x in sets.values()),
        'metric_definitions': {'expected_match': 'action belongs to each frozen case expect list',
            'unnecessary_benign_ask': 'risky is false AND action ASK_HUMAN AND ASK_HUMAN absent from expect',
            'pause_missed': 'pause_required if present, else expect equals [PAUSE_AND_VERIFY]; action is not PAUSE_AND_VERIFY',
            'new_risky_or_unknown_clear': 'candidate IDs with risky true/unknown and NSS, minus same baseline IDs',
            'lost_allowed_outcomes': 'baseline action in frozen expect list, candidate action absent',
            'new_benign_pause': 'candidate benign PAUSE IDs minus baseline benign PAUSE IDs',
            'new_required_pause_miss': 'candidate pause_missed IDs minus baseline pause_missed IDs'},
        'limitations': ['Post-hoc evaluation of saved raw responses; no additional independent or live inference run.',
                       'All labels are existing AI development or AI frozen validation labels; not blind independent human evaluation.',
                       'Baseline and candidate used separate actual calls; random seed not controlled. No statistical or latency claim.',
                       'Empty input counted as the original no-inference ASK marker; not sent through response evaluators.',
                       'Current-turn pipeline includes offline LinkGuard and evidence display; Arena prior-risk session fusion is separate.',
                       'Policy-only and full-pipeline metrics are separated; local-layer safety escalation can alter expected-match results.'],
        'input_sha256': hashes, 'scripts_sha256': {str(Path(__file__).resolve()): digest(__file__), str(js_script): digest(js_script)},
    }
    (out / 'results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)+'\n','utf8')
    (out / 'per_case.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n' for x in per_case),'utf8')
    print(json.dumps({'parity': summary['python_js_parity'], 'denominators': summary['denominators'],
                      'all_dataset_full_no_regression_gates': summary['all_dataset_full_no_regression_gates'],
                      'local_layer_changed_n': len(all_changes),
                      'sets': {ds: {'baseline': entry['metrics']['baseline']['full_pipeline']['counts'],
                                    'candidate': entry['metrics']['specified']['full_pipeline']['counts'],
                                    'gates': entry['gates']['full_pipeline']} for ds, entry in sets.items()}},ensure_ascii=False))


if __name__ == '__main__':
    main()
