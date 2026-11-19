"""Single-question route with a controlled model and isolated Arena state."""

from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from arena.server import Handler
from arena.store import Arena


class ControlledModel:
    def __init__(self):
        self.requests = []
        self.answers = {
            'q_signal': {
                'type': 'choice',
                'choice': 'red',
                'confidence': .9,
                'probabilities': {'red': .94, 'orange': .03, 'green': .01, 'gray': .02},
            },
        }

    def infer(self, text, *, question_payload):
        self.requests.append((text, question_payload))
        return {'answers': self.answers}, .1


class SignalHttpTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.model = ControlledModel()
        self.arena = Arena(Path(temp.name) / 'arena.sqlite3', client=self.model)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.arena = self.arena
        self.addCleanup(self.server.server_close)
        thread = Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, payload=None, origin=None):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            headers = {'Content-Type': 'application/json'}
            if origin:
                headers['Origin'] = origin
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            return response.status, response.read().decode('utf-8')
        finally:
            conn.close()

    def test_assets_and_single_question_without_session_change(self):
        status, page = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('id="inlineSignal"', page)
        self.assertNotIn('href="/signal"', page)
        self.assertEqual(self.request('GET', '/signal'), (200, page))
        for path in ('/main.js', '/style.css'):
            self.assertEqual(self.request('GET', path)[0], 200)
        sid = self.arena.start()['session_id']
        before = self.arena.read(sid)
        text = ' 가상 문자\n인증번호를 보내주세요. '
        status, raw = self.request('POST', '/api/signal', {'text': text, 'synthetic_only': True})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['grade'], 'red')
        self.assertEqual(len(self.model.requests), 1)
        received, payload = self.model.requests[0]
        self.assertEqual(received, text)
        self.assertEqual(payload['state'], text)
        self.assertEqual(set(payload['questions']), {'q_signal'})
        self.assertEqual(self.arena.read(sid), before)

    def test_rejects_invalid_or_cross_origin_inputs_before_inference(self):
        for payload, origin, want in [
            ({'text': '가상 문자'}, None, 400),
            ({'text': ' ', 'synthetic_only': True}, None, 400),
            ({'text': '가상 문자', 'synthetic_only': True}, 'https://other.example', 403),
        ]:
            with self.subTest(payload=payload, origin=origin):
                self.assertEqual(self.request('POST', '/api/signal', payload, origin)[0], want)
        self.assertEqual(self.model.requests, [])

    def test_invalid_response_is_model_error(self):
        self.model.answers = {}
        status, raw = self.request('POST', '/api/signal', {'text': '가상 문자', 'synthetic_only': True})
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(raw), {'error': 'SIGNAL_MODEL_UNAVAILABLE'})
