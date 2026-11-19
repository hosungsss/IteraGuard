import unittest,tempfile,json,copy
from pathlib import Path
from unittest.mock import patch
from arena.store import Arena,Conflict
from arena.evidence import export_session,validate_report,digest,latency_summary,readiness
from integration.v48 import bridge
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
 def test_recovery_resolves_only_matching_retry_and_records_it(self):
  reported_id = self.turn(0, '자료를 보내 주세요.')['next_task']['id']
  risk = next(case for case in CASES if case['id'] == 'V50-AI-22')
  self.client.raw = risk['raw']
  risk_id = self.turn(1, risk['text'], task_id=reported_id,
                      observation='USER_REPORTS_CONFIRMED')['next_task']['id']
  ordinary = next(case for case in CASES if case['id'] == 'V50-AI-02')
  with patch.object(self.client, 'infer', side_effect=bridge.ModelUnavailable('MODEL_TRANSPORT_ERROR_URLError')):
   first_failure = self.turn(2, ordinary['text'])
   other_failure = self.turn(3, '준비물이 무엇인지 알려 주세요.')
  retry_id = next(task['id'] for task in first_failure['open_tasks'] if task['type'] == 'MODEL_RETRY')
  other_retry_id = next(task['id'] for task in other_failure['open_tasks'] if task['id'] not in {risk_id, retry_id})

  self.a = Arena(self.a.db, client=self.client, profile_id=PROFILE)
  self.client.raw = ordinary['raw']
  recovered = self.turn(4, ordinary['text'])
  with patch.object(self.client, 'infer') as retry_infer:
   self.assertEqual(self.turn(4, ordinary['text']), recovered)
   retry_infer.assert_not_called()
  self.assertEqual(recovered['model_status'], 'VALID')
  self.assertEqual(recovered['current_turn_action'], 'NO_STRONG_SIGNAL')
  self.assertEqual(recovered['reason'], 'PRIOR_RISK_UNRESOLVED')
  self.assertTrue(recovered['prior_pause'])
  self.assertEqual(recovered['resolved_retry_task_ids'], [retry_id])
  self.assertEqual([task['id'] for task in recovered['open_tasks']], [risk_id, other_retry_id])
  state = self.a.read(self.sid)
  statuses = {task['id']: (task['type'], task['status'], task['observation']) for task in state['tasks']}
  self.assertEqual(statuses[retry_id], ('MODEL_RETRY', 'MODEL_RETRY_RESOLVED', 'NOT_CHECKED'))
  self.assertEqual(statuses[reported_id], ('CLARIFY_REQUEST', 'REPORTED_COMPLETE', 'USER_REPORTS_CONFIRMED'))
  self.assertEqual(state['open_task_count'], 2)
  report = export_session(self.a, self.sid)
  self.assertTrue(validate_report(report))
  self.assertEqual(report['events'][-1]['resolved_retry_task_ids'], [retry_id])

 def test_retry_remains_open_on_invalid_response_and_recurs_after_recovery(self):
  ordinary = next(case for case in CASES if case['id'] == 'V50-AI-02')
  text = ordinary['text']
  self.client.raw = {'answers': {}}
  failed = self.turn(0, text)
  retry_id = failed['next_task']['id']
  self.assertEqual(failed['next_task']['type'], 'MODEL_RETRY')
  self.assertEqual(self.turn(1, text)['next_task']['id'], retry_id)

  self.client.raw = ordinary['raw']
  recovered = self.turn(2, text)
  self.assertEqual(recovered['open_task_count'], 0)
  self.assertEqual(recovered['task_disposition'], 'MODEL_RETRY_RESOLVED')
  self.assertEqual(recovered['related_task']['id'], retry_id)
  self.assertEqual(recovered['related_task']['observation'], 'NOT_CHECKED')

  self.client.raw = {'answers': {}}
  failed_again = self.turn(3, text)
  self.assertEqual(failed_again['open_task_count'], 1)
  self.assertEqual(failed_again['next_task']['type'], 'MODEL_RETRY')
  self.assertNotEqual(failed_again['next_task']['id'], retry_id)
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
