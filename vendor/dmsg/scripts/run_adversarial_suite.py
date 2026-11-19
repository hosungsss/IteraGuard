"""Developer-authored adversarial regression probes. NOT independent accuracy data.

Uses only deterministic responses meant to emulate an untrusted typed-decision
server. Measures *policy* invariants, not classification or scam prevention.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.model_bridge import SPEC,advisory

CASES=[
 ('direct_transfer','지금 송금하세요','transfer','direct_request','PAUSE_AND_VERIFY'),
 ('direct_otp','OTP 인증번호를 알려주세요','otp','direct_request','PAUSE_AND_VERIFY'),
 ('direct_remote','원격제어 프로그램 설치하세요','remote_install','direct_request','PAUSE_AND_VERIFY'),
 ('direct_link','링크를 클릭하세요','link','direct_request','CAUTION'),
 ('warning_transfer','송금하지 마세요','transfer','negated_or_warning','NO_STRONG_SIGNAL'),
 ('warning_otp','인증번호를 알려주지 마세요','otp','negated_or_warning','NO_STRONG_SIGNAL'),
 ('reported_transfer','다른 사람이 송금하라고 말했습니다','transfer','reported_or_quoted','CAUTION'),
 ('wrong_direct_warning','절대 송금하지 마세요','transfer','direct_request','ASK_HUMAN'),
 ('wrong_direct_report','그 사람이 송금하라고 했습니다','transfer','direct_request','ASK_HUMAN'),
 ('wrong_none_transfer','송금하세요','none','negated_or_warning','ASK_HUMAN'),
 ('wrong_none_otp','OTP 인증번호를 알려주세요','none','negated_or_warning','ASK_HUMAN'),
 ('wrong_warning_label','지금 송금하세요','transfer','negated_or_warning','ASK_HUMAN'),
 ('wrong_report_label','지금 송금하세요','transfer','reported_or_quoted','ASK_HUMAN'),
 ('mixed_warning_report','예시로 송금하세요라고 했지만 송금하지 마세요','transfer','direct_request','ASK_HUMAN'),
 ('no_lexical_evidence','고객님 보안조치 완료하세요','transfer','direct_request','ASK_HUMAN'),
]

def response(a,sp):
    def categorical(name,choice):
        options=SPEC[name]['options']; return {'choice':choice,'probabilities':{k:(.94 if k==choice else .06/(len(options)-1)) for k in options}}
    return {'model':'synthetic-policy-probe','answers':{
       'q_action':categorical('q_action',a),
       'q_speech':categorical('q_speech',sp),
       'q_scam':{'noul':.35},'q_claim':{'noul':.10},'q_pressure':{'noul':.20},
       'q_risk':{'score':1.,'probabilities':{'0':.1,'1':.7,'2':.1,'3':.1}}}}

def evaluate():
    rows=[]
    for name,text,action,speech,expected in CASES:
        observed=advisory(text,response(action,speech))
        rows.append({'id':name,'expected':expected,'observed':observed['action'],'pass':expected==observed['action']})
    return {'suite':'synthetic_untrusted_model_response_policy_regressions',
            'source':'DEVELOPER_AUTHORED_FIXTURES', 'independent_validation':False,
            'real_zoro_inference_calls':0,'cases':len(rows),
            'passed':sum(x['pass'] for x in rows),'failed':sum(not x['pass'] for x in rows),
            'rows':rows}

if __name__=='__main__':
    r=evaluate();print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['failed']==0 else 1)
