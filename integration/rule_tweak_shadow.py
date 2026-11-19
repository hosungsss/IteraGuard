"""Read-only candidate trace for bounded Korean warnings / reported quotes.

Derived from the team's v5.6 RuleTweak Candidate 1. This module NEVER changes
action, reason, model probabilities, task state, or authority. It is deliberately
not an enforcement path. The existing v5.1 semantic policy remains authoritative.

Source: uploaded IteraGuard_v56_RuleTweak_Candidate1.zip (2026-11-19).
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import re
import unicodedata

from integration import v51

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "rule_tweak_shadow.json"
MODULE = Path(__file__)
REQUIRED = (
    "q_current_exposure", "q_payment_anomaly", "q_evidence",
    "q_speech", "q_request_scope", "q_scam",
)
WARNING = re.compile(
    r"(?:본인 확인을 하더라도 )?(?:지금 받은 |받은 )?"
    r"(?:OTP 인증번호|OTP|인증번호|비밀번호)를 "
    r"(?:(?:이 채팅으로|상대방에게|누구에게도) )?"
    r"(?:보내지 마세요|알려주지 마세요|전달하지 마세요|공유하지 마세요)[.!]?"
)
REPORT = re.compile(
    r"(?:어제|지난주|지난번에) (?:누군가가|상대방이|그 사람이) "
    r"(?:‘[^‘’\n]{1,180}’|\"[^\"\n]{1,180}\"|「[^「」\n]{1,180}」)"
    r"라고 (?:말했다고 들었어요|말했어요|했어요)[.!]?"
)
LIMITS = (
    "min_exposure_no", "min_payment_no", "max_evidence_no",
    "min_warning", "min_warning_no_request", "min_warning_scam_no",
    "min_report", "min_report_no_request",
)


@lru_cache(maxsize=1)
def _config():
    """Load immutable experiment parameters once per process."""
    content = CONFIG.read_bytes()
    obj = json.loads(content)
    if type(obj) is not dict or set(obj) != {"version", "status", *LIMITS}:
        raise ValueError("INVALID_SHADOW_CONFIG_FIELDS")
    if obj["version"] != "bounded-warning-report/1" or obj["status"] != "EXPERIMENT_NOT_VALIDATED":
        raise ValueError("INVALID_SHADOW_CONFIG_VERSION")
    if any(type(obj[x]) not in (int, float) or not math.isfinite(obj[x]) or not 0 <= obj[x] <= 1 for x in LIMITS):
        raise ValueError("INVALID_SHADOW_THRESHOLD")
    return obj, hashlib.sha256(content).hexdigest()


def _score(response, question, key):
    entry = response[question]
    value = entry["probabilities"][key]
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("INVALID_TYPED_PROBABILITY")
    return float(value)


def _candidate(text, outcome, normalized, config):
    if not isinstance(text, str) or not isinstance(outcome, dict):
        return None, "UNAVAILABLE"
    st = outcome.get("semantic_trace")
    if not isinstance(st, dict):
        return None, "NO_SEMANTIC_TRACE"
    if not all(q in normalized for q in REQUIRED):
        return None, "QUESTION_PROFILE_NOT_SUPPORTED"
    eligible = (outcome.get("action") == "ASK_HUMAN"
                and outcome.get("reason") == "MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS"
                and st.get("rule_id") == "BASELINE_FALLBACK"
                and st.get("baseline_action") != "PAUSE_AND_VERIFY")
    if not eligible:
        return None, "INELIGIBLE_BASELINE"
    norm = unicodedata.normalize("NFKC", text).strip()
    norm = re.sub(r"[ \t]+", " ", norm)
    common = (_score(normalized, "q_current_exposure", "no") >= config["min_exposure_no"]
              and _score(normalized, "q_payment_anomaly", "no") >= config["min_payment_no"]
              and _score(normalized, "q_evidence", "no") < config["max_evidence_no"])
    if not common:
        return None, "CONFLICTING_MODEL_SIGNAL"
    speech = normalized["q_speech"]["choice"]
    scope = normalized["q_request_scope"]["choice"]
    if (WARNING.fullmatch(norm) is not None
            and speech == "negated_or_warning" and scope == "no_request"
            and _score(normalized, "q_speech", speech) >= config["min_warning"]
            and _score(normalized, "q_request_scope", "no_request") >= config["min_warning_no_request"]
            and _score(normalized, "q_scam", "no") >= config["min_warning_scam_no"]):
        return "BOUNDED_PROTECTIVE_WARNING", "MATCH"
    if (REPORT.fullmatch(norm) is not None
            and speech == "reported_or_quoted" and scope == "no_request"
            and _score(normalized, "q_speech", speech) >= config["min_report"]
            and _score(normalized, "q_request_scope", "no_request") >= config["min_report_no_request"]):
        return "BOUNDED_PAST_REPORT", "MATCH"
    return None, "NO_BOUNDED_MATCH"


def observe(text, raw, outcome, *, profile_id, policy_id):
    """Add explicit advisory-only trace; never alter the policy decision.

    All shadow errors are isolated from the primary decision path. No raw input
    or raw model output is included in the trace.
    """
    mode = os.environ.get("DMSG_RULE_TWEAK_MODE", "shadow").strip().lower()
    if mode == "off":
        return outcome
    result = deepcopy(outcome)
    metadata = {
        "mode": "shadow" if mode == "shadow" else "unsupported",
        "status": "NOT_EVALUATED", "candidate_rule": None,
        "baseline_action": outcome.get("action"),
        "baseline_reason": outcome.get("reason"),
        "proposed_action": outcome.get("action"),
        "applied": False, "raw_text_stored": False,
        "policy_decision_changed": False,
        "evidence_level": "MODEL_CORRELATED_BOUNDED_GRAMMAR_NOT_INDEPENDENT",
    }
    try:
        if mode != "shadow":
            raise ValueError("SHADOW_ONLY_ENFORCE_BLOCKED")
        if result.get("model_status") == "FAILED":
            metadata["status"] = "MODEL_UNAVAILABLE"
        elif not isinstance(result.get("semantic_trace"), dict):
            metadata["status"] = "NO_SEMANTIC_TRACE"
        else:
            config, digest = _config()
            metadata.update(config_sha256=digest, module_sha256=hashlib.sha256(MODULE.read_bytes()).hexdigest(),
                            version=config["version"])
            normalized = v51.P.normalize_response(raw, profile_id, policy_id)
            rule, status = _candidate(text, result, normalized, config)
            metadata["status"] = status
            metadata["candidate_rule"] = rule
            if rule == "BOUNDED_PROTECTIVE_WARNING":
                metadata["proposed_action"] = "NO_STRONG_SIGNAL"
            elif rule == "BOUNDED_PAST_REPORT":
                metadata["proposed_action"] = "CAUTION"
    except Exception as exc:
        # Shadow observability may not change user protection, including on bad
        # configuration/unknown response shape. Do not include exception text
        # because it might contain user-supplied model output.
        metadata["status"] = "SHADOW_OBSERVATION_ERROR"
        metadata["error_type"] = type(exc).__name__
    trace = result.get("execution_trace")
    if isinstance(trace, dict):
        trace["rule_tweak_shadow"] = metadata
    else:
        # No primary execution trace: never add a false authenticated claim.
        result["rule_tweak_shadow"] = metadata
    return result
