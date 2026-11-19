"""Local question profiles; no inference, policy change, or response attestation.
 
The wire envelope stays exactly {state, questions}. Binding metadata belongs to
the trusted caller, never to model instructions or untrusted model assertions.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading

from integration import v50

ROOT = Path(__file__).resolve().parents[1]
ContractError = v50.ContractError
BASELINE = "v50-baseline"
EVIDENCE_LEGACY = "v51-evidence-legacy"
SEMANTIC_CANDIDATE = "v51-semantic-candidate"
SPECIFIED_CANDIDATE = "v51-specific-candidate"
PROFILE_IDS = (BASELINE, EVIDENCE_LEGACY, SEMANTIC_CANDIDATE, SPECIFIED_CANDIDATE)
CANDIDATE_SOURCE = "internal/evidence/v50/question_ablation/replay_inputs/previous_inputs/candidate_questions.json"
CANDIDATE_SHA256 = "d30bdcddaf6214e262db13418fe8cb2a3a832ce52dbf367a9d6f8f4d07e11f77"
BASE_MANIFEST_FINGERPRINT = "a7edba89bbfe78ed22c067959058762cc1003a2df5286fcae36d38725ea895a3"
REGISTRY_PATH = "configs/v51_profiles.json"
SEMANTIC_QUESTIONS = {
    "q_request_scope": {
        "type": "choice",
        "instructions": "Classify the CURRENT speaker request to the recipient, not an action merely mentioned in a warning or quotation. A new current demand after a warning still counts. If the requested act is unspecified, choose unclear.",
        "criteria": {
            "no_request": "no current request, only a notice, completed action, warning not to act, or report/quotation",
            "other_request": "explicit current request outside money transfer, credentials/personal data, remote access, links and concealment; e.g. ordinary attendance or preparation",
            "sensitive_request": "current request involving transfer/payment, credentials/personal data, remote access, a link or concealment",
            "unclear": "a request is implied but its act or current directness is insufficiently specified"}},
    "q_current_exposure": {
        "type": "noul",
        "instructions": "Does the current speaker ask the recipient now to disclose an OTP, login password or sensitive identifying data/images, or to install/grant remote control? Do not count a warning not to do this, a past report or a quoted example alone. A new present demand after a warning counts. Merely noting authentication is complete does not count."},
    "q_payment_anomaly": {
        "type": "noul",
        "instructions": "Is there BOTH a current payment or transfer demand AND an explicit unusual condition such as a changed destination account, a claimed emergency/impersonation, secrecy or blocking independent checking, a threat, guaranteed investment returns or a fee demanded before a promised benefit? Do not infer an anomaly from a routine fee, reimbursement or ordinary deadline alone. A warning or report without a new present payment demand does not count."},
}
SPECIFIED_QUESTIONS = {
    "q_request_specified": {
        "type": "noul",
        "instructions": "Does the current message explicitly specify what the listener is being asked to do now? Count everyday non-sensitive tasks as well as sensitive actions. Answer no if there is no current request, only a report or quotation, or the requested act is left as do that / follow my instructions without saying what that act is. Do not infer missing facts."},
}


def wire_bytes(value):
    """Match ModelClient.infer's UTF-8 JSON serialization, including key order."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _file_hash(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def _read_json(relative):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ContractError("PROFILE_DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    def invalid(_):
        raise ContractError("PROFILE_INVALID_JSON_CONSTANT")
    return json.loads((ROOT / relative).read_text(encoding="utf-8"),
                      object_pairs_hook=pairs, parse_constant=invalid)


def build_registry():
    """Construct the explicitly registered profiles; used by generator and checker."""
    manifest = v50.execution_manifest()
    if manifest["manifest_fingerprint"] != BASE_MANIFEST_FINGERPRINT:
        raise ContractError("PROFILE_BASE_MANIFEST_DRIFT")
    if _file_hash(CANDIDATE_SOURCE) != CANDIDATE_SHA256:
        raise ContractError("PROFILE_CANDIDATE_SOURCE_DRIFT")
    source = _read_json(CANDIDATE_SOURCE)
    candidates = [c for c in source["candidates"] if c["candidate_id"] == "EN_SCOPE_V1"]
    if len(candidates) != 1:
        raise ContractError("PROFILE_CANDIDATE_MISMATCH")
    original = v50.bridge.questions("")["questions"]
    candidate = deepcopy(original)
    # The old candidate contains other proposed changes: copy only q_evidence.
    candidate["q_evidence"] = deepcopy(candidates[0]["questions"]["q_evidence"])
    if (candidate["q_evidence"].keys() != original["q_evidence"].keys()
            or candidate["q_evidence"]["type"] != original["q_evidence"]["type"]
            or not isinstance(candidate["q_evidence"]["instructions"], str)
            or candidate["q_evidence"]["instructions"] == original["q_evidence"]["instructions"]):
        raise ContractError("PROFILE_EVIDENCE_SCHEMA_DRIFT")
    semantic = deepcopy(candidate)
    semantic.update(deepcopy(SEMANTIC_QUESTIONS))
    semantic_spec = deepcopy(v50.bridge.SPEC)
    semantic_spec.update({
        "q_request_scope": {"type": "choice", "options": list(SEMANTIC_QUESTIONS["q_request_scope"]["criteria"])},
        "q_current_exposure": {"type": "noul"},
        "q_payment_anomaly": {"type": "noul"}})
    specified = deepcopy(semantic)
    specified.update(deepcopy(SPECIFIED_QUESTIONS))
    specified_spec = deepcopy(semantic_spec)
    specified_spec["q_request_specified"] = {"type": "noul"}
    profiles = {}
    for ident, questions_, spec, allowed, status in (
            (BASELINE, original, v50.bridge.SPEC, ["legacy", "dra"], "FROZEN_V50_BASELINE"),
            (EVIDENCE_LEGACY, candidate, v50.bridge.SPEC, ["legacy"], "EXPLICIT_CANDIDATE_NOT_PROMOTED"),
            (SEMANTIC_CANDIDATE, semantic, semantic_spec, ["legacy"], "EXPLICIT_CANDIDATE_NOT_PROMOTED"),
            (SPECIFIED_CANDIDATE, specified, specified_spec, ["legacy"], "EXPLICIT_CANDIDATE_NOT_PROMOTED")):
        signature = v50.question_signature(questions_)
        item = {"profile_id": ident, "allowed_policy_ids": allowed, "status": status,
                "base_execution_manifest_fingerprint": manifest["manifest_fingerprint"],
                "questions": deepcopy(questions_), "question_signature": signature,
                "question_contract_sha256": _hash(signature),
                "questions_sha256": hashlib.sha256(wire_bytes(questions_)).hexdigest(),
                "empty_state_payload_sha256": hashlib.sha256(wire_bytes({"state": "", "questions": questions_})).hexdigest(),
                "response_schema": deepcopy(spec),
                "optional_questions": sorted(v50.bridge.OPTIONAL_QUESTIONS),
                "required_questions": [key for key in spec if key not in v50.bridge.OPTIONAL_QUESTIONS],
                "changed_fields": ([] if ident == BASELINE else ["/q_evidence/instructions"])
                    + (["/" + key for key in SEMANTIC_QUESTIONS] if ident in (SEMANTIC_CANDIDATE, SPECIFIED_CANDIDATE) else [])
                    + (["/q_request_specified"] if ident == SPECIFIED_CANDIDATE else [])}
        item["profile_fingerprint"] = _hash(item)
        profiles[ident] = item
    result = {"schema_version": "dmsg-v51-question-profiles/1",
              "default_profile_id": BASELINE, "default_policy_id": "legacy",
              "base_execution_manifest_fingerprint": manifest["manifest_fingerprint"],
              "wire_envelope_keys": ["state", "questions"],
              "hash_encoding": {"questions_sha256": "UTF-8 json.dumps ensure_ascii=False, allow_nan=False; insertion order and default separators",
                                "question_contract_sha256": "UTF-8 compact sorted-key JSON of ordered signature arrays"},
              "candidate_provenance": {"path": CANDIDATE_SOURCE, "sha256": CANDIDATE_SHA256,
                                       "candidate_id": "EN_SCOPE_V1", "copied_question": "q_evidence"},
              "source_hashes": {p: _file_hash(p) for p in (
                  "integration/v51_profiles.py", "tools/export_v51_profiles.py",
                  "configs/v50_contract.json", CANDIDATE_SOURCE)},
              "profiles": profiles,
              "scope": "QUESTION_SELECTION_AND_DECLARED_RESPONSE_SCHEMA_ONLY; NO_POLICY_EVALUATION_OR_MODEL_ATTESTATION"}
    result["registry_fingerprint"] = _hash(result)
    return result


# v5.9: request-scoped verification. One Arena request used to rebuild and
# re-verify the full registry twelve times. Inside verification_scope() the first
# call performs the complete fail-closed check; later calls in the same thread and
# scope reuse that verified snapshot (callers always receive copies). Outside a
# scope every call still verifies from scratch, exactly as before.
_SCOPE = threading.local()


@contextmanager
def verification_scope():
    if getattr(_SCOPE, "active", False):
        yield
        return
    _SCOPE.active, _SCOPE.cache = True, {}
    try:
        yield
    finally:
        _SCOPE.active, _SCOPE.cache = False, {}


def refresh_scope():
    """Drop verified values so the next call in this scope verifies again (e.g. after a network call)."""
    if getattr(_SCOPE, "active", False):
        _SCOPE.cache = {}


def scope_cached(key, compute):
    """Memoize a verified value for the current scope only; outside a scope compute every time."""
    if not getattr(_SCOPE, "active", False):
        return compute()
    if key not in _SCOPE.cache:
        _SCOPE.cache[key] = compute()
    return _SCOPE.cache[key]


def _verified_registry():
    return scope_cached("registry", _verify_registry)


def registry():
    """Verify source, baseline manifest, full content and all insertion orders."""
    return deepcopy(_verified_registry())


def _verify_registry():
    stored = _read_json(REGISTRY_PATH)
    if type(stored) is not dict:
        raise ContractError("PROFILE_REGISTRY_INVALID")
    unsigned = {k: v for k, v in stored.items() if k != "registry_fingerprint"}
    if stored.get("registry_fingerprint") != _hash(unsigned):
        raise ContractError("PROFILE_REGISTRY_FINGERPRINT_MISMATCH")
    expected = build_registry()
    if wire_bytes(stored) != wire_bytes(expected):
        raise ContractError("PROFILE_REGISTRY_DRIFT")
    return stored


def _selected(data, profile_id, policy_id):
    if type(profile_id) is not str or profile_id not in PROFILE_IDS:
        raise ContractError("UNSUPPORTED_PROFILE_ID")
    if type(policy_id) is not str or policy_id not in ("legacy", "dra"):
        raise ContractError("UNSUPPORTED_POLICY_ID")
    selected = data["profiles"][profile_id]
    if policy_id not in selected["allowed_policy_ids"]:
        raise ContractError("PROFILE_POLICY_NOT_ALLOWED")
    return selected


def profile(profile_id=BASELINE, policy_id="legacy"):
    return deepcopy(_selected(_verified_registry(), profile_id, policy_id))


def questions(text, profile_id=BASELINE, policy_id="legacy"):
    if type(text) is not str:
        raise ContractError("TEXT_REQUIRED")
    return {"state": text, "questions": profile(profile_id, policy_id)["questions"]}


def binding(profile_id=BASELINE, policy_id="legacy"):
    data = _verified_registry()
    selected = _selected(data, profile_id, policy_id)
    return {"profile_id": profile_id, "policy_id": policy_id,
            "question_contract_sha256": selected["question_contract_sha256"],
            "questions_sha256": selected["questions_sha256"],
            "profile_fingerprint": selected["profile_fingerprint"],
            "registry_fingerprint": data["registry_fingerprint"],
            "base_execution_manifest_fingerprint": data["base_execution_manifest_fingerprint"]}


def validate_binding(value, profile_id=BASELINE, policy_id="legacy"):
    """Check caller-owned request metadata, not a claim that the model used it."""
    expected = binding(profile_id, policy_id)
    if type(value) is not dict or value != expected:
        raise ContractError("PROFILE_BINDING_MISMATCH")
    return expected


def validate_payload(payload, profile_id=BASELINE, policy_id="legacy"):
    if type(payload) is not dict or set(payload) != {"state", "questions"}:
        raise ContractError("PROFILE_PAYLOAD_MISMATCH")
    expected = questions(payload["state"], profile_id, policy_id)
    if wire_bytes(payload) != wire_bytes(expected):
        raise ContractError("PROFILE_PAYLOAD_MISMATCH")
    return expected


def normalize_response(raw, profile_id=BASELINE, policy_id="legacy"):
    """Use the selected schema; v5 optional fields keep their original behavior."""
    selected = profile(profile_id, policy_id)
    return v50.bridge.normalize_response(raw, selected["response_schema"],
                                         optional=selected["optional_questions"])
