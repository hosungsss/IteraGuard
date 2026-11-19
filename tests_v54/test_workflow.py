"""Controlled responses only; no live model inference or independent evaluation."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from arena.store import Arena
from integration import v51
PROFILE='v51-specific-candidate'
ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'tests_data/v51/execution_cases.json').read_text(encoding='utf-8'))

def unclear():
 a={}; winners={'q_action':'unclear','q_speech':'unclear','q_request_scope':'unclear','q_risk':'low'}
 for k,s in v51.P.profile(PROFILE,'legacy')['response_schema'].items():
  if s['type']=='noul':a[k]={'type':'noul','noul':.1};continue
  w=winners.get(k,s['options'][0]);a[k]={'type':s['type'],'probabilities':{x:.96 if x==w else .04/(len(s['options'])-1) for x in s['options']}}
  a[k]['choice' if s['type']=='choice' else 'score']=w
 return {'answers':a}
class Client:
 def __init__(self):self.raw=unclear()
 def infer(self,text,*,question_payload=None):return copy.deepcopy(self.raw),0.

class Workflow(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.client=Client();self.db=Path(self.tmp.name)/'a.db'
  self.a=Arena(self.db,client=self.client,profile_id=PROFILE);self.sid=self.a.start()['session_id']
 def tearDown(self):self.tmp.cleanup()
 def run_turn(self,version,text,**kw):return self.a.evaluate(session_id=self.sid,version=version,request_id='r'+str(version),text=text,synthetic_only=True,**kw)
 def test_new_uncertainty_creates_task_after_prior_report(self):
  x=self.run_turn(0,'그 자료를 안내받은 곳으로 보내 주세요.')
  y=self.run_turn(1,'다른 문서도 새로 받은 번호로 보내 주세요.',task_id=x['next_task']['id'],observation='USER_REPORTS_CONFIRMED')
  self.assertEqual(y['current_turn_action'],'ASK_HUMAN');self.assertIn('next_task',y)
  self.assertNotEqual(x['next_task']['id'],y['next_task']['id'])
  self.assertEqual(sum(t['status']=='OPEN' for t in self.a.read(self.sid)['tasks']),1)
 def test_same_input_reason_deduplicates_and_retry_is_identical(self):
  text='그 자료를 안내받은 곳으로 보내 주세요.';x=self.run_turn(0,text)
  kw=dict(task_id=x['next_task']['id'],observation='USER_REPORTS_CONFIRMED')
  y=self.run_turn(1,text,**kw);self.assertNotIn('next_task',y)
  self.assertEqual(y,self.run_turn(1,text,**kw))
 def test_restart_preserves_guidance_and_private_fingerprints(self):
  x=self.run_turn(0,'그 자료를 안내받은 곳으로 보내 주세요.')
  restarted=Arena(self.db,client=self.client,profile_id=PROFILE);t=restarted.read(self.sid)['tasks'][0]
  self.assertEqual(t['instruction'],x['next_task']['instruction']);self.assertEqual(t['type'],'CLARIFY_REQUEST')
  self.assertNotIn('trigger_fingerprint',t)
 def test_same_input_changed_reason_creates_task(self):
  text='그 자료를 안내받은 곳으로 보내 주세요.';x=self.run_turn(0,text)
  original=v51.apply_local_layers
  def changed(*a,**k):
   out=original(*a,**k);out['reason']='DIFFERENT_UNCERTAINTY';return out
  with patch.object(v51,'apply_local_layers',side_effect=changed):
   y=self.run_turn(1,text,task_id=x['next_task']['id'],observation='USER_REPORTS_CONFIRMED')
  self.assertIn('next_task',y)
 def test_model_failure_gets_retry_guidance_and_restores_it(self):
  with patch.object(self.client,'infer',side_effect=v51.v50.bridge.ModelUnavailable('MODEL_NOT_CONFIGURED')):
   x=self.run_turn(0,'그 자료를 안내받은 곳으로 보내 주세요.')
  self.assertEqual(x['next_task']['type'],'MODEL_RETRY')
  self.assertEqual(self.a.read(self.sid)['tasks'][0]['instruction'],x['next_task']['instruction'])
 def test_inherited_risk_does_not_create_endless_tasks(self):
  secret=next(r for r in CASES if r['id']=='V50-AI-22');ordinary=next(r for r in CASES if r['id']=='V50-AI-02')
  self.client.raw=secret['raw'];x=self.run_turn(0,secret['text']);self.assertEqual(x['action'],'PAUSE_AND_VERIFY')
  self.client.raw=ordinary['raw'];y=self.run_turn(1,ordinary['text'],task_id=x['next_task']['id'],observation='USER_REPORTS_CONFIRMED')
  self.assertEqual(y['current_turn_action'],'NO_STRONG_SIGNAL');self.assertEqual(y['action'],'ASK_HUMAN')
  self.assertTrue(y['prior_pause']);self.assertNotIn('next_task',y)

if __name__=='__main__':unittest.main()
