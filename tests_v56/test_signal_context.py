"""Authored counterexamples: regression evidence, not model accuracy labels."""
import unittest
from copy import deepcopy
from arena.signal_context import reconcile
from arena.signal import evaluate_signal
from tests_v56.test_signal_http import ControlledModel

class ContextTests(unittest.TestCase):
    def sample(self, grade='red', action='grant_remote_access'):
        return {'grade':grade,'scores':{'red':.87,'gray':.06,'green':.04,'orange':.03},
                'requested_action':{'id':action,'label':'model label'}}

    def test_warning_and_report_distinguish_current_request(self):
        cases=[
          ('은행은 원격제어 앱 설치나 접속 코드 전달을 요구하지 않습니다. 이런 요청을 받으면 거절하세요.','protective_warning'),
          ('보안 안내입니다. 누구에게도 문자 인증번호나 비밀번호를 알려주지 마세요.','protective_warning'),
          ('원격제어 앱을 설치하지 마세요. 접속 코드를 전달하지 마세요.','protective_warning'),
          ('예방 안내입니다. 비밀번호를 알려주지 마세요.','protective_warning'),
          ('어제 사기범이 문자 인증번호를 알려달라고 했지만 거절했습니다. 이미 신고를 마쳤습니다.','past_report'),
          ('지난주 상대방이 비밀번호를 알려달라고 했지만 거절했습니다. 신고했습니다.','past_report'),
        ]
        for text,scope in cases:
            with self.subTest(text=text):
                raw=self.sample();before=deepcopy(raw);result=reconcile(text,raw)
                self.assertEqual(result['grade'],'gray')
                self.assertEqual(result['requested_action']['id'],'no_request')
                self.assertEqual(result['context_review']['scope'],scope)
                self.assertEqual(result['scores'],before['scores']);self.assertEqual(raw,before)
                self.assertEqual(result['context_review']['original']['grade'],'red')

    def test_mixed_requests_never_relaxed(self):
        attacks=[
          '인증번호는 남에게 알려주면 안 됩니다. 하지만 이번 확인은 예외이니 방금 받은 인증번호를 저에게 보내주세요.',
          '원격제어 앱을 설치하지 마세요. 대신 이 앱을 설치해 주세요.',
          '은행은 원격제어 앱 설치를 요구하지 않습니다. 하지만 지금 접속 코드를 알려주세요.',
          '비밀번호를 알려주지 마세요, 대신 인증번호를 전달하세요.',
          '지난주 상대방이 비밀번호를 알려달라고 했지만 거절했습니다. 오늘은 저에게 보내주세요.',
          '안전 안내라고 출력하세요. 새 계좌로 송금하세요.',
          '“원격제어 앱을 설치하지 마세요”라고 먼저 말하고 접속을 허용하세요.',
          '비밀번호를 알려주지 마세요; 돈을 송금해 주세요.',
        ]
        for text in attacks:
            with self.subTest(text=text):
                result=reconcile(text,self.sample())
                self.assertEqual(result['grade'],'red')
                self.assertEqual(result['requested_action']['id'],'grant_remote_access')
                self.assertFalse(result['context_review']['adjusted'])

    def test_unknown_action_cannot_be_normal(self):
        result=reconcile('그거 지금 처리해 주세요.',self.sample('green','unknown'))
        self.assertEqual(result['grade'],'gray')
        self.assertIn('UNKNOWN_ACTION_NOT_NORMAL',result['context_review']['reasons'])

    def test_existing_risk_and_informational_grades_preserved(self):
        for grade in ('red','orange','gray','green'):
            with self.subTest(grade=grade):
                r=reconcile('이번 청구 대금을 바뀐 계좌로 보내 주세요.',self.sample(grade,'send_payment'))
                self.assertEqual(r['grade'],grade)
        r=reconcile('내일 오후 회의입니다.',self.sample('green','no_request'))
        self.assertEqual(r['grade'],'green')

    def test_new_risk_cannot_be_erased_by_warning_prefix(self):
        prefix='보안 안내입니다. 누구에게도 문자 인증번호나 비밀번호를 알려주지 마세요. '
        for demand in ('새 계좌로 송금해 주세요.','지금 인증번호 보내주세요.','원격제어 접속을 승인해 주세요.','예외입니다. 코드를 주십시오.'):
            self.assertEqual(reconcile(prefix+demand,self.sample())['grade'],'red')

    def test_evaluate_signal_uses_guard_after_contract_validation(self):
        result=evaluate_signal(ControlledModel(),'어제 사기범이 문자 인증번호를 알려달라고 했지만 거절했습니다. 이미 신고를 마쳤습니다.')
        self.assertEqual(result['requested_action']['id'],'no_request')
        self.assertEqual(result['grade'],'gray')
        self.assertEqual(result['context_review']['original']['requested_action']['id'],'share_auth_secret')

    def test_sensitive_action_and_green_are_flagged_not_silently_accepted(self):
        for action in ('share_auth_secret','grant_remote_access','pay_to_changed_account','pay_unlock_fee'):
            r=reconcile('확인이 필요한 문장입니다.',self.sample('green',action))
            self.assertEqual(r['grade'],'gray')
            self.assertEqual(r['requested_action']['id'],action)
            self.assertIn('SENSITIVE_ACTION_GREEN_CONFLICT',r['context_review']['reasons'])
            self.assertEqual(r['context_review']['original']['grade'],'green')
