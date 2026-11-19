from contextlib import closing
"""v5 lifecycle, migration and task contract. All inference clients are synthetic."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hmac
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from arena.store import Arena, Conflict, SCHEMA_VERSION, check_loopback_endpoint
from integration.v48 import bridge
from integration.v48_replay import stub_raw


class Client:
    def __init__(self, action='money_transfer', speech='direct_request'):
        self.action, self.speech, self.calls = action, speech, 0
        self.started = self.release = None

    def infer(self, text):
        self.calls += 1
        if self.started is not None:
            self.started.set()
            if not self.release.wait(5):
                raise RuntimeError('TEST_BARRIER_TIMEOUT')
        return stub_raw({'fixture_spec': {'q_action': self.action, 'q_speech': self.speech,
                                         'q_evidence': 'yes'}}), 1.0


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.sqlite3'
        self.client = Client()
        self.arena = Arena(self.path, self.client)
        self.sid = self.arena.start()['session_id']

    def request(self, version=0, request_id='eval1', **more):
        return dict(session_id=self.sid, version=version, request_id=request_id,
                    text='지금 송금하세요.', synthetic_only=True, **more)

    def life(self, version, request_id):
        return dict(session_id=self.sid, version=version, request_id=request_id, synthetic_only=True)

    def normal(self):
        self.client.action, self.client.speech = 'none', 'information'

    def test_close_reopen_restart_preserves_risk_tasks_and_history(self):
        first = self.arena.evaluate(**self.request())
        closed = self.arena.close(**self.life(1, 'close1'))
        self.assertEqual(closed['lifecycle'], 'CLOSED_UNRESOLVED')
        self.assertFalse(closed['risk_cleared'])
        self.assertFalse(closed['model_called'])
        restarted = Arena(self.path, self.client)
        state = restarted.read(self.sid)
        self.assertEqual(state['prior_pause'], 1)
        self.assertEqual(state['tasks'][0]['id'], first['next_task']['id'])
        self.assertEqual(state['tasks'][0]['status'], 'OPEN')
        self.assertEqual(len(state['events']), 2)
        with self.assertRaisesRegex(Conflict, 'SESSION_CLOSED_UNRESOLVED'):
            restarted.evaluate(**self.request(2, 'closed_eval'))
        self.assertEqual(self.client.calls, 1)
        self.assertEqual(restarted.close(**self.life(1, 'close1')), closed)
        self.assertEqual(restarted.evaluate(**self.request()), first)
        resumed = restarted.reopen(**self.life(2, 'reopen1'))
        self.assertEqual(resumed['version'], 3)
        self.assertTrue(resumed['prior_pause'])
        self.normal()
        outcome = restarted.evaluate(**dict(self.request(3, 'eval2'), text='회의가 끝났습니다.'))
        self.assertEqual(outcome['current_turn_action'], 'NO_STRONG_SIGNAL')
        self.assertEqual(outcome['action'], 'ASK_HUMAN')
        self.assertEqual(outcome['reason'], 'PRIOR_RISK_UNRESOLVED')
        self.assertEqual(len(restarted.read(self.sid)['events']), 4)

    def test_transition_retry_identity_version_and_cross_operation(self):
        args = self.life(0, 'close1')
        closed = self.arena.close(**args)
        self.assertEqual(self.arena.close(**args), closed)
        for changed in (dict(args, version=1), dict(args, version=3)):
            with self.assertRaisesRegex(Conflict, 'CONFLICTING_RETRY'):
                self.arena.close(**changed)
        with self.assertRaisesRegex(Conflict, 'CONFLICTING_RETRY'):
            self.arena.reopen(**args)
        with self.assertRaisesRegex(Conflict, 'STALE_VERSION'):
            self.arena.reopen(**self.life(0, 'other'))
        with self.assertRaisesRegex(Conflict, 'SESSION_ALREADY_CLOSED'):
            self.arena.close(**self.life(1, 'other'))
        resumed = self.arena.reopen(**self.life(1, 'reopen1'))
        self.assertEqual(self.arena.reopen(**self.life(1, 'reopen1')), resumed)
        with self.assertRaisesRegex(Conflict, 'SESSION_ALREADY_OPEN'):
            self.arena.reopen(**self.life(2, 'other'))
        self.assertEqual(self.client.calls, 0)

    def test_close_during_inference_rejects_late_commit(self):
        self.client.started, self.client.release = threading.Event(), threading.Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.arena.evaluate, **self.request())
            self.assertTrue(self.client.started.wait(3))
            self.arena.close(**self.life(0, 'close_during_model'))
            self.client.release.set()
            with self.assertRaisesRegex(Conflict, 'STALE_VERSION'):
                future.result(3)
        state = self.arena.read(self.sid)
        self.assertEqual(state['lifecycle'], 'CLOSED_UNRESOLVED')
        self.assertEqual(state['tasks'], [])
        self.assertEqual(state['prior_pause'], 0)
        self.assertEqual([e['event_type'] for e in state['events']], ['CLOSE_UNRESOLVED'])

    def test_concurrent_identical_close_is_one_event(self):
        other = Arena(self.path, self.client)
        barrier = threading.Barrier(2)
        def run(arena):
            barrier.wait()
            return arena.close(**self.life(0, 'close1'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(run, self.arena), pool.submit(run, other)
            self.assertEqual(a.result(3), b.result(3))
        state = self.arena.read(self.sid)
        self.assertEqual(state['version'], 1)
        self.assertEqual(len(state['events']), 1)

    def test_reported_completion_does_not_create_unending_tasks(self):
        first = self.arena.evaluate(**self.request())
        tid = first['next_task']['id']
        self.normal()
        second = self.arena.evaluate(**dict(self.request(1, 'eval2', task_id=tid,
                                      observation='USER_REPORTS_CONFIRMED'), text='회의가 끝났습니다.'))
        self.assertNotIn('next_task', second)
        self.assertEqual(second['related_task']['id'], tid)
        for version in (2, 3, 4):
            outcome = self.arena.evaluate(**dict(self.request(version, 'repeat' + str(version)), text='회의가 끝났습니다.'))
            self.assertEqual(outcome['action'], 'ASK_HUMAN')
            self.assertEqual(outcome['related_task']['id'], tid)
            self.assertNotIn('next_task', outcome)
        self.assertEqual(len(self.arena.read(self.sid)['tasks']), 1)
        self.client.action, self.client.speech = 'credential_or_otp', 'direct_request'
        new_risk = self.arena.evaluate(**dict(self.request(5, 'newrisk'), text='지금 인증번호를 알려주세요.'))
        self.assertEqual(new_risk['action'], 'PAUSE_AND_VERIFY')
        self.assertNotEqual(new_risk['next_task']['id'], tid)
        self.assertEqual(len(self.arena.read(self.sid)['tasks']), 2)

    def test_same_risk_after_report_keeps_pause_without_duplicate_task(self):
        first = self.arena.evaluate(**self.request())
        tid = first['next_task']['id']
        second = self.arena.evaluate(**self.request(1, 'eval2', task_id=tid, observation='USER_REPORTS_CONFIRMED'))
        self.assertEqual(second['action'], 'PAUSE_AND_VERIFY')
        self.assertNotIn('next_task', second)
        self.assertEqual(second['related_task']['id'], tid)
        self.assertEqual(len(self.arena.read(self.sid)['tasks']), 1)

    def test_new_strong_signal_on_same_text_requires_new_task(self):
        class Fail:
            def infer(self, text):
                raise bridge.ModelUnavailable('MODEL_NOT_CONFIGURED')
        self.arena.client = Fail()
        first = self.arena.evaluate(**self.request())
        tid = first['next_task']['id']
        self.arena.evaluate(**self.request(1, 'report', task_id=tid, observation='USER_REPORTS_CONFIRMED'))
        self.arena.client = self.client
        stronger = self.arena.evaluate(**self.request(2, 'stronger'))
        self.assertEqual(stronger['action'], 'PAUSE_AND_VERIFY')
        self.assertNotEqual(stronger['next_task']['id'], tid)

    def test_no_new_report_preserves_unresolved_across_lifecycle(self):
        first = self.arena.evaluate(**self.request())
        tid = first['next_task']['id']
        self.arena.evaluate(**self.request(1, 'unresolved', task_id=tid, observation='UNRESOLVED'))
        self.arena.close(**self.life(2, 'close'))
        self.arena.reopen(**self.life(3, 'reopen'))
        outcome = self.arena.evaluate(**self.request(4, 'default', task_id=tid))
        self.assertEqual(outcome['next_task']['observation'], 'UNRESOLVED')
        self.assertEqual(outcome['observation'], 'NOT_CHECKED')

    def test_trace_session_order_and_no_raw_text_url_or_quote_in_storage(self):
        self.normal()
        text = '비공개표식_820419 https://example.invalid/path?token=PRIVATE_VALUE_80342'
        outcome = self.arena.evaluate(**dict(self.request(), text=text, user_review=True))
        trace = outcome['execution_trace']
        self.assertEqual(trace['session']['version_before'], 0)
        self.assertEqual(trace['session']['version_after'], 1)
        self.assertEqual(trace['session']['session_action'], outcome['action'])
        self.assertEqual(trace['session']['current_turn_action'], outcome['current_turn_action'])
        self.assertEqual(trace['session']['context_scope'], 'CURRENT_TEXT_ONLY')
        serialized = json.dumps(self.arena.read(self.sid), ensure_ascii=False)
        raw = self.path.read_bytes()
        for secret in (text, '비공개표식_820419', 'PRIVATE_VALUE_80342', 'example.invalid'):
            self.assertNotIn(secret, serialized)
            self.assertNotIn(secret.encode(), raw)
        self.assertNotIn('"quote"', serialized)
        self.assertNotIn('"display_url"', serialized)
        self.assertNotIn('"linkguard"', serialized)
        self.assertFalse(outcome['link_summary']['network_used'])

    def test_review_options_are_bound_to_retry_and_do_not_weaken_risk(self):
        args = self.request(user_review=True)
        outcome = self.arena.evaluate(**args)
        self.assertEqual(outcome['action'], 'PAUSE_AND_VERIFY')
        self.assertEqual(self.arena.evaluate(**args), outcome)
        with self.assertRaisesRegex(Conflict, 'CONFLICTING_RETRY'):
            self.arena.evaluate(**dict(args, user_review=False))
        with self.assertRaisesRegex(Conflict, 'CONFLICTING_RETRY'):
            self.arena.evaluate(**dict(args, consent={'web_analysis': True}))
        self.assertEqual(self.client.calls, 1)

    def test_cross_session_closed_task_and_mutated_response_are_isolated(self):
        first = self.arena.evaluate(**self.request())
        tid = first['next_task']['id']
        saved = deepcopy(first)
        first['execution_trace']['session']['prior_pause_after'] = False
        self.assertEqual(self.arena.evaluate(**self.request()), saved)
        other = self.arena.start()['session_id']
        with self.assertRaisesRegex(Conflict, 'UNKNOWN_OR_CLOSED_TASK'):
            self.arena.evaluate(**dict(self.request(), session_id=other, task_id=tid))
        self.normal()
        self.arena.evaluate(**dict(self.request(1, 'report', task_id=tid, observation='USER_REPORTS_DENIED'), text='회의가 끝났습니다.'))
        with self.assertRaisesRegex(Conflict, 'UNKNOWN_OR_CLOSED_TASK'):
            self.arena.evaluate(**self.request(2, 'closed_task', task_id=tid, observation='UNRESOLVED'))

    def test_unknown_policy_and_invalid_controls_before_any_model(self):
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_POLICY_ID'):
            Arena(self.path, self.client, policy_id='auto-promote')
        for update in ({'synthetic_only': False}, {'version': True}, {'request_id': '../x'},
                       {'user_review': 1}, {'consent': {'web_analysis': 'yes'}},
                       {'consent': {'endpoint': True}}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.arena.evaluate(**dict(self.request(), **update))
        with self.assertRaises(ValueError):
            self.arena.close(**dict(self.life(0, 'close'), synthetic_only=False))
        self.assertEqual(self.client.calls, 0)


class MigrationAndEndpointTests(unittest.TestCase):
    def test_v49_migration_preserves_exact_event_and_retry_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'old.sqlite3'
            sid, tid, key = 'a' * 32, 'b' * 32, bytes.fromhex('22' * 32)
            text = '이전 합성 문장입니다.'
            old = {'session_id': sid, 'request_id': 'old', 'version': 1, 'action': 'ASK_HUMAN',
                   'current_turn_action': 'NO_STRONG_SIGNAL', 'mode': 'MODEL_RESPONSE_UNATTESTED',
                   'reason': 'PRIOR_RISK_UNRESOLVED', 'probabilities': {}, 'evidence': []}
            payload = json.dumps([0, text, None, 'NOT_CHECKED'], ensure_ascii=False).encode()
            digest = hmac.new(key, payload, 'sha256').hexdigest()
            with closing(sqlite3.connect(path)) as c, c:
                c.executescript('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);'
                    'CREATE TABLE sessions(id TEXT PRIMARY KEY,version INTEGER NOT NULL,prior_pause INTEGER NOT NULL);'
                    'CREATE TABLE events(sid TEXT,request_id TEXT,digest TEXT,result TEXT NOT NULL,PRIMARY KEY(sid,request_id));'
                    'CREATE TABLE tasks(id TEXT PRIMARY KEY,sid TEXT NOT NULL,created_version INTEGER NOT NULL,status TEXT NOT NULL,observation TEXT NOT NULL);')
                c.execute('INSERT INTO meta VALUES (?,?)', ('digest_key', key.hex()))
                c.execute('INSERT INTO sessions VALUES (?,1,1)', (sid,))
                c.execute('INSERT INTO tasks VALUES (?,?,1,?,?)', (tid, sid, 'OPEN', 'UNRESOLVED'))
                c.execute('INSERT INTO events VALUES (?,?,?,?)', (sid, 'old', digest, json.dumps(old)))
            client = Client()
            migrated = Arena(path, client)
            self.assertEqual(migrated.read(sid)['events'], [old])
            self.assertEqual(migrated.read(sid)['tasks'][0]['observation'], 'UNRESOLVED')
            self.assertEqual(migrated.read(sid)['lifecycle'], 'OPEN')
            request = dict(session_id=sid, version=0, request_id='old', text=text, synthetic_only=True)
            self.assertEqual(migrated.evaluate(**request), old)
            self.assertEqual(Arena(path, client).evaluate(**request), old)
            self.assertEqual(client.calls, 0)
            with closing(sqlite3.connect(path)) as c, c:
                self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
                self.assertEqual(c.execute('SELECT digest FROM events').fetchone()[0], digest)
            self.assertNotIn(text.encode(), path.read_bytes())

    def test_future_schema_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'future.sqlite3'
            with closing(sqlite3.connect(path)) as c, c:
                c.execute('PRAGMA user_version = 777')
                c.execute('CREATE TABLE keep(value TEXT)')
                c.execute("INSERT INTO keep VALUES ('future')")
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_DATABASE_SCHEMA'):
                Arena(path, Client())
            self.assertEqual(path.read_bytes(), before)

    def test_migration_failure_rolls_back_additive_columns_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'broken.sqlite3'
            with closing(sqlite3.connect(path)) as c, c:
                c.execute('CREATE TABLE sessions(id TEXT PRIMARY KEY,version INTEGER,prior_pause INTEGER)')
                c.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)')
                c.execute("INSERT INTO meta VALUES ('digest_key','not-hex')")
            with self.assertRaises(ValueError):
                Arena(path, Client())
            with closing(sqlite3.connect(path)) as c, c:
                self.assertNotIn('lifecycle', {r[1] for r in c.execute('PRAGMA table_info(sessions)')})
                self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0], 0)
                self.assertEqual(c.execute("SELECT count(*) FROM sqlite_master WHERE name='tasks'").fetchone()[0], 0)

    def test_remote_environment_cannot_broaden_v5_scope(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {
                'DMSG_MODEL_ENABLED': '1', 'DMSG_MODEL_ID': 'trillionlabs/Zoro-1',
                'DMSG_SYSTEMONE_ENDPOINT': 'https://remote.example/v1/systemone',
                'DMSG_REMOTE_TEXT_CONSENT': '1', 'DMSG_REMOTE_HOST_ALLOWLIST': 'remote.example'}):
            with self.assertRaisesRegex(bridge.ModelUnavailable, 'V50_LOOPBACK_ONLY'):
                Arena(Path(tmp) / 'not_created.sqlite3')
            self.assertFalse((Path(tmp) / 'not_created.sqlite3').exists())

    def test_endpoint_validation_precedes_host_scope_check(self):
        for endpoint in ['https://user:pass@remote.example/v1/systemone', 'https://remote.example/other',
                         'http://127.0.0.1:99999/v1/systemone', 'http://127.0.0.1/v1/systemone?q=1',
                         'http://127.0.0.1/v1/systemone#x', ' http://127.0.0.1/v1/systemone']:
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(bridge.ModelUnavailable, 'INVALID_MODEL_ENDPOINT'):
                check_loopback_endpoint(endpoint)
        for endpoint in ['http://127.0.0.1:8008/v1/systemone', 'https://localhost/v1/systemone/', '']:
            check_loopback_endpoint(endpoint)
        with self.assertRaisesRegex(bridge.ModelUnavailable, 'V50_LOOPBACK_ONLY'):
            check_loopback_endpoint('https://remote.example/v1/systemone')


if __name__ == '__main__':
    unittest.main()
