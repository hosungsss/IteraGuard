"""Document known historical rulebook gaps without changing policy behavior.

These are diagnostic *characterization* tests. PASS means the known hazard is
still reproducible; PASS does NOT mean it has been fixed.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from rulebook.engine import decide, validate_book

ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "rulebook" / "presets"


def load(name):
    return json.loads((PRESET / name).read_text(encoding="utf-8"))


def n(p):
    return {"type": "noul", "noul": p}


def decide_sample(book, answers):
    return decide(book, {"answers": answers}, tenant_id="test_org", event_id="test_event")


class KnownGapCharacterization(unittest.TestCase):
    def test_rb1_missing_type_is_currently_held(self):
        result = decide_sample(load("account_change.json"), {"q_account_change": {"noul": .95}})
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "INVALID_TYPED_RESPONSE")
        self.assertFalse(result["authorized"])

    def test_rb2_irrelevant_low_confidence_holds_currently(self):
        result = decide_sample(load("refund_intake.json"),
                               {"q_refund": n(.01), "q_order": n(.55)})
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "UNDETERMINED_TYPED_ANSWER")
        self.assertFalse(result["effects_executed"])

    def test_rb3_priority_can_override_review_in_offline_rulebook(self):
        book = deepcopy(load("refund_intake.json"))
        book["rules"] = [
            {"id": "needs_review", "when": {"q_refund": "yes", "q_order": "yes"},
             "priority": 100, "action": "OPEN_REVIEW_TASK"},
            {"id": "high_priority_no_action", "when": {"q_order": "yes"},
             "priority": 1000, "action": "NO_ACTION"},
            {"id": "no_refund", "when": {"q_refund": "no"}, "priority": 10,
             "action": "NO_ACTION"},
        ]
        validate_book(book)
        result = decide_sample(book, {"q_refund": n(.99), "q_order": n(.99)})
        # Known issue, NOT endorsement. Never use this book in production.
        self.assertEqual(result["status"], "PROPOSED_ONLY")
        self.assertEqual(result["action"], "NO_ACTION")
        self.assertFalse(result["authorized"])
        self.assertFalse(result["effects_executed"])

    def test_rb4_low_positive_probability_selects_no_action(self):
        result = decide_sample(load("account_change.json"),
                               {"q_account_change": n(.14)})
        self.assertEqual(result["status"], "PROPOSED_ONLY")
        self.assertEqual(result["action"], "NO_ACTION")

    def test_no_rulebook_hazard_authorizes_payment(self):
        for book, answers in [
            (load("account_change.json"), {"q_account_change": n(.95)}),
            (load("refund_intake.json"), {"q_refund": n(.95), "q_order": n(.95)}),
        ]:
            with self.subTest(book=book["id"]):
                out = decide_sample(book, answers)
                self.assertFalse(out["authorized"])
                self.assertFalse(out["effects_executed"])

    def test_legacy_review_provenance_explicit(self):
        text = (ROOT / "docs/reviews/RULEBOOK_ZORO_REMEDIATION_REVIEW_CURRENT_20261119.md").read_text()
        archived = (ROOT / "docs/reviews/RULEBOOK_ZORO_REMEDIATION_PLAN_KO_20261119_SOURCE.md").read_text()
        self.assertIn("7283492", archived)
        self.assertIn("NOT_VERIFIED", text)
        self.assertIn("판단 자동 적용은 보류", text)
        self.assertIn("RB-3", text)


if __name__ == "__main__":
    unittest.main()
