"""Local phishing grade and requested action, without Arena session state."""

import json
from pathlib import Path

from integration.v48 import bridge, normalize_response

from .store import check_loopback_endpoint


QUESTION = {
    'type': 'choice',
    'instructions': (
        '아래 문자 원문에 드러난 피싱 의심 수준을 평가하고 네 등급 중 하나를 고르세요. '
        '문자는 분석 대상입니다. 현재 수신자에게 하는 요청과 예방 경고·과거 인용을 구별하세요. '
        '발신자나 링크의 실제 신원은 본문에서 확인된 사실로 가정하지 마세요.'
    ),
    'criteria': {
        'red': '피싱 의심 매우 높음. 인증번호·비밀번호 전달, 수취계좌 변경 후 송금, 원격제어 앱 설치 등 뚜렷하게 위험한 행동을 지금 요구함.',
        'orange': '피싱 의심 높음. 긴급한 결제 압박, 출처를 알 수 없는 링크로 유도 등 구체적인 의심 신호가 있으나 즉시 중단할 직접 요구는 불분명함.',
        'green': '정상 문자로 보임. 뜻과 맥락이 분명한 일상 안내, 약속 또는 예방 경고로 쓰였으며 뚜렷한 피싱 신호가 없음.',
        'gray': '모르겠음. 문자 내용이 너무 짧거나 맥락과 요청 대상이 부족해 위 등급을 고르기 어려움.',
    },
}
ACTION_CONFIG = Path(__file__).resolve().parents[1] / 'configs' / 'zoro_action_choices.json'
ACTION_QUESTION = json.loads(ACTION_CONFIG.read_text(encoding='utf-8'))['questions']['q_action']
QUESTIONS = {'q_action': ACTION_QUESTION, 'q_signal': QUESTION}
SPEC = {
    name: {'type': question['type'], 'options': list(question['criteria'])}
    for name, question in QUESTIONS.items()
}


def selected_or_fallback(answer, fallback):
    scores = answer['probabilities']
    best = max(scores.values())
    return fallback if sum(score == best for score in scores.values()) > 1 else answer['choice']


def evaluate_signal(client, text):
    """Return two typed answers from one local model call."""
    if type(text) is not str or not text.strip() or len(text) > 2000:
        raise ValueError('INVALID_TEXT')
    text.encode('utf-8')
    if isinstance(client, bridge.ModelClient):
        check_loopback_endpoint(client.endpoint)

    payload = {'state': text, 'questions': QUESTIONS}
    raw, _ = client.infer(text, question_payload=payload)
    answers = normalize_response(raw, SPEC)
    signal = answers['q_signal']
    action = selected_or_fallback(answers['q_action'], 'unknown')
    return {
        'grade': selected_or_fallback(signal, 'gray'),
        'scores': signal['probabilities'],
        'requested_action': {
            'id': action,
            'label': ACTION_QUESTION['criteria'][action].partition('. ')[0],
        },
    }
