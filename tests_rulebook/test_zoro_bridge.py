"""Bridge unit tests with test doubles; no actual Zoro call or network."""
import json
import unittest
from pathlib import Path

from rulebook.zoro_bridge import run_rulebook

ROOT = Path(__file__).resolve().parents[1]


class DummyClient:
    def __init__(self, value=None, duration=2.5, error=None):
        self.value = value
        self.duration = duration
        self.error = error
        self.calls = 0
        self.last = None

    def infer(self, state, *, question_payload=None):
        self.calls += 1
        self.last = (state, question_payload)
        if self.error:
            raise self.error
        return self.value, self.duration


class ZoroBridgeTests(unittest.TestCase):
    def setUp(self):
        self.book = json.loads((ROOT / "rulebook/presets/refund_intake.json").read_text(encoding="utf-8"))
        self.raw = {"answers": {"q_refund": {"type": "noul", "noul": .98},
                                "q_order": {"type": "noul", "noul": .97}}}

    def run(self, client, **kwargs):
        return run_rulebook(self.book, "Synthetic refund intent with order ID",
                            tenant_id="test_company", event_id="event_one", client=client, **kwargs)

    def test_disabled_never_calls_model(self):
        client = DummyClient(self.raw)
        result = self.run(client, allow_live=False)
        self.assertEqual(client.calls, 0)
        self.assertEqual(result["source"], "NOT_RUN")
        self.assertFalse(result["effects_executed"])

    def test_typed_request_and_policy_decoupled(self):
        client = DummyClient(self.raw)
        result = self.run(client, allow_live=True)
        self.assertEqual(client.calls, 1)
        self.assertEqual(set(client.last[1]["questions"]), {"q_refund", "q_order"})
        self.assertEqual(result["action"], "OPEN_REVIEW_TASK")
        self.assertFalse(result["authorized"])
        self.assertEqual(result["source"], "TEST_DOUBLE_NOT_ZORO")

    def test_model_fails_closed(self):
        from integration.v48 import bridge
        client = DummyClient(error=bridge.ModelUnavailable("offline"))
        result = self.run(client, allow_live=True)
        self.assertEqual(result["source"], "MODEL_UNAVAILABLE")
        self.assertEqual(result["action"], "HOLD_FOR_REVIEW")
        self.assertFalse(result["model_response_received"])

    def test_invalid_envelope_review_only(self):
        client = DummyClient({"unexpected": 1})
        result = self.run(client, allow_live=True)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["effects_executed"])

    def test_invalid_latency_review_only(self):
        client = DummyClient(self.raw, duration=float("nan"))
        result = self.run(client, allow_live=True)
        self.assertEqual(result["source"], "MODEL_UNAVAILABLE")
        self.assertFalse(result["effects_executed"])


if __name__ == "__main__":
    unittest.main()
