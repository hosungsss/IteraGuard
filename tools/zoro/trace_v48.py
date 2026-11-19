"""v4.8 diagnostic-only Zoro decision trace. No inference, no threshold override, no raw text saved.
Input is an offline JSON file with [{id,text,response}]. Output excludes raw text and full probabilities.
Use only with appropriately authorized, de-identified saved responses. Never misreport mock data as real.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dmsg'))
from prototype import model_bridge as mb
from prototype.typed_contract import normalize_response
from prototype.context_guard import context_flags, context_conflict, clause_profile

def trace_items(items):
    reports=[]
    for it in items:
        case_id=it.get('id','UNSPECIFIED'); text=it.get('text',''); raw=it.get('response')
        row={'id':case_id,'raw_text_logged':False,'model_was_called':False,'question_contract':'v4.7-existing/7q',
             'calibration':'DOMAIN_UNVERIFIED','threshold_source':'UNVALIDATED_DEMO_HEURISTIC','gate_results':[]}
        if not isinstance(text,str) or not text.strip() or not isinstance(raw,dict):
            row.update(status='INVALID_INPUT'); reports.append(row); continue
        try:
            n=normalize_response(raw,mb.SPEC, optional=mb.OPTIONAL_QUESTIONS)
            a=n['q_action']['choice']; s=n['q_speech']['choice']; threshold=.70
            pa=n['q_action']['probabilities'][a]; ps=n['q_speech']['probabilities'][s]
            flags=context_flags(text); conflict=context_conflict(a,s,flags,clause_profile(text))
            factors=[('ACTION_CONFIDENCE',pa>=threshold),('SPEECH_CONFIDENCE',ps>=threshold),
                     ('NO_EXPLICIT_CONFLICT',not bool(conflict)),('NOT_UNCLEAR',a!='unclear' and s!='unclear')]
            if 'q_evidence' in n: factors.append(('EVIDENCE_COMPLETENESS',n['q_evidence']['probabilities']['no']<threshold))
            else: row['gate_results'].append({'gate':'OPTIONAL_EVIDENCE','state':'NOT_APPLICABLE'})
            row['gate_results'] += [{'gate':name,'state':'PASS' if ok else 'BLOCKED'} for name,ok in factors]
            advice=mb.advisory(text,raw); dra=mb.decision_relevant_advisory(text,raw)
            row.update(status='OK',model_candidate={'action':a,'speech':s,'p_action':round(pa,4),'p_speech':round(ps,4)},
                       final_action=advice['action'], primary_reason=advice['reason'],
                       all_blocking_gates=[x['gate'] for x in row['gate_results'] if x['state']=='BLOCKED'],
                       current_dra_action=dra['action'],current_dra_reason=dra['reason'],
                       compare_not_equivalent_to_independent_evaluation=True)
        except Exception as ex:
            row.update(status='REJECTED',error_type=type(ex).__name__)
        reports.append(row)
    return {'provenance':'OFFLINE_REPLAY_ONLY_NO_MODEL_INFERENCE','items':reports,'n':len(reports)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args(); data=json.loads(Path(args.input).read_text('utf8'))
    if not isinstance(data,list): raise SystemExit('INPUT_MUST_BE_LIST')
    # never write full raw messages/responses to output
    out=trace_items(data)
    out['input_sha256']=hashlib.sha256(Path(args.input).read_bytes()).hexdigest()
    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps({'status':'TRACE_COMPLETE','n':out['n'],'model_run':False}))
if __name__=='__main__':main()
