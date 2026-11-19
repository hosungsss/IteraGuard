"""Development counterexamples. Fixed model vectors, not new model evaluations."""
import unittest
from unittest.mock import patch
from tests_v51.test_semantic_parity import raw,profile,javascript
from integration import v51_policy as P

class Lexical(unittest.TestCase):
 def cases(self):
  return [
   ('본인에게 전송된 일회용 확인 코드를 이 메시지의 답장으로 보내세요.',True),
   ('일회용 확인코드를 보내 주세요.',True),
   ('일회용 인증 코드를 알려 주세요.',True),
   ('일회용 확인 코드를 보내지 마세요.',False),
   ('일회용 확인 코드를 절대 알려주지 마세요.',False),
   ('사기범이 일회용 확인 코드를 보내라고 했습니다.',False),
   ('일회용 확인 코드를 보내지 마세요. 하지만 지금 제게 일회용 확인 코드를 보내 주세요.',True),
   ('일회용 확인 코드란 로그인에 쓰는 코드입니다.',False),
  ]
 def test_synonyms_and_warning_report_guards(self):
  for text,risk in self.cases():
   with self.subTest(text=text):
    vector=raw(action='otp',scope='sensitive_request',exposure=.95) if risk or '마세요' in text or '사기범' in text else raw(speech='informational',scope='no_request')
    out=P.advisory(text,vector,profile())
    self.assertEqual(out['action']=='PAUSE_AND_VERIFY',risk)
 def test_same_response_before_after_and_threshold_unchanged(self):
  text=self.cases()[0][0];vector=raw(action='otp',scope='sensitive_request',exposure=.95)
  current=P._rules();old=dict(current,exposure_terms=[x for x in current['exposure_terms'] if x not in ['일회용 확인 코드','일회용 확인코드','일회용 인증 코드']])
  with patch.object(P,'_rules',return_value=old):before=P.advisory(text,vector,profile())
  after=P.advisory(text,vector,profile())
  self.assertEqual(before['action'],'ASK_HUMAN');self.assertEqual(after['action'],'PAUSE_AND_VERIFY');self.assertEqual(current['threshold'],.7)
 def test_python_javascript_same_results(self):
  cases=[dict(text=t,raw=raw(action='otp',scope='sensitive_request',exposure=.95)) for t,_ in self.cases()]
  results=javascript(cases)
  for case,result in zip(cases,results):self.assertEqual(result,dict(ok=True,result=P.advisory(case['text'],case['raw'],profile())))

if __name__=='__main__':unittest.main()
