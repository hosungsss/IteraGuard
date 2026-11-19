"""Deterministic contract checks; NOT a Zoro runtime or business accuracy test."""
import json
import unittest
from copy import deepcopy
from pathlib import Path

from rulebook.engine import RulebookError, validate_book, build_questions, decide

ROOT = Path(__file__).resolve().parents[1]


def book(name):
    return json.loads((ROOT / "rulebook" / "presets" / name).read_text(encoding="utf-8"))


def raw(refund=0.97, order=0.95):
    return {"answers": {
        "q_refund": {"type": "noul", "noul": refund},
        "q_order": {"type": "noul", "noul": order},
    }}


class RulebookContracts(unittest.TestCase):
    def setUp(self):
        self.b = book("refund_intake.json")

    def evaluate(self, answer=None, b=None, event="event_1"):
        return decide(b or self.b, answer if answer is not None else raw(),
                      tenant_id="tenant_demo", event_id=event)

    def test_valid_presets(self):
        validate_book(self.b)
        validate_book(book("account_change.json"))

    def test_systemone_request_preserves_questions(self):
        payload = build_questions(self.b, "Synthetic refund request 123")
        self.assertEqual(set(payload["questions"]), {"q_refund", "q_order"})

    def test_refund_proposes_manual_review_not_execution(self):
        r = self.evaluate()
        self.assertEqual(r["action"], "OPEN_REVIEW_TASK")
        self.assertFalse(r["authorized"])
        self.assertFalse(r["effects_executed"])
        self.assertFalse(r["model_identity_verified"])
        self.assertIsNone(r["outcome_probability"])

    def test_missing_order_proposes_info_request_no_sms(self):
        r = self.evaluate(raw(0.99, 0.02))
        self.assertEqual(r["action"], "REQUEST_INFORMATION")
        self.assertFalse(r["effects_executed"])

    def test_no_refund_is_no_action(self):
        r = self.evaluate(raw(0.01, 0.90))
        self.assertEqual(r["action"], "NO_ACTION")

    def test_uncertainty_abstains(self):
        r = self.evaluate(raw(0.51, 0.99))
        self.assertEqual(r["reason"], "UNDETERMINED_TYPED_ANSWER")
        self.assertEqual(r["action"], "HOLD_FOR_REVIEW")

    def test_missing_question_abstains(self):
        r = self.evaluate({"answers": {"q_refund": {"type": "noul", "noul": .95}}})
        self.assertEqual(r["reason"], "QUESTION_PROFILE_MISMATCH")

    def test_invalid_confidence_abstains(self):
        r = self.evaluate(raw(float("nan"), 0.91))
        self.assertEqual(r["reason"], "INVALID_TYPED_RESPONSE")

    def test_no_model_never_claims_success(self):
        r = self.evaluate({"error": "timeout"})
        self.assertEqual(r["status"], "REVIEW_REQUIRED")
        self.assertFalse(r["effects_executed"])

    def test_duplicate_conditions_invalid(self):
        b = deepcopy(self.b)
        b["rules"].append(deepcopy(b["rules"][0]))
        b["rules"][-1]["id"] = "duplicate"
        with self.assertRaises(RulebookError):
            validate_book(b)

    def test_unauthorized_action_invalid(self):
        b = deepcopy(self.b)
        b["rules"][0]["action"] = "WIRE_TRANSFER"
        with self.assertRaises(RulebookError):
            validate_book(b)

    def test_stable_idempotency_and_tenant_scope(self):
        a = self.evaluate()
        b = self.evaluate()
        c = decide(self.b, raw(), tenant_id="another_tenant", event_id="event_1")
        self.assertEqual(a["idempotency_key"], b["idempotency_key"])
        self.assertNotEqual(a["idempotency_key"], c["idempotency_key"])
        self.assertFalse(a["idempotency_persisted"])

    def test_account_change_industry_switch(self):
        a = book("account_change.json")
        r = self.evaluate({"answers": {"q_account_change": {"type": "noul", "noul": .93}}}, a)
        self.assertEqual(r["action"], "OPEN_VERIFICATION_TASK")

    def test_unrecognized_option_rejected(self):
        b = deepcopy(self.b)
        b["rules"][0]["when"]["q_refund"] = "maybe"
        with self.assertRaises(RulebookError):
            validate_book(b)

    def test_rule_priority_ambiguity_requires_review(self):
        b = deepcopy(self.b)
        b["rules"].append({"id": "generic_refund", "when": {"q_refund": "yes"},
                           "action": "HOLD_FOR_REVIEW", "priority": 100})
        r = self.evaluate(b=b)
        self.assertEqual(r["reason"], "CONFLICTING_RULES")


if __name__ == "__main__":
    unittest.main()
