"""v3.4 runtime trust-boundary / release evidence regression tests."""
import sys, unittest, json, inspect
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.session import Store,Conflict
from prototype.server import Handler
from scripts.metamorphic_audit import report
class Linkage(unittest.TestCase):
    def setUp(self):
        self.s=Store();self.sid=self.s.start()['session_id']
    def test_ack_requires_matching_turn(self):
        self.s.process(session_id=self.sid,turn_id='T1',version=0,fixture_id='RISK_TRANSFER')
        with self.assertRaisesRegex(Conflict,'ACK_NOT_LINKED_TO_LATEST_TURN'):
            self.s.acknowledge(session_id=self.sid,event_id='RANDOM',version=1)
        self.assertEqual(self.s.acknowledge(session_id=self.sid,event_id='T1',version=1)['linked_turn_id'],'T1')
    def test_ack_stale_prior_turn_rejected(self):
        self.s.process(session_id=self.sid,turn_id='T1',version=0,fixture_id='NORMAL_BANK')
        self.s.process(session_id=self.sid,turn_id='T2',version=1,fixture_id='RISK_TRANSFER')
        with self.assertRaisesRegex(Conflict,'ACK_NOT_LINKED_TO_LATEST_TURN'):
            self.s.acknowledge(session_id=self.sid,event_id='T1',version=2)
    def test_mutated_audit_prevents_turn(self):
        self.s.process(session_id=self.sid,turn_id='T1',version=0,fixture_id='RISK_TRANSFER')
        self.s._sessions[self.sid].history[0]['action']='REWRITTEN'
        with self.assertRaisesRegex(Conflict,'AUDIT_INTEGRITY_FAILED'):
            self.s.process(session_id=self.sid,turn_id='T2',version=1,fixture_id='NORMAL_BANK')
    def test_mutated_audit_prevents_ack(self):
        self.s.process(session_id=self.sid,turn_id='T1',version=0,fixture_id='NORMAL_BANK')
        self.s._sessions[self.sid].audit_head='HACKED'
        with self.assertRaisesRegex(Conflict,'AUDIT_INTEGRITY_FAILED'):
            self.s.acknowledge(session_id=self.sid,event_id='T1',version=1)
    def test_ack_result_detached(self):
        self.s.process(session_id=self.sid,turn_id='T1',version=0,fixture_id='RISK_TRANSFER')
        r=self.s.acknowledge(session_id=self.sid,event_id='T1',version=1)
        r['history'][0]['action']='WRONG'
        self.assertTrue(self.s.verify_audit(self.sid))
        self.assertNotEqual(self.s.acknowledge(session_id=self.sid,event_id='T1',version=1)['history'][0]['action'],'WRONG')
class Metamorphic(unittest.TestCase):
    def test_synthetic_invariants(self):
        r=report();self.assertEqual(r['checks'],r['passed']);self.assertFalse(r['independent_validation'])
class HTTPContext(unittest.TestCase):
    def context(self, headers):
        obj=object.__new__(Handler)
        from email.message import Message
        msg=Message()
        for k,v in headers:msg.add_header(k,v)
        obj.headers=msg
        return obj._request_context_safe()
    def test_reject_cross_origin(self):
        self.assertFalse(self.context([('Content-Length','2'),('Origin','https://evil.example')]))
    def test_reject_cross_site_fetch(self):
        self.assertFalse(self.context([('Content-Length','2'),('Sec-Fetch-Site','cross-site')]))
    def test_reject_duplicate_length(self):
        self.assertFalse(self.context([('Content-Length','2'),('Content-Length','4')]))
    def test_reject_chunked(self):
        self.assertFalse(self.context([('Content-Length','2'),('Transfer-Encoding','chunked')]))
    def test_accept_matching_local_origin(self):
        self.assertTrue(self.context([('Content-Length','2'),('Origin','http://127.0.0.1:8765'),('Sec-Fetch-Site','same-origin')]))
if __name__=='__main__':unittest.main()
