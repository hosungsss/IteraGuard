"""Read-only guided conversation contracts and real Arena state isolation tests.

No live Zoro/GPT/Jev or external SMS/email data is used.
"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from arena.conversation import SCENARIOS, GuidanceError, guide
from arena.store import Arena
from tests_v54.test_workflow import Client, PROFILE


SID = "a" * 32


def state(*, version=1, held=True, valid=True, last="EVALUATE", lifecycle="OPEN"):
    event = {"event_type": "EVALUATE", "model_status": "VALID" if valid else "FAILED",
             "action": "ASK_HUMAN" if held else "NO_STRONG_SIGNAL"}
    events = [event] if last == "EVALUATE" else [event, {"event_type": last}]
    return {"id": SID, "version": version, "prior_pause": int(held),
            "lifecycle": lifecycle, "tasks": [], "events": events}


class ConversationContract(unittest.TestCase):
    def perform(self, scenario, **changes):
        payload = state(**changes)
        return guide(payload, session_id=SID, version=payload["version"],
                     scenario=scenario, synthetic_only=True)

    def test_each_followup_is_advisory_and_closed(self):
        self.assertGreaterEqual(len(SCENARIOS), 8)
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                result = self.perform(scenario)
                self.assertEqual(result["schema"], "iteraguard-guided-conversation/1")
                self.assertEqual(result["mode"], "RULE_BASED_FOLLOWUP_NOT_GENERATIVE")
                self.assertTrue(result["prior_pause_retained"])
                self.assertFalse(result["decision_changed"])
                self.assertFalse(result["risk_cleared"])
                self.assertFalse(result["action_taken"])
                self.assertFalse(result["task_updated"])
                self.assertFalse(result["raw_question_stored"])
                self.assertTrue(result["steps"])

    def test_link_click_is_not_declared_safe_or_infected(self):
        item = self.perform("clicked")
        self.assertIn("단정할 수 없습니다", item["introduction"])
        self.assertIn("안전", item["introduction"])
        self.assertIn("이전 위험", item["risk_notice"])

    def test_pending_risk_not_cleared_for_any_scenario(self):
        for scenario in SCENARIOS:
            item = self.perform(scenario)
            self.assertTrue(item["prior_pause_retained"])
            self.assertFalse(item["risk_cleared"])

    def test_without_risk_still_no_safety_guarantee(self):
        item = self.perform("link_only", held=False)
        self.assertFalse(item["prior_pause_retained"])
        self.assertIn("안전성", item["risk_notice"])

    def test_model_failure_is_never_reported_as_real_judgment(self):
        item = self.perform("paid", valid=False)
        self.assertEqual(item["model_status"], "FAILED")
        self.assertIn("모델 응답을 검증하지 못했습니다", item["risk_notice"])

    def test_no_initial_evaluation(self):
        s = state()
        s["events"] = []
        with self.assertRaisesRegex(GuidanceError, "FIRST_EVALUATION_REQUIRED"):
            guide(s, session_id=SID, version=1, scenario="clicked", synthetic_only=True)

    def test_closed_session_rejected(self):
        with self.assertRaisesRegex(GuidanceError, "SESSION_CLOSED_UNRESOLVED"):
            self.perform("verify", lifecycle="CLOSED_UNRESOLVED")

    def test_new_lifecycle_event_requires_new_evaluation(self):
        with self.assertRaisesRegex(GuidanceError, "CURRENT_EVALUATION_REQUIRED"):
            self.perform("paid", last="REOPEN")

    def test_stale_session_version_rejected(self):
        with self.assertRaisesRegex(GuidanceError, "STALE_SESSION_VERSION"):
            guide(state(version=3), session_id=SID, version=2,
                  scenario="clicked", synthetic_only=True)

    def test_wrong_session_binding_rejected(self):
        with self.assertRaisesRegex(GuidanceError, "SESSION_BINDING_MISMATCH"):
            guide(state(), session_id="b" * 32, version=1,
                  scenario="clicked", synthetic_only=True)

    def test_non_synthetic_rejected(self):
        with self.assertRaisesRegex(GuidanceError, "SYNTHETIC_ONLY_REQUIRED"):
            guide(state(), session_id=SID, version=1,
                  scenario="clicked", synthetic_only=False)

    def test_unknown_scenario_rejected(self):
        for bad in ("__proto__", "open-url", "pay-now", "gpt", "", "clicked;DROP TABLE", 42):
            with self.subTest(bad=bad), self.assertRaises(GuidanceError):
                guide(state(), session_id=SID, version=1,
                      scenario=bad, synthetic_only=True)

    def test_bool_version_is_not_int(self):
        with self.assertRaisesRegex(GuidanceError, "INVALID_CONVERSATION_CONTRACT"):
            guide(state(), session_id=SID, version=True,
                  scenario="verify", synthetic_only=True)

    def test_sources_are_official_https_only(self):
        item = self.perform("verify")
        self.assertEqual(len(item["sources"]), 2)
        for src in item["sources"]:
            self.assertTrue(src["url"].startswith("https://"))
            self.assertNotIn("example.com", src["url"])

    def test_real_arena_read_only_and_current_risk_unchanged(self):
        with TemporaryDirectory() as d:
            client = Client()
            arena = Arena(Path(d) / "chat-state.sqlite3", client=client, profile_id=PROFILE)
            sid = arena.start()["session_id"]
            result = arena.evaluate(session_id=sid, version=0, request_id="testturn1",
                                    text="이 자료를 새 담당자에게 보내 주세요.", synthetic_only=True)
            before = deepcopy(arena.read(sid))
            for scenario in ("link_only", "clicked", "installed", "paid", "verify"):
                output = guide(arena.read(sid), session_id=sid, version=before["version"],
                               scenario=scenario, synthetic_only=True)
                self.assertEqual(output["version"], result["version"])
                self.assertFalse(output["task_updated"])
            self.assertEqual(before, arena.read(sid), "Follow-up must not change sqlite events/tasks")


if __name__ == "__main__":
    unittest.main()
