"""Synthetic stubs only, never recorded Zoro inference."""
import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.model_bridge import SPEC,questions,advisory,ModelClient,ModelUnavailable
from prototype.typed_contract import ContractError
from prototype.session import Store,Conflict


def sample(action='transfer',speech='direct_request',pa=.92,ps=.93):
    def cat(options,key,p):
        return {'type':'choice','choice':key,'probabilities':{k:(p if k==key else (1-p)/(len(options)-1)) for k in options}}
    def yn(x):return {'type':'noul','noul':x}
    return {'model':'operator-test-stub','answers':{
        'q_action':cat(SPEC['q_action']['options'],action,pa),
        'q_speech':cat(SPEC['q_speech']['options'],speech,ps),
        'q_scam':yn(.75),'q_claim':yn(.7),'q_pressure':yn(.8),
        'q_risk':{'type':'score','score':1.9,'probabilities':{'0':.05,'1':.25,'2':.45,'3':.25}}
    }}

class Stub:
    def __init__(self,raw):self.raw=raw;self.calls=0
    def infer(self,text):self.calls+=1;return copy.deepcopy(self.raw), 12.5
class Down:
    def infer(self,text):raise ModelUnavailable('SIMULATED_DOWN')

class ModelBridgeTests(unittest.TestCase):
    def test_provisional_question_contract(self):
        q=questions('송금하세요');self.assertEqual(len(q['questions']),7)  # v4.5: +q_evidence
        self.assertEqual(q['questions']['q_risk']['type'],'score')
    def test_direct_grounded_advisory(self):
        r=advisory('지금 송금하세요',sample());self.assertEqual(r['action'],'PAUSE_AND_VERIFY')
        self.assertFalse(r['model_attested']);self.assertEqual(r['calibration_status'],'NOT_ESTABLISHED')
        self.assertEqual(r['evidence'][0]['quote'],'송금')
    def test_negated_warning(self):
        self.assertEqual(advisory('송금하지 마세요',sample(speech='negated_or_warning'))['action'],'NO_STRONG_SIGNAL')
    def test_report_not_direct(self):
        self.assertEqual(advisory('다른 사람에게 송금하라는 말을 들었습니다',sample(speech='reported_or_quoted'))['action'],'CAUTION')
    def test_low_confidence_abstains(self):
        self.assertEqual(advisory('송금하세요',sample(pa=.6))['action'],'ASK_HUMAN')
    def test_obvious_warning_conflict_abstains(self):
        self.assertEqual(advisory('절대 송금하지 마세요',sample())['action'],'ASK_HUMAN')
    def test_report_conflict_abstains(self):
        self.assertEqual(advisory('그 사람이 송금하라고 했습니다',sample())['action'],'ASK_HUMAN')
    def test_no_action_high_scam_conflict_abstains(self):
        self.assertEqual(advisory('안녕하세요',sample(action='none'))['action'],'ASK_HUMAN')
    def test_missing_lexical_anchor_abstains(self):
        self.assertEqual(advisory('무슨 일이든 해결합시다',sample())['action'],'ASK_HUMAN')
    def test_no_action_never_safe_claim(self):
        v=sample(action='none',speech='negated_or_warning');v['answers']['q_scam']['noul']=.2
        a=advisory('좋은 하루',v);self.assertEqual(a['action'],'NO_STRONG_SIGNAL')
        self.assertIn('안전하다는 의미는 아닙니다',a['message'])
    def test_nonfinite_rejected(self):
        v=sample();v['answers']['q_scam']['noul']=float('nan')
        with self.assertRaises(ContractError):advisory('송금하세요',v)
    def test_optional_choice_derived_from_argmax(self):
        v=sample();del v['answers']['q_action']['choice']
        self.assertEqual(advisory('송금하세요',v)['action'],'PAUSE_AND_VERIFY')
    def test_score_fractional_not_fraud_probability(self):
        self.assertIn('q_risk',advisory('송금하세요',sample())['probs'])
    def test_no_external_endpoint_default(self):
        c=ModelClient(enabled=False)
        with self.assertRaises(ModelUnavailable):c.infer('합성')
    def test_http_public_forbidden(self):
        c=ModelClient(endpoint='http://example.com/v1/systemone',model_id='x',enabled=True)
        with self.assertRaises(ModelUnavailable):c._check_target()
    def test_endpoint_must_match(self):
        c=ModelClient(endpoint='https://example.com/other',model_id='x',enabled=True)
        with self.assertRaises(ModelUnavailable):c._check_target()
    def test_session_proposed_result_without_claiming_real(self):
        st=Store();s=st.start();f=Stub(sample())
        a=st.process_model(session_id=s['session_id'],turn_id='M1',version=0,text='송금하세요',client=f)
        self.assertEqual(a['action'],'PAUSE_AND_VERIFY');self.assertEqual(f.calls,1)
        self.assertFalse(a['verified_model']);self.assertNotIn('송금하세요',str(a['history']))
        b=st.process_model(session_id=s['session_id'],turn_id='M1',version=0,text='송금하세요',client=f)
        self.assertEqual(a,b);self.assertEqual(f.calls,1)
    def test_session_bad_source_abstains(self):
        st=Store();s=st.start()
        a=st.process_model(session_id=s['session_id'],turn_id='M1',version=0,text='송금하세요',client=Down())
        self.assertEqual(a['action'],'ASK_HUMAN');self.assertFalse(a['verified_model'])
    def test_session_stale_rejects(self):
        st=Store();s=st.start();st.process_model(session_id=s['session_id'],turn_id='M1',version=0,text='송금하세요',client=Stub(sample()))
        with self.assertRaises(Conflict):st.process_model(session_id=s['session_id'],turn_id='M2',version=0,text='송금하세요',client=Stub(sample()))
    def test_reject_user_forged_response(self):
        st=Store();s=st.start()
        with self.assertRaises(TypeError):st.process_model(session_id=s['session_id'],turn_id='M1',version=0,text='송금하세요',raw=sample())

if __name__=='__main__':unittest.main()
