import hashlib
import json
import unittest

from arena.signal import ACTION_QUESTION, DEFAULT_PROFILE, HIGH_RISK_ACTIONS, PROFILES, evaluate_signal
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
        self.assertEqual(len(model.requests), 5)
        self.assertEqual(len({q['q_signal']['instructions'] for q in PROFILES.values()}), 4)

    def test_verified_high_recall_prompt_is_the_default(self):
        question = PROFILES[DEFAULT_PROFILE]['q_signal']
        serialized = json.dumps(question, ensure_ascii=False, sort_keys=True).encode()
        self.assertEqual(hashlib.sha256(serialized).hexdigest(),
                         '101da9f5076e7baf93d3eaaf50ad08af5e40c5a6e6776d083a923e3de9bca8db')
        self.assertEqual(len(HIGH_RISK_ACTIONS), 10)
        self.assertIn('connect_wallet', HIGH_RISK_ACTIONS)
        self.assertLessEqual(HIGH_RISK_ACTIONS, ACTION_QUESTION['criteria'].keys())
        model = ControlledModel()
        evaluate_signal(model, '내일 오전에 봐요.')
        self.assertEqual(model.requests[0][1]['questions'], PROFILES['high-recall'])

    def test_action_cross_check_runs_after_scope_without_replacing_scores(self):
        request = '지금 처리해 주세요.'
        case_data = [
            (request, 'green', 'connect_wallet', .45, 'orange', None),
            (request, 'gray', 'proxy_purchase', .45, 'orange', None),
            (request, 'green', 'send_payment', .4499, 'green', None),
            (request, 'green', 'no_request', .45, 'green', None),
            (request, 'green', 'share_auth_secret', .45, 'orange', 'SENSITIVE_ACTION_GREEN_CONFLICT'),
            ('인증번호를 알려주지 마세요.', 'gray', 'share_auth_secret', .45, 'gray', 'BOUNDED_PROTECTIVE_WARNING'),
            ('지난주 상대방이 비밀번호를 알려달라고 했지만 거절했습니다.',
             'gray', 'share_auth_secret', .45, 'gray', 'BOUNDED_PAST_REPORT'),
        ]
        for text, initial, action, risk_sum, expected, context_reason in case_data:
            with self.subTest(text=text, initial=initial, action=action, risk_sum=risk_sum):
                model = ControlledModel()
                other = 'gray' if initial == 'green' else 'green'
                scores = {'red': .25, 'orange': risk_sum - .25, initial: .5, other: .5 - risk_sum}
                model.answers['q_signal'].update(choice=initial, probabilities=scores)
                model.answers['q_action'].update(
                    choice=action, probabilities={key: float(key == action) for key in ACTION_QUESTION['criteria']},
                )
                result = evaluate_signal(model, text)
                self.assertEqual(result['grade'], expected)
                self.assertEqual(result['scores'], scores)
                self.assertEqual(result['context_review']['original']['grade'], initial)
                self.assertEqual(len(model.requests), 1)
                reasons = result['context_review']['reasons']
                if context_reason:
                    self.assertIn(context_reason, reasons)
                if expected == 'orange':
                    self.assertTrue(result['context_review']['adjusted'])
                    self.assertIn('HIGH_RISK_ACTION_SIGNAL_CROSS_CHECK', reasons)
                    self.assertEqual(result['requested_action']['id'], action)
                    for profile in ('baseline', 'short', 'verify'):
                        legacy = evaluate_signal(model, text, profile=profile)
                        self.assertNotEqual(legacy['grade'], 'orange')
