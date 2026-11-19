"""Educational fixture-only ablation, NOT a model benchmark nor independent test."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from prototype.paylock import EXAMPLES, validate_request, VENDORS, INVOICES, assess_request

# These six expected outcomes are AUTHOR-SPECIFIED, not blind annotations.
EXPECTED={'MATCH':False,'ACCOUNT_CHANGE':True,'SPOOF':True,
          'AMOUNT':True,'PRESSURE':True,'FALSE_AUTHORITY':True}

def baseline_structured(p):
    p=validate_request(p)
    v=VENDORS.get(p['vendor_id']); inv=INVOICES.get(p['invoice_id'])
    return bool(v is None or inv is None or inv.vendor_id!=p['vendor_id']
                or p['requested_bank']!=v.bank or p['requested_account']!=v.account
                or p['sender_email']!=v.known_email or p['amount_krw']!=inv.amount_krw)

def report():
    rows=[]
    for example in EXAMPLES:
        p={k:v for k,v in example.items() if k not in ('id','title')}
        simple=baseline_structured(p)
        extended=assess_request(p)[0]=='HOLD_FOR_INDEPENDENT_VERIFICATION'
        rows.append({'fixture_id':example['id'],'author_expected_hold':EXPECTED[example['id']],
                     'structured_only_hold':simple,'structured_plus_lexical_hold':extended,
                     'actual_zoro_called':False})
    return {'source':'AUTHOR_SYNTHETIC_FIXTURES',
            'actual_zoro_model_invocations':0,
            'independent_generalization_accuracy':None,
            'experimental_status':'ILLUSTRATIVE_ABLATION_NOT_INDEPENDENT_EVALUATION',
            'n':len(rows),'rows':rows}

if __name__=='__main__':print(json.dumps(report(),ensure_ascii=False,indent=2))
