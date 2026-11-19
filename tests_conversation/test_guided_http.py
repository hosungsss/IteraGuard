"""Live localhost HTTP integration tests, controlled model double, no network provider."""
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from http.server import ThreadingHTTPServer

from arena.server import Handler
from arena.store import Arena
from tests_v54.test_workflow import Client, PROFILE


class GuidedHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.arena = Arena(Path(cls.temp.name) / "arena.sqlite3", client=Client(),
                          profile_id=PROFILE)
        cls.sid = cls.arena.start()["session_id"]
        cls.decision = cls.arena.evaluate(
            session_id=cls.sid, version=0, request_id="initial-controlled",
            text="새로운 계좌로 정산대금을 보내주세요.", synthetic_only=True)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.arena = cls.arena
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def request(self, path, body=None, origin=None, method="POST"):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        b = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        conn.request(method, path, body=b, headers=headers)
        response = conn.getresponse()
        data = response.read()
        status = response.status
        ctype = response.getheader("Content-Type") or ""
        conn.close()
        return status, json.loads(data) if "application/json" in ctype else data

    def body(self, scenario="clicked", **kwargs):
        return dict(session_id=self.sid, version=self.decision["version"],
                    scenario=scenario, synthetic_only=True, **kwargs)

    def test_real_http_followup_is_bound_to_state_and_does_not_write(self):
        before = self.arena.read(self.sid)
        status, result = self.request("/api/conversation/followup", self.body())
        self.assertEqual(status, 200)
        self.assertEqual(result["session_id"], self.sid)
        self.assertEqual(result["scenario"], "clicked")
        self.assertFalse(result["action_taken"])
        self.assertFalse(result["task_updated"])
        self.assertFalse(result["risk_cleared"])
        self.assertEqual(before, self.arena.read(self.sid))
        self.assertNotIn("새로운 계좌", json.dumps(result, ensure_ascii=False))

    def test_stale_version_fails_closed(self):
        b = self.body()
        b["version"] -= 1
        status, result = self.request("/api/conversation/followup", b)
        self.assertEqual(status, 409)
        self.assertEqual(result["error"], "STALE_SESSION_VERSION")

    def test_extra_request_field_rejected(self):
        b = self.body(extra="sneaky")
        status, result = self.request("/api/conversation/followup", b)
        self.assertEqual(status, 400)

    def test_absent_input_not_accepted(self):
        status, result = self.request("/api/conversation/followup", {})
        self.assertEqual(status, 400)

    def test_synthetic_only_flag_is_required(self):
        b = self.body()
        b["synthetic_only"] = False
        status, result = self.request("/api/conversation/followup", b)
        self.assertEqual(status, 400)
        self.assertEqual(result["error"], "SYNTHETIC_ONLY_REQUIRED")

    def test_unknown_scenario_is_not_model_generated(self):
        status, result = self.request("/api/conversation/followup", self.body(scenario="unclear"))
        self.assertEqual(status, 400)
        self.assertEqual(result["error"], "UNKNOWN_FOLLOWUP_SCENARIO")

    def test_cross_origin_rejected(self):
        status, result = self.request("/api/conversation/followup", self.body(),
                                      origin="https://malicious.example")
        self.assertEqual(status, 403)

    def test_session_id_well_formed_but_absent_is_rejected(self):
        b = self.body()
        b["session_id"] = "b" * 32
        status, result = self.request("/api/conversation/followup", b)
        self.assertEqual(status, 409)
        self.assertEqual(result["error"], "UNKNOWN_SESSION")

    def test_chatscript_is_served_under_current_csp(self):
        status, source = self.request("/chat.js", method="GET")
        self.assertEqual(status, 200)
        self.assertIn(b"RULE_BASED_FOLLOWUP_NOT_GENERATIVE", source if b"RULE_BASED_FOLLOWUP_NOT_GENERATIVE" in source else b"")
        # The actual file intentionally uses schema and readonly fields; response
        # is served as text, not as an arbitrary file path.
        self.assertIn(b"conversationFeed", source)


if __name__ == "__main__":
    unittest.main()
