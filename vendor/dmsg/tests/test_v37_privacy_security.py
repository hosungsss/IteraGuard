"""v3.7: privacy, auxiliary-signal, pinned remote TLS synthetic regressions."""
from __future__ import annotations
import copy,json,os,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.model_bridge import ModelClient,ModelUnavailable,advisory
from prototype.session import Store
from prototype.core import fingerprint
from test_v35_model_bridge import sample,Stub

class PrivacyTests(unittest.TestCase):
    def _run(self,store):
        s=store.start()
        return store.process_model(session_id=s['session_id'],turn_id='T1',version=0,text='송금하세요',client=Stub(sample()))
    def test_no_unsalted_sha_in_history(self):
        v=self._run(Store());strval=str(v['history'])
        self.assertNotIn('transcript_sha256',strval)
        self.assertNotIn(fingerprint('송금하세요'),strval)
        self.assertNotIn('송금하세요',strval)
    def test_private_digest_stable_only_within_store(self):
        store=Store();h1=store._private_digest('송금하세요');h2=store._private_digest('송금하세요')
        self.assertEqual(h1,h2)
        self.assertNotEqual(h1,Store()._private_digest('송금하세요'))
    def test_audit_remains_valid_with_private_digest(self):
        store=Store();s=store.start();self._run # distinct path below
        store.process_model(session_id=s['session_id'],turn_id='T1',version=0,text='송금하세요',client=Stub(sample()))
        self.assertTrue(store.verify_audit(s['session_id']))
    def test_digest_never_labeled_safety_evidence(self):
        st=Store();a=self._run(st)
        self.assertIn('transcript_hmac_sha256',a['history'][-1])
        self.assertNotIn('transcript_sha256',a['history'][-1])

class AuxiliarySignalTests(unittest.TestCase):
    def test_none_high_pressure_abstains(self):
        r=sample(action='none',speech='negated_or_warning');r['answers']['q_scam']['noul']=.1
        r['answers']['q_pressure']['noul']=.92
        x=advisory('지금 바로 진행하셔야 합니다',r)
        self.assertEqual(x['action'],'ASK_HUMAN')
        self.assertEqual(x['reason'],'CONFLICTING_MODEL_QUESTIONS')
    def test_none_low_pressure_no_safety_claim(self):
        r=sample(action='none',speech='negated_or_warning');r['answers']['q_scam']['noul']=.1
        r['answers']['q_pressure']['noul']=.10
        x=advisory('좋은 하루 되세요',r)
        self.assertEqual(x['action'],'NO_STRONG_SIGNAL')
        self.assertIn('안전하다는 의미는 아닙니다',x['message'])
    def test_claim_only_does_not_force_warning(self):
        r=sample(action='none',speech='negated_or_warning');r['answers']['q_scam']['noul']=.1
        r['answers']['q_pressure']['noul']=.1;r['answers']['q_claim']['noul']=.95
        self.assertEqual(advisory('OO은행입니다',r)['action'],'NO_STRONG_SIGNAL')
    def test_direct_grounded_risk_still_warns(self):
        self.assertEqual(advisory('송금하세요',sample())['action'],'PAUSE_AND_VERIFY')

class RemoteTransportTests(unittest.TestCase):
    def settings(self):
        return patch.dict(os.environ,{'DMSG_REMOTE_TEXT_CONSENT':'1','DMSG_REMOTE_HOST_ALLOWLIST':'model.example.com'})
    def client(self):
        return ModelClient(endpoint='https://model.example.com/v1/systemone',model_id='operator-test-stub',enabled=True)
    def test_dns_pinning_ip_is_verified_and_reused(self):
        addr=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        with self.settings(),patch('prototype.model_bridge.socket.getaddrinfo',return_value=addr):
            c=self.client();self.assertEqual(c._check_target().hostname,'model.example.com')
            self.assertEqual(c._pinned_ip,'8.8.8.8')
    def test_mixed_dns_answers_block_remote(self):
        addr=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]
        with self.settings(),patch('prototype.model_bridge.socket.getaddrinfo',return_value=addr):
            with self.assertRaises(ModelUnavailable) as cm:self.client()._check_target()
            self.assertEqual(str(cm.exception),'NON_PUBLIC_ENDPOINT_IP')
    def test_pinned_http_path_avoids_urllib_dns_resolution(self):
        addr=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        info={'calls':[]}
        class Response:
            status=200
            def getheader(self,k,default=''):return 'application/json'
            def read(self,n):return json.dumps(sample()).encode('utf8')
        class Conn:
            def __init__(self,host,ip,port,timeout):info['args']=(host,ip,port,timeout)
            def request(self,method,path,body,headers):info['calls'].append((method,path,headers.get('Content-Type')))
            def getresponse(self):return Response()
            def close(self):info['closed']=True
        with self.settings(),patch('prototype.model_bridge.socket.getaddrinfo',return_value=addr),patch('prototype.model_bridge._PinnedHTTPSConnection',Conn),patch('prototype.model_bridge.urllib.request.build_opener',side_effect=AssertionError('no urllib for remote')):
            raw,latency=self.client().infer('합성 문장')
        self.assertEqual(info['args'],('model.example.com','8.8.8.8',443,4.0))
        self.assertEqual(info['calls'],[('POST','/v1/systemone','application/json')]);self.assertTrue(info['closed'])
        self.assertEqual(raw['model'],'operator-test-stub')
    def test_remote_response_bad_type_fails_closed(self):
        addr=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        class Response:
            status=200
            def getheader(self,k,default=''):return 'text/plain'
            def read(self,n):return b'{}'
        class Conn:
            def __init__(self,*args,**kwargs):pass
            def request(self,*args,**kwargs):pass
            def getresponse(self):return Response()
            def close(self):pass
        with self.settings(),patch('prototype.model_bridge.socket.getaddrinfo',return_value=addr),patch('prototype.model_bridge._PinnedHTTPSConnection',Conn):
            with self.assertRaises(ModelUnavailable):self.client().infer('합성 문장')
    def test_remote_unlisted_blocked_before_resolution(self):
        with patch.dict(os.environ,{'DMSG_REMOTE_TEXT_CONSENT':'1','DMSG_REMOTE_HOST_ALLOWLIST':'unrelated.example'}),patch('prototype.model_bridge.socket.getaddrinfo',side_effect=AssertionError('dns should not occur')):
            with self.assertRaises(ModelUnavailable):self.client().infer('합성 문장')

if __name__=='__main__':unittest.main()

class PinnedTLSInternalsTests(unittest.TestCase):
    def test_tls_sni_uses_hostname_while_socket_uses_verified_ip(self):
        from prototype.model_bridge import _PinnedHTTPSConnection
        class Socket:
            closed=False
            def close(self):self.closed=True
        raw_sock=Socket(); wrapped=object(); trace={}
        class Context:
            check_hostname=True
            def wrap_socket(self,sock,server_hostname):
                trace['sni']=server_hostname;trace['sock']=sock
                return wrapped
        def creator(address,timeout,source_address):
            trace['target']=address;trace['timeout']=timeout;return raw_sock
        with patch('prototype.model_bridge.ssl.create_default_context',return_value=Context()),patch('prototype.model_bridge.socket.create_connection',side_effect=creator):
            conn=_PinnedHTTPSConnection('model.example.com','8.8.8.8',443,4.0)
            conn.connect()
            self.assertEqual(trace['target'],('8.8.8.8',443))
            self.assertEqual(trace['sni'],'model.example.com')
            self.assertIs(conn.sock,wrapped)
