"""dmsg reference policy: synthetic transcript only, no network/device effects.

This is not a fraud classifier. It validates externally supplied evidence offsets,
then chooses one of four bounded advisory actions. It intentionally cannot freeze
funds, intercept calls, send alerts, or infer a caller's true identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Action(str, Enum):
    NO_STRONG_SIGNAL = "NO_STRONG_SIGNAL"
    CAUTION = "CAUTION"
    PAUSE_AND_VERIFY = "PAUSE_AND_VERIFY"
    ASK_HUMAN = "ASK_HUMAN"


class EvidenceKind(str, Enum):
    MONEY_TRANSFER = "MONEY_TRANSFER"
    REMOTE_ACCESS = "REMOTE_ACCESS"
    CREDENTIAL_OR_OTP = "CREDENTIAL_OR_OTP"
    UNTRUSTED_APP_INSTALL = "UNTRUSTED_APP_INSTALL"
    UNVERIFIED_LINK = "UNVERIFIED_LINK"
    SECRECY_PRESSURE = "SECRECY_PRESSURE"
    IDENTITY_CLAIM = "IDENTITY_CLAIM"
    OTHER = "OTHER"


class Mode(str, Enum):
    REAL_ZORO = "REAL_ZORO"
    SURROGATE = "SURROGATE"
    FIXTURE = "FIXTURE"


class ModelStatus(str, Enum):
    OK = "OK"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class EvidenceSpan:
    kind: EvidenceKind
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Observation:
    transcript: str
    spans: Tuple[EvidenceSpan, ...] = ()
    mode: Mode = Mode.FIXTURE
    model_status: ModelStatus = ModelStatus.OK
    human_review_requested: bool = False
    claimed_identity: str | None = None
    run_id: str = "synthetic"
    model_attested: bool = False  # caller claims completed external endpoint handshake
    model_id: str | None = None
    checkpoint_revision: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    action: Action
    template_ko: str
    evidence_spans: Tuple[EvidenceSpan, ...]
    reason_code: str
    engine_mode: Mode
    live_attestation_declared: bool


TEMPLATES = {
    Action.NO_STRONG_SIGNAL: "현재 입력에서 뚜렷한 위험 행동 요청은 확인되지 않았습니다. 안전한 통화라는 뜻은 아닙니다.",
    Action.CAUTION: "상대의 요구에 응하기 전에 신뢰할 수 있는 독립된 경로로 확인하세요.",
    Action.PAUSE_AND_VERIFY: "송금·인증정보 제공·원격제어 등 요청된 행동을 잠시 멈추고 공식 경로에서 직접 확인하세요.",
    Action.ASK_HUMAN: "정보가 부족하거나 판단할 수 없습니다. 통화 상대가 알려준 번호 대신 독립된 경로로 확인하세요.",
}

DANGEROUS = {
    EvidenceKind.MONEY_TRANSFER,
    EvidenceKind.REMOTE_ACCESS,
    EvidenceKind.CREDENTIAL_OR_OTP,
    EvidenceKind.UNTRUSTED_APP_INSTALL,
}
CAUTIONARY = {EvidenceKind.UNVERIFIED_LINK, EvidenceKind.SECRECY_PRESSURE}


def _validated_spans(obs: Observation) -> Tuple[EvidenceSpan, ...] | None:
    if not isinstance(obs.transcript, str) or len(obs.transcript) > 50000:
        return None
    if not isinstance(obs.spans, tuple) or len(obs.spans) > 30:
        return None
    for span in obs.spans:
        if not isinstance(span, EvidenceSpan) or not isinstance(span.kind, EvidenceKind):
            return None
        if not isinstance(span.start, int) or isinstance(span.start, bool):
            return None
        if not isinstance(span.end, int) or isinstance(span.end, bool):
            return None
        if not isinstance(span.text, str):
            return None
        if span.start < 0 or span.end > len(obs.transcript) or span.start >= span.end:
            return None
        if obs.transcript[span.start:span.end] != span.text:
            return None
    return obs.spans


def evaluate(obs: Observation) -> PolicyDecision:
    """Return a safe *advisory* state. No detection-performance claim implied.

    NOTE: exact substring matching is only evidence *fidelity*, NOT proof that the
    semantic label of the span is true. A separate labeled benchmark and human
    review are mandatory before deployment.
    """
    if not isinstance(obs, Observation) or not isinstance(obs.mode, Mode) or not isinstance(obs.model_status, ModelStatus):
        mode = obs.mode if isinstance(obs, Observation) and isinstance(obs.mode, Mode) else Mode.FIXTURE
        return PolicyDecision(Action.ASK_HUMAN, TEMPLATES[Action.ASK_HUMAN], (), "INVALID_SCHEMA", mode, False)

    spans = _validated_spans(obs)
    if spans is None:
        return PolicyDecision(Action.ASK_HUMAN, TEMPLATES[Action.ASK_HUMAN], (), "INVALID_EVIDENCE", obs.mode, False)

    # A verified text quote labeled as risky is sufficient to recommend pausing;
    # this does not certify the label or any actual financial risk.
    dangerous = tuple(s for s in spans if s.kind in DANGEROUS)
    if dangerous:
        action, reason, supporting = Action.PAUSE_AND_VERIFY, "EXPLICIT_RISKY_ACTION", dangerous
    elif obs.model_status != ModelStatus.OK:
        action, reason, supporting = Action.ASK_HUMAN, "MODEL_UNAVAILABLE_OR_INVALID", ()
    elif obs.human_review_requested:
        action, reason, supporting = Action.ASK_HUMAN, "AMBIGUOUS_INPUT", ()
    else:
        caution = tuple(s for s in spans if s.kind in CAUTIONARY)
        if caution:
            action, reason, supporting = Action.CAUTION, "CAUTIONARY_CUE", caution
        else:
            action, reason, supporting = Action.NO_STRONG_SIGNAL, "NO_EXPLICIT_RISKY_REQUEST", ()

    return PolicyDecision(
        action=action,
        template_ko=TEMPLATES[action],
        evidence_spans=supporting,
        reason_code=reason,
        engine_mode=obs.mode,
        live_attestation_declared=(obs.mode == Mode.REAL_ZORO and obs.model_status == ModelStatus.OK
                                and obs.model_attested is True and bool(obs.model_id)
                                and bool(obs.checkpoint_revision)),
    )
