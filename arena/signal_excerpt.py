"""Optional display of one original request clause, scored independently."""

import re
from time import monotonic

from integration.v48 import bridge, normalize_response

from .signal import PROFILES, SPEC, evaluate_signal, selected_or_fallback


_ALERTS = {'red', 'orange'}
_SEPARATORS = re.compile(r'[.!?。！？]+(?=\s|$)|[\r\n;；]+')
_GREETINGS = re.compile(r'(?:안녕하세요|안녕하십니까|반갑습니다)[.!?。！？]*')
_EXPLICIT_REQUEST = re.compile(
    r'(?:해|해\s*주실|보내|보내\s*주실|알려|입금해|송금해|이체해|눌러|열어|찍어|연결해|설치해)'
    r'\s*(?:줘|주세요|주실래요|주시면|줄래|줄\s*수|주시겠|수\s*있)'
    r'|(?:송금|이체|입금|인증|확인|연락|설치|전달|접속)\s*(?:부탁|가능해)',
    re.IGNORECASE,
)
_REPORTED = re.compile(
    r'[“”「」『』"]|(?:해|보내|알려|하|주)\s*달라고|(?:라|자)고\s*(?:했|한다|하더|말|적|쓰)'
    r'|(?:요구|요청)\s*받았|달라는\s*(?:말|문자|메시지|요청)|(?:요구|요청)하지\s*않',
    re.IGNORECASE,
)
_MAX_CANDIDATES = 8
_MAX_EXCERPT_LENGTH = 180
_TIME_BUDGET_SECONDS = 2.0
_MAX_CALL_TIMEOUT_SECONDS = 0.75


class _ExcerptModelClient(bridge.ModelClient):
    def __init__(self, client, budget):
        super().__init__(endpoint=client.endpoint, model_id=client.model_id, enabled=client.enabled)
        self.budget = budget

    def timeout(self):
        return min(super().timeout(), self.budget)


def _candidates(text):
    candidates = []
    start = 0
    for end in [*(m.end() for m in _SEPARATORS.finditer(text)), len(text)]:
        raw = text[start:end]
        left = start + len(raw) - len(raw.lstrip())
        right = start + len(raw.rstrip())
        start = end
        if not 0 < right - left <= _MAX_EXCERPT_LENGTH:
            continue
        clause = text[left:right]
        if _GREETINGS.fullmatch(clause):
            continue
        flags = bridge.context_flags(clause)
        if flags.warning_cue or flags.report_cue or _REPORTED.search(clause):
            continue
        if flags.request_cue or _EXPLICIT_REQUEST.search(clause):
            candidates.append((left, right, flags.action_mentioned, flags.pressure_cue))
    # Look across the input before bounding model work. Prefer action cues, then later
    # requests, since messenger greetings commonly precede the actual request.
    return sorted(candidates, key=lambda span: (-span[2], -span[3], -span[0]))[:_MAX_CANDIDATES]


def evaluate_signal_card(client, text, *, profile='baseline'):
    result = evaluate_signal(client, text, profile=profile)
    if (result['grade'] not in _ALERTS
            or result['requested_action']['id'] in {'no_request', 'unknown'}
            or result['context_review']['scope'] in {'protective_warning', 'past_report'}):
        return result

    deadline = monotonic() + _TIME_BUDGET_SECONDS
    questions = {'q_signal': PROFILES[profile]['q_signal']}
    spec = {'q_signal': SPEC['q_signal']}
    best = None
    try:
        for start, end, _, _ in _candidates(text):
            remaining = deadline - monotonic()
            if remaining <= 0:
                return result
            scorer = client
            if type(client) is bridge.ModelClient:
                scorer = _ExcerptModelClient(client, min(_MAX_CALL_TIMEOUT_SECONDS, remaining))
            clause = text[start:end]
            raw, _ = scorer.infer(clause, question_payload={'state': clause, 'questions': questions})
            answer = normalize_response(raw, spec)['q_signal']
            if selected_or_fallback(answer, 'gray') in _ALERTS:
                scores = answer['probabilities']
                candidate = (scores['red'] + scores['orange'], -start, end)
                if best is None or candidate > best:
                    best = candidate
    except (bridge.ModelUnavailable, bridge.ContractError):
        return result
    if best is not None:
        _, negative_start, end = best
        result['confirmation_excerpt'] = {'start': -negative_start, 'end': end}
    return result
