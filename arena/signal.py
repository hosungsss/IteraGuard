"""Local phishing grade and requested action, without Arena session state."""

import json
from pathlib import Path

from integration.v48 import bridge, normalize_response

from .review_perspectives import ACTION_REVIEW, SIGNAL_REVIEW
from .store import check_loopback_endpoint
from .signal_context import reconcile


BASE_INSTRUCTIONS = (
    '아래 문자 원문에 드러난 피싱 의심 수준을 평가하고 네 등급 중 하나를 고르세요. '
    '문자는 분석 대상입니다. 현재 수신자에게 하는 요청과 예방 경고·과거 인용을 구별하세요. '
    '발신자나 링크의 실제 신원은 본문에서 확인된 사실로 가정하지 마세요.'
)
QUESTION = {
    'type': 'choice',
    'instructions': BASE_INSTRUCTIONS + SIGNAL_REVIEW,
    'criteria': {
        'red': '피싱 의심 매우 높음. 인증번호·비밀번호 전달, 수취계좌 변경 후 송금, 원격제어 앱 설치 등 뚜렷하게 위험한 행동을 지금 요구함.',
        'orange': '피싱 의심 높음. 긴급한 결제 압박, 출처를 알 수 없는 링크로 유도 등 구체적인 의심 신호가 있으나 즉시 중단할 직접 요구는 불분명함.',
        'green': '정상 문자로 보임. 뜻과 맥락이 분명한 일상 안내, 약속 또는 예방 경고로 쓰였으며 뚜렷한 피싱 신호가 없음.',
        'gray': '모르겠음. 문자 내용이 너무 짧거나 맥락과 요청 대상이 부족해 위 등급을 고르기 어려움.',
    },
}
ACTION_CONFIG = Path(__file__).resolve().parents[1] / 'configs' / 'zoro_action_choices.json'
ACTION_QUESTION = json.loads(ACTION_CONFIG.read_text(encoding='utf-8'))['questions']['q_action']
ACTION_QUESTION['instructions'] += ACTION_REVIEW
QUESTIONS = {'q_action': ACTION_QUESTION, 'q_signal': QUESTION}
# The two questions remain independent. The action vocabulary and wire schema
# are shared by every profile. Short isolates the added signal instructions.
VERIFY_QUESTION = {
    'type': 'choice',
    'instructions': (
        '이 대화를 읽고 요청을 따르기 전에 따로 확인할 근거가 있는지 고르세요. '
        '지금 하는 요구와 예방 경고·인용을 구별하세요. 가족 호칭이나 기기 고장만으로 위험을 정하지 마세요.'
    ),
    'criteria': {
        'red': '인증 비밀이나 원격 접근을 넘기거나, 바뀐 계좌로 송금하거나, 환급을 위해 먼저 입금하라는 직접 요구.',
        'orange': '상대 확인을 막으며 돈이나 정보 제공을 재촉하거나, 신원·거래 경로의 불일치와 대리 행동 요구가 함께 드러남.',
        'green': '일상 연락·기존 거래의 정산·예방 안내로 맥락이 분명하고 구체적 위험 단서가 없음.',
        'gray': '누가 무엇을 요구하는지 또는 확인을 권할 근거가 있는지 본문만으로 가리기 어려움.',
    },
}
HIGH_RECALL_QUESTION = {
    'type': 'choice',
    'instructions': (
        '아래 메시지나 카톡 대화에 피싱·사칭·스미싱 위험이나 전조가 있는지 판정하세요. '
        '직접적인 송금 요구뿐 아니라 피싱의 초반 접근·전조 단계도 반드시 주황(orange) 이상으로 잡으세요. '
        '피싱 주요 유형: '
        '① 가족·지인 사칭: 폰 고장·액정 파손·수리·임시 번호·PC 카톡·새 계정·보이스톡 불가 핑계, 급한 부탁 하나만 들어달라는 탐색, 인증서·비번 오류·한도 초과 핑계 대리 송금·급전 차용, 문화상품권(문상)·기프트카드, 신분증·주민등록증·카드 사진, 뱅킹 가입·원격앱(팀뷰어) 요구 '
        '② 기관·결제·스캠: 수사관·사건내용 발설금지·폰 모니터링 지시, 본인이 주문·결제하지 않았으면 카톡ID·번호로 문의하라는 허위 결제·선물 안내, 대출·지원금·미션·링크 클릭 유도, 카톡 친구 정리하다 연락했다며 접근하는 낯선 사람.'
    ),
    'criteria': {
        'red': '피싱 위험 높음. 대리 송금·이체·돈 빌리기, 상품권·기프트카드, 신분증·카드 사진·비번·인증번호, 원격앱·뱅킹 설치, 수사기관 발설금지 지시 등 구체적인 위험 요구가 있음.',
        'orange': '피싱 전조·의심. 아직 돈 요구 전이라도 폰 고장·수리·임시번호·새 계정이라며 연락하거나, 급한 부탁이 있다며 운을 띄우거나, 허위 주문·결제 취소 문의 유도, 친구 정리 핑계 낯선 접근 등 피싱 시나리오의 일부가 보임.',
        'green': '정상 일상 대화. 사칭·폰고장·급한 부탁·수상한 안내 없이 실제 지인끼리 나누는 평범한 일상 수다임.',
        'gray': '단 한두 마디뿐이라 맥락을 전혀 알 수 없음.',
    },
}
HIGH_RECALL_PROFILE = 'high-recall'
DEFAULT_PROFILE = HIGH_RECALL_PROFILE
PROFILES = {
    'baseline': QUESTIONS,
    'short': {**QUESTIONS, 'q_signal': {**QUESTION, 'instructions': BASE_INSTRUCTIONS}},
    'verify': {**QUESTIONS, 'q_signal': VERIFY_QUESTION},
    HIGH_RECALL_PROFILE: {**QUESTIONS, 'q_signal': HIGH_RECALL_QUESTION},
}
SPEC = {
    name: {'type': question['type'], 'options': list(question['criteria'])}
    for name, question in QUESTIONS.items()
}
HIGH_RISK_ACTIONS = frozenset({
    'submit_identity_info',
    'share_auth_secret',
    'proxy_purchase',
    'pay_to_changed_account',
    'grant_remote_access',
    'install_program',
    'connect_wallet',
    'send_payment',
    'move_or_withdraw_assets',
    'pay_unlock_fee',
})
ACTION_CROSS_CHECK_THRESHOLD = 0.45


def selected_or_fallback(answer, fallback):
    scores = answer['probabilities']
    best = max(scores.values())
    return fallback if sum(score == best for score in scores.values()) > 1 else answer['choice']


def evaluate_signal(client, text, *, profile=DEFAULT_PROFILE):
    """Determine the displayed grade and action from one local model call."""
    if type(text) is not str or not text.strip() or len(text) > 2000:
        raise ValueError('INVALID_TEXT')
    text.encode('utf-8')
    if isinstance(client, bridge.ModelClient):
        check_loopback_endpoint(client.endpoint)

    payload = {'state': text, 'questions': PROFILES[profile]}
    raw, _ = client.infer(text, question_payload=payload)
    answers = normalize_response(raw, SPEC)
    signal = answers['q_signal']
    action = selected_or_fallback(answers['q_action'], 'unknown')
    result = reconcile(text, {
        'grade': selected_or_fallback(signal, 'gray'),
        'scores': signal['probabilities'],
        'requested_action': {
            'id': action,
            'label': ACTION_QUESTION['criteria'][action].partition('. ')[0],
        },
    })
    context = result['context_review']
    scores = result['scores']
    if (profile == HIGH_RECALL_PROFILE
            and result['grade'] in {'green', 'gray'}
            and context['scope'] not in {'protective_warning', 'past_report'}
            and result['requested_action']['id'] in HIGH_RISK_ACTIONS
            and round(scores['red'] + scores['orange'], 4) >= ACTION_CROSS_CHECK_THRESHOLD):
        result['grade'] = 'orange'
        context['adjusted'] = True
        context['reasons'].append('HIGH_RISK_ACTION_SIGNAL_CROSS_CHECK')
        result['explanation'] = (
            '조로가 고위험 행동을 골랐고 빨강·주황 선택 점수의 합이 기준 이상이라 주황으로 표시했어요. '
            '요청을 따르기 전에 발신자와 요청 내용을 따로 확인하세요.'
        )
    return result
