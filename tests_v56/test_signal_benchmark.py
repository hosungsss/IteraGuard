"""Exercise the benchmark with synthetic inputs and controlled model responses."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore, Event
from time import monotonic, sleep
import unittest
from unittest.mock import call, patch

from arena import signal_benchmark
from integration.v48 import bridge


CASES = [
    ('0', '가상 테스트 정상 한 건'),
    ('1', '가상 테스트 피싱 한 건'),
    ('0', '가상 테스트 정상 두 번째'),
]
LABEL_COUNTS = {'0': 2, '1': 1}


class DatasetTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'test.csv'

    def check_dataset(self, content):
        data = content.encode('utf-8-sig')
        self.path.write_bytes(data)
        with patch.multiple(
            signal_benchmark,
            CSV_BYTES=len(data),
            CSV_SHA256=hashlib.sha256(data).hexdigest(),
            TOTAL=len(CASES),
            LABEL_COUNTS=LABEL_COUNTS,
        ):
            return signal_benchmark.load_cases(self.path)

    def test_preserves_quoted_newlines_and_labels(self):
        self.assertEqual(
            self.check_dataset('LABEL,TEXT\r\n0," 가상, 한 줄\r\n두 줄 "\r\n1,가상 둘\r\n0,가상 셋\r\n'),
            [('0', ' 가상, 한 줄\r\n두 줄 '), ('1', '가상 둘'), ('0', '가상 셋')],
        )

    def test_rejects_same_size_file_with_wrong_fingerprint(self):
        data = 'LABEL,TEXT\n0,가상\n'.encode('utf-8')
        self.path.write_bytes(data)
        with patch.object(signal_benchmark, 'CSV_BYTES', len(data)), self.assertRaises(ValueError):
            signal_benchmark.load_cases(self.path)

    def test_pinned_file_must_still_match_the_expected_schema(self):
        for broken in (
            'TYPE,MSG\n0,가상 한 건\n1,가상 둘\n0,가상 셋\n',
            'LABEL,TEXT\n0,가상 한 건\n1,가상 둘\n',
            'LABEL,TEXT\n0,가상 한 건\n1,가상 둘\n1,가상 셋\n',
            'LABEL,TEXT\n0,가상 한 건\n1,가상 둘,여분\n0,가상 셋\n',
            'LABEL,TEXT\n0,가상 한 건\n1,가상 둘\n0, \n',
            'LABEL,TEXT\n0,가상 한 건\n1,가상 둘\n0,' + '가' * 2001 + '\n',
        ):
            with self.subTest(sample=broken[:30]), self.assertRaises(ValueError):
                self.check_dataset(broken)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / 'test.csv'
        path.touch()
        self.client = object()
        self.slot = BoundedSemaphore(1)
        self.job = signal_benchmark.SignalBenchmark(path, self.client, self.slot, profile='verify')

    def until_finished(self):
        deadline = monotonic() + 5
        while monotonic() < deadline:
            state = self.job.snapshot()
            if state['status'] != 'running':
                return state
            sleep(.01)
        self.fail('The controlled benchmark remained running')

    @patch.object(signal_benchmark, 'TOTAL', len(CASES))
    @patch.object(signal_benchmark, 'load_cases', return_value=CASES)
    @patch.object(signal_benchmark, 'evaluate_signal')
    def test_runs_once_with_per_row_slot_and_reports_only_aggregate(self, evaluate, load):
        first_case = Event()
        release_first = Event()
        grades = iter(('green', 'red', 'gray'))

        def judge(client, text, *, profile):
            if self.slot.acquire(blocking=False):
                self.slot.release()
                self.fail('Inference ran without reserving the model slot')
            if not first_case.is_set():
                first_case.set()
                if not release_first.wait(3):
                    self.fail('Test did not release first inference')
            return {'grade': next(grades), 'unneeded_raw_input': text}

        evaluate.side_effect = judge
        try:
            self.assertEqual(self.job.start()['status'], 'running')
            self.assertTrue(first_case.wait(2))
            active = self.job.start()
            self.assertEqual(active['status'], 'running')
            self.assertEqual(active['completed'], 0)
            self.assertIsNone(active['result'])
        finally:
            release_first.set()
        final = self.until_finished()
        self.assertEqual(final['status'], 'completed')
        self.assertEqual(final['completed'], len(CASES))
        self.assertIsNone(final['error'])
        self.assertEqual(final['result']['counts'], {
            'normal': {'green': 1, 'orange': 0, 'red': 0, 'gray': 1},
            'phishing': {'green': 0, 'orange': 0, 'red': 1, 'gray': 0},
        })
        load.assert_called_once()
        self.assertEqual(evaluate.call_args_list, [
            call(self.client, text, profile='verify') for _, text in CASES
        ])
        self.assertNotIn('가상 테스트', json.dumps(final, ensure_ascii=False))
        self.assertTrue(self.slot.acquire(blocking=False))
        self.slot.release()

    @patch.object(signal_benchmark, 'TOTAL', len(CASES))
    @patch.object(signal_benchmark, 'load_cases', return_value=CASES)
    @patch.object(signal_benchmark, 'evaluate_signal')
    def test_failed_rerun_preserves_last_complete_result(self, evaluate, load):
        evaluate.return_value = {'grade': 'gray'}
        self.job.start()
        previous = self.until_finished()['result']
        self.assertIsNotNone(previous)

        evaluate.side_effect = [{'grade': 'red'}, bridge.ModelUnavailable('sensitive details')]
        self.job.start()
        failed = self.until_finished()
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['completed'], 1)
        self.assertEqual(failed['result'], previous)
        self.assertEqual(failed['error'], 'BENCHMARK_MODEL_UNAVAILABLE')
        self.assertEqual(load.call_count, 2)
        self.assertTrue(self.slot.acquire(blocking=False))
        self.slot.release()

    @patch.object(signal_benchmark, 'load_cases', side_effect=ValueError('sensitive path'))
    @patch.object(signal_benchmark, 'evaluate_signal')
    def test_bad_csv_never_reaches_model(self, evaluate, load):
        self.job.start()
        failed = self.until_finished()
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['completed'], 0)
        self.assertIsNone(failed['result'])
        self.assertEqual(failed['error'], 'BENCHMARK_CSV_INVALID')
        evaluate.assert_not_called()
