import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests_v56.test_signal_http import ControlledModel
from tools.zoro import benchmark_signal as bench


class PairedEvaluationTests(unittest.TestCase):
    def test_cutoff_keeps_ties_together_and_obeys_negative_budget(self):
        def row(label, score):
            return {'label': label, 'scores': {'red': score, 'orange': 0}}
        rows = [row(1, .9), row(1, .7), row(0, .7)] + [row(0, .1)] * 19
        self.assertEqual(bench.validation_cutoff(rows), .7)
        self.assertEqual(bench.validation_cutoff(rows[:-1]), .9)
        self.assertIsNone(bench.validation_cutoff([row(0, .8), row(1, .8)]))

    def test_paired_and_privacy_and_partial_failure(self):
        model = ControlledModel()
        rows = [(0, '합성 평문 일상'), (1, '합성 평문 위험')]
        data = {k: rows for k in ('valid', 'test', 'challenge')}
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'complete'
            summary = bench.run(model, data, out, 'TEST_DOUBLE')
            self.assertEqual(len(model.requests), 18)
            self.assertEqual(summary['test']['verify']['display']['n'], 2)
            self.assertTrue(all(n == 0 for n in summary['test']['verify']['paired_vs_baseline'].values()))
            self.assertNotIn('합성 평문', (out / 'predictions.jsonl').read_text(encoding='utf8'))
            self.assertEqual(json.loads((out / 'manifest.json').read_text())['status'], 'COMPLETE')
            with self.assertRaises(FileExistsError):
                bench.run(model, data, out, 'TEST_DOUBLE')
            model.answers = {}
            failed = Path(tmp) / 'failed'
            with self.assertRaises(bench.bridge.ContractError):
                bench.run(model, data, failed, 'TEST_DOUBLE')
            self.assertEqual(json.loads((failed / 'manifest.json').read_text())['status'], 'INCOMPLETE')
            self.assertFalse((failed / 'summary.json').exists())

    def test_pairing_rejects_a_shift_and_counts_both_directions(self):
        left = [dict(row=i, input_sha256=str(i), label=label, grade=grade)
                for i, (label, grade) in enumerate([(1,'gray'),(1,'red'),(0,'orange'),(0,'green')])]
        right = [dict(row, grade=g) for row, g in zip(left, ('red','green','gray','red'))]
        self.assertEqual(set(bench.paired(left, right).values()), {1})
        with self.assertRaises(ValueError):
            bench.paired(left, right[::-1])
