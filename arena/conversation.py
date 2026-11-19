"""Bounded follow-up incident guidance based on an EXISTING Arena session.

No generative chat, Zoro re-inference, database writes, outbound calls, message
transcript storage or risk clearance. Questions are explicit named situations.
A follow-up is not a new incoming SMS and MUST NOT be sent to /api/evaluate.
"""
from __future__ import annotations

KISA = "https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205023&nttId=71936&pageIndex=1&searchCnd=&searchWrd="
FTC = "https://consumer.ftc.gov/articles/how-recognize-avoid-phishing-scams"
SOURCES = [
    {"name": "KISA 스미싱 대응 공식 권고", "url": KISA},
    {"name": "FTC 피싱 대응 소비자 안내", "url": FTC},
]

# These responses are human-authored conservative guidance, NOT language-model
# text. They deliberately don't give clean bills of safety or perform actions.
SCENARIOS = {
    "link_only": (
        "링크만 누르면 안전한가요?",
        "링크 클릭과 인증정보 입력은 서로 다른 행동이지만, 입력하지 않았다고 그 링크가 안전한 것은 아닙니다.",
        [
            "메시지에 포함된 링크를 실제로 열지 마세요. 기관 앱이나 직접 입력한 공식 주소에서 확인하세요.",
            "이미 열었다면 웹페이지만 봤는지, 파일을 내려받거나 앱을 설치했는지, 비밀번호·인증번호를 입력했는지 구분해 주세요.",
            "이 앱은 링크나 발신자 신원을 직접 검증하지 않으므로 안전 판정을 제공하지 않습니다.",
        ],
        ["clicked", "installed", "entered_secret", "verify"],
    ),
    "clicked": (
        "이미 링크를 눌렀어요.",
        "클릭 사실만으로 악성앱 감염이나 개인정보 유출을 단정할 수 없습니다. 그렇다고 안전을 보증할 수도 없습니다.",
        [
            "의심 페이지를 닫고 추가 입력·다운로드·앱 설치를 중단하세요.",
            "파일 다운로드 또는 앱 설치, 계정 로그인·인증번호 입력, 결제 여부를 각각 확인하세요.",
            "보안 업데이트와 기기 보안 점검을 진행하고 필요하면 KISA 118 등 공식 상담 경로를 사용하세요.",
        ],
        ["downloaded", "installed", "entered_secret", "paid", "verify"],
    ),
    "downloaded": (
        "파일을 다운로드했어요.",
        "파일을 내려받은 사실과 실행·설치한 사실은 다릅니다. 무엇을 실행했는지 확인해야 합니다.",
        [
            "다운로드한 파일을 실행하거나 설치하지 말고, 공식 보안 앱 또는 전문가를 통해 검사하세요.",
            "이미 앱을 실행·설치했다면 설치/실행 상황에 대한 별도 대응을 진행하세요.",
            "다운로드 경로와 파일 종류를 확인하되 의심 링크를 다시 열지 마세요.",
        ],
        ["installed", "entered_secret", "verify"],
    ),
    "installed": (
        "의심스러운 앱을 설치했어요.",
        "앱의 실제 악성 여부는 이 대화만으로 확정할 수 없지만, 추가 피해를 막기 위한 기기 점검이 필요합니다.",
        [
            "해당 앱을 더 이상 사용하거나 권한을 추가로 허용하지 마세요.",
            "신뢰할 수 있는 모바일 보안 점검을 수행하고, 악성앱으로 확인되면 제거하거나 공식 서비스센터의 지원을 받으세요.",
            "금융·인증정보가 노출됐을 가능성이 있다면 별도 안전한 기기에서 관련 서비스의 공식 지원 채널에 문의하세요.",
            "지속적인 이상 활동이나 금전 피해가 있다면 KISA 118 및 해당 금융기관에 확인하세요.",
        ],
        ["entered_secret", "paid", "verify"],
    ),
    "entered_secret": (
        "인증번호나 비밀번호를 입력했어요.",
        "인증정보를 입력하거나 전달했다면 계정·결제 악용 위험을 우선 확인해야 합니다. 실제 악용 여부는 아직 알 수 없습니다.",
        [
            "메시지에 적힌 연락처가 아니라 해당 서비스의 공식 앱이나 직접 찾은 고객센터에 즉시 문의하세요.",
            "관련 계정의 비밀번호와 인증수단을 안전한 기기에서 변경·재설정하고 로그인 이력과 결제 내역을 확인하세요.",
            "SMS 인증번호·OTP를 다시 보내거나 추가 인증 요구에 응답하지 마세요.",
            "금융 피해가 의심되면 금융기관의 사고 신고 및 거래 제한 절차를 문의하세요.",
        ],
        ["paid", "verify"],
    ),
    "paid": (
        "이미 송금하거나 결제했어요.",
        "금전 거래가 이미 진행됐다면 재확인보다 피해 확산 방지와 긴급 신고가 우선입니다. 이 앱은 거래를 취소하거나 지급 정지하지 못합니다.",
        [
            "즉시 사용한 은행·카드사의 공식 고객센터에 연락해 사고 신고, 거래 정지 또는 회수 가능성을 문의하세요.",
            "국내 피해라면 경찰 112 등 공식 신고 경로를 이용하고, 수신 문자와 거래내역 등 증거를 안전하게 보존하세요.",
            "송금 취소를 명목으로 추가 이체·수수료 납부·원격앱 설치를 요구하면 응하지 마세요.",
        ],
        ["verify", "unknown"],
    ),
    "verify": (
        "어떻게 공식적으로 확인하나요?",
        "보낸 사람의 표시명이나 문자 속 URL·전화번호만으로 발신자를 인증할 수 없습니다.",
        [
            "기존에 직접 저장했거나 기관 공식 사이트·앱에서 확인한 연락처로 별도 연락하세요.",
            "계좌 변경이면 기존 계약서·장부에 등록된 담당자에게 독립 확인하고, 확인 전 송금을 보류하세요.",
            "문자·스미싱은 KISA 보호나라의 공식 확인 서비스나 118 상담을 이용할 수 있습니다.",
            "확인 결과를 사용자가 보고했다고 해서 독립적으로 사실이 인증된 것은 아닙니다.",
        ],
        ["link_only", "clicked", "entered_secret"],
    ),
    "not_clicked": (
        "아직 링크를 누르지 않았어요.",
        "아직 행동하지 않았다면 메시지 안의 안내 대신 공식 경로를 이용하는 것이 우선입니다.",
        [
            "메시지의 링크·첨부·QR코드를 열거나 인증정보를 입력하지 마세요.",
            "기존에 알고 있던 전화번호 또는 공식 앱에서 요청의 진위를 확인하세요.",
            "정상 공지로 보이더라도 이 앱의 판단만으로 안전이 보증되지는 않습니다.",
        ],
        ["verify", "unknown"],
    ),
    "unknown": (
        "현재 상황을 더 확인하고 싶어요.",
        "무엇을 했는지 확인되지 않아 피해 여부나 안전 여부를 단정할 수 없습니다.",
        [
            "링크만 열었는지, 파일을 받았는지, 앱을 설치했는지, 인증정보를 입력했는지, 송금·결제를 했는지 구분해 주세요.",
            "모르는 상태라면 새로 링크를 열거나 정보를 입력하지 말고 기존 공식 경로로 확인하세요.",
            "이 안내는 정해진 상황별 규칙으로 작성됐으며 일반 대화형 모델이 생성한 답변이 아닙니다.",
        ],
        ["clicked", "downloaded", "installed", "entered_secret", "paid", "verify"],
    ),
}


class GuidanceError(Exception):
    def __init__(self, code, status=400):
        self.code = code
        self.status = status
        super().__init__(code)


def guide(state, *, session_id, version, scenario, synthetic_only):
    """Read-only guidance with server-side session/version binding.

    The caller MUST obtain state from Arena.read(session_id). This function
    cannot create tasks, mark outcomes verified, clear a hold or write SQLite.
    """
    if synthetic_only is not True:
        raise GuidanceError("SYNTHETIC_ONLY_REQUIRED")
    if type(session_id) is not str or type(version) is not int or type(scenario) is not str:
        raise GuidanceError("INVALID_CONVERSATION_CONTRACT")
    if scenario not in SCENARIOS:
        raise GuidanceError("UNKNOWN_FOLLOWUP_SCENARIO")
    if not isinstance(state, dict) or state.get("id") != session_id:
        raise GuidanceError("SESSION_BINDING_MISMATCH", 409)
    if state.get("version") != version:
        raise GuidanceError("STALE_SESSION_VERSION", 409)
    if state.get("lifecycle") != "OPEN":
        raise GuidanceError("SESSION_CLOSED_UNRESOLVED", 409)
    events = state.get("events")
    if not isinstance(events, list):
        raise GuidanceError("INVALID_SESSION_EVENTS", 409)
    last = next((e for e in reversed(events) if isinstance(e, dict) and
                 e.get("event_type") == "EVALUATE"), None)
    if last is None:
        raise GuidanceError("FIRST_EVALUATION_REQUIRED", 409)
    # If an evaluation was followed by a new state transition, do not claim
    # its result is the latest actionable guidance without re-evaluation.
    if not isinstance(events[-1], dict) or events[-1] is not last:
        raise GuidanceError("CURRENT_EVALUATION_REQUIRED", 409)
    heading, introduction, steps, next_scenarios = SCENARIOS[scenario]
    action = last.get("action")
    model_failed = last.get("model_status") != "VALID"
    held = bool(state.get("prior_pause"))
    if model_failed:
        banner = "기존 모델 응답을 검증하지 못했습니다. 아래 내용은 모델 판단이 아닌 일반적인 사고 대응 안내입니다."
    elif held:
        banner = "이전 위험 판단이 미해결로 유지됩니다. 후속 상담은 이를 해제하거나 결제·연락을 실행하지 않습니다."
    elif action in ("ASK_HUMAN", "CAUTION", "PAUSE_AND_VERIFY"):
        banner = "현재 문장에 대한 추가 확인이 필요합니다. 사기 여부 확정이나 안전 보증은 아닙니다."
    else:
        banner = "현재 문장에서 강한 위험이 탐지되지 않았더라도 링크·거래 안전성이 검증된 것은 아닙니다."
    return {
        "schema": "iteraguard-guided-conversation/1",
        "mode": "RULE_BASED_FOLLOWUP_NOT_GENERATIVE",
        "session_id": session_id,
        "version": version,
        "scenario": scenario,
        "title": heading,
        "introduction": introduction,
        "steps": list(steps),
        "risk_notice": banner,
        "next_scenarios": list(next_scenarios),
        "sources": [dict(src) for src in SOURCES],
        "model_status": "FAILED" if model_failed else "VALID_UNATTESTED",
        "prior_pause_retained": held,
        "action_taken": False,
        "task_updated": False,
        "risk_cleared": False,
        "raw_question_stored": False,
        "decision_changed": False,
    }
