"""dmsg v3.4: fail-closed, source-aware synthetic demo policy.

Caution: evidence substrings only prove transcription fidelity. Evidence KIND
and DIRECTNESS are human-authored labels for controlled fixtures, not model facts.
No banking, telephony, messaging or network side effects.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Optional, Tuple

class Action(str, Enum):
    NO_STRONG_SIGNAL = 'NO_STRONG_SIGNAL'
    CAUTION = 'CAUTION'
    PAUSE_AND_VERIFY = 'PAUSE_AND_VERIFY'
    ASK_HUMAN = 'ASK_HUMAN'

class Kind(str, Enum):
    TRANSFER = 'TRANSFER'
    OTP = 'OTP'
    REMOTE_INSTALL = 'REMOTE_INSTALL'
    PERSONAL_DATA = 'PERSONAL_DATA'
    UNVERIFIED_LINK = 'UNVERIFIED_LINK'
    SECRECY = 'SECRECY'
    OTHER = 'OTHER'

class Directness(str, Enum):
    DIRECT_REQUEST = 'DIRECT_REQUEST'
    REPORTED_OR_QUOTED = 'REPORTED_OR_QUOTED'
    NEGATED_OR_WARNING = 'NEGATED_OR_WARNING'
    UNCLEAR = 'UNCLEAR'

class Origin(str, Enum):
    FIXTURE_ANNOTATED = 'FIXTURE_ANNOTATED'
    HUMAN_CONFIRMED = 'HUMAN_CONFIRMED'
    MODEL_PROPOSED = 'MODEL_PROPOSED'

class Status(str, Enum):
    OK = 'OK'
    UNAVAILABLE = 'UNAVAILABLE'
    INVALID = 'INVALID'
    NOT_CONNECTED = 'NOT_CONNECTED'

@dataclass(frozen=True)
class Evidence:
    kind: Kind
    start: int
    end: int
    quote: str
    directness: Directness
    origin: Origin

@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str
    evidence: Tuple[Evidence, ...]
    # This display is intentionally not a numeric risk / scam posterior.
    message: str
    mode: str = 'FIXTURE / SIMULATED'

MESSAGES = {
  Action.NO_STRONG_SIGNAL: '이 입력에서 뚜렷한 위험 행동 요청을 찾지 못했습니다. 안전하다는 의미는 아닙니다.',
  Action.CAUTION: '추가 확인이 필요합니다. 상대방이 알려준 연락처 대신 스스로 찾은 공식 경로를 사용하세요.',
  Action.PAUSE_AND_VERIFY: '요청받은 송금·인증정보 제공·원격제어 설치 등을 멈추고 독립적인 공식 경로로 확인하세요.',
  Action.ASK_HUMAN: '판단 근거가 불충분합니다. 지금 중요한 행동을 실행하지 말고 신뢰할 수 있는 사람이나 공식 창구에서 확인하세요.'
}
DANGEROUS = {Kind.TRANSFER, Kind.OTP, Kind.REMOTE_INSTALL, Kind.PERSONAL_DATA}
CAUTIONARY = {Kind.UNVERIFIED_LINK, Kind.SECRECY}

def _result(action: Action, reason: str, spans: Tuple[Evidence,...] = ()) -> Decision:
    return Decision(action, reason, spans, MESSAGES[action])

def decide(text: str, spans: Tuple[Evidence, ...], *, status: Status = Status.OK,
           user_asks_review: bool = False) -> Decision:
    if type(text) is not str or not text.strip() or len(text) > 2000:
        return _result(Action.ASK_HUMAN, 'EMPTY_OR_INVALID_INPUT')
    if not isinstance(status, Status) or type(user_asks_review) is not bool:
        return _result(Action.ASK_HUMAN, 'INVALID_CONTROL_SCHEMA')
    if type(spans) is not tuple or len(spans) > 20:
        return _result(Action.ASK_HUMAN, 'INVALID_EVIDENCE_COLLECTION')
    for s in spans:
        if not isinstance(s, Evidence) or not isinstance(s.kind, Kind) or not isinstance(s.directness, Directness) or not isinstance(s.origin, Origin):
            return _result(Action.ASK_HUMAN, 'INVALID_EVIDENCE_SCHEMA')
        if type(s.start) is not int or type(s.end) is not int or type(s.quote) is not str:
            return _result(Action.ASK_HUMAN, 'INVALID_EVIDENCE_OFFSET')
        if not (0 <= s.start < s.end <= len(text)) or text[s.start:s.end] != s.quote:
            return _result(Action.ASK_HUMAN, 'EVIDENCE_OFFSET_MISMATCH')
    # Contradictory overlapping spans cannot be promoted to a verified action.
    from .ontology import assess_evidence
    if assess_evidence(spans).contradictions:
        return _result(Action.ASK_HUMAN, 'CONFLICTING_EVIDENCE_ANNOTATIONS')
    # A text quote is not evidence of its *meaning*. Unverified labels must never
    # silently acquire the authority of a checked dangerous-action request.
    unreviewed = [s for s in spans if s.origin == Origin.MODEL_PROPOSED]
    if unreviewed:
        return _result(Action.ASK_HUMAN, 'UNVERIFIED_MODEL_EVIDENCE')
    verified_direct = tuple(s for s in spans if s.directness == Directness.DIRECT_REQUEST)
    risk = tuple(s for s in verified_direct if s.kind in DANGEROUS)
    if risk:
        return _result(Action.PAUSE_AND_VERIFY, 'CONFIRMED_DIRECT_RISK_REQUEST', risk)
    if status is not Status.OK:
        return _result(Action.ASK_HUMAN, 'MODEL_NOT_AVAILABLE')
    if user_asks_review or any(s.directness == Directness.UNCLEAR for s in spans):
        return _result(Action.ASK_HUMAN, 'AMBIGUOUS_DIRECTNESS')
    caution = tuple(s for s in verified_direct if s.kind in CAUTIONARY)
    if caution:
        return _result(Action.CAUTION, 'CONFIRMED_CAUTIONARY_REQUEST', caution)
    # A reported risk, training warning, or negation is NOT direct instruction.
    if spans and any(s.directness == Directness.REPORTED_OR_QUOTED for s in spans):
        return _result(Action.CAUTION, 'REPORTED_ACTION_NOT_DIRECT_REQUEST')
    return _result(Action.NO_STRONG_SIGNAL, 'NO_VALIDATED_DIRECT_REQUEST')


def quote_from(text: str, snippet: str, kind: Kind, directness: Directness,
               origin: Origin = Origin.FIXTURE_ANNOTATED) -> Evidence:
    index = text.index(snippet)
    return Evidence(kind, index, index + len(snippet), snippet, directness, origin)


def fingerprint(text: str) -> str:
    """A non-reversible per-event content digest. Never a proof of semantic truth."""
    return sha256(text.encode('utf-8')).hexdigest()
