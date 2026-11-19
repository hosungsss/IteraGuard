"""Bounded rule-tweak observations. This is NOT independent model accuracy."""
import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from integration import rule_tweak_shadow as tweak

class RuleTweakShadow(unittest.TestCase):
    def setUp(self):
        self.base = {
            "action": "ASK_HUMAN", "reason": "MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS",
            "semantic_trace": {"rule_id": "BASELINE_FALLBACK",
                               "baseline_action": "ASK_HUMAN"},
            "execution_trace": {"applied_rule_ids": [], "final_action": "ASK_HUMAN"}
        }
        self.normal = {
            "q_current_exposure": {"probabilities": {"no": .97}},
            "q_payment_anomaly": {"probabilities": {"no": .97}},
            "q_evidence": {"probabilities": {"no": .24}},
            "q_speech": {"choice": "negated_or_warning",
                         "probabilities": {"negated_or_warning": .94}},
            "q_request_scope": {"choice": "no_request",
                                "probabilities": {"no_request": .88}},
            "q_scam": {"probabilities": {"no": .94}},
        }
        self.config = tweak._config()[0]

    def propose(self, text, normalized=None, outcome=None):
        return tweak._candidate(text, outcome or self.base,
                                normalized or self.normal, self.config)

    def test_bounded_warning_is_proposal_only(self):
        self.assertEqual(self.propose("받은 OTP 인증번호를 보내지 마세요.")[0],
                         "BOUNDED_PROTECTIVE_WARNING")

    def test_trailing_transfer_is_not_relaxed(self):
        for suffix in (" 그리고 지금 송금하세요.", "\n원격제어 앱을 설치하세요.",
                       " 대신 접속 코드를 알려주세요.", " https://example.com"):
            with self.subTest(suffix=suffix):
                self.assertIsNone(self.propose("받은 OTP 인증번호를 보내지 마세요." + suffix)[0])

    def test_report_is_proposal_only(self):
        n = copy.deepcopy(self.normal)
        n["q_speech"]["choice"] = "reported_or_quoted"
        n["q_speech"]["probabilities"] = {"reported_or_quoted": .90}
        self.assertEqual(self.propose("어제 누군가가 ‘OTP를 보내 주세요’라고 말했어요.", n)[0],
                         "BOUNDED_PAST_REPORT")

    def test_open_quote_and_current_report_block(self):
        n = copy.deepcopy(self.normal)
        n["q_speech"]["choice"] = "reported_or_quoted"
        n["q_speech"]["probabilities"] = {"reported_or_quoted": .9}
        for text in ("어제 누군가가 ‘OTP를 보내 주세요라고 했어요.",
                     "지금 누군가가 ‘OTP를 보내 주세요’라고 했어요.",
                     "어제 누군가가 ‘OTP를 보내 주세요’라고 했어요. 지금도 보내세요."):
            self.assertIsNone(self.propose(text, n)[0])

    def test_pause_is_never_eligible(self):
        b = copy.deepcopy(self.base)
        b["action"] = "PAUSE_AND_VERIFY"
        self.assertIsNone(self.propose("받은 OTP 인증번호를 보내지 마세요.", outcome=b)[0])

    def test_contradictory_exposure_blocks(self):
        n = copy.deepcopy(self.normal)
        n["q_current_exposure"]["probabilities"]["no"] = .1
        self.assertIsNone(self.propose("받은 OTP 인증번호를 보내지 마세요.", n)[0])

    def test_missing_question_blocks(self):
        n = copy.deepcopy(self.normal)
        del n["q_speech"]
        self.assertIsNone(self.propose("받은 OTP 인증번호를 보내지 마세요.", n)[0])

    def test_full_observer_never_changes_core_output(self):
        raw = {"answers": {}}
        original = copy.deepcopy(self.base)
        with patch.object(tweak.v51.P, "normalize_response", return_value=self.normal):
            result = tweak.observe("받은 OTP 인증번호를 보내지 마세요.", raw, self.base,
                                   profile_id="v51-specific-candidate", policy_id="legacy")
        self.assertEqual(result["action"], original["action"])
        self.assertEqual(result["reason"], original["reason"])
        self.assertEqual(result["execution_trace"]["final_action"], "ASK_HUMAN")
        self.assertFalse(result["execution_trace"]["rule_tweak_shadow"]["applied"])
        self.assertEqual(result["execution_trace"]["rule_tweak_shadow"]["proposed_action"], "NO_STRONG_SIGNAL")
        self.assertEqual(self.base, original)

    def test_off_has_no_trace(self):
        with patch.dict(os.environ, {"DMSG_RULE_TWEAK_MODE": "off"}):
            result = tweak.observe("abc", {}, self.base, profile_id="x", policy_id="legacy")
        self.assertEqual(result, self.base)

    def test_enforce_environment_is_blocked(self):
        with patch.dict(os.environ, {"DMSG_RULE_TWEAK_MODE": "enforce"}):
            result = tweak.observe("abc", {}, self.base, profile_id="x", policy_id="legacy")
        self.assertEqual(result["execution_trace"]["rule_tweak_shadow"]["status"], "SHADOW_OBSERVATION_ERROR")
        self.assertEqual(result["action"], "ASK_HUMAN")

    def test_model_failure_is_not_silently_relaxed(self):
        b = copy.deepcopy(self.base)
        b["model_status"] = "FAILED"
        out = tweak.observe("abc", None, b, profile_id="x", policy_id="legacy")
        self.assertEqual(out["action"], "ASK_HUMAN")
        self.assertEqual(out["execution_trace"]["rule_tweak_shadow"]["status"], "MODEL_UNAVAILABLE")

    def test_bad_normalizer_is_isolated(self):
        with patch.object(tweak.v51.P, "normalize_response", side_effect=ValueError("input secret")):
            result = tweak.observe("abc", {}, self.base, profile_id="x", policy_id="legacy")
        self.assertEqual(result["action"], "ASK_HUMAN")
        self.assertEqual(result["execution_trace"]["rule_tweak_shadow"]["error_type"], "ValueError")
        self.assertNotIn("secret", json.dumps(result))

if __name__ == "__main__":
    unittest.main()
