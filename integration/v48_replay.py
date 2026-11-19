"""Convert explicit synthetic saved raw responses, or build a labelled STUB demonstration."""
import argparse
import hashlib
import json
from pathlib import Path
from experiments.contracts import ContractError, fingerprint, strict_json
from experiments.run import load_cases
from .v48 import ACTION_MAP, SPEECH_MAP, bridge, convert


def stub_raw(case):
    spec=case['fixture_spec']
    action={v:k for k,v in ACTION_MAP.items()}[spec['q_action']]
    speech={v:k for k,v in SPEECH_MAP.items()}[spec['q_speech']]
    top=spec.get('top',.94)
    answers={}
    for name, req in bridge.SPEC.items():
        if req['type']=='choice':
            selected=action if name=='q_action' else speech
            answers[name]={'type':'choice','choice':selected,'probabilities':{
                k:top if k==selected else (1-top)/(len(req['options'])-1) for k in req['options']}}
        elif req['type']=='noul':
            answers[name]={'type':'noul','noul':.94 if spec.get(name,'no')=='yes' else .06}
        else:
            answers[name]={'type':'score','score':1.0,'probabilities':{'0':.1,'1':.8,'2':.1,'3':0}}
    return {'answers':answers}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,default=Path('data/development.jsonl'))
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--raw',type=Path,help='JSONL {case_id,input_sha256,raw,latency_ms}; synthetic input only')
    group.add_argument('--demo',action='store_true',help='Invented responses: never actual Zoro inference')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Output exists')
    cases=load_cases(a.dataset)
    if a.demo and any(c['split']!='development' for c in cases):p.error('Demo is development-only')
    records={}
    if a.raw:
        for line in a.raw.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():continue
            item=strict_json(line)
            if item['case_id'] in records:raise ContractError('Duplicate raw case ID')
            records[item['case_id']]=item
        if set(records)!={c['case_id'] for c in cases}:raise ContractError('Raw IDs differ from dataset')
    result=[]
    for case in cases:
        if a.demo:
            # These are valid contract STUBs, not fixtures reproducing all source failure scenarios.
            trace=convert(case['text'],stub_raw(case),0.0,'FIXTURE')
        else:
            item=records[case['case_id']]
            if item['input_sha256']!=fingerprint(case['text']):raise ContractError('Raw input fingerprint differs')
            trace=convert(case['text'],item['raw'],item['latency_ms'])
        result.append({'case_id':case['case_id'],'trace':trace})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in result),encoding='utf-8')
    a.output.with_suffix('.protocol.json').write_text(json.dumps({
        'mode':'FIXTURE_STUB' if a.demo else 'SAVED_RESPONSE_UNATTESTED','count':len(result),
        'dataset_sha256':hashlib.sha256(a.dataset.read_bytes()).hexdigest(),
        'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest() if a.raw else None,
        'new_model_requests':0,'source_policy_threshold':.70,'source_policy_modified':False},indent=2),encoding='utf-8')
    print(json.dumps({'output':str(a.output),'cases':len(result),'new_model_requests':0}))


if __name__=='__main__':main()
