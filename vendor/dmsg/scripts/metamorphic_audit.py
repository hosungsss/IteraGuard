"""Deterministic local invariants only; this is NOT an external accuracy evaluation."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.core import decide,Action,Kind,Directness,Origin,Evidence,quote_from
from prototype.fixtures import CASES
from scripts.evaluate_fixtures import EXPECTED

def report():
    rules=[]
    for case in CASES:
        base=decide(case.transcript,case.evidence,user_asks_review=(case.id=="AMBIGUOUS"))
        rules.append((case.id+' expected fixture action',base.action.value==EXPECTED[case.id]))
        for j,e in enumerate(case.evidence):
            tampered=Evidence(e.kind,e.start,e.end,e.quote+'X',e.directness,e.origin)
            altered=list(case.evidence); altered[j]=tampered
            rules.append((case.id+' offset/quote mismatch '+str(j),decide(case.transcript,tuple(altered)).action is Action.ASK_HUMAN))
            suggested=Evidence(e.kind,e.start,e.end,e.quote,e.directness,Origin.MODEL_PROPOSED)
            altered[j]=suggested
            rules.append((case.id+' unverified model provenance '+str(j),decide(case.transcript,tuple(altered)).action is Action.ASK_HUMAN))
    return {'scope':'LOCAL_SYNTHETIC_INVARIANTS_NOT_SAFETY_ACCURACY',
            'checks':len(rules),'passed':sum(ok for _,ok in rules),
            'failed':[name for name,ok in rules if not ok],
            'independent_validation':False,'real_model_called':False}
if __name__=='__main__':
    r=report();print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['checks']==r['passed'] else 1)
