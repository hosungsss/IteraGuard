"""Safety regression for optional Jev 1.14 and zero-cost local patterns.

Every Jev response here is an explicitly synthetic TEST DOUBLE, not a real API.
"""
import copy
import json
import os
import unittest
from unittest.mock import patch
from arena import secondary as s


def response():
    return {
        "model": "jev-1.14.0",
        "answers": {
            "intent": {
                "type": "choice",
                "choice": "active_sensitive_request",
                "confidence": .79,
                "probabilities": {
                    "active_sensitive_request": .8,
                    "protective_warning": .05,
                    "historical_report": .03,
                    "ordinary_message": .02,
                    "unclear": .1
                }
            },
            "active_sensitive": {"type": "noul", "noul": .91}
        },
        "usage": {"input_tokens": 143, "output_tokens": 12}
    }


class SecondaryTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "DMSG_JEV_LIVE_ENABLE": "1",
            "DMSG_JEV_SPEND_ACK": "I_ACKNOWLEDGE_CHARGES",
            "TYPESAFE_API_KEY": "test-only-not-a-real-secret"
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = s.JevShadow()

    def fake(self, body, key, timeout):
        self.assertEqual(timeout, 8)
        self.assertEqual(key, "test-only-not-a-real-secret")
        payload = json.loads(body)
        self.assertEqual(payload["model"], "jev-1.14.0")
        self.assertEqual(payload["state"], "지금 계좌로 송금하세요")
        self.assertEqual(set(payload), {"model", "state", "questions"})
        self.assertEqual(set(payload["questions"]), {"intent", "active_sensitive"})
        return json.dumps(response()).encode()

    def test_capabilities_without_billing_ack_is_disabled(self):
        with patch.dict(os.environ, {"DMSG_JEV_SPEND_ACK": "0"}):
            self.assertFalse(s.capabilities()["jev_live_available"])

    def test_capabilities_without_key_is_disabled(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}):
            self.assertFalse(s.capabilities()["jev_live_available"])

    def test_capabilities_without_live_enable_is_disabled(self):
        with patch.dict(os.environ, {"DMSG_JEV_LIVE_ENABLE": "0"}):
            self.assertFalse(s.capabilities()["jev_live_available"])

    def test_capabilities_include_no_secrets(self):
        c = s.capabilities()
        self.assertTrue(c["jev_live_available"])
        self.assertEqual(c["cost"], "PROVIDER_BILLED_NOT_FREE")
        self.assertNotIn("test-only-not-a-real-secret", json.dumps(c))

    def test_zero_cost_is_never_model_or_safety_verdict(self):
        a = s.indicators("지금 계좌로 송금하고 OTP를 보내세요", synthetic_only=True)
        self.assertEqual(a["mode"], "OFFLINE_LEXICAL_INDICATORS")
        self.assertIn("payment_terms", a["indicators"])
        self.assertIn("credential_terms", a["indicators"])
        self.assertIsNone(a["safety_verdict"])
        self.assertIsNone(a["action"])
        self.assertFalse(a["external_call"])

    def test_negated_warning_detects_words_but_not_safety(self):
        a = s.indicators("인증번호를 보내지 마세요.", synthetic_only=True)
        self.assertIn("credential_terms", a["indicators"])
        self.assertIsNone(a["safety_verdict"])

    def test_no_signal_is_not_safe(self):
        a = s.indicators("오늘 회의는 3시입니다.", synthetic_only=True)
        self.assertEqual(a["indicators"], [])
        self.assertIsNone(a["safety_verdict"])

    def test_real_input_not_authorized(self):
        with self.assertRaises(s.SecondaryError) as ctx:
            s.indicators("문장", synthetic_only=False)
        self.assertEqual(ctx.exception.code, "SYNTHETIC_ONLY_REQUIRED")

    def test_empty_or_long_or_control_input_rejected(self):
        for t in ("", " ", "x" * 2001, "문자\x00입력"):
            with self.subTest(t=t[:8]), self.assertRaises(s.SecondaryError):
                s.indicators(t, synthetic_only=True)

    def test_jev_requires_per_request_consent(self):
        with self.assertRaises(s.SecondaryError) as ctx:
            self.client.check("지금 계좌로 송금하세요", synthetic_only=True, transport=self.fake)
        self.assertEqual(ctx.exception.code, "EXPLICIT_EXTERNAL_CONSENT_REQUIRED")
        self.assertEqual(self.client._calls_reserved, 0)

    def test_jev_bool_true_not_integer_one(self):
        with self.assertRaises(s.SecondaryError):
            self.client.check("지금 계좌로 송금하세요", synthetic_only=True, consent_external=1, transport=self.fake)

    def test_jev_billing_approval_required_even_if_credential_present(self):
        with patch.dict(os.environ, {"DMSG_JEV_SPEND_ACK": ""}):
            with self.assertRaises(s.SecondaryError) as ctx:
                self.client.check("지금 계좌로 송금하세요", synthetic_only=True, consent_external=True, transport=self.fake)
        self.assertEqual(ctx.exception.code, "JEV_DISABLED_OR_PAID_CREDITS_NOT_AUTHORIZED")
        self.assertEqual(self.client._calls_reserved, 0)

    def test_jev_valid_test_double_never_changes_action(self):
        a = self.client.check("지금 계좌로 송금하세요", synthetic_only=True,
                              consent_external=True, transport=self.fake)
        self.assertEqual(a["mode"], "JEV_PROVIDER_HTTP_UNATTESTED")
        self.assertEqual(a["provider_model_echo"], "jev-1.14.0")
        self.assertEqual(a["intent"], "active_sensitive_request")
        self.assertIsNone(a["action"])
        self.assertIsNone(a["safety_verdict"])
        self.assertEqual(a["billing"], "PROVIDER_BILLED")
        self.assertNotIn("지금 계좌로", json.dumps(a, ensure_ascii=False))
        self.assertNotIn("test-only-not-a-real-secret", json.dumps(a))

    def test_jev_unknown_model_not_accepted(self):
        bad = response()
        bad["model"] = "jev-other"
        with self.assertRaises(s.SecondaryError) as ctx:
            s._validate_response(json.dumps(bad))
        self.assertEqual(ctx.exception.code, "MODEL_VERSION_UNVERIFIED")

    def test_jev_missing_question_not_accepted(self):
        bad = response()
        del bad["answers"]["active_sensitive"]
        with self.assertRaises(s.SecondaryError):
            s._validate_response(json.dumps(bad))

    def test_jev_extra_question_not_accepted(self):
        bad = response()
        bad["answers"]["untrusted"] = {"type": "noul", "noul": .5}
        with self.assertRaises(s.SecondaryError):
            s._validate_response(json.dumps(bad))

    def test_jev_choice_not_in_options_not_accepted(self):
        bad = response()
        bad["answers"]["intent"]["choice"] = "untrusted_action"
        with self.assertRaises(s.SecondaryError):
            s._validate_response(json.dumps(bad))

    def test_jev_choice_distribution_must_sum_to_one(self):
        bad = response()
        bad["answers"]["intent"]["probabilities"]["unclear"] = .8
        with self.assertRaises(s.SecondaryError):
            s._validate_response(json.dumps(bad))

    def test_jev_choice_selection_must_match_argmax(self):
        bad = response()
        bad["answers"]["intent"]["choice"] = "ordinary_message"
        with self.assertRaises(s.SecondaryError):
            s._validate_response(json.dumps(bad))

    def test_jev_nan_and_boolean_probabilities_rejected(self):
        for val in (float("nan"), float("inf"), True, -1, 1.1):
            bad = response()
            bad["answers"]["active_sensitive"]["noul"] = val
            with self.subTest(val=str(val)), self.assertRaises(s.SecondaryError):
                s._validate_response(json.dumps(bad))

    def test_jev_invalid_token_usage_rejected(self):
        for value in ("100", True, -1, 1000001):
            bad = response()
            bad["usage"]["input_tokens"] = value
            with self.subTest(value=value), self.assertRaises(s.SecondaryError):
                s._validate_response(json.dumps(bad))

    def test_jev_non_json_is_rejected_and_no_raw_echo(self):
        with self.assertRaises(s.SecondaryError) as ctx:
            s._validate_response('not a JSON document with personal data')
        self.assertEqual(ctx.exception.code, "INVALID_PROVIDER_JSON")

    def test_transport_exception_sanitized(self):
        def broken(*args):
            raise RuntimeError("the key and private message are secret")
        with self.assertRaises(s.SecondaryError) as ctx:
            self.client.check("지금 계좌로 송금하세요", synthetic_only=True,
                              consent_external=True, transport=broken)
        self.assertEqual(ctx.exception.code, "JEV_UNAVAILABLE_OR_INVALID_RESPONSE")
        self.assertNotIn("secret", str(ctx.exception))

    def test_no_automatic_retries(self):
        calls = []
        def broken(*args):
            calls.append(1)
            raise OSError("outage")
        with self.assertRaises(s.SecondaryError):
            self.client.check("지금 계좌로 송금하세요", synthetic_only=True,
                              consent_external=True, transport=broken)
        self.assertEqual(len(calls), 1)

    def test_process_call_cap_including_failures(self):
        self.client._calls_reserved = s.MAX_CALLS_PER_PROCESS
        with self.assertRaises(s.SecondaryError) as ctx:
            self.client.check("지금 계좌로 송금하세요", synthetic_only=True,
                              consent_external=True, transport=self.fake)
        self.assertEqual(ctx.exception.code, "JEV_PROCESS_CALL_CAP_REACHED")

    def test_endpoint_is_fixed_https_not_user_or_env_controlled(self):
        with patch.dict(os.environ, {"DMSG_JEV_ENDPOINT": "http://127.0.0.1/private"}):
            self.assertEqual(s.ENDPOINT, "https://api.typesafe.ai/v1/systemone")

    def test_body_is_bounded_and_text_only(self):
        text = "감사" * 950
        def f(payload, key, timeout):
            self.assertLessEqual(len(payload), 16384)
            self.assertEqual(json.loads(payload)["state"], text)
            return json.dumps(response()).encode()
        self.client.check(text, synthetic_only=True, consent_external=True, transport=f)

if __name__ == "__main__":
    unittest.main()
