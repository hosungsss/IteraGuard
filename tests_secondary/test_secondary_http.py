"""Actual localhost HTTP route contracts, without provider calls or paid access."""
import http.client
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from arena.server import Handler
from arena.secondary import JevShadow


class SecondaryHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.jev_shadow = JevShadow()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, body=None, *, origin=None, content_type="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        headers = {"Content-Type": content_type}
        if origin is not None:
            headers["Origin"] = origin
        conn.request(method, path, body=data, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status, content_type = response.status, response.getheader("Content-Type")
        conn.close()
        return status, json.loads(raw) if content_type and "application/json" in content_type else raw

    def test_get_capabilities_does_not_expose_key(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "NEVER_SHARE_THIS_TEST_KEY",
                                     "DMSG_JEV_LIVE_ENABLE": "0"}):
            status, data = self.request("GET", "/api/secondary/capabilities")
        self.assertEqual(status, 200)
        self.assertFalse(data["jev_live_available"])
        self.assertNotIn("NEVER_SHARE_THIS_TEST_KEY", json.dumps(data))

    def test_offline_is_real_local_route(self):
        status, data = self.request("POST", "/api/secondary/check",
                                    {"text": "안내입니다. 인증번호는 보내지 마세요.",
                                     "mode": "offline", "synthetic_only": True})
        self.assertEqual(status, 200)
        self.assertEqual(data["mode"], "OFFLINE_LEXICAL_INDICATORS")
        self.assertFalse(data["external_call"])
        self.assertIsNone(data["safety_verdict"])

    def test_live_without_authorization_returns_503_not_fake_jev(self):
        with patch.dict(os.environ, {"DMSG_JEV_LIVE_ENABLE": "0"}):
            status, data = self.request("POST", "/api/secondary/check",
                                        {"text": "지금 계좌로 보내세요", "mode": "jev",
                                         "synthetic_only": True, "consent_external": True})
        self.assertEqual(status, 503)
        self.assertEqual(data["error"], "JEV_DISABLED_OR_PAID_CREDITS_NOT_AUTHORIZED")

    def test_wrong_origin_rejected_before_any_processing(self):
        status, data = self.request("POST", "/api/secondary/check",
                                    {"text": "문장", "mode": "offline", "synthetic_only": True},
                                    origin="https://untrusted.example.com")
        self.assertEqual(status, 403)

    def test_duplicate_json_contract_rejected(self):
        status, data = self.request("POST", "/api/secondary/check",
                                    {"text": "문장", "mode": "offline", "synthetic_only": True,
                                     "extra": "unexpected"})
        self.assertEqual(status, 400)

    def test_missing_consent_field_rejected(self):
        status, data = self.request("POST", "/api/secondary/check",
                                    {"text": "문장", "mode": "jev", "synthetic_only": True})
        self.assertEqual(status, 400)

    def test_offline_fails_closed_on_fake_non_synthetic(self):
        status, data = self.request("POST", "/api/secondary/check",
                                    {"text": "문장", "mode": "offline", "synthetic_only": False})
        self.assertEqual(status, 400)
        self.assertEqual(data["error"], "SYNTHETIC_ONLY_REQUIRED")

    def test_offline_cannot_sneak_external_consent_field(self):
        status, data = self.request("POST", "/api/secondary/check",
                                    {"text": "문장", "mode": "offline", "synthetic_only": True,
                                     "consent_external": True})
        self.assertEqual(status, 400)

    def test_bad_mode_rejected(self):
        status, data = self.request("POST", "/api/secondary/check",
                                    {"text": "문장", "mode": "enforce", "synthetic_only": True})
        self.assertEqual(status, 400)

    def test_new_ui_script_is_served_without_secrets(self):
        status, raw = self.request("GET", "/secondary.js")
        self.assertEqual(status, 200)
        self.assertIn(b"secondaryStatus", raw)
        self.assertNotIn(b"TYPESAFE_API_KEY", raw)

if __name__ == "__main__":
    unittest.main()
