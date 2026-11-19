"""Typed-output proposal adapter. Separates untrusted inference from policy authority.

No HTTP client or credential is embedded. Supply a validated response mapping to
inspect a model suggestion; it cannot label a conversation as fraudulent.
"""
from __future__ import annotations
from dataclasses import dataclass
from .typed_contract import normalize_response, QUESTION_SPEC
from .core import Origin, Directness, Kind, Evidence, Action, decide

@dataclass(frozen=True)
class Proposal:
    kind: Kind
    directness: Directness
    candidate_probability: float
    evidence: Evidence | None
    policy_action: Action
    confidence_is_scam_probability: bool = False
    source_status: str = 'UNVERIFIED_MODEL_PROPOSAL'

_KIND={'transfer':Kind.TRANSFER, 'otp':Kind.OTP,
       'remote_install':Kind.REMOTE_INSTALL, 'link':Kind.UNVERIFIED_LINK,
       'none':Kind.OTHER, 'unclear':Kind.OTHER}

def inspect_response(text: str, raw: dict, start: int, end: int) -> Proposal:
    parsed=normalize_response(raw,QUESTION_SPEC)
    kind_key=parsed['request_action']['choice']
    directness=Directness.DIRECT_REQUEST if parsed['direct_instruction']['probabilities']['yes'] > 0.5 else Directness.UNCLEAR
    candidate=float(parsed['request_action']['probabilities'][kind_key])
    if type(start) is not int or type(end) is not int or type(text) is not str or not (0<=start<end<=len(text)):
        raise ValueError('INVALID_GROUNDED_SPAN')
    # Even correctly grounded bytes are not verification of semantic meaning.
    span=Evidence(_KIND[kind_key],start,end,text[start:end],directness,Origin.MODEL_PROPOSED)
    policy=decide(text,(span,)).action
    return Proposal(span.kind,directness,candidate,span,policy)
