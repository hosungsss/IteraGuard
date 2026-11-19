"""Synthetic authored demonstration cases; NOT an independent validation set."""
from dataclasses import dataclass
from .core import Kind, Directness, Evidence, quote_from

@dataclass(frozen=True)
class Fixture:
    id: str
    family: str
    title: str
    transcript: str
    evidence: tuple[Evidence, ...]
    story: str


def f(id, family, title, transcript, snippet='', kind=Kind.OTHER,
      directness=Directness.UNCLEAR, story=''):
    evidence=(quote_from(transcript,snippet,kind,directness),) if snippet else ()
    return Fixture(id,family,title,transcript,evidence,story)

CASES = (
 f('NORMAL_BANK','bank_normal','정상적인 은행 방문 안내',
   '고객님, 예금 만기일이 다가옵니다. 자세한 사항은 은행 공식 앱이나 지점에서 직접 확인해 주세요.',story='안전 판정이 아닌, 위험 요청 부재를 표시'),
 f('LEGITIMATE_WARNING','bank_training','정상적인 피해 예방 안내',
   "은행 직원: '송금하세요'라는 요구를 받으면 절대 송금하지 마세요.",
   '송금하세요',Kind.TRANSFER,Directness.NEGATED_OR_WARNING,story='위험 단어가 있다고 경고를 남발하는 실패 방지'),
 f('RISK_TRANSFER','fraud_transfer','송금 압박',
   '검찰입니다. 수사에 필요하니 지금 지정 계좌로 300만 원을 송금하세요.',
   '송금하세요',Kind.TRANSFER,Directness.DIRECT_REQUEST,story='직접 행동 요청이 있을 때만 개입'),
 f('RISK_REMOTE','fraud_remote','원격제어 설치 강요',
   '보안 점검을 해야 합니다. 지금 이 원격제어 앱을 설치하세요.',
   '원격제어 앱을 설치하세요',Kind.REMOTE_INSTALL,Directness.DIRECT_REQUEST,story='설치 전 중단과 독립 확인'),
 f('RISK_OTP','fraud_otp','일회용 인증번호 요구',
   '계정 인증을 위해 문자로 온 OTP 인증번호를 저에게 알려주세요.',
   'OTP 인증번호를 저에게 알려주세요',Kind.OTP,Directness.DIRECT_REQUEST,story='인증정보를 공유하지 않도록 조언'),
 f('AMBIGUOUS','unclear_coupon','모호한 전달 요청',
   '상품권 안내를 보내 드리겠습니다. 다음에 다시 이야기하죠.',story='불명확한 사기 판단 보류'),
 f('CAUTION_LINK','possible_phishing','확인되지 않은 링크',
   '확인을 위해 문자로 받은 링크를 클릭해 주세요.',
   '링크를 클릭해 주세요',Kind.UNVERIFIED_LINK,Directness.DIRECT_REQUEST,story='검증되지 않은 링크의 독립 확인'),
 f('REPORTED','reported_case','신고자의 제3자 발화 인용',
   '고객: 다른 사람이 저에게 송금하세요라고 했다고 신고하려고요.',
   '송금하세요',Kind.TRANSFER,Directness.REPORTED_OR_QUOTED,story='직접 요청과 인용된 신고를 구별'),
)
FIXTURES = {case.id:case for case in CASES}

# Counterfactual / ambiguity-only examples. They remain authored fixtures, not
# labeled ground truth from external call recordings.
EXTRA_CASES = (
 f('LEGIT_TRANSFER','legitimate_action','합법적인 송금 지시 가능성',
   '고객님이 직접 요청한 이체 신청서를 확인하고 정상 처리하려면 지정 계좌로 송금하세요.',
   '송금하세요',Kind.TRANSFER,Directness.DIRECT_REQUEST,
   story='합법성 여부와 무관하게 독립 확인 우선; 범죄 판정 아님'),
 f('IMPERSONATION','authority_unverified','기관 신분 사칭 여부 불명',
   '금융감독원 직원입니다. 제 신분을 믿고 절차를 따라주세요.',
   '절차를 따라주세요',Kind.OTHER,Directness.UNCLEAR,
   story='권위 주장만으로 신분 검증 불가'),
 f('COERCION_INDIRECT','implicit_pressure','간접적인 행동 압박',
   '일을 해결하려면 보유 자금을 잠깐 다른 곳으로 옮길 준비를 하셔야 할 텐데요.',
   '자금을 잠깐 다른 곳으로 옮길 준비',Kind.TRANSFER,Directness.UNCLEAR,
   story='간접 화행은 사전 주석만으로도 직접 명령으로 단정하지 않음'),
 f('REPORTED_OTP','reported_auth','인증번호 요구 신고 인용',
   '고객: 상대방이 OTP 인증번호를 저에게 알려달라고 했습니다.',
   'OTP 인증번호를 저에게 알려달라고',Kind.OTP,Directness.REPORTED_OR_QUOTED,
   story='신고 내용의 인용은 현재 직접 요청이 아님'),
 f('NEGATIVE_OTP','training_auth','인증번호 제공 금지',
   '교육 안내: OTP 인증번호를 알려주지 마세요.',
   'OTP 인증번호를 알려주지 마세요',Kind.OTP,Directness.NEGATED_OR_WARNING,
   story='보안 경고를 범죄 지시로 해석하지 않음'),
 f('SECRET_REQUEST','secrecy_pressure','상담 비밀 유지 지시',
   '이 절차는 다른 가족에게 절대 말하지 마세요.',
   '다른 가족에게 절대 말하지 마세요',Kind.SECRECY,Directness.DIRECT_REQUEST,
   story='비밀 유지 요구만 있을 때는 확인 권고'),
)
CASES = CASES + EXTRA_CASES
FIXTURES = {case.id:case for case in CASES}
