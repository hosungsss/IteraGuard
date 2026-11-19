import unittest,tempfile,json,copy
from pathlib import Path
from unittest.mock import patch
from arena.store import Arena,Conflict
from arena.evidence import export_session,validate_report,digest,latency_summary,readiness
from tests_v54.test_workflow import Client,CASES,PROFILE

class EvidenceQueue(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.client=Client();self.a=Arena(Path(self.tmp.name)/'a.db',client=self.client,profile_id=PROFILE);self.sid=self.a.start()['session_id']
 def tearDown(self):self.tmp.cleanup()
 def turn(self,v,text,**kw):return self.a.evaluate(session_id=self.sid,version=v,request_id='r'+str(v),text=text,synthetic_only=True,**kw)
 def report(self):self.turn(0,'자료를 그곳으로 보내 주세요.');return export_session(self.a,self.sid)
 def test_second_risk_is_queued_and_prioritized(self):
  first=self.turn(0,'자료를 보내 주세요.');s=next(x for x in CASES if x['id']=='V50-AI-22');self.client.raw=s['raw'];second=self.turn(1,s['text'])
  self.assertEqual(second['open_task_count'],2);self.assertNotEqual(first['next_task']['id'],second['next_task']['id'])
  self.assertEqual(second['next_task']['type'],'PAUSE_AND_INDEPENDENT_CHECK');self.assertEqual(self.a.read(self.sid)['tasks'][0]['id'],second['next_task']['id'])
 def test_distinct_asks_remain_accessible_and_repeat_dedupes(self):
  self.turn(0,'자료를 보내 주세요.');self.turn(1,'문서를 다른 곳으로 보내 주세요.');x=self.turn(2,'자료를 보내 주세요.')
  self.assertEqual(x['open_task_count'],2)
 def test_completed_duplicate_after_intervening_request_not_recreated(self):
  x=self.turn(0,'자료를 보내 주세요.');self.turn(1,'문서를 보내 주세요.',task_id=x['next_task']['id'],observation='USER_REPORTS_CONFIRMED')
  self.turn(2,'자료를 보내 주세요.');self.assertEqual(len(self.a.read(self.sid)['tasks']),2)
 def test_capacity_rejects_atomically_without_losing_prior_state(self):
  self.turn(0,'자료를 보내 주세요.');before=self.a.read(self.sid)
  with patch('arena.store.MAX_OPEN_TASKS',1),self.assertRaisesRegex(Conflict,'TASK_CAPACITY_REACHED'):self.turn(1,'다른 문서를 보내 주세요.')
  self.assertEqual(before,self.a.read(self.sid))
 def test_nonfinite_response_is_explicit_failure(self):
  self.client.raw={'answers':{'bad':float('nan')}};x=self.turn(0,'합성 입력')
  self.assertEqual(x['model_status'],'FAILED');self.assertEqual(x['action'],'ASK_HUMAN');self.assertIsNone(x['provenance']['response_sha256'])
 def test_export_omits_input_and_raw_response(self):
  r=self.report();self.assertTrue(validate_report(r));text=json.dumps(r,ensure_ascii=False)
  self.assertNotIn('자료를 그곳으로',text);self.assertNotIn('probabilities',text);self.assertEqual(r['events'][0]['provenance']['execution_source'],'CONTROLLED_CLIENT')
 def test_modified_report_rejected(self):
  r=self.report();r['events'][0]['action']='NO_STRONG_SIGNAL'
  with self.assertRaisesRegex(ValueError,'DIGEST'):validate_report(r)
 def test_resigned_false_attestation_rejected(self):
  r=self.report();r['model_identity_verified']='true';r.pop('sha256');r['sha256']=digest(r)
  with self.assertRaisesRegex(ValueError,'ATTESTATION'):validate_report(r)
 def test_missing_event_rejected_even_with_new_hash(self):
  r=self.report();r['events']=[];r.pop('sha256');r['sha256']=digest(r)
  with self.assertRaisesRegex(ValueError,'SEQUENCE'):validate_report(r)
 def test_latency_is_separated_and_invalid_values_excluded(self):
  events=[{'model_status':'VALID','provenance':{'pipeline_ms':n,'execution_source':s}} for s,n in [('CONTROLLED_CLIENT',1),('LOCAL_HTTP_MODEL_UNATTESTED',1000),('CONTROLLED_CLIENT',True),('CONTROLLED_CLIENT',float('nan'))]]
  x=latency_summary([{'events':events}]);self.assertEqual(x['groups']['CONTROLLED_CLIENT']['n'],1);self.assertEqual(x['groups']['LOCAL_HTTP_MODEL_UNATTESTED']['p95'],1000);self.assertEqual(x['excluded_events'],2)
 def test_readiness_does_not_promote_controlled_logs(self):
  x=readiness([self.report()]);self.assertEqual(x['status'],'NOT_SUBMISSION_READY');self.assertEqual(x['evidence_validation_errors'],[])
 def test_export_has_current_arena_source_fingerprints(self):
  r=self.report();self.assertEqual(set(r['events'][0]['provenance']['arena_sources']),{'store.py','server.py','evidence.py','web/main.js'})
if __name__=='__main__':unittest.main()
