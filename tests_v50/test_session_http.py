"""Loopback HTTP lifecycle contracts; every inference uses a synthetic client."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from arena.server import Handler
from arena.store import Arena
from integration.v48 import bridge
from tests_v50.test_session_lifecycle import Client


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class SessionHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'http.sqlite3'
        self.client = Client()
        self.start_server()

    def start_server(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.server.arena = Arena(self.db, self.client)
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def tearDown(self):
        self.stop_server()
        self.temp.cleanup()

    def call(self, path, body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data=data,
                                     headers={'Content-Type': 'application/json', **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=5) as result:
                return result.status, json.load(result)
        except urllib.error.HTTPError as result:
            return result.code, json.load(result)

    def start(self):
        code, body = self.call('/api/start', {})
        self.assertEqual(code, 200)
        return body['session_id']

    def control(self, sid, version, request_id):
        return dict(session_id=sid, version=version, request_id=request_id, synthetic_only=True)

    def test_full_lifecycle_with_recreated_server_and_same_database(self):
        sid = self.start()
        args = dict(self.control(sid, 0, 'eval'), text='지금 송금하세요.')
        code, first = self.call('/api/evaluate', args)
        self.assertEqual((code, first['action']), (200, 'PAUSE_AND_VERIFY'))
        code, closed = self.call('/api/close', self.control(sid, 1, 'close'))
        self.assertEqual((code, closed['lifecycle']), (200, 'CLOSED_UNRESOLVED'))
        self.stop_server(); self.start_server()
        code, state = self.call('/api/state?session_id=' + sid)
        self.assertEqual((code, state['version'], state['prior_pause']), (200, 2, 1))
        self.assertEqual(state['tasks'][0]['id'], first['next_task']['id'])
        code, error = self.call('/api/evaluate', dict(self.control(sid, 2, 'closed-eval'), text='회의가 끝났습니다.'))
        self.assertEqual((code, error['error']), (409, 'SESSION_CLOSED_UNRESOLVED'))
        self.assertEqual(self.client.calls, 1)
        self.assertEqual(self.call('/api/evaluate', args), (200, first))
        self.assertEqual(self.call('/api/close', self.control(sid, 1, 'close')), (200, closed))
        code, resumed = self.call('/api/reopen', self.control(sid, 2, 'reopen'))
        self.assertEqual((code, resumed['version'], resumed['prior_pause']), (200, 3, True))
        self.client.action, self.client.speech = 'none', 'information'
        code, final = self.call('/api/evaluate', dict(self.control(sid, 3, 'normal'), text='회의가 끝났습니다.',
            task_id=first['next_task']['id'], observation='USER_REPORTS_CONFIRMED'))
        self.assertEqual((code, final['current_turn_action'], final['action']), (200, 'NO_STRONG_SIGNAL', 'ASK_HUMAN'))
        self.assertEqual(final['related_task']['id'], first['next_task']['id'])
        self.assertNotIn('next_task', final)
        state = self.call('/api/state?session_id=' + sid)[1]
        self.assertEqual(state['events'][-1], final)
        self.assertEqual(state['version'], 4)

    def test_manifest_policy_is_server_owned(self):
        code, manifest = self.call('/api/manifest')
        self.assertEqual((code, manifest['version'], manifest['active_policy_id']), (200, '5.6', 'legacy'))
        self.assertEqual(manifest['contract_version'], '5.1')
        self.assertFalse(manifest['risk_release_implemented'])
        sid = self.start()
        code, _ = self.call('/api/evaluate', dict(self.control(sid, 0, 'policy'), text='합성 문장', policy_id='dra'))
        self.assertEqual(code, 400)
        self.assertEqual(self.client.calls, 0)

    def test_evidence_endpoint_has_digest_no_raw_text_and_no_attestation(self):
        from arena.evidence import validate_report
        sid = self.start()
        code, decision = self.call('/api/evaluate', dict(self.control(sid, 0, 'ev1'), text='지금 송금하세요.'))
        self.assertEqual(code, 200)
        code, report = self.call('/api/evidence?session_id=' + sid)
        self.assertEqual(code, 200)
        self.assertTrue(validate_report(report))
        self.assertFalse(report['model_identity_verified'])
        self.assertNotIn('지금 송금하세요.', json.dumps(report, ensure_ascii=False))
        self.assertEqual(self.call('/api/evidence?session_id=bad')[0], 400)

    def test_manifest_failure_is_static_503_before_inference(self):
        sid = self.start()
        for error in (bridge.ContractError('source-drift'), OSError('private/path'), KeyError('private-field'), TypeError('secret')):
            with self.subTest(kind=type(error).__name__), patch('arena.store.v50.execution_manifest', side_effect=error):
                self.assertEqual(self.call('/api/manifest'), (503, {'error': 'EXECUTION_CONTRACT_UNAVAILABLE'}))
                self.assertEqual(self.call('/api/evaluate', dict(self.control(sid, 0, 'failure'), text='합성 문장')),
                                 (503, {'error': 'EXECUTION_CONTRACT_UNAVAILABLE'}))
        self.assertEqual(self.client.calls, 0)
        self.assertEqual(self.server.arena.read(sid)['version'], 0)

    def test_lifecycle_conflicting_retry_stale_and_origin(self):
        sid = self.start()
        args = self.control(sid, 0, 'same')
        self.assertEqual(self.call('/api/close', args)[0], 200)
        self.assertEqual(self.call('/api/close', dict(args, version=1)), (409, {'error': 'CONFLICTING_RETRY'}))
        self.assertEqual(self.call('/api/reopen', self.control(sid, 0, 'stale')), (409, {'error': 'STALE_VERSION'}))
        self.assertEqual(self.call('/api/reopen', self.control(sid, 1, 'remote'), {'Origin': 'https://untrusted.invalid'})[0], 403)
        self.assertEqual(self.call('/api/manifest', headers={'Host': 'untrusted.invalid'})[0], 403)
        self.assertEqual(self.call('/api/state?session_id=invalid')[0], 400)
        self.assertEqual(self.call('/api/close', dict(args, force=True))[0], 400)
        self.assertEqual(self.client.calls, 0)


if __name__ == '__main__':
    unittest.main()
