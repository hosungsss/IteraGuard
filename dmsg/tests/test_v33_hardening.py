"""Safety boundary, ontology, audit, and contract tests for current implementation."""
import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.core import Action,Kind,Origin,Directness,Evidence,Status,decide,quote_from
from prototype.session import Store,Conflict
from prototype.ontology import assess_evidence
from prototype.typed_contract import normalize_response,ContractError
from prototype.decision_oracle import inspect_response
from prototype.fixtures import CASES,FIXTURES
from scripts.evaluate_fixtures import assess as fixture_assess

class OntologyBoundary(unittest.TestCase):
    def test_ontology_never_claims_external_verification(self):
        f=FIXTURES['RISK_TRANSFER'];a=assess_evidence(f.evidence)
        self.assertFalse(a.independent_verification)
        self.assertFalse(a.external_action_performed)
        self.assertEqual(a.edges[0].predicate,'REQUESTS')
        self.assertEqual(a.edges[0].epistemic_status,'PREANNOTATED_SIMULATION')
    def test_quotes_not_direct(self):
        f=FIXTURES['REPORTED'];a=assess_evidence(f.evidence)
        self.assertEqual(a.edges[0].predicate,'REPORTS')
    def test_negation_not_direct(self):
        f=FIXTURES['NEGATIVE_OTP'];a=assess_evidence(f.evidence)
        self.assertEqual(a.edges[0].predicate,'WARNS_AGAINST')
    def test_conflict_in_overlapping_evidence_abstains(self):
        t='송금하세요';a=quote_from(t,t,Kind.TRANSFER,Directness.DIRECT_REQUEST)
        b=quote_from(t,t,Kind.TRANSFER,Directness.NEGATED_OR_WARNING)
        self.assertEqual(decide(t,(a,b)).action,Action.ASK_HUMAN)
    def test_same_redundant_evidence_not_conflict(self):
        t='송금하세요';a=quote_from(t,t,Kind.TRANSFER,Directness.DIRECT_REQUEST)
        self.assertEqual(decide(t,(a,a)).action,Action.PAUSE_AND_VERIFY)
    def test_model_claim_is_untrusted_in_ontology(self):
        e=Evidence(Kind.OTP,0,3,'OTP',Directness.DIRECT_REQUEST,Origin.MODEL_PROPOSED)
        self.assertEqual(assess_evidence((e,)).edges[0].epistemic_status,'MODEL_PROPOSAL_UNVERIFIED')

class AuditChain(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.sid=self.store.start()['session_id']
    def test_chain_turn_ack_turn(self):
        s=self.store
        r=s.process(session_id=self.sid,turn_id='one',version=0,fixture_id='RISK_TRANSFER')
        self.assertTrue(s.verify_audit(self.sid))
        a=s.acknowledge(session_id=self.sid,event_id='one',version=1)
        self.assertTrue(s.verify_audit(self.sid))
        r2=s.process(session_id=self.sid,turn_id='two',version=2,fixture_id='NORMAL_BANK')
        self.assertTrue(s.verify_audit(self.sid))
        self.assertEqual(r2['history'][1]['audit_prev'],r['history'][0]['audit_hash'])
    def test_return_mutations_do_not_change_store_or_cached_response(self):
        s=self.store
        r=s.process(session_id=self.sid,turn_id='one',version=0,fixture_id='RISK_TRANSFER')
        r['history'][0]['action']='HACKED';r['evidence'][0]['quote']='TOKEN'
        again=s.process(session_id=self.sid,turn_id='one',version=0,fixture_id='RISK_TRANSFER')
        self.assertNotEqual(again['history'][0]['action'],'HACKED')
        self.assertNotEqual(again['evidence'][0]['quote'],'TOKEN')
        self.assertTrue(s.verify_audit(self.sid))
    def test_internal_modification_detected(self):
        self.store.process(session_id=self.sid,turn_id='one',version=0,fixture_id='RISK_TRANSFER')
        self.store._sessions[self.sid].history[0]['reason']='TAMPERED'
        self.assertFalse(self.store.verify_audit(self.sid))
    def test_hash_not_claimed_as_external_attestation(self):
        r=self.store.process(session_id=self.sid,turn_id='one',version=0,fixture_id='RISK_TRANSFER')
        self.assertEqual(r['audit_integrity'],'UNSIGNED_LOCAL_HASH_CHAIN')
    def test_raw_manual_text_not_in_history(self):
        r=self.store.process(session_id=self.sid,turn_id='one',version=0,text='MY_SECRET_1234')
        self.assertNotIn('MY_SECRET_1234',str(r['history']))

class TypedEvidence(unittest.TestCase):
    def test_score_supported(self):
        a=normalize_response({'answers':{'severity':{'score':'high','probabilities':{'low':.1,'high':.9}}}},
             {'severity':{'type':'score','options':['low','high']}})
        self.assertEqual(a['severity']['score'],'high')
    def test_score_probability_nan_rejected(self):
        with self.assertRaises(ContractError):
            normalize_response({'answers':{'severity':{'score':'high','probabilities':{'low':float('nan'),'high':1}}}},
             {'severity':{'type':'score','options':['low','high']}})
    def test_proposal_never_authorizes_high_risk(self):
        raw={'answers':{'request_action':{'choice':'transfer',
            'probabilities':{'transfer':1.0,'otp':0,'remote_install':0,'link':0,'none':0,'unclear':0}},
            'direct_instruction':{'noul':1.0}}}
        t='지금 송금하세요';p=inspect_response(t,raw,3,len(t))
        self.assertEqual(p.policy_action,Action.ASK_HUMAN)
        self.assertEqual(p.source_status,'UNVERIFIED_MODEL_PROPOSAL')
        self.assertFalse(p.confidence_is_scam_probability)
        self.assertEqual(p.evidence.origin,Origin.MODEL_PROPOSED)
    def test_bad_proposal_span_rejected(self):
        raw={'answers':{'request_action':{'choice':'transfer',
            'probabilities':{'transfer':1.0,'otp':0,'remote_install':0,'link':0,'none':0,'unclear':0}},
            'direct_instruction':{'noul':1.0}}}
        with self.assertRaises(ValueError):inspect_response('text',raw,-1,2)

class FixtureConformance(unittest.TestCase):
    def test_all_authored_cases_conform(self):
        a=fixture_assess()
        self.assertEqual(a['pass_count'],a['sample_size'])
        self.assertEqual(a['sample_size'],len(CASES))
        self.assertFalse(a['independent_validation'])
    def test_distinct_families(self):
        self.assertEqual(len(set(f.family for f in CASES)),len(CASES))
    def test_legal_transfer_remains_action_paused_not_scam_labeled(self):
        f=FIXTURES['LEGIT_TRANSFER'];r=decide(f.transcript,f.evidence)
        self.assertEqual(r.action,Action.PAUSE_AND_VERIFY)
        self.assertNotIn('사기 확정',r.message)

if __name__=='__main__':unittest.main()
