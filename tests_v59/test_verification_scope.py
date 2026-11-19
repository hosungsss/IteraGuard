"""v5.9 request-scoped contract verification: faster, but never weaker than per-call verification."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from arena.store import Arena  # noqa: E402
from integration import v51, v51_profiles as P  # noqa: E402

CASES = [c for c in json.loads((ROOT / 'tests_data/v51/execution_cases.json').read_text(encoding='utf-8')) if c.get('raw')]


class Client:
    def __init__(self, raw, during=None):
        self.raw, self.during = raw, during

    def infer(self, text, *, question_payload=None):
        if self.during:
            self.during()
        return copy.deepcopy(self.raw), 0.


def counting():
    calls = []
    real = P.build_registry

    def wrapped():
        calls.append(1)
        return real()
    return calls, patch.object(P, 'build_registry', side_effect=wrapped)


class Scope(unittest.TestCase):
    def test_outside_scope_every_call_verifies(self):
        calls, p = counting()
        with p:
            P.registry(); P.profile(); P.binding()
        self.assertEqual(len(calls), 3)

    def test_inside_scope_verifies_once_and_returns_copies(self):
        calls, p = counting()
        with p, P.verification_scope():
            a = P.registry(); a['profiles'].clear()
            b = P.registry(); P.profile(); P.binding(); v51.execution_manifest(); v51.execution_manifest()
        self.assertEqual(len(calls), 1)
        self.assertTrue(b['profiles'])

    def test_drift_outside_scope_still_rejected(self):
        real = P._read_json

        def drift(rel):
            value = real(rel)
            if rel == P.REGISTRY_PATH:
                value['profiles'][P.BASELINE]['status'] = 'TAMPERED'
            return value
        with patch.object(P, '_read_json', side_effect=drift):
            with self.assertRaises(P.ContractError):
                P.registry()

    def test_refresh_scope_forces_reverification(self):
        calls, p = counting()
        with p, P.verification_scope():
            P.registry(); P.refresh_scope(); P.registry()
        self.assertEqual(len(calls), 2)

    def test_scope_is_thread_local(self):
        calls, p = counting()
        seen = []
        with p, P.verification_scope():
            P.registry()
            t = threading.Thread(target=lambda: (P.registry(), P.registry(), seen.append(True)))
            t.start(); t.join()
        self.assertEqual(seen, [True])
        self.assertEqual(len(calls), 3)  # 1 in scope + 2 in the other thread (no scope there)

    def test_nested_scope_does_not_reset_outer_cache(self):
        calls, p = counting()
        with p, P.verification_scope():
            P.registry()
            with P.verification_scope():
                P.registry()
            P.registry()
        self.assertEqual(len(calls), 1)


class ArenaRequest(unittest.TestCase):
    def arena(self, d, client):
        return Arena(Path(d) / 'a.db', client=client, profile_id=v51.selected_profile())

    def test_one_request_verifies_at_most_three_times(self):
        with tempfile.TemporaryDirectory() as d:
            a = self.arena(d, Client(CASES[0]['raw']))
            sid = a.start()['session_id']
            calls, p = counting()
            with p:
                r = a.evaluate(session_id=sid, version=0, request_id='r1', text=CASES[0]['text'], synthetic_only=True)
            self.assertEqual(r['model_status'], 'VALID')
            self.assertLessEqual(len(calls), 3)  # identity binding + pre-model scope + post-model scope

    def test_contract_drift_during_model_call_fails_closed(self):
        real = P._read_json
        state = {'drift': False}

        def drift(rel):
            value = real(rel)
            if state['drift'] and rel == P.REGISTRY_PATH:
                value['profiles'][P.BASELINE]['status'] = 'TAMPERED'
            return value
        with tempfile.TemporaryDirectory() as d, patch.object(P, '_read_json', side_effect=drift):
            a = self.arena(d, Client(CASES[0]['raw'], during=lambda: state.update(drift=True)))
            sid = a.start()['session_id']
            with self.assertRaises(P.ContractError):
                a.evaluate(session_id=sid, version=0, request_id='r1', text=CASES[0]['text'], synthetic_only=True)
            state['drift'] = False
            self.assertEqual(a.read(sid)['version'], 0)  # nothing was recorded from a drifted contract

    def test_scope_closed_after_request(self):
        with tempfile.TemporaryDirectory() as d:
            a = self.arena(d, Client(CASES[0]['raw']))
            sid = a.start()['session_id']
            a.evaluate(session_id=sid, version=0, request_id='r1', text=CASES[0]['text'], synthetic_only=True)
        self.assertFalse(getattr(P._SCOPE, 'active', False))


if __name__ == '__main__':
    unittest.main()
