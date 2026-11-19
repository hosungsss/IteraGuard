import hashlib
import json
import unittest

from arena.signal import PROFILES, evaluate_signal
from tests_v56.test_signal_http import ControlledModel


class ProfileTests(unittest.TestCase):
    def test_baseline_fingerprint_and_fixed_output(self):
        serialized = json.dumps(PROFILES['baseline'], ensure_ascii=False, sort_keys=True).encode()
        signature = hashlib.sha256(serialized).hexdigest()
        self.assertEqual(signature, '7e89c81e25973e5f749a3bb93ea326c31ba2cbc3d10581921867b4fc3d08653e')
        model = ControlledModel()
        message = '합성 테스트입니다.'
        original = evaluate_signal(model, message)
        for name, questions in PROFILES.items():
            self.assertEqual(evaluate_signal(model, message, profile=name), original)
            self.assertEqual(model.requests[-1][1], {'state': message, 'questions': questions})
            self.assertEqual(list(questions), ['q_action', 'q_signal'])
            self.assertEqual(questions['q_action'], PROFILES['baseline']['q_action'])
            self.assertEqual(list(questions['q_signal']['criteria']), ['red', 'orange', 'green', 'gray'])
        self.assertEqual(len(model.requests), 4)
        self.assertEqual(len({q['q_signal']['instructions'] for q in PROFILES.values()}), 3)
