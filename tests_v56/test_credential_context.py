"""Replay four synthetic recorded Zoro responses and check scoped counterexamples."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from arena.store import Arena
from integration import v51, v51_policy
from tests_v51.test_semantic_parity import javascript

CASES = json.loads(Path(__file__).with_name('synthetic_credential_cases.json').read_text(encoding='utf-8'))
NEW_RULES = {'V51_EXPLICIT_CREDENTIAL_WARNING', 'V51_EXPLICIT_PAST_CREDENTIAL_REPORT'}


class RecordedResponse:
    def __init__(self, raw):
        self.raw = raw

    def infer(self, text, *, question_payload):
        return deepcopy(self.raw), 1.0


class CredentialContext(unittest.TestCase):
    def test_recorded_decision_and_open_tasks(self):
        for case in CASES:
            with self.subTest(case=case['id']), TemporaryDirectory() as path:
                arena = Arena(Path(path) / 'arena.sqlite3', client=RecordedResponse(case['raw']),
                              profile_id=v51.selected_profile())
                sid = arena.start()['session_id']
                result = arena.evaluate(session_id=sid, version=0, request_id='replay',
                                        text=case['text'], synthetic_only=True)
                self.assertEqual(result['model_status'], 'VALID')
                self.assertIn(result['current_turn_action'], case['expect_current'])
                self.assertEqual(arena.read(sid)['open_task_count'], case['expect_open_tasks'])

    def test_bounded_forms_preserve_contrary_context_and_js_parity(self):
        warning, report = CASES[1:3]
        p = v51.P.profile(v51.selected_profile(), 'legacy')
        profile = {'spec': p['response_schema'], 'optional': p['optional_questions']}
        probes = [
            (warning['text'], warning['raw'], 'V51_EXPLICIT_CREDENTIAL_WARNING'),
            (report['text'], report['raw'], 'V51_EXPLICIT_PAST_CREDENTIAL_REPORT'),
            ('인증번호를 절대 알려 주지 마십시오.', warning['raw'], 'V51_EXPLICIT_CREDENTIAL_WARNING'),
            ('지난번에 상대가 “OTP를 보내 주세요”라고 말했습니다.', report['raw'], 'V51_EXPLICIT_PAST_CREDENTIAL_REPORT'),
            (warning['text'][:-1] + ', 지금은 그 코드를 보내 주세요.', warning['raw'], None),
            (warning['text'] + '\n받은 OTP를 보내 주세요.', warning['raw'], None),
            (report['text'][:-1] + ', 이번에는 그대로 하세요.', report['raw'], None),
            (report['text'].replace('’', '"'), report['raw'], None),
        ]
        strong_exposure = deepcopy(warning['raw'])
        strong_exposure['answers']['q_current_exposure']['noul'] = 0.95
        probes.append((warning['text'], strong_exposure, None))
        missing_evidence = deepcopy(report['raw'])
        del missing_evidence['answers']['q_evidence']
        probes.append((report['text'], missing_evidence, None))
        js_cases = [{'text': text, 'raw': raw} for text, raw, _ in probes]
        js = javascript(js_cases, profile)
        for (text, raw, expected), other in zip(probes, js):
            with self.subTest(text=text, expected=expected):
                decision = v51_policy.advisory(text, raw, profile)
                self.assertEqual(other, {'ok': True, 'result': decision})
                if expected:
                    self.assertEqual(decision['reason'], expected)
                else:
                    self.assertNotIn(decision['reason'], NEW_RULES)


if __name__ == '__main__':
    unittest.main()
