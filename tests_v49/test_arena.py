import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from arena.store import Arena,Conflict
from integration.v48 import bridge
from integration.v48_replay import stub_raw

class Client:
    def __init__(self,action='money_transfer',speech='direct_request'):
        self.action=action;self.speech=speech;self.calls=0;self.hook=None
    def infer(self,text):
        self.calls+=1
        if self.hook:self.hook()
        return stub_raw({'fixture_spec':{'q_action':self.action,'q_speech':self.speech,'q_evidence':'yes'}}),1.0

class Failing:
    def infer(self,text):raise bridge.ModelUnavailable('CONNECTION_FAILED')

class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'audit.db'
        self.client=Client();self.arena=Arena(self.path,self.client);self.session=self.arena.start()
    def tearDown(self):self.temp.cleanup()
    def request(self,**kw):
        return dict(session_id=self.session['session_id'],version=0,request_id='r1',text='지금 송금하세요.',synthetic_only=True,**kw)
    def test_task_persisted_and_idempotent(self):
        req=self.request();r=self.arena.evaluate(**req)
        self.assertEqual(r['action'],'PAUSE_AND_VERIFY')
        self.assertEqual(r,self.arena.evaluate(**req));self.assertEqual(self.client.calls,1)
        reopened=Arena(self.path,self.client)
        self.assertEqual(r,reopened.evaluate(**req))
        self.assertEqual(len(reopened.read(self.session['session_id'])['tasks']),1)
    def test_changed_retry_and_stale_rejected(self):
        req=self.request();self.arena.evaluate(**req)
        with self.assertRaisesRegex(Conflict,'CONFLICTING_RETRY'):self.arena.evaluate(**{**req,'text':'다른 내용'})
        with self.assertRaisesRegex(Conflict,'STALE_VERSION'):self.arena.evaluate(**{**req,'request_id':'r2'})
    def test_new_observation_recomputes_but_does_not_clear_risk(self):
        r=self.arena.evaluate(**self.request());self.client.action='none';self.client.speech='information'
        r2=self.arena.evaluate(**{**self.request(),'version':1,'request_id':'r2','text':'안내를 확인했습니다.',
            'task_id':r['next_task']['id'],'observation':'USER_REPORTS_CONFIRMED'})
        self.assertEqual(self.client.calls,2);self.assertEqual(r2['version'],2)
        self.assertEqual(r2['current_turn_action'],'NO_STRONG_SIGNAL')
        self.assertEqual(r2['action'],'ASK_HUMAN');self.assertEqual(r2['reason'],'PRIOR_RISK_UNRESOLVED')
        self.assertEqual(self.arena.read(self.session['session_id'])['tasks'][0]['status'],'REPORTED_COMPLETE')
    def test_cross_session_task_rejected(self):
        r=self.arena.evaluate(**self.request());other=self.arena.start()
        with self.assertRaisesRegex(Conflict,'UNKNOWN_OR_CLOSED_TASK'):
            self.arena.evaluate(**{**self.request(),'session_id':other['session_id'],'task_id':r['next_task']['id']})
    def test_stale_response_after_inference_rejected(self):
        def advance():
            with self.arena.connect() as c:c.execute('UPDATE sessions SET version=1')
        self.client.hook=advance
        with self.assertRaisesRegex(Conflict,'STALE_VERSION'):self.arena.evaluate(**self.request())
        self.assertEqual(self.arena.read(self.session['session_id'])['tasks'],[])
    def test_failure_is_not_fixture(self):
        self.arena.client=Failing();r=self.arena.evaluate(**self.request())
        self.assertEqual(r['mode'],'MODEL_UNAVAILABLE');self.assertEqual(r['action'],'ASK_HUMAN')
        self.assertEqual(r['probabilities'],{});self.assertIsNone(r['latency_ms'])
    def test_no_raw_text_in_persistence(self):
        marker='합성_비공개_표시_84921 지금 송금하세요.'
        self.arena.evaluate(**{**self.request(),'text':marker})
        self.assertNotIn(marker.encode(),self.path.read_bytes())
        state=self.arena.read(self.session['session_id'])
        self.assertTrue(all('quote' not in e for event in state['events'] for e in event['evidence']))
    def test_invalid_controls_rejected_before_model(self):
        for patch in ({'synthetic_only':False},{'version':True},{'request_id':'../x'},{'text':''},
                      {'observation':'BANK_VERIFIED'},{'observation':'USER_REPORTS_CONFIRMED'}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):self.arena.evaluate(**{**self.request(),**patch})
        self.assertEqual(self.client.calls,0)

if __name__=='__main__':unittest.main()
