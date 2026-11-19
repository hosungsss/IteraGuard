"""Observation regression: synthetic clients only, in-memory SQLite only."""
import sqlite3
import unittest
from contextlib import contextmanager
from arena.store import Arena
from integration.v48 import bridge


class MissingModel:
    def infer(self, text):
        raise bridge.ModelUnavailable('TEST_MODEL_UNAVAILABLE')


class MemoryArena(Arena):
    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        super().__init__(':memory:', client=MissingModel())

    @contextmanager
    def connect(self):
        with self.connection:
            yield self.connection


class ObservationPreservationTests(unittest.TestCase):
    def test_no_new_observation_preserves_unresolved_and_retry(self):
        arena = MemoryArena()
        session = arena.start()
        args = dict(session_id=session['session_id'], version=0, request_id='r1',
                    text='합성 확인 요청입니다.', synthetic_only=True)
        first = arena.evaluate(**args)
        task = first['next_task']['id']
        arena.evaluate(**dict(args, version=1, request_id='r2',
                              task_id=task, observation='UNRESOLVED'))
        request = dict(args, version=2, request_id='r3', task_id=task)
        result = arena.evaluate(**request)
        self.assertEqual(arena.read(session['session_id'])['tasks'][0]['observation'], 'UNRESOLVED')
        self.assertEqual(arena.evaluate(**request), result)
        self.assertEqual(result['observation'], 'NOT_CHECKED')
        self.assertEqual(arena.read(session['session_id'])['version'], 3)

    def test_explicit_confirmed_still_completes_the_task(self):
        arena = MemoryArena()
        session = arena.start()
        args = dict(session_id=session['session_id'], version=0, request_id='r1',
                    text='합성 확인 요청입니다.', synthetic_only=True)
        first = arena.evaluate(**args)
        task = first['next_task']['id']
        result = arena.evaluate(**dict(args, version=1, request_id='r2',
                                      task_id=task, observation='USER_REPORTS_CONFIRMED'))
        tasks = arena.read(session['session_id'])['tasks']
        previous = next(t for t in tasks if t['id'] == task)
        self.assertEqual(previous['status'], 'REPORTED_COMPLETE')
        self.assertEqual(previous['observation'], 'USER_REPORTS_CONFIRMED')
        self.assertEqual(result['action'], 'ASK_HUMAN')


if __name__ == '__main__':
    unittest.main()

