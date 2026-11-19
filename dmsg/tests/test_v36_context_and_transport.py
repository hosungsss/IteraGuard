"""Adversarial safety regression, using synthetic responses only."""
import os
import sys
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.model_bridge import ModelClient,ModelUnavailable,advisory
from prototype.context_guard import context_flags,context_conflict
from prototype.session import Store
from test_v35_model_bridge import sample,Stub

class ContextRegressions(unittest.TestCase):
    def check(self,text,action='transfer',speech='direct_request',expect='ASK_HUMAN'):
        result=advisory(text,sample(action=action,speech=speech))
        self.assertEqual(result['action'],expect,f'{text!r}: {result}')
        return result
    def test_explicit_warning_is_not_model_direct_request(self):
        for x in ('송금하지 마세요', '절대 송금하지 마세요', '송금하면 안 됩니다', '인증번호를 알려주지 마세요', 'Please do not transfer money'):
            with self.subTest(x=x):self.check(x)
    def test_quoted_instruction_is_not_direct(self):
        for x in ('그가 송금하라고 말했습니다', '그런 요청은 예시입니다: 송금하세요', '송금하라는 말을 들었어요', '상담원이 송금하라고 했다고 신고했습니다'):
            with self.subTest(x=x):self.check(x)
    def test_model_none_cannot_disguise_explicit_action_terms(self):
        for x in ('지금 송금하세요','주민등록번호 알려주세요','원격제어 앱 설치하세요','은행 계좌가 맞나요?'):
            with self.subTest(x=x): self.check(x,'none','negated_or_warning')
    def test_unsubstantiated_warning_label_cannot_clear_transfer(self):
        self.check('지금 송금하세요','transfer','negated_or_warning')
    def test_unsubstantiated_report_label_cannot_clear_transfer(self):
        self.check('지금 송금하세요','transfer','reported_or_quoted')
    def test_explicit_warning_remains_warning_when_label_matches(self):
        self.check('송금하지 마세요','transfer','negated_or_warning','NO_STRONG_SIGNAL')
    def test_explicit_report_remains_caution_when_label_matches(self):
        self.check('송금하라고 했습니다','transfer','reported_or_quoted','CAUTION')
    def test_direct_unambiguous_transfer_still_warns(self):
        self.check('지금 150만원 송금하세요','transfer','direct_request','PAUSE_AND_VERIFY')
    def test_mixed_messages_abstain_instead_of_choosing_scope(self):
        self.check('사기 예방 안내: 송금하지 마세요. 하지만 누군가 송금하세요라고 했습니다.')
    def test_noul_probabilities_not_scam_probability(self):
        r=advisory('지금 송금하세요',sample())
        self.assertEqual(r['calibration_status'],'NOT_ESTABLISHED')
        self.assertFalse(r['model_attested'])
        self.assertEqual(r['threshold_type'],'UNVALIDATED_DEMO_HEURISTIC')
    def test_no_raw_text_in_model_audit_log(self):
        st=Store();s=st.start()
        r=st.process_model(session_id=s['session_id'],turn_id='t1',version=0,text='송금하지 마세요',client=Stub(sample()))
        self.assertEqual(r['action'],'ASK_HUMAN')
        self.assertNotIn('송금하지 마세요',json.dumps(r['history'],ensure_ascii=False))
    def test_flags_are_not_claimed_as_semantic_proof(self):
        f=context_flags('송금하세요')
        self.assertTrue(f.action_mentioned)
        self.assertFalse(f.warning_cue)
        self.assertIsNone(context_conflict('transfer','direct_request',f))

class StubTransportHandler(BaseHTTPRequestHandler):
    mode='normal'
    def log_message(self,*args):pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length','0')))
        response=sample();response['model']='local-fixture'
        status=200
        ct='application/json'
        raw=json.dumps(response).encode('utf8')
        if type(self).mode=='duplicate':raw=b'{"model":"local-fixture","model":"injected","answers":{}}'
        if type(self).mode=='wrong_type':ct='text/html'
        if type(self).mode=='too_large':raw=b'X'*120001
        if type(self).mode=='bad_status':status=503
        self.send_response(status);self.send_header('Content-Type',ct);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

class TransportRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),StubTransportHandler)
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.worker.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def client(self):return ModelClient(endpoint=f'http://127.0.0.1:{self.server.server_port}/v1/systemone',model_id='local-fixture',enabled=True)
    def test_local_mock_http_only_unattested(self):
        StubTransportHandler.mode='normal';raw,ms=self.client().infer('송금하세요')
        self.assertEqual(raw['model'],'local-fixture');self.assertGreaterEqual(ms,0)
        self.assertFalse(self.client().status()['verified_model'])
    def test_duplicate_json_denied(self):
        StubTransportHandler.mode='duplicate'
        try:
            with self.assertRaises(ModelUnavailable) as cm:self.client().infer('송금하세요')
            self.assertEqual(str(cm.exception),'INVALID_RESPONSE_JSON')
        finally:StubTransportHandler.mode='normal'
    def test_wrong_response_content_type_denied(self):
        StubTransportHandler.mode='wrong_type'
        try:
            with self.assertRaises(ModelUnavailable) as cm:self.client().infer('송금하세요')
            self.assertEqual(str(cm.exception),'UNEXPECTED_MODEL_CONTENT_TYPE')
        finally:StubTransportHandler.mode='normal'
    def test_response_body_bounded(self):
        StubTransportHandler.mode='too_large'
        try:
            with self.assertRaises(ModelUnavailable) as cm:self.client().infer('송금하세요')
            self.assertEqual(str(cm.exception),'RESPONSE_TOO_LARGE')
        finally:StubTransportHandler.mode='normal'
    def test_bad_status_rejected(self):
        StubTransportHandler.mode='bad_status'
        try:
            with self.assertRaises(ModelUnavailable):self.client().infer('송금하세요')
        finally:StubTransportHandler.mode='normal'
    def test_remote_text_has_explicit_opt_in(self):
        with patch.dict(os.environ, {'DMSG_REMOTE_TEXT_CONSENT':'0'}):
            c=ModelClient(endpoint='https://model.example.org/v1/systemone',model_id='x',enabled=True)
            with self.assertRaises(ModelUnavailable) as cm:c._check_target()
            self.assertEqual(str(cm.exception),'REMOTE_TEXT_TRANSFER_NOT_CONSENTED')
    def test_remote_host_requires_allowlist(self):
        with patch.dict(os.environ, {'DMSG_REMOTE_TEXT_CONSENT':'1','DMSG_REMOTE_HOST_ALLOWLIST':''}):
            c=ModelClient(endpoint='https://model.example.org/v1/systemone',model_id='x',enabled=True)
            with self.assertRaises(ModelUnavailable) as cm:c._check_target()
            self.assertEqual(str(cm.exception),'REMOTE_HOST_NOT_ALLOWLISTED')
            self.assertFalse(c.status()['configured'])
    def test_remote_http_rejected_with_or_without_consent(self):
        with patch.dict(os.environ, {'DMSG_REMOTE_TEXT_CONSENT':'1'}):
            c=ModelClient(endpoint='http://remote.example.org/v1/systemone',model_id='x',enabled=True)
            with self.assertRaises(ModelUnavailable):c._check_target()
    def test_remote_metadata_ip_rejected(self):
        with patch.dict(os.environ, {'DMSG_REMOTE_TEXT_CONSENT':'1','DMSG_REMOTE_HOST_ALLOWLIST':'169.254.169.254'}):
            c=ModelClient(endpoint='https://169.254.169.254/v1/systemone',model_id='x',enabled=True)
            with self.assertRaises(ModelUnavailable):c._check_target()


# LAYER V4.7 — decision-relevant arbiter (DRA): merges same-guidance options, prices ASK_HUMAN, keeps advisory() intact.
from prototype.model_bridge import decision_relevant_advisory as _v47dra, abstention_cause as _v47cause, retemper as _v47rt, advisory as _v47adv
from prototype.model_bridge import ACTION_OPTIONS as _V47A, SPEECH_OPTIONS as _V47S


def _v47raw(a, pa, s, ps, scam=0.1, press=0.1):
    def d(opts, win, p):
        r = {o: (1 - p) / (len(opts) - 1) for o in opts}; r[win] = p; return r
    return {'answers': {'q_action': {'type': 'choice', 'probabilities': d(_V47A, a, pa)}, 'q_speech': {'type': 'choice', 'probabilities': d(_V47S, s, ps)},
                        'q_scam': {'type': 'noul', 'noul': scam}, 'q_claim': {'type': 'noul', 'noul': 0.1}, 'q_pressure': {'type': 'noul', 'noul': press}}}


class V47DecisionRelevantArbiter(unittest.TestCase):
    def test_harmless_request_cleared_where_v46_abstained(self):
        t, r = '택배 기사님, 경비실에 맡겨 주세요.', _v47raw('none', 0.8, 'direct_request', 0.9)
        self.assertEqual(_v47adv(t, r)['action'], 'ASK_HUMAN')
        self.assertEqual(_v47dra(t, r)['action'], 'NO_STRONG_SIGNAL')
        self.assertEqual(_v47cause(t, r)['cause_side'], 'GATE')
    def test_direct_high_risk_request_still_pauses_with_anchor(self):
        d = _v47dra('지금 바로 안전계좌로 이체하세요.', _v47raw('transfer', 0.6, 'direct_request', 0.6))
        self.assertEqual(d['action'], 'PAUSE_AND_VERIFY'); self.assertEqual(d['evidence'][0]['quote'], '이체')
    def test_model_span_alone_cannot_pause(self):
        d = _v47dra('확인 부탁드립니다.', _v47raw('transfer', 0.95, 'direct_request', 0.95), model_anchor=(0, 2, '확인'))
        self.assertNotEqual(d['action'], 'PAUSE_AND_VERIFY')
    def test_unclear_model_keeps_human_check(self):
        self.assertEqual(_v47dra('계좌 관련해서 처리할 게 있어요.', _v47raw('unclear', 0.7, 'unclear', 0.7))['action'], 'ASK_HUMAN')
    def test_retemper_identity(self):
        r = _v47raw('otp', 0.6, 'direct_request', 0.6)
        self.assertAlmostEqual(_v47rt(r, 1.52, 1.52)['answers']['q_action']['probabilities']['otp'], 0.6, places=12)

if __name__=='__main__':unittest.main()


# LAYER V4.2 — kev contract adaptation, clause-scoped guard, session binding.
# Every case below was a reproduced v4.1 counterexample (see internal/POST_RELEASE_AUDIT_V42.md).
from prototype.model_bridge import SPEC as _SPEC, questions as _questions, RISK_LEVELS as _RISK
from prototype.typed_contract import ContractError as _CE, normalize_response as _norm
# v4.5 added optional q_evidence; strict-normalization tests keep the six-question kev shape so a
# rejection is caused by the mutated field, not by the missing new key.
_SPEC6={k:v for k,v in _SPEC.items() if k!='q_evidence'}
from prototype.context_guard import clause_profile as _clauses


def kev_shaped(action='transfer', speech='direct_request', scam=.2, press=.2, risk_keys='label', drop=()):
    """Mimics only the publicly documented kev fields: answers/type/noul/probabilities. No 'model' echo."""
    q=_questions('x')['questions']
    def ch(opts,win,p=.9):
        r={o:(1-p)/(len(opts)-1) for o in opts}; r[win]=p; return r
    risk=q['q_risk']['criteria'] if risk_keys=='label' else [str(i) for i in range(len(_RISK))]
    ans={'q_action':{'type':'choice','probabilities':ch(list(q['q_action']['criteria']),action)},
         'q_speech':{'type':'choice','probabilities':ch(list(q['q_speech']['criteria']),speech)},
         'q_scam':{'type':'noul','noul':scam},'q_claim':{'type':'noul','noul':.1},
         'q_pressure':{'type':'noul','noul':press},
         'q_risk':{'type':'score','probabilities':ch(risk,risk[2])}}
    for k in drop: ans.pop(k)
    return {'answers':ans}


class V42KevContract(unittest.TestCase):
    def test_request_criteria_equal_accepted_response_keys(self):
        self.assertEqual(_questions('x')['questions']['q_risk']['criteria'],_SPEC['q_risk']['options'])
    def test_label_keyed_score_without_score_field_accepted(self):
        r=advisory('지금 바로 이 계좌로 송금하세요.',kev_shaped())
        self.assertEqual(r['action'],'PAUSE_AND_VERIFY')
    def test_index_keyed_score_maps_positionally(self):
        out=_norm(kev_shaped(risk_keys='index'),_SPEC6)
        self.assertEqual(out['q_risk']['key_format'],'INDEX_KEYS')
        self.assertEqual(set(out['q_risk']['probabilities']),set(_RISK))
    def test_foreign_score_keys_rejected(self):
        v=kev_shaped();v['answers']['q_risk']['probabilities']={'a':.5,'b':.5}
        with self.assertRaises(_CE):_norm(v,_SPEC6)
    def test_answer_type_mismatch_rejected(self):
        v=kev_shaped();v['answers']['q_scam']['type']='choice'
        with self.assertRaises(_CE):advisory('송금하세요',v)
    def test_optional_aux_absent_keeps_primary_decision(self):
        r=advisory('지금 송금하세요',kev_shaped(drop=('q_claim','q_risk')))
        self.assertEqual(r['action'],'PAUSE_AND_VERIFY')
        self.assertEqual(r['dropped_optional_questions'],['q_claim','q_evidence','q_risk'])
    def test_required_gate_question_absent_rejected(self):
        for k in ('q_action','q_speech','q_scam','q_pressure'):
            with self.subTest(k=k), self.assertRaises(_CE):
                advisory('지금 송금하세요',kev_shaped(drop=(k,)))
    def test_unknown_answer_key_still_rejected(self):
        v=kev_shaped();v['answers']['q_extra']={'type':'noul','noul':.5}
        with self.assertRaises(_CE):advisory('송금하세요',v)


class _KevHandler(BaseHTTPRequestHandler):
    echo=None; seen=[]
    def log_message(self,*a):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        type(self).seen.append(body)
        v=kev_shaped()
        if type(self).echo is not None: v['model']=type(self).echo
        raw=json.dumps(v).encode()
        self.send_response(200);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)


class V42KevTransport(unittest.TestCase):
    def setUp(self):
        _KevHandler.echo=None;_KevHandler.seen=[]
        self.srv=ThreadingHTTPServer(('127.0.0.1',0),_KevHandler)
        threading.Thread(target=self.srv.serve_forever,daemon=True).start()
        self.env={'DMSG_MODEL_ENABLED':'1','DMSG_MODEL_ID':'trillionlabs/Zoro-1',
                  'DMSG_SYSTEMONE_ENDPOINT':f'http://127.0.0.1:{self.srv.server_port}/v1/systemone'}
    def tearDown(self):self.srv.shutdown();self.srv.server_close()
    def run_turn(self,extra=None):
        env=dict(self.env,**(extra or {}))
        with patch.dict(os.environ,env,clear=False):
            for k in ('DMSG_SEND_MODEL_FIELD','DMSG_REQUIRE_MODEL_ECHO','DMSG_MODEL_TIMEOUT_S'):
                if k not in env: os.environ.pop(k,None)
            st=Store();s=st.start()
            return st.process_model(session_id=s['session_id'],turn_id='K1',version=0,text='지금 바로 이 계좌로 송금하세요.')
    def test_documented_shape_without_model_echo_reaches_policy(self):
        r=self.run_turn()
        self.assertEqual(r['action'],'PAUSE_AND_VERIFY');self.assertEqual(r['model_id_echo'],'ABSENT')
        self.assertFalse(r['verified_model'])
    def test_model_field_not_sent_by_default_but_opt_in(self):
        self.run_turn();self.assertNotIn('model',_KevHandler.seen[-1])
        self.run_turn({'DMSG_SEND_MODEL_FIELD':'1'});self.assertEqual(_KevHandler.seen[-1]['model'],'trillionlabs/Zoro-1')
    def test_present_but_different_echo_rejected_with_reason(self):
        _KevHandler.echo='other-model'
        r=self.run_turn();self.assertEqual(r['action'],'ASK_HUMAN')
        self.assertEqual(r['reason'],'ModelUnavailable:MODEL_ID_MISMATCH')
    def test_strict_echo_mode_rejects_absent_echo(self):
        r=self.run_turn({'DMSG_REQUIRE_MODEL_ECHO':'1'})
        self.assertEqual(r['reason'],'ModelUnavailable:MODEL_ID_ECHO_REQUIRED')
    def test_invalid_timeout_config_fails_closed(self):
        for bad in ('abc','0.1','999'):
            with self.subTest(bad=bad):
                r=self.run_turn({'DMSG_MODEL_TIMEOUT_S':bad})
                self.assertEqual(r['reason'],'ModelUnavailable:INVALID_TIMEOUT_CONFIG')


class V42ClauseScopedGuard(unittest.TestCase):
    IMPERATIVES=('지금 바로 이 계좌로 송금하세요.','인증번호 여섯 자리 알려주세요.','원격제어 앱 설치하세요.')
    DECOR_BEFORE=('[경고] 계좌가 동결됩니다. ','검찰 신고 사건입니다. ','피싱 예방 교육과 무관합니다. ','예시를 들 필요 없습니다. ')
    DECOR_AFTER=(' 가족에게 말하지 마세요.',' 은행에 알리지 마세요.',' 전화 끊지 마세요.')
    KIND={'송금':'transfer','인증번호':'otp','원격제어':'remote_install'}
    def kind(self,t):return next(v for k,v in self.KIND.items() if k in t)
    def test_metamorphic_decoration_cannot_remove_pause(self):
        """Adding warning/report words in ANOTHER clause must not change a correct direct label."""
        n=0
        for core in self.IMPERATIVES:
            for d in ('',)+self.DECOR_BEFORE:
                for e in ('',)+self.DECOR_AFTER:
                    t=d+core+e;n+=1
                    with self.subTest(t=t):
                        r=advisory(t,kev_shaped(self.kind(t),'direct_request'))
                        self.assertEqual(r['action'],'PAUSE_AND_VERIFY',r['reason'])
        self.assertEqual(n,60)
    def test_mislabel_as_warning_or_quote_never_clears_imperative(self):
        for core in self.IMPERATIVES:
            for e in ('',)+self.DECOR_AFTER:
                for sp in ('negated_or_warning','reported_or_quoted'):
                    for scam in (.05,.99):
                        t=core+e
                        with self.subTest(t=t,sp=sp,scam=scam):
                            r=advisory(t,kev_shaped(self.kind(t),sp,scam,scam))
                            self.assertNotIn(r['action'],('NO_STRONG_SIGNAL','CAUTION'),r['reason'])
    def test_secrecy_demand_is_pressure_not_warning(self):
        f=context_flags('가족에게 말하지 마세요');self.assertFalse(f.warning_cue);self.assertTrue(f.pressure_cue)
    def test_credential_nondisclosure_warning_preserved(self):
        f=context_flags('인증번호는 누구에게도 말하지 마세요');self.assertTrue(f.warning_cue)
        r=advisory('인증번호는 누구에게도 말하지 마세요.',kev_shaped('otp','negated_or_warning',.05,.05))
        self.assertEqual(r['action'],'NO_STRONG_SIGNAL')
    def test_genuine_warning_with_coercive_aux_and_pressure_abstains(self):
        r=advisory('송금하지 마세요. 지금 바로 결정해야 합니다.',kev_shaped('transfer','negated_or_warning',.95,.95))
        self.assertEqual(r['reason'],'AUX_COERCION_BLOCKS_WARNING_CLEARANCE')
    def test_genuine_quote_stays_caution(self):
        r=advisory('그 사람이 송금하라고 했어요.',kev_shaped('transfer','reported_or_quoted'))
        self.assertEqual(r['action'],'CAUTION')
    def test_anchor_is_inside_clean_clause(self):
        r=advisory('사기 예방: 송금하지 마세요. 지금 이 계좌로 송금하세요.',kev_shaped())
        self.assertEqual(r['action'],'PAUSE_AND_VERIFY');self.assertGreater(r['evidence'][0]['start'],10)
    def test_clause_profile_offsets_cover_text(self):
        t='A 송금. B 이체하세요\n하지만 C'
        for c in _clauses(t):self.assertTrue(0<=c.start<c.end<=len(t))


class V42SessionBinding(unittest.TestCase):
    def test_turn_retry_with_changed_version_rejected(self):
        st=Store();sid=st.start()['session_id']
        st.process(session_id=sid,turn_id='T1',version=0,text='안녕하세요')
        self.assertEqual(st.process(session_id=sid,turn_id='T1',version=0,text='안녕하세요')['version'],1)
        with self.assertRaises(Exception) as cm:st.process(session_id=sid,turn_id='T1',version=999,text='안녕하세요')
        self.assertIn('CONFLICTING_RETRY',str(cm.exception))
    def test_model_retry_with_changed_version_rejected(self):
        st=Store();sid=st.start()['session_id'];c=Stub(sample())
        st.process_model(session_id=sid,turn_id='M1',version=0,text='송금하세요',client=c)
        with self.assertRaises(Exception) as cm:st.process_model(session_id=sid,turn_id='M1',version=7,text='송금하세요',client=c)
        self.assertIn('CONFLICTING_RETRY',str(cm.exception));self.assertEqual(c.calls,1)
    def test_ack_retry_with_changed_version_rejected(self):
        st=Store();sid=st.start()['session_id']
        st.process(session_id=sid,turn_id='T1',version=0,text='안녕하세요')
        st.acknowledge(session_id=sid,event_id='T1',version=1)
        with self.assertRaises(Exception) as cm:st.acknowledge(session_id=sid,event_id='T1',version=12345)
        self.assertIn('CONFLICTING_RETRY',str(cm.exception))
    def test_keyless_recomputed_chain_detected(self):
        import hashlib
        st=Store();sid=st.start()['session_id']
        st.process(session_id=sid,turn_id='T1',version=0,text='안녕하세요')
        s=st._sessions[sid];s.history[0]['action']='PAUSE_AND_VERIFY';prev='GENESIS'
        for it in s.history:
            clean={k:v for k,v in it.items() if k not in('audit_prev','audit_hash')}
            it['audit_prev']=prev
            it['audit_hash']=hashlib.sha256((prev+'\n'+json.dumps(clean,ensure_ascii=False,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
            prev=it['audit_hash']
        s.audit_head=prev
        self.assertFalse(st.verify_audit(sid))


# LAYER V4.3 — cross-implementation portability (Python reference == JS port).
class V43Portability(unittest.TestCase):
    def test_unicode_digit_score_is_contract_error_not_value_error(self):
        v=kev_shaped(risk_keys='index');v['answers']['q_risk']['score']='²'
        with self.assertRaises(_CE):_norm(v,_SPEC6)
    def test_ascii_index_score_still_maps(self):
        v=kev_shaped(risk_keys='index');v['answers']['q_risk']['score']='2'
        self.assertEqual(_norm(v,_SPEC6)['q_risk']['score'],_RISK[2])
    def test_guard_patterns_have_no_inline_flag_groups(self):
        import re as _re
        from prototype import context_guard as cg
        pats=list(cg.WARNING_PATTERNS)+list(cg.REPORT_PATTERNS)+list(cg.PRESSURE_PATTERNS)+list(cg.REQUEST_CUES)+list(cg.SECRECY_IMPERATIVES)+[cg.CLAUSE_SPLIT.pattern,cg.CREDENTIAL_TOPIC]
        for p in pats:
            with self.subTest(p=p):self.assertIsNone(_re.search(r'\(\?[imsx]+:',p))
        self.assertTrue(cg.CLAUSE_SPLIT.flags & _re.IGNORECASE)
        self.assertEqual(len(_clauses('송금하세요 BUT do not tell')),2)
    def test_nonstandard_json_constants_rejected_by_transport(self):
        class H(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']));raw=b'{"answers":{"q_scam":{"noul":NaN}}}'
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        srv=ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=srv.serve_forever,daemon=True).start()
        try:
            c=ModelClient(endpoint=f'http://127.0.0.1:{srv.server_port}/v1/systemone',model_id='m',enabled=True)
            with self.assertRaises(ModelUnavailable) as cm:c.infer('합성 문장')
            self.assertEqual(str(cm.exception),'INVALID_RESPONSE_JSON')
        finally:srv.shutdown();srv.server_close()

# LAYER V4.5 — on-device NLP integration contract, informational speech act, model attribution span,
# team PRD/System Prompting v3.3 alignment (evidence_sufficient, forbidden phrases, locked-set hygiene).
# Appended to an existing module so the skill's file-path set stays identical to the baseline.
import hashlib as _v45hashlib, json as _v45json, re, subprocess as _v45sp, sys as _v45sys
from pathlib import Path as _V45Path
from prototype.model_bridge import advisory as _v45advisory, questions as _v45questions, SPEC as _V45SPEC, OPTIONAL_QUESTIONS, SPEECH_OPTIONS
_V45ROOT = _V45Path(__file__).resolve().parents[2]
_V45NLP = _V45ROOT / 'tools' / 'nlp'
_v45sys.path.insert(0, str(_V45NLP))


def _v45raw(action='transfer', speech='direct_request', p=.92, scam=.1, press=.1, evidence=None):
    def ch(opts, win):
        r = {o: (1 - p) / (len(opts) - 1) for o in opts}; r[win] = p; return r
    a = {'q_action': {'type': 'choice', 'probabilities': ch(_V45SPEC['q_action']['options'], action)},
         'q_speech': {'type': 'choice', 'probabilities': ch(_V45SPEC['q_speech']['options'], speech)},
         'q_scam': {'type': 'noul', 'noul': scam}, 'q_pressure': {'type': 'noul', 'noul': press}}
    if evidence is not None: a['q_evidence'] = {'type': 'noul', 'noul': evidence}
    return {'answers': a}


class V45Informational(unittest.TestCase):
    def test_option_present_and_requested(self):
        self.assertIn('informational', SPEECH_OPTIONS)
        self.assertIn('informational', _v45questions('x')['questions']['q_speech']['criteria'])
    def test_notice_cleared_without_safety_claim(self):
        r = _v45advisory('급여가 입금되었습니다.', _v45raw('transfer', 'informational'))
        self.assertEqual((r['action'], r['reason']), ('NO_STRONG_SIGNAL', 'MODEL_INFORMATIONAL_NOT_REQUEST'))
        self.assertIn('안전하다는 의미는 아닙니다', r['message'])
    def test_informational_label_cannot_hide_imperative(self):
        r = _v45advisory('지금 바로 이 계좌로 송금하세요.', _v45raw('transfer', 'informational'))
        self.assertEqual(r['action'], 'ASK_HUMAN')
        self.assertEqual(r['reason'], 'INFORMATIONAL_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE')
    def test_informational_with_coercion_abstains(self):
        r = _v45advisory('긴급 안내입니다. 계좌 정보가 변경되었습니다.', _v45raw('none', 'informational', scam=.95, press=.95))
        self.assertEqual(r['action'], 'ASK_HUMAN')


class V45ModelAttributionSpan(unittest.TestCase):
    T = '보안 점검 앱을 깔아 두셔야 합니다.'
    def test_span_used_only_when_no_lexical_anchor(self):
        r = _v45advisory(self.T, _v45raw('remote_install'), source='ON_DEVICE_NLP', model_anchor=(9, 11, '깔아'))
        self.assertEqual(r['action'], 'PAUSE_AND_VERIFY')
        self.assertEqual(r['evidence'][0]['origin'], 'MODEL_ATTRIBUTION_SPAN')
        self.assertEqual(r['grounding'], 'MODEL_ATTRIBUTION_SPAN_NOT_SEMANTIC_PROOF')
    def test_lexical_anchor_wins(self):
        r = _v45advisory('지금 송금하세요', _v45raw(), source='ON_DEVICE_NLP', model_anchor=(0, 2, '지금'))
        self.assertEqual(r['evidence'][0]['origin'], 'MODEL_SCHEMA_CHECKED'); self.assertEqual(r['evidence'][0]['quote'], '송금')
    def test_forged_or_empty_spans_rejected(self):
        for ma in [(9, 11, '송금'), (0, 0, ''), (-1, 2, '보안'), (0, 99, self.T), ('9', 11, '깔아'), (9, 11), (2, 3, ' ')]:
            with self.subTest(ma=ma):
                r = _v45advisory(self.T, _v45raw('remote_install'), source='ON_DEVICE_NLP', model_anchor=ma)
                self.assertEqual((r['action'], r['reason']), ('ASK_HUMAN', 'NO_GROUNDED_ACTION_ANCHOR'))
    def test_code_point_offsets_with_emoji(self):
        t = '😀 이 앱 깔아줘'
        r = _v45advisory(t, _v45raw('remote_install'), source='ON_DEVICE_NLP', model_anchor=(6, 8, '깔아'))
        self.assertEqual(r['evidence'][0]['start'], 6)


class V45EvidenceSufficient(unittest.TestCase):
    """Team PRD v3.3 rule 6 mapped to optional q_evidence; it may only move toward abstention."""
    def test_optional_and_requested(self):
        self.assertIn('q_evidence', OPTIONAL_QUESTIONS); self.assertIn('q_evidence', _v45questions('x')['questions'])
    def test_insufficient_blocks_clearance_and_caution(self):
        self.assertEqual(_v45advisory('송금하지 마세요', _v45raw('transfer', 'negated_or_warning', evidence=.05))['reason'], 'MODEL_EVIDENCE_INSUFFICIENT')
        self.assertEqual(_v45advisory('이 링크를 누르세요', _v45raw('link', evidence=.05))['action'], 'ASK_HUMAN')
    def test_grounded_direct_high_risk_keeps_priority(self):
        self.assertEqual(_v45advisory('지금 송금하세요', _v45raw(evidence=.05))['action'], 'PAUSE_AND_VERIFY')
    def test_sufficient_or_malformed_changes_nothing(self):
        self.assertEqual(_v45advisory('송금하지 마세요', _v45raw('transfer', 'negated_or_warning', evidence=.95))['action'], 'NO_STRONG_SIGNAL')
        r = _v45advisory('송금하지 마세요', _v45raw('transfer', 'negated_or_warning', evidence='bad'))
        self.assertEqual(r['action'], 'NO_STRONG_SIGNAL'); self.assertIn('q_evidence', r['dropped_optional_questions'])


class V45TypedMapping(unittest.TestCase):
    def setUp(self):
        import train_heads as T; self.T = T
    def test_request_mass_moves_to_informational_without_action(self):
        T = self.T
        ps = [0.6, 0.2, 0.05, 0.05, 0.1]; pa = [0.05, 0, 0, 0, 0, 0, 0.95]
        sp = T.typed_raw(ps, pa)['answers']['q_speech']['probabilities']
        self.assertAlmostEqual(sum(sp.values()), 1.0, places=9)
        self.assertGreater(sp['informational'], sp['direct_request'])
    def test_everyday_command_not_routed_to_conflict(self):
        T = self.T
        r = _v45advisory('시험 잘 봐! 끝나고 전화해.', T.typed_raw([0.9, 0.05, 0, 0, 0.05], [0, 0, 0, 0, 0, 0, 1.0]), source='ON_DEVICE_NLP', threshold=.5)
        self.assertEqual(r['action'], 'NO_STRONG_SIGNAL')


class V45Hygiene(unittest.TestCase):
    def test_locked_sets_frozen(self):
        for f in ('locked_handwritten.jsonl', 'locked_handwritten_v2.jsonl'):
            frz = _v45json.loads((_V45NLP / f.replace('.jsonl', '.freeze.json')).read_text('utf8'))
            self.assertEqual(_v45hashlib.sha256((_V45NLP / f).read_bytes()).hexdigest(), frz['sha256'], f)
    def test_locked_text_not_in_training_generator(self):
        gen = (_V45NLP / 'make_dataset.py').read_text('utf8')
        for f in ('locked_handwritten.jsonl', 'locked_handwritten_v2.jsonl'):
            for l in (_V45NLP / f).read_text('utf8').splitlines():
                t = _v45json.loads(l)['text']
                if len(t) > 12: self.assertNotIn(t, gen)
    def test_final_report_scored_v2_once_with_frozen_hash(self):
        rep = _v45json.loads((_V45NLP / 'eval' / 'nlp_eval_report_v45_final.json').read_text('utf8'))
        self.assertEqual(rep['locked_sha256'], rep['locked_freeze']['sha256'])
        self.assertEqual(rep['locked_handwritten_v2']['B3_real_zoro'], 'NOT_RUN')
    def test_nlp_assets_manifest_matches(self):
        man = _v45json.loads((_V45ROOT / 'apps/shared/nlp/NLP_ASSETS_MANIFEST.json').read_text('utf8'))
        for f, m in man['files'].items():
            self.assertEqual(_v45hashlib.sha256((_V45ROOT / 'apps/shared/nlp' / f).read_bytes()).hexdigest(), m['sha256'], f)
    def test_no_network_or_key_in_nlp_runtime(self):
        js = (_V45ROOT / 'apps/shared/dmsg-nlp.js').read_text('utf8')
        for bad in ('fetch(', 'XMLHttpRequest', 'WebSocket', 'api_key', 'apiKey', 'Authorization'):
            self.assertNotIn(bad, js)
    def test_forbidden_phrase_gate_passes_and_detects(self):
        r = _v45sp.run([_v45sys.executable, str(_V45ROOT / 'tools/check_forbidden_phrases.py')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-500:])
        spec = None
        pats = re.findall(r"r'([^']+)'", (_V45ROOT / 'tools/check_forbidden_phrases.py').read_text('utf8').split('FILES')[0])
        for s in ('이 통화는 안전합니다', '사기 확률 97%', '계좌 동결 완료'):
            self.assertTrue(any(re.search(p, s) for p in pats), s)





# LAYER V4.6 — structural evidence, risk-indicator policy (never downgrades), shipped-model golden snapshot.
from prototype.context_guard import structural_evidence as _v46se
from prototype.model_bridge import indicator_advisory as _v46ia, UNGROUNDED_MIN_PROBABILITY as _V46UMP
_V46_INFO = {'action': 'NO_STRONG_SIGNAL', 'reason': 'MODEL_INFORMATIONAL_NOT_REQUEST', 'selected_speech': 'informational'}


class V46StructuralEvidence(unittest.TestCase):
    def kinds(self, t): return [(e['kind'], e['quote']) for e in _v46se(t)]
    def test_messenger_handoff_and_tags(self):
        k = self.kinds('[국제발신] 안녕하세요 라인 아이디 sora_0921 로 연락 주세요')
        self.assertIn(('OVERSEAS_SENDER_TAG', '[국제발신]'), k); self.assertIn(('MESSENGER_HANDOFF', '라인 아이디 sora_0921'), k)
    def test_plain_messenger_mention_is_not_a_handoff(self):
        self.assertEqual(self.kinds('카톡이 안 돼서 라인으로 사진 보냈어'), [])
        self.assertEqual(self.kinds('Line is fun'), [])
    def test_url_phone_money_account_change(self):
        k = [x[0] for x in self.kinds('결제 계좌가 바뀌었어요. 50만원 http://cj-dlvry.top/k2 010-1234-5678')]
        for want in ('ACCOUNT_CHANGE_PHRASE', 'MONEY_AMOUNT', 'URL', 'PHONE'): self.assertIn(want, k)
    def test_email_not_url_and_offsets_are_code_points(self):
        self.assertEqual(self.kinds('메일 a@b.com'), [])
        e = _v46se('😀 라인 abc_12')[0]; self.assertEqual((e['start'], e['end']), (2, 11))


class V46IndicatorPolicy(unittest.TestCase):
    T = '[국제발신] 안녕하세요 라인 아이디 sora_0921 로 연락 주세요'
    def test_case_a_shape_structural_ground_gives_caution(self):
        r = _v46ia(self.T, _V46_INFO, {'OFF_PLATFORM_CONTACT': .9})
        self.assertEqual((r['action'], r['reason']), ('CAUTION', 'RISK_INDICATORS_WITHOUT_EXPLICIT_ACTION'))
        self.assertEqual(r['sender_identity'], 'UNVERIFIED')
    def test_no_explicit_action_is_not_safe_but_model_only_needs_strong_score(self):
        self.assertEqual(_v46ia('오늘 만나요', _V46_INFO, {'UNWANTED_SOLICITATION': .7})['action'], 'NO_STRONG_SIGNAL')
        self.assertEqual(_v46ia('오늘 만나요', _V46_INFO, {'UNWANTED_SOLICITATION': _V46UMP})['reason'], 'UNGROUNDED_RISK_INDICATOR')
    def test_model_span_explains_but_does_not_ground(self):
        r = _v46ia('오늘 만나요', _V46_INFO, {'UNWANTED_SOLICITATION': .9}, model_spans={'UNWANTED_SOLICITATION': (3, 5, '만나')})
        self.assertEqual(r['action'], 'ASK_HUMAN'); self.assertEqual(r['indicators'][0]['grounded_by'], 'MODEL_ONLY')
    def test_never_downgrades_and_warning_is_not_escalated(self):
        p = {'action': 'PAUSE_AND_VERIFY', 'reason': 'MODEL_DIRECT_ACTION_ADVISORY', 'selected_speech': 'direct_request'}
        self.assertEqual(_v46ia(self.T, p, {})['action'], 'PAUSE_AND_VERIFY')
        w = {'action': 'NO_STRONG_SIGNAL', 'reason': 'MODEL_WARNING_NOT_REQUEST', 'selected_speech': 'negated_or_warning'}
        self.assertEqual(_v46ia('라인 sora_0921 로 옮기자는 사람 조심하세요', w, {'OFF_PLATFORM_CONTACT': .99})['action'], 'NO_STRONG_SIGNAL')
    def test_high_severity_needs_structure_and_direct_request(self):
        t = '결제 계좌가 바뀌었습니다 새 계좌로 보내세요'
        d = {'action': 'CAUTION', 'reason': 'MODEL_DIRECT_CAUTION_ADVISORY', 'selected_speech': 'direct_request'}
        self.assertEqual(_v46ia(t, d, {'ACCOUNT_CHANGE_REQUEST': .9})['action'], 'PAUSE_AND_VERIFY')
        q = dict(d, selected_speech='reported_or_quoted')
        self.assertEqual(_v46ia(t, q, {'ACCOUNT_CHANGE_REQUEST': .9})['action'], 'CAUTION')
    def test_contract_errors(self):
        for bad in ({'X': .5}, {'OFF_PLATFORM_CONTACT': 1.5}, {'OFF_PLATFORM_CONTACT': True}, {'OFF_PLATFORM_CONTACT': float('nan')}):
            with self.subTest(bad=bad), self.assertRaises(_CE): _v46ia(self.T, _V46_INFO, bad)
        with self.assertRaises(_CE): _v46ia(self.T, {'action': 'SAFE', 'reason': 'x'}, {})
        with self.assertRaises(_CE): _v46ia(self.T, _V46_INFO, {}, thresholds={'OFF_PLATFORM_CONTACT': 0.99})


class V46ShippedModel(unittest.TestCase):
    def test_golden_snapshot_and_case_ab_not_cleared(self):
        import shutil
        if not shutil.which('node'): self.skipTest('node missing')
        r = _v45sp.run(['node', str(_V45ROOT / 'tools/nlp/regress_cases_v46.js')], capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout[-800:])
    def test_v46_locked_set_frozen_and_not_in_training(self):
        nlp = _V45ROOT / 'tools/nlp'; f = nlp / 'locked_v46_multitask.jsonl'
        self.assertEqual(_v45hashlib.sha256(f.read_bytes()).hexdigest(), _v45json.loads((nlp / 'locked_v46_multitask.freeze.json').read_text('utf8'))['sha256'])
        train = (nlp / 'data' / 'v46_train.jsonl').read_text('utf8')
        for l in f.read_text('utf8').splitlines():
            self.assertNotIn(_v45json.loads(l)['text'], train)


# LAYER V4.7 — decision-relevant arbiter (DRA): merges same-guidance options, prices ASK_HUMAN, keeps advisory() intact.
from prototype.model_bridge import decision_relevant_advisory as _v47dra, abstention_cause as _v47cause, retemper as _v47rt, advisory as _v47adv
from prototype.model_bridge import ACTION_OPTIONS as _V47A, SPEECH_OPTIONS as _V47S


def _v47raw(a, pa, s, ps, scam=0.1, press=0.1):
    def d(opts, win, p):
        r = {o: (1 - p) / (len(opts) - 1) for o in opts}; r[win] = p; return r
    return {'answers': {'q_action': {'type': 'choice', 'probabilities': d(_V47A, a, pa)}, 'q_speech': {'type': 'choice', 'probabilities': d(_V47S, s, ps)},
                        'q_scam': {'type': 'noul', 'noul': scam}, 'q_claim': {'type': 'noul', 'noul': 0.1}, 'q_pressure': {'type': 'noul', 'noul': press}}}


class V47DecisionRelevantArbiter(unittest.TestCase):
    def test_harmless_request_cleared_where_v46_abstained(self):
        t, r = '택배 기사님, 경비실에 맡겨 주세요.', _v47raw('none', 0.8, 'direct_request', 0.9)
        self.assertEqual(_v47adv(t, r)['action'], 'ASK_HUMAN')
        self.assertEqual(_v47dra(t, r)['action'], 'NO_STRONG_SIGNAL')
        self.assertEqual(_v47cause(t, r)['cause_side'], 'GATE')
    def test_direct_high_risk_request_still_pauses_with_anchor(self):
        d = _v47dra('지금 바로 안전계좌로 이체하세요.', _v47raw('transfer', 0.6, 'direct_request', 0.6))
        self.assertEqual(d['action'], 'PAUSE_AND_VERIFY'); self.assertEqual(d['evidence'][0]['quote'], '이체')
    def test_model_span_alone_cannot_pause(self):
        d = _v47dra('확인 부탁드립니다.', _v47raw('transfer', 0.95, 'direct_request', 0.95), model_anchor=(0, 2, '확인'))
        self.assertNotEqual(d['action'], 'PAUSE_AND_VERIFY')
    def test_unclear_model_keeps_human_check(self):
        self.assertEqual(_v47dra('계좌 관련해서 처리할 게 있어요.', _v47raw('unclear', 0.7, 'unclear', 0.7))['action'], 'ASK_HUMAN')
    def test_retemper_identity(self):
        r = _v47raw('otp', 0.6, 'direct_request', 0.6)
        self.assertAlmostEqual(_v47rt(r, 1.52, 1.52)['answers']['q_action']['probabilities']['otp'], 0.6, places=12)

if __name__=='__main__':unittest.main()
