"""v4.7 decision-relevant arbiter, abstention-cause audit and re-tempering (offline)."""
import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dmsg')); sys.path.insert(0, str(ROOT))
from prototype import model_bridge as mb  # noqa: E402
from prototype.typed_contract import ContractError  # noqa: E402
from tools.zoro.abstention_audit import audit  # noqa: E402

A, S = mb.ACTION_OPTIONS, mb.SPEECH_OPTIONS


def dist(opts, win, p, second=None, p2=0.0):
    rest = [o for o in opts if o not in (win, second)]
    r = {o: (1 - p - p2) / len(rest) for o in rest}; r[win] = p
    if second: r[second] = p2
    return r


def raw(pa, ps, scam=0.1, press=0.1, evidence=None):
    a = {'q_action': {'type': 'choice', 'probabilities': pa}, 'q_speech': {'type': 'choice', 'probabilities': ps},
         'q_scam': {'type': 'noul', 'noul': scam}, 'q_claim': {'type': 'noul', 'noul': 0.1}, 'q_pressure': {'type': 'noul', 'noul': press}}
    if evidence is not None: a['q_evidence'] = {'type': 'noul', 'noul': evidence}
    return {'answers': a}


class DRA(unittest.TestCase):
    def test_harmless_request_is_not_a_contradiction(self):
        t = '택배 기사님, 경비실에 맡겨 주세요.'
        r = raw(dist(A, 'none', 0.8), dist(S, 'direct_request', 0.9))
        self.assertEqual(mb.advisory(t, r)['reason'], 'NONE_DIRECT_REQUEST_CONFLICT')
        self.assertEqual(mb.decision_relevant_advisory(t, r)['action'], 'NO_STRONG_SIGNAL')

    def test_speech_uncertainty_irrelevant_when_no_action(self):
        t = '우리 내일 영화 보러 갈래?'
        r = raw(dist(A, 'none', 0.75), dist(S, 'direct_request', 0.45, 'informational', 0.4))
        self.assertEqual(mb.advisory(t, r)['action'], 'ASK_HUMAN')
        self.assertEqual(mb.decision_relevant_advisory(t, r)['action'], 'NO_STRONG_SIGNAL')

    def test_split_mass_same_decision_class(self):
        # transfer 0.45 + otp 0.40 are both HIGH: a direct request for either deserves a pause
        t = '지금 이 계좌로 송금하고 인증번호도 알려 주세요.'
        r = raw(dist(A, 'transfer', 0.45, 'otp', 0.40), dist(S, 'direct_request', 0.85))
        self.assertEqual(mb.advisory(t, r)['action'], 'ASK_HUMAN')
        d = mb.decision_relevant_advisory(t, r)
        self.assertEqual(d['action'], 'PAUSE_AND_VERIFY'); self.assertTrue(d['evidence'])

    def test_pause_needs_lexical_anchor(self):
        t = '확인 부탁드립니다.'           # no action words at all
        r = raw(dist(A, 'transfer', 0.9), dist(S, 'direct_request', 0.9))
        d = mb.decision_relevant_advisory(t, r, model_anchor=(0, 2, '확인'))
        self.assertNotEqual(d['action'], 'PAUSE_AND_VERIFY')

    def test_genuine_uncertainty_still_asks(self):
        t = '계좌 관련해서 처리할 게 있어요.'
        r = raw(dist(A, 'unclear', 0.6, 'transfer', 0.3), dist(S, 'unclear', 0.6))
        self.assertEqual(mb.decision_relevant_advisory(t, r)['action'], 'ASK_HUMAN')

    def test_warning_clears_without_veto(self):
        t = '인증번호는 누구에게도 알려 주지 마세요.'
        r = raw(dist(A, 'otp', 0.85), dist(S, 'negated_or_warning', 0.85))
        self.assertIn(mb.decision_relevant_advisory(t, r)['action'], ('NO_STRONG_SIGNAL', 'CAUTION'))

    def test_coercion_and_evidence_doubt_never_clear_more(self):
        t = '지금 당장 해야 해요. 아무에게도 말하지 마세요.'
        calm = mb.decision_relevant_advisory(t, raw(dist(A, 'none', 0.8), dist(S, 'informational', 0.8)))
        hot = mb.decision_relevant_advisory(t, raw(dist(A, 'none', 0.8), dist(S, 'informational', 0.8), scam=0.95, press=0.95, evidence=0.9))
        self.assertLessEqual(hot['guidance_distribution']['NO_STRONG_SIGNAL'], calm['guidance_distribution']['NO_STRONG_SIGNAL'])

    def test_costs_validated(self):
        r = raw(dist(A, 'none', 0.8), dist(S, 'informational', 0.8))
        with self.assertRaises(ContractError): mb.decision_relevant_advisory('안녕', r, costs={'x': (1.0,)})
        with self.assertRaises(ContractError): mb.decision_relevant_advisory('', r)

    def test_distribution_sums_to_one(self):
        r = raw(dist(A, 'link', 0.5, 'none', 0.3), dist(S, 'reported_or_quoted', 0.5))
        d = mb.decision_relevant_advisory('링크 누르라는 문자가 왔대', r)
        self.assertAlmostEqual(sum(d['guidance_distribution'].values()), 1.0, places=9)


class Audit(unittest.TestCase):
    def test_cause_buckets(self):
        t = '택배 기사님, 경비실에 맡겨 주세요.'
        c = mb.abstention_cause(t, raw(dist(A, 'none', 0.8), dist(S, 'direct_request', 0.9)))
        self.assertEqual(c['cause'], 'GATE_ONTOLOGY_GAP_HARMLESS_REQUEST'); self.assertEqual(c['cause_side'], 'GATE')
        c2 = mb.abstention_cause('우리 영화 볼래?', raw(dist(A, 'none', 0.75), dist(S, 'informational', 0.45, 'direct_request', 0.4)))
        self.assertEqual(c2['cause'], 'GATE_DECISION_IRRELEVANT_SPEECH_THRESHOLD')
        c3 = mb.abstention_cause('지금 송금하고 인증번호도 알려 주세요', raw(dist(A, 'transfer', 0.45, 'otp', 0.4), dist(S, 'direct_request', 0.85)))
        self.assertEqual(c3['cause'], 'GATE_SPLIT_MASS_SAME_DECISION_CLASS')
        c4 = mb.abstention_cause('계좌 관련 처리', raw(dist(A, 'unclear', 0.6), dist(S, 'unclear', 0.6)))
        self.assertEqual(c4['cause_side'], 'MODEL')

    def test_audit_tool_end_to_end(self):
        labels = [{'id': 'X1', 'text': '택배 기사님, 경비실에 맡겨 주세요.', 'expect': ['NO_STRONG_SIGNAL'], 'risky': False},
                  {'id': 'X2', 'text': '지금 송금하고 인증번호도 알려 주세요.', 'expect': ['PAUSE_AND_VERIFY'], 'risky': True}]
        rawi = [{'id': 'X1', 'response': raw(dist(A, 'none', 0.8), dist(S, 'direct_request', 0.9))},
                {'id': 'X2', 'response': raw(dist(A, 'transfer', 0.45, 'otp', 0.4), dist(S, 'direct_request', 0.85))}]
        rep = audit(rawi, labels)
        self.assertEqual(rep['summary']['advisory_abstain'], 2); self.assertEqual(rep['summary']['dra_abstain'], 0)
        self.assertEqual(rep['summary']['abstain_side'].get('GATE'), 2)
        self.assertIn('2.19', rep['items'][0]['sweep'])

    def test_retemper_exact(self):
        r = raw(dist(A, 'transfer', 0.6), dist(S, 'direct_request', 0.6))
        same = mb.retemper(r, 1.52, 1.52)
        self.assertAlmostEqual(same['answers']['q_action']['probabilities']['transfer'], 0.6, places=12)
        flat = mb.retemper(r, 1.52, 3.0)
        self.assertLess(flat['answers']['q_action']['probabilities']['transfer'], 0.6)
        back = mb.retemper(flat, 3.0, 1.52)
        self.assertAlmostEqual(back['answers']['q_action']['probabilities']['transfer'], 0.6, places=9)


if __name__ == '__main__':
    unittest.main()
