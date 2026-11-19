"""Descriptive display coverage and CP alignment on existing frozen candidate responses.
AI-proposed annotation overlap is a coordinate statistic, not semantic accuracy.
No model calls, network, source edits or tuning.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

from replay_full_pipeline import digest, rows, denied_network


def cp_set(spans, start='start', end='end'):
    return {i for span in spans for i in range(span[start], span[end])}


def aggregate(items):
    evaluated = [x for x in items if x['evaluation'] == 'EVALUATED']
    sums = {k: sum(x['display_meta'][k] for x in evaluated) for k in (
        'candidate_clause_count', 'displayed_clause_count', 'unavailable_clause_count',
        'upstream_span_count', 'upstream_span_displayed_count', 'upstream_span_unavailable_count',
        'invalid_upstream_span_count')}
    ratio = lambda n, d: sums[n]/sums[d] if sums[d] else None
    return {'case_count_including_empty': len(items), 'evaluated_nonempty_cases': len(evaluated),
            'empty_no_inference_not_evaluated': len(items)-len(evaluated),
            'status_case_counts': dict(Counter(x['display_meta']['status'] for x in evaluated)),
            'cases_with_any_display': sum(bool(x['display_meta']['displayed_clause_count']) for x in evaluated),
            'counts': sums,
            'candidate_clause_coverage_micro': ratio('displayed_clause_count', 'candidate_clause_count'),
            'unavailable_clause_rate_micro': ratio('unavailable_clause_count', 'candidate_clause_count'),
            'upstream_span_unavailable_rate_micro': ratio('upstream_span_unavailable_count', 'upstream_span_count'),
            'cases_with_zero_candidate_clauses': sum(not x['display_meta']['candidate_clause_count'] for x in evaluated),
            'cases_with_zero_upstream_spans': sum(not x['display_meta']['upstream_span_count'] for x in evaluated),
            'reason_code_case_counts': dict(Counter(code for x in evaluated for code in x['display_meta']['reason_codes'])),
            'displayed_span_method_counts': dict(Counter(s['method'] for x in evaluated for s in x['display_spans'])),
            'displayed_span_context_counts': dict(Counter(s['clause_mode'] for x in evaluated for s in x['display_spans']))}


def annotation_overlap(items):
    sums = {k: sum(x['annotation_overlap'][k] for x in items) for k in (
        'annotation_span_count', 'display_span_count', 'annotation_cp', 'display_cp', 'intersection_cp',
        'outside_annotation_cp', 'annotation_uncovered_cp', 'display_spans_with_any_annotation_overlap',
        'annotation_spans_with_any_display_overlap', 'exact_span_match_count')}
    return {'cases': len(items), 'label_status': 'AI_PROPOSED_NOT_HUMAN_VALIDATED',
            'annotation_key': 'evidence[] with start_cp/end_cp/quote', 'coordinate_counts': sums,
            'cases_with_any_display': sum(x['annotation_overlap']['display_cp'] > 0 for x in items),
            'cases_with_any_overlap': sum(x['annotation_overlap']['intersection_cp'] > 0 for x in items),
            'displayed_cases_with_no_annotation_overlap': [x['id'] for x in items if x['annotation_overlap']['display_cp'] and not x['annotation_overlap']['intersection_cp']],
            'display_cp_inside_annotation_fraction': sums['intersection_cp']/sums['display_cp'] if sums['display_cp'] else None,
            'annotation_cp_covered_fraction': sums['intersection_cp']/sums['annotation_cp'] if sums['annotation_cp'] else None,
            'coordinate_iou': sums['intersection_cp']/(sums['display_cp']+sums['annotation_cp']-sums['intersection_cp']) if sums['display_cp']+sums['annotation_cp'] else None,
            'cases_with_display_outside_annotation': sum(x['annotation_overlap']['outside_annotation_cp'] > 0 for x in items),
            'largest_display_extensions': [{'id': x['id'], **x['annotation_overlap'], 'display_spans': x['display_spans'],
                                            'annotation_spans': x['annotation_spans']} for x in sorted(items,key=lambda x:x['annotation_overlap']['outside_annotation_cp'],reverse=True)[:5]],
            'interpretation': 'Clause context expansion can include words outside narrow AI annotations; omitted punctuation also reduces overlap. These values do not establish true/false evidence, model grounding, fraud accuracy or human semantic quality.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args(); out = args.out.resolve()
    full_report = json.loads((out/'results.json').read_text('utf8'))
    root = Path(full_report['root']); sys.path.insert(0,str(root));sys.dont_write_bytecode=True
    socket.socket.connect=denied_network; socket.create_connection=denied_network
    from integration import v51
    from integration.v51_evidence import enrich_evidence
    manifest = v51.execution_manifest()
    assert manifest['manifest_fingerprint'] == full_report['manifest_fingerprint']
    evidence_root = out.parent/'experiments'
    records, differences, invalid_offsets, invariant_checks = [], [], [], 0
    sources = {}
    for stage in ['stage5_specified_candidate','stage7_locked_validation24']:
        protocol_path = evidence_root/stage/'protocol.json'
        protocol = json.loads(protocol_path.read_text('utf8'));sources[str(protocol_path)]=digest(protocol_path)
        labels = {}
        for ds,meta in protocol['datasets'].items():
            assert digest(meta['path']) == meta['sha256']
            sources[meta['path']]=meta['sha256']
            for row in rows(meta['path']):labels[(ds,row['id'])]=row
        raw_path=evidence_root/stage/'specified_raw.jsonl';sources[str(raw_path)]=digest(raw_path)
        for event in rows(raw_path):
            ds,ident=event['dataset'],event['id']; label=labels[(ds,ident)]; text=label['text']
            record={'dataset':ds,'id':ident,'text_sha256':hashlib.sha256(text.encode()).hexdigest()}
            if event['status']=='EMPTY_NO_INFERENCE':
                record['evaluation']='NOT_EVALUATED_EMPTY_NO_INFERENCE';records.append(record);continue
            # Capture the normal wrapper's input to the display-only module.
            # Patching is scoped to this offline verifier process, never product sources.
            with patch.object(v51,'enrich_display',lambda _text,result:result):
                before=v51.evaluate_current(text,event['raw'],'legacy',profile_id='v51-specific-candidate',
                                           binding=v51.request_binding('v51-specific-candidate'))
            original=deepcopy(before); after=enrich_evidence(text,before)
            checks={'caller_unchanged':before==original,'action':after['action']==original['action'],
                    'reason':after['reason']==original['reason'], 'message':after['message']==original['message'],
                    'execution_trace':after['execution_trace']==original['execution_trace'],
                    'execution_evidence_spans':after['execution_trace']['evidence_spans']==original['execution_trace']['evidence_spans'],
                    'original_evidence':after['original_evidence']==original.get('evidence',[])}
            invariant_checks+=1
            if not all(checks.values()):differences.append({'dataset':ds,'id':ident,'checks':checks})
            full=v51.apply_local_layers(text,after,user_review=False,consent=None)
            assert full['action']==after['action'] and full['reason']==after['reason']
            assert full['execution_trace']['evidence_spans']==original['execution_trace']['evidence_spans']
            spans=full['evidence']
            for i,s in enumerate(spans):
                valid=(type(s['start']) is int and type(s['end']) is int and 0<=s['start']<s['end']<=len(text)
                       and s['quote']==text[s['start']:s['end']])
                if not valid:invalid_offsets.append({'dataset':ds,'id':ident,'index':i})
            record.update(evaluation='EVALUATED',display_meta=full['evidence_display'],
                          display_spans=[{k:s[k] for k in ['start','end','clause_mode','method']} for s in spans])
            if ds in ['AI36_development','AI24_locked']:
                annotations=label['evidence']
                assert all(type(e['start_cp']) is int and type(e['end_cp']) is int and
                           0<=e['start_cp']<e['end_cp']<=len(text) and text[e['start_cp']:e['end_cp']]==e['quote'] for e in annotations)
                ps,gs=cp_set(spans),cp_set(annotations,'start_cp','end_cp')
                record['annotation_spans']=[{k:e[k] for k in ['start_cp','end_cp','kind','directness','annotation_status']} for e in annotations]
                record['annotation_overlap']={
                    'annotation_span_count':len(annotations),'display_span_count':len(spans),
                    'annotation_cp':len(gs),'display_cp':len(ps),'intersection_cp':len(ps&gs),
                    'outside_annotation_cp':len(ps-gs),'annotation_uncovered_cp':len(gs-ps),
                    'display_spans_with_any_annotation_overlap':sum(bool(set(range(s['start'],s['end']))&gs) for s in spans),
                    'annotation_spans_with_any_display_overlap':sum(bool(set(range(s['start_cp'],s['end_cp']))&ps) for s in annotations),
                    'exact_span_match_count':sum(any(s['start']==e['start_cp'] and s['end']==e['end_cp'] for e in annotations) for s in spans)}
            records.append(record)
    assert len(records)==158
    summary={'scope':'DISPLAY_ONLY_LEXICAL_CLAUSE_COVERAGE_AND_COORDINATE_ALIGNMENT',
             'new_model_calls':0,'network_used':False,'source_edits':False,'semantic_quality':'NOT_INDEPENDENTLY_EVALUATED',
             'manifest_fingerprint':manifest['manifest_fingerprint'],'overall':aggregate(records),
             'by_dataset':{ds:aggregate([r for r in records if r['dataset']==ds]) for ds in sorted({r['dataset'] for r in records})},
             'ai_annotation_overlap':{ds:annotation_overlap([r for r in records if r['dataset']==ds]) for ds in ['AI36_development','AI24_locked']},
             'invariants':{'evaluated_nonempty_cases':invariant_checks,'decision_or_original_evidence_trace_change_n':len(differences),
                           'differences':differences,'display_span_cp_quote_checks':sum(len(r.get('display_spans',[])) for r in records),
                           'invalid_display_cp_offsets_or_quotes':invalid_offsets},
             'definitions':{'status_cases':'AVAILABLE all eligible lexical candidates shown; PARTIAL some omitted/invalid; UNAVAILABLE none shown among candidates; NOT_APPLICABLE no candidate clauses; empty no-inference excluded from evaluator.',
                            'clause_denominator':'clauses with topic cue OR request cue OR valid upstream anchor; not all semantic action clauses',
                            'upstream_denominator':'all pre-display decision evidence anchors including unavailable/invalid ones',
                            'rates':'micro rates use summed clause/span counts, never mean of per-message percentages',
                            'ai_overlap':'Python Unicode code-point set intersections; gold key is evidence[]; AI labels are not independently human verified'},
             'input_sha256':sources,'script_sha256':digest(__file__),
             'limitations':['Clause expansion intentionally displays context and may overhighlight relative to narrow annotated spans.',
                            'Coverage is neither evidence semantic correctness nor model attention/attribution fidelity.',
                            'No threshold/policy/question/display algorithm changes followed locked validation inspection.',
                            'Existing frozen AI36 development and AI24 validation annotations remain separate.']}
    assert v51.execution_manifest()==manifest
    for path,expected in sources.items():assert digest(path)==expected
    (out/'evidence_display_quality.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n','utf8')
    (out/'evidence_display_per_case.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),'utf8')
    print(json.dumps({'overall':summary['overall'],'invariants':summary['invariants'],
                      'overlap':{ds:{k:v for k,v in x.items() if k!='largest_display_extensions'} for ds,x in summary['ai_annotation_overlap'].items()}},ensure_ascii=False))


if __name__=='__main__':main()
