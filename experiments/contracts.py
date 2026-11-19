"""Application-normalized contract, not a kev wire schema."""
import hashlib
import json
import math

STATES = {"NO_STRONG_SIGNAL", "CAUTION", "PAUSE_AND_VERIFY", "ASK_HUMAN"}
MODES = {"FIXTURE", "SURROGATE", "MODEL_RESPONSE_UNATTESTED", "REAL_ZORO"}
CHOICES = {
    "q_action": ["none", "money_transfer", "remote_app_install", "credential_or_otp", "personal_data", "verification_link", "secrecy", "other_unclear"],
    "q_speech": ["direct_request", "quoted_or_reported", "negated_or_warning", "information", "unclear"],
    "q_scam": ["yes", "no"], "q_pressure": ["yes", "no"],
    "q_claim": ["yes", "no"], "q_risk": ["none", "low", "moderate", "high"],
    "q_evidence": ["yes", "no"],
}
REQUIRED = {"q_action", "q_speech", "q_scam", "q_pressure"}


class ContractError(ValueError):
    pass


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def strict_json(line):
    def reject(value):
        raise ContractError("Non-finite JSON constant")
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ContractError("Duplicate JSON key")
            out[key] = value
        return out
    return json.loads(line, parse_constant=reject, object_pairs_hook=unique)


def finite(value, lo=0, hi=1):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ContractError("Invalid numeric value")
    return float(value)


def validate_case(case):
    if not isinstance(case, dict) or case.get("data_mode") != "SYNTHETIC":
        raise ContractError("Only explicitly synthetic datasets are supported")
    for key in ("case_id", "family_id", "text", "split"):
        if not isinstance(case.get(key), str) or not case[key].strip():
            raise ContractError("Missing dataset field: " + key)
    if case["split"] not in {"development", "validation", "locked"} or len(case["text"]) > 2000:
        raise ContractError("Invalid split or text length")
    expected = case.get("expected")
    if not isinstance(expected, list) or not expected or not all(x in STATES for x in expected) or len(set(expected)) != len(expected):
        raise ContractError("Invalid expected states")
    if type(case.get("risk_context")) is not bool:
        raise ContractError("risk_context must be boolean")


def validate_trace(trace, text):
    if not isinstance(trace, dict) or trace.get("schema_version") != "dmsg-kit-trace-v1":
        raise ContractError("Unsupported trace schema")
    if trace.get("inference_mode") not in MODES or trace.get("input_sha256") != fingerprint(text):
        raise ContractError("Input fingerprint or mode mismatch")
    if trace.get("model_status") not in {"VALID", "INVALID", "UNAVAILABLE"}:
        raise ContractError("Invalid model status")
    finite(trace.get("latency_ms"), 0, 3600000)
    if type(trace.get("session_version")) is not int or trace["session_version"] != 1:
        raise ContractError("This single-turn kit requires session version 1")
    if trace["inference_mode"] == "REAL_ZORO" and not isinstance(trace.get("provenance_ref"), str):
        raise ContractError("REAL_ZORO requires an operator evidence reference")
    # The reference is recorded, not authenticated by this validator.
    answers = trace.get("answers")
    if not isinstance(answers, dict) or set(answers) - set(CHOICES):
        raise ContractError("Unknown question IDs")
    if trace["model_status"] == "VALID" and not REQUIRED <= set(answers):
        raise ContractError("Missing required questions")
    for key, answer in answers.items():
        if not isinstance(answer, dict):
            raise ContractError("Invalid answer")
        probs = answer.get("probabilities")
        if not isinstance(probs, dict) or set(probs) != set(CHOICES[key]):
            raise ContractError("Probability labels differ from normalized contract")
        values = {k: finite(v) for k, v in probs.items()}
        if abs(sum(values.values()) - 1) > 0.01:
            raise ContractError("Probability sum invalid")
        selected = answer.get("selected")
        if selected not in values or values[selected] < max(values.values()):
            raise ContractError("Selected label inconsistent")
    evidence = trace.get("evidence")
    if not isinstance(evidence, list):
        raise ContractError("evidence must be a list")
    for span in evidence:
        start, end = span.get("start_cp"), span.get("end_cp")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ContractError("Invalid code-point offsets")
        if text[start:end] != span.get("quote"):
            raise ContractError("Evidence quote mismatch")
        if span.get("action") not in CHOICES["q_action"] or span.get("directness") not in {"DIRECT", "WARNING", "QUOTED", "UNCLEAR"}:
            raise ContractError("Invalid evidence labels")
        if span.get("origin") not in {"FIXTURE_ANNOTATED", "ADAPTER_VALIDATED", "MODEL_PROPOSED"}:
            raise ContractError("Invalid evidence origin")
        if span["origin"] == "FIXTURE_ANNOTATED" and trace["inference_mode"] != "FIXTURE":
            raise ContractError("Fixture evidence is prohibited in a non-fixture run")
    if type(trace.get("context_conflict")) is not bool:
        raise ContractError("context_conflict must be boolean")
    if "reference_outcome" in trace and trace["reference_outcome"] not in STATES:
        raise ContractError("Invalid original policy outcome")
    return trace


def safe_trace(trace):
    """Never serialize the raw transcript, quoted span, arbitrary provider payload, or credentials."""
    return {key: trace[key] for key in ("schema_version", "inference_mode", "model_status", "latency_ms", "input_sha256", "session_version", "answers", "context_conflict")} | {
        "evidence": [{k: e[k] for k in ("start_cp", "end_cp", "action", "directness", "origin")} for e in trace["evidence"]],
        "provenance_ref_present": bool(trace.get("provenance_ref")),
        "identity_attested_by_kit": False,
        **({"reference_outcome":trace["reference_outcome"],"reference_reason":trace.get("reference_reason"),
            "source_diagnostics":trace.get("source_diagnostics")} if "reference_outcome" in trace else {}),
    }
