"""Versioned current-turn evaluation. No inference, persistence, or session clearance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from integration.v48 import bridge, normalize_response

ROOT = Path(__file__).resolve().parents[1]
ContractError = bridge.ContractError
SOURCES = frozenset(("MODEL_RESPONSE_UNATTESTED", "FIXTURE", "SURROGATE", "ON_DEVICE_NLP"))


def question_signature(questions):
    """Arrays explicitly preserve question and Choice order; object field order is irrelevant."""
    rows = []
    for key, question in questions.items():
        criteria = question.get("criteria")
        rows.append([key, question["type"], question.get("instructions"),
                     "choice" if isinstance(criteria, dict) else "levels" if isinstance(criteria, list) else "absent",
                     list(map(list, criteria.items())) if isinstance(criteria, dict) else criteria])
    return rows


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def execution_manifest():
    manifest = json.loads((ROOT / "configs/v50_contract.json").read_text(encoding="utf-8"))
    fingerprint = manifest.pop("manifest_fingerprint")
    if _hash(manifest) != fingerprint:
        raise ContractError("EXECUTION_MANIFEST_FINGERPRINT_MISMATCH")
    signature = question_signature(bridge.questions("")["questions"])
    if signature != manifest["question_signature"] or _hash(signature) != manifest["question_contract_sha256"]:
        raise ContractError("QUESTION_CONTRACT_DRIFT")
    for relative, expected in manifest["source_hashes"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ContractError("EXECUTION_SOURCE_DRIFT")
    manifest["manifest_fingerprint"] = fingerprint
    return manifest


def _policy(policy_id):
    if policy_id not in ("legacy", "dra"):
        raise ContractError("UNSUPPORTED_POLICY_ID")


def _legacy_predicates(text, normalized, result):
    """Calculate the unchanged policy's predicates, including conditions shadowed by priority."""
    a, speech = normalized["q_action"]["choice"], normalized["q_speech"]["choice"]
    pa = normalized["q_action"]["probabilities"][a]
    ps = normalized["q_speech"]["probabilities"][speech]
    flags, profile = bridge.context_flags(text), bridge.clause_profile(text)
    acts = [c for c in profile if c.flags.action_mentioned]
    clean, imperative = [c for c in acts if c.clean_action], [c for c in acts if c.clean_imperative]
    values = [
        ("MODEL_NONE_BUT_ACTION_TERMS_PRESENT", a == "none" and flags.action_mentioned and speech != "informational"),
        ("NONE_DIRECT_REQUEST_CONFLICT", a == "none" and speech == "direct_request"),
        ("DIRECT_REQUEST_CONTRADICTS_CONTEXT", speech == "direct_request" and bool(acts) and not clean),
        ("WARNING_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE", speech == "negated_or_warning" and bool(imperative)),
        ("UNSUPPORTED_WARNING_LABEL", speech == "negated_or_warning" and bool(acts) and not any(c.flags.warning_cue for c in acts)),
        ("INFORMATIONAL_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE", speech == "informational" and bool(imperative)),
        ("REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE", speech == "reported_or_quoted" and bool(imperative)),
        ("UNSUPPORTED_QUOTATION_LABEL", speech == "reported_or_quoted" and bool(acts) and not any(c.flags.report_cue for c in acts)),
    ]
    predicates, context_rule = [], None
    for ident, condition in values:
        predicates.append({"id": ident, "condition_met": bool(condition), "eligible": context_rule is None})
        if condition and context_rule is None:
            context_rule = ident
    if context_rule != bridge.context_conflict(a, speech, flags, profile):
        raise ContractError("TRACE_CONTEXT_POLICY_DRIFT")
    low_parts = [("LOW_ACTION_PROBABILITY", pa < .70), ("LOW_SPEECH_PROBABILITY", ps < .70),
                 ("UNCLEAR_ACTION_LABEL", a == "unclear"), ("UNCLEAR_SPEECH_LABEL", speech == "unclear")]
    low = any(value for _, value in low_parts)
    predicates.extend({"id": ident, "condition_met": value, "eligible": context_rule is None} for ident, value in low_parts)
    predicates.append({"id": "MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS", "condition_met": low, "eligible": context_rule is None})
    scam, pressure = normalized["q_scam"]["probabilities"]["yes"], normalized["q_pressure"]["probabilities"]["yes"]
    aux = bool(flags.pressure_cue and (scam >= .70 or pressure >= .70))
    conflict = a == "none" and (scam >= .70 or pressure >= .70 and flags.pressure_cue)
    eligible = context_rule is None and not low
    predicates.append({"id": "CONFLICTING_MODEL_QUESTIONS", "condition_met": bool(conflict), "eligible": eligible})
    branch = eligible and not conflict
    anchor = bridge._choose_anchor(text, a) is not None
    anchor_branch = branch and speech != "informational" and a != "none"
    branches = [
        ("AUX_COERCION_BLOCKS_INFORMATIONAL_CLEARANCE", speech == "informational" and aux, branch),
        ("MODEL_INFORMATIONAL_NOT_REQUEST", speech == "informational" and not aux, branch),
        ("NO_ACTION_CANDIDATE_NOT_SAFETY_CLEARANCE", a == "none", branch and speech != "informational"),
        ("NO_GROUNDED_ACTION_ANCHOR", not anchor, anchor_branch),
        ("AUX_COERCION_BLOCKS_WARNING_CLEARANCE", speech == "negated_or_warning" and aux, anchor_branch and anchor),
        ("MODEL_WARNING_NOT_REQUEST", speech == "negated_or_warning" and not aux, anchor_branch and anchor),
        ("MODEL_REPORTED_REQUEST", speech == "reported_or_quoted", anchor_branch and anchor),
        ("MODEL_DIRECT_ACTION_ADVISORY", a in ("transfer", "otp", "remote_install", "personal_data"), anchor_branch and anchor and speech not in ("negated_or_warning", "reported_or_quoted")),
        ("MODEL_DIRECT_CAUTION_ADVISORY", a not in ("transfer", "otp", "remote_install", "personal_data"), anchor_branch and anchor and speech not in ("negated_or_warning", "reported_or_quoted")),
    ]
    predicates.extend({"id": ident, "condition_met": bool(value), "eligible": bool(allowed)} for ident, value, allowed in branches)
    base_rule = context_rule or ("MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS" if low else "CONFLICTING_MODEL_QUESTIONS" if conflict else next(ident for ident, value, allowed in branches if value and allowed))
    clear_or_caution = base_rule in {"MODEL_INFORMATIONAL_NOT_REQUEST", "NO_ACTION_CANDIDATE_NOT_SAFETY_CLEARANCE", "MODEL_WARNING_NOT_REQUEST", "MODEL_REPORTED_REQUEST", "MODEL_DIRECT_CAUTION_ADVISORY"}
    ev_no = normalized.get("q_evidence", {}).get("probabilities", {}).get("no")
    ev_condition = ev_no is not None and ev_no >= .70
    predicates.append({"id": "MODEL_EVIDENCE_INSUFFICIENT", "condition_met": ev_condition, "eligible": clear_or_caution})
    applied = [base_rule] + (["MODEL_EVIDENCE_INSUFFICIENT"] if ev_condition and clear_or_caution else [])
    if applied[-1] != result["reason"]:
        raise ContractError("TRACE_FINAL_POLICY_DRIFT")
    return predicates, applied


def _dra_predicates(normalized, result):
    # The arbiter already emits its actual applied adjustment list. Do not infer missing vetoes.
    fired = result["trace"]
    catalog = ["UNGROUNDED_" + a.upper() for a in bridge.ACTION_OPTIONS if bridge.DRA_ACTION_CLASS[a] in ("HIGH", "MID")]
    catalog += ["CLEAN_IMPERATIVE_ACTION_CLAUSE", "ALL_ACTION_CLAUSES_WARNED_OR_REPORTED", "AUX_COERCION_WITH_PRESSURE_CUE", "MODEL_EVIDENCE_DOUBT", "PAUSE_WITHOUT_ANCHOR_DEMOTED"]
    predicates = [{"id": key, "condition_met": key in fired, "eligible": True} for key in catalog]
    ev_no = normalized.get("q_evidence", {}).get("probabilities", {}).get("no")
    transfer = ev_no is not None and ev_no > 0
    predicates.append({"id": "DRA_EVIDENCE_TRANSFER_FACTOR", "condition_met": transfer, "eligible": ev_no is not None})
    return predicates, list(fired) + (["DRA_EVIDENCE_TRANSFER_FACTOR"] if transfer else []) + [result["reason"]]


def _trace(manifest, policy_id, source, status, result, normalized=None, predicates=None, applied=None, raw=None):
    normalized = normalized or {}
    echo = raw.get("model") if isinstance(raw, dict) else None
    return {"schema_version": manifest["trace_schema_version"], "manifest_fingerprint": manifest["manifest_fingerprint"],
        "question_contract_sha256": manifest["question_contract_sha256"], "policy_id": policy_id,
        "model_status": status, "inference_source": source, "runtime": {
            "expected_temperature": manifest["runtime"]["expected_temperature"],
            "temperature_source": manifest["runtime"]["temperature_source"],
            "temperature_observed_by_this_evaluator": False, "model_attested": False,
            "domain_calibration": "NOT_ESTABLISHED", "client_probability_recalibration": "NONE",
            "model_echo_status": "ABSENT" if echo is None else "MATCH_UNAUTHENTICATED" if echo == manifest["runtime"]["model_id"] else "MISMATCH_UNAUTHENTICATED"},
        "predicates": predicates or [], "condition_ids": [p["id"] for p in predicates or [] if p["condition_met"]],
        "applied_rule_ids": applied or [], "final_rule": result["reason"], "final_action": result["action"],
        "normalized_probabilities": {k: v["probabilities"] for k, v in normalized.items() if not k.startswith("_")},
        "dropped_optional_questions": list(normalized.get("_dropped_optional", [])),
        "evidence_spans": [{k: e[k] for k in ("start", "end", "kind", "directness", "origin") if k in e} for e in result.get("evidence", [])],
        "predicate_semantics": "CONDITION_TRUE_IS_NOT_RULE_APPLIED; eligibility respects current-turn priority",
        "trace_scope": "CURRENT_TURN_ONLY_NO_SESSION_DECISION", "raw_text_stored": False}


def evaluate_current(text, raw, policy_id="legacy", *, source="MODEL_RESPONSE_UNATTESTED"):
    _policy(policy_id)
    if source not in SOURCES:
        raise ContractError("UNSUPPORTED_INFERENCE_SOURCE")
    manifest = execution_manifest()
    normalized = normalize_response(raw, bridge.SPEC, optional=bridge.OPTIONAL_QUESTIONS)
    result = bridge.advisory(text, raw, source=source, threshold=.70) if policy_id == "legacy" else bridge.decision_relevant_advisory(text, raw, source=source)
    predicates, applied = _legacy_predicates(text, normalized, result) if policy_id == "legacy" else _dra_predicates(normalized, result)
    result.setdefault("probs", {k: v["probabilities"] for k, v in normalized.items() if not k.startswith("_")})
    result.update(policy_id=policy_id, manifest_fingerprint=manifest["manifest_fingerprint"],
                  execution_trace=_trace(manifest, policy_id, source, "VALID", result, normalized, predicates, applied, raw))
    return result


def unavailable_current(code, policy_id="legacy"):
    _policy(policy_id)
    # Failure details are untrusted. Never reflect a user message, URL, or credential into a stored trace.
    known = {"MODEL_NOT_CONFIGURED", "INVALID_TIMEOUT_CONFIG", "INVALID_MODEL_ENDPOINT", "HTTPS_REQUIRED",
             "REMOTE_TEXT_TRANSFER_NOT_CONSENTED", "REMOTE_HOST_NOT_ALLOWLISTED", "NON_PUBLIC_ENDPOINT_IP", "DNS_FAILURE",
             "REQUEST_TOO_LARGE", "HTTP_STATUS_NOT_OK", "UNEXPECTED_MODEL_CONTENT_TYPE", "RESPONSE_TOO_LARGE",
             "INVALID_RESPONSE_JSON", "MODEL_ID_MISMATCH", "MODEL_ID_ECHO_REQUIRED", "INVALID_TEXT", "EMPTY",
             "CONTRACT_INVALID", "LOCAL_APP_UNREACHABLE", "V50_LOOPBACK_ONLY", "REMOTE_RELAY_DISABLED_V50"}
    value = str(code).split(":")[-1]
    safe = value if value in known or re.fullmatch(r"MODEL_TRANSPORT_ERROR_(?:OSError|TimeoutError|ConnectionRefusedError|ConnectionResetError|gaierror|SSLError|URLError)", value) else "MODEL_OR_CONTRACT_FAILURE"
    manifest = execution_manifest()
    result = {"source": "MODEL_UNAVAILABLE_OR_INVALID", "model_attested": False, "calibration_status": "NOT_ESTABLISHED",
              "action": "ASK_HUMAN", "reason": safe, "message": bridge.MESSAGES[bridge.Action.ASK_HUMAN],
              "mode": "MODEL_UNAVAILABLE_OR_INVALID / NOT_ATTESTED", "probs": {}, "evidence": [], "grounding": "NONE",
              "policy_id": policy_id, "manifest_fingerprint": manifest["manifest_fingerprint"]}
    result["execution_trace"] = _trace(manifest, policy_id, "MODEL_UNAVAILABLE_OR_INVALID", "UNAVAILABLE_OR_INVALID", result, applied=[safe])
    return result


def apply_local_layers(text, result, *, user_review=False, consent=None):
    """Offline postprocessing only. Detailed LinkGuard output is display-only; persist link_summary."""
    if type(text) is not str or type(user_review) is not bool:
        raise ContractError("INVALID_LOCAL_LAYER_INPUT")
    if consent is not None and (type(consent) is not dict or any(k not in {"external_reputation", "web_analysis"} or type(v) is not bool for k, v in consent.items())):
        raise ContractError("INVALID_LOCAL_LAYER_CONSENT")
    out = deepcopy(result)
    if out.get("action") not in {"NO_STRONG_SIGNAL", "CAUTION", "ASK_HUMAN", "PAUSE_AND_VERIFY"}:
        raise ContractError("INVALID_LOCAL_LAYER_ACTION")
    trace = out.get("execution_trace")
    if trace is None:
        manifest = execution_manifest()
        trace = _trace(manifest, out.get("policy_id", "legacy"), "LOCAL_OR_NLP_UPSTREAM", "NOT_EVALUATED_BY_THIS_CONTRACT", out)
        trace.update(trace_scope="LOCAL_POSTPROCESS_ONLY", upstream_evaluation_trace_available=False)
        out["execution_trace"] = trace
    if "local_layers" in trace:
        raise ContractError("LOCAL_LAYERS_ALREADY_APPLIED")
    steps = []
    before = out["action"]
    if user_review and before == "NO_STRONG_SIGNAL":
        out.update(base_action=before, base_reason=out["reason"], action="ASK_HUMAN", reason="USER_REQUESTED_REVIEW", message=bridge.MESSAGES[bridge.Action.ASK_HUMAN])
    steps.append({"id": "USER_REQUESTED_REVIEW", "status": "EVALUATED", "condition_met": user_review,
                  "before_action": before, "after_action": out["action"], "applied": before != out["action"]})
    before = out["action"]
    try:
        from linkguard.intake import intake
        from linkguard.policy import assess_message, fuse
        link = assess_message(intake(text, consent=consent or {}))
        fusion = fuse({"policy_action": before}, link)
        status = "EVALUATED_OFFLINE"
    except ImportError:
        link = {"overall": "SCAN_FAILED", "urls": [], "url_count": 0, "network_used": False, "status": "NOT_AVAILABLE"}
        fusion = {"policy_action": "ASK_HUMAN" if before == "NO_STRONG_SIGNAL" else before,
                  "base_action": before, "escalated": before == "NO_STRONG_SIGNAL",
                  "escalation_reasons": ["LOCAL_LINKGUARD_NOT_AVAILABLE"] if before == "NO_STRONG_SIGNAL" else [], "downgraded": False}
        status = "NOT_AVAILABLE"
    out.update(linkguard=link, linkguard_fusion=fusion)
    if fusion["escalated"]:
        out.update(base_action=before, base_reason=out["reason"], action=fusion["policy_action"], reason=fusion["escalation_reasons"][0], message=bridge.MESSAGES[bridge.Action(fusion["policy_action"])])
    summary = {"status": status, "overall": link["overall"], "url_count": link["url_count"], "network_used": False,
               "escalated": fusion["escalated"], "escalation_reasons": list(fusion["escalation_reasons"])}
    out["link_summary"] = summary
    steps.append({"id": "OFFLINE_LINKGUARD", "status": status, "before_action": before, "after_action": out["action"],
                  "applied": fusion["escalated"], "summary": deepcopy(summary)})
    trace["local_layers"] = steps
    trace["current_turn_policy_action"] = trace["final_action"]
    trace["current_turn_policy_rule"] = trace["final_rule"]
    trace["final_action"], trace["final_rule"] = out["action"], out["reason"]
    trace["applied_rule_ids"] += [s["id"] if s["id"] == "USER_REQUESTED_REVIEW" else out["reason"] for s in steps if s["applied"]]
    return out
