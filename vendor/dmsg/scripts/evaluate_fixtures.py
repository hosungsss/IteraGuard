"""Deterministic fixture-family conformance tests, NOT measured field accuracy."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.fixtures import CASES
from prototype.core import decide,Action
EXPECTED={
 'NORMAL_BANK':'NO_STRONG_SIGNAL','LEGITIMATE_WARNING':'NO_STRONG_SIGNAL',
 'RISK_TRANSFER':'PAUSE_AND_VERIFY','RISK_REMOTE':'PAUSE_AND_VERIFY',
 'RISK_OTP':'PAUSE_AND_VERIFY','AMBIGUOUS':'ASK_HUMAN',
 'CAUTION_LINK':'CAUTION','REPORTED':'CAUTION',
 'LEGIT_TRANSFER':'PAUSE_AND_VERIFY','IMPERSONATION':'ASK_HUMAN',
 'COERCION_INDIRECT':'ASK_HUMAN','REPORTED_OTP':'CAUTION',
 'NEGATIVE_OTP':'NO_STRONG_SIGNAL','SECRET_REQUEST':'CAUTION'
}

def assess():
    rows=[]
    for f in CASES:
        got=decide(f.transcript,f.evidence,user_asks_review=f.id=='AMBIGUOUS')
        rows.append({'id':f.id,'family':f.family,'expected':EXPECTED[f.id],
                     'actual':got.action.value,'pass':got.action.value==EXPECTED[f.id]})
    return {'mode':'FIXTURE_CONFORMANCE_ONLY','sample_size':len(rows),
            'pass_count':sum(x['pass'] for x in rows),'rows':rows,
            'independent_validation':False,'real_model_invocations':0}
if __name__=='__main__':
    out=assess();print(json.dumps(out,ensure_ascii=False,indent=2))
    sys.exit(0 if out['pass_count']==out['sample_size'] else 1)
