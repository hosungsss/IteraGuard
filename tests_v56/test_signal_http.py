"""Two-question route with a controlled model and isolated Arena state."""

from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import Mock

from arena.server import Handler
from arena.signal import ACTION_QUESTION
from arena.store import Arena


class ControlledModel:
    def __init__(self):
        self.requests = []
        self.answers = {
            'q_action': {
                'type': 'choice',
                'choice': 'share_auth_secret',
                'probabilities': {
                    key: float(key == 'share_auth_secret') for key in ACTION_QUESTION['criteria']
                },
            },
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

    def test_assets_and_two_questions_without_session_change(self):
        status, page = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('id="inlineSignal"', page)
        self.assertIn('id="inlineRequestedAction"', page)
        self.assertIn('src="/signal.js"', page)
        self.assertNotIn('src="/main.js"', page)
        self.assertNotIn('id="nextAction"', page)
        self.assertNotIn('href="/signal"', page)
        self.assertEqual(self.request('GET', '/signal'), (200, page))
        for path in ('/signal.js', '/main.js', '/style.css'):
            self.assertEqual(self.request('GET', path)[0], 200)
        sid = self.arena.start()['session_id']
        before = self.arena.read(sid)
        text = ' 가상 문자\n인증번호를 보내주세요. '
        status, raw = self.request('POST', '/api/signal', {'text': text, 'synthetic_only': True})
        self.assertEqual(status, 200)
        result = json.loads(raw)
        self.assertEqual(result['grade'], 'red')
        self.assertEqual(result['requested_action'], {
            'id': 'share_auth_secret', 'label': '비밀번호·인증번호 알려주기',
        })
        self.assertEqual(len(self.model.requests), 1)
        received, payload = self.model.requests[0]
        self.assertEqual(received, text)
        self.assertEqual(payload['state'], text)
        self.assertEqual(list(payload['questions']), ['q_action', 'q_signal'])
        self.assertEqual(len(payload['questions']['q_action']['criteria']), 20)
        action = payload['questions']['q_action']['instructions']
        signal = payload['questions']['q_signal']['instructions']
        self.assertIn('누가 누구에게', action)
        for cue in ('접근 권한', '기억을 부정', '약관', '나이·장애'):
            self.assertIn(cue, signal)
        self.assertEqual(set(result), {'grade', 'scores', 'requested_action', 'context_review', 'explanation'})
        self.assertEqual(set(result['scores']), {'red', 'orange', 'green', 'gray'})
        self.assertEqual(self.arena.read(sid), before)

    def test_verify_profile_is_selected_by_server_only(self):
        from arena.signal import PROFILES
        self.server.signal_profile = 'verify'
        body = {'text': '합성 안내', 'synthetic_only': True}
        status, raw = self.request('POST', '/api/signal', body)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['grade'], 'red')
        self.assertEqual(self.model.requests[0][1]['questions'], PROFILES['verify'])
        self.assertEqual(self.request('POST', '/api/signal', dict(body, profile='short'))[0], 400)
        self.assertEqual(len(self.model.requests), 1)

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

    def test_benchmark_requires_operator_configuration_and_empty_same_origin_start(self):
        path = '/api/signal/benchmark'
        for method, payload in (('GET', None), ('POST', {})):
            status, raw = self.request(method, path, payload)
            self.assertEqual((status, json.loads(raw)), (404, {'error': 'BENCHMARK_DISABLED'}))

        benchmark = self.server.signal_benchmark = Mock()
        benchmark.snapshot.return_value = {'status': 'idle'}
        benchmark.start.return_value = {'status': 'running'}
        status, raw = self.request('GET', path)
        self.assertEqual((status, json.loads(raw)), (200, {'status': 'idle'}))
        self.assertEqual(self.request('POST', path, {}, 'https://other.example')[0], 403)
        self.assertEqual(self.request('POST', path, {'csv': 'arbitrary.csv'})[0], 400)
        benchmark.start.assert_not_called()
        benchmark.snapshot.assert_called_once_with()
        status, raw = self.request('POST', path, {})
        self.assertEqual((status, json.loads(raw)), (202, {'status': 'running'}))
        benchmark.start.assert_called_once_with()
