"""Strict Zoro typed-answer -> deterministic, proposal-only industry rulebook.

This module neither invokes a model nor authorizes/executes external operations.
Zoro's decision probability is not the probability that a real-world event is true.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

ACTIONS = frozenset({
    "NO_ACTION", "OPEN_VERIFICATION_TASK", "OPEN_REVIEW_TASK",
    "REQUEST_INFORMATION", "HOLD_FOR_REVIEW",
})
ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
SCHEMA = "iteraguard-rulebook/1"


class RulebookError(ValueError):
    pass


def _fail(reason: str) -> None:
    raise RulebookError(reason)


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        _fail("INVALID_" + field)
    return value


def _number(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        _fail("NONFINITE_OR_INVALID_PROBABILITY")
    if not 0.0 <= value <= 1.0:
        _fail("PROBABILITY_OUT_OF_RANGE")
    return float(value)


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_book(book: dict) -> dict:
    """Return the validated book; reject ambiguous and executable fields."""
    if type(book) is not dict or set(book) != {
        "schema_version", "id", "version", "domain", "questions",
        "rules", "minimum_confidence",
    }:
        _fail("INVALID_RULEBOOK_FIELDS")
    if book["schema_version"] != SCHEMA:
        _fail("UNSUPPORTED_SCHEMA")
    _identifier(book["id"], "BOOK_ID")
    _identifier(book["domain"], "DOMAIN")
    if not isinstance(book["version"], str) or not re.fullmatch(r"[0-9]+\.[0-9]+", book["version"]):
        _fail("INVALID_VERSION")
    conf = _number(book["minimum_confidence"])
    if conf < 0.5 or conf > 1.0:
        _fail("INVALID_THRESHOLD")
    questions = book["questions"]
    if type(questions) is not dict or not 1 <= len(questions) <= 32:
        _fail("INVALID_QUESTIONS")
    for name, question in questions.items():
        _identifier(name, "QUESTION_ID")
        if type(question) is not dict or not isinstance(question.get("instructions"), str):
            _fail("INVALID_QUESTION")
        if not 8 <= len(question["instructions"].strip()) <= 500:
            _fail("INVALID_INSTRUCTIONS")
        if question.get("type") == "noul":
            if set(question) != {"type", "instructions"}:
                _fail("INVALID_NOUL_SPEC")
        elif question.get("type") == "choice":
            if set(question) != {"type", "instructions", "criteria"}:
                _fail("INVALID_CHOICE_SPEC")
            criteria = question["criteria"]
            if type(criteria) is not dict or not 2 <= len(criteria) <= 20:
                _fail("INVALID_CRITERIA")
            for option, text in criteria.items():
                _identifier(option, "OPTION")
                if not isinstance(text, str) or not text.strip() or len(text) > 300:
                    _fail("INVALID_OPTION_DESCRIPTION")
        else:
            _fail("UNSUPPORTED_QUESTION_TYPE")
    rules = book["rules"]
    if type(rules) is not list or not 1 <= len(rules) <= 100:
        _fail("INVALID_RULES")
    ids, fingerprints = set(), set()
    for rule in rules:
        if type(rule) is not dict or set(rule) != {"id", "when", "action", "priority"}:
            _fail("INVALID_RULE_FIELDS")
        _identifier(rule["id"], "RULE_ID")
        if rule["id"] in ids:
            _fail("DUPLICATE_RULE_ID")
        ids.add(rule["id"])
        if type(rule["action"]) is not str or rule["action"] not in ACTIONS:
            _fail("UNAUTHORIZED_ACTION")
        if type(rule["priority"]) is not int or not 0 <= rule["priority"] <= 1000:
            _fail("INVALID_PRIORITY")
        cond = rule["when"]
        if type(cond) is not dict or not cond:
            _fail("INVALID_CONDITION")
        for qid, answer in cond.items():
            if qid not in questions:
                _fail("UNKNOWN_CONDITION_QUESTION")
            spec = questions[qid]
            allowed = {"yes", "no"} if spec["type"] == "noul" else set(spec["criteria"])
            if type(answer) is not str or answer not in allowed:
                _fail("UNKNOWN_CONDITION_OPTION")
        signature = _fingerprint([cond, rule["priority"]])
        if signature in fingerprints:
            _fail("DUPLICATE_CONDITION_PRIORITY")
        fingerprints.add(signature)
    return book


def build_questions(book: dict, state: str) -> dict:
    """Build a typed System One request; transport and identity handled elsewhere."""
    validate_book(book)
    if type(state) is not str or not state.strip() or len(state) > 2000:
        _fail("INVALID_STATE")
    return {"state": state, "questions": book["questions"]}


def _selection(spec: dict, item: dict) -> tuple[str, float]:
    if type(item) is not dict or item.get("type") != spec["type"]:
        _fail("TYPED_ANSWER_MISMATCH")
    if spec["type"] == "noul":
        if set(item) != {"type", "noul"}:
            _fail("INVALID_NOUL_ANSWER")
        p = _number(item["noul"])
        return ("yes", p) if p >= 0.5 else ("no", 1.0 - p)
    if set(item) != {"type", "choice", "probabilities"}:
        _fail("INVALID_CHOICE_ANSWER")
    probs = item["probabilities"]
    if type(probs) is not dict or set(probs) != set(spec["criteria"]):
        _fail("INVALID_CHOICE_DISTRIBUTION")
    dist = {k: _number(v) for k, v in probs.items()}
    if abs(sum(dist.values()) - 1.0) > 0.002:
        _fail("PROBABILITY_SUM_MISMATCH")
    choice = item["choice"]
    if choice not in dist or dist[choice] < max(dist.values()) - 0.002:
        _fail("SELECTED_CHOICE_MISMATCH")
    if sum(v >= max(dist.values()) - 0.002 for v in dist.values()) > 1:
        _fail("AMBIGUOUS_CHOICE_TIE")
    return choice, dist[choice]


def decide(book: dict, raw: dict, *, tenant_id: str, event_id: str) -> dict:
    """Resolve a typed answer without triggering an external side effect.

    Upstream must supply a v5.1-compatible System One envelope (answers).
    Missing/invalid/uncertain evidence fails closed to review. In all cases
    authorized=False and effects_executed=False.
    """
    validate_book(book)
    _identifier(tenant_id, "TENANT")
    _identifier(event_id, "EVENT")
    digest = _fingerprint(book)
    base = {
        "book_id": book["id"], "book_version": book["version"], "book_sha256": digest,
        "domain": book["domain"], "tenant_id": tenant_id, "event_id": event_id,
        "execution_mode": "PROPOSAL_ONLY_UNATTESTED_MODEL",
        "authorized": False, "effects_executed": False,
        "model_identity_verified": False, "outcome_probability": None,
    }

    def pending(reason: str) -> dict:
        return dict(base, status="REVIEW_REQUIRED", reason=reason,
                    action="HOLD_FOR_REVIEW", rule_id=None, selections={},
                    requires_independent_approval=True, idempotency_key=None)

    if type(raw) is not dict or type(raw.get("answers")) is not dict:
        return pending("MODEL_RESPONSE_MISSING_OR_INVALID")
    answers = raw["answers"]
    if set(answers) != set(book["questions"]):
        return pending("QUESTION_PROFILE_MISMATCH")
    try:
        selections = {
            name: _selection(spec, answers[name])
            for name, spec in book["questions"].items()
        }
    except (RulebookError, TypeError, ValueError, KeyError):
        return pending("INVALID_TYPED_RESPONSE")
    if any(conf < book["minimum_confidence"] for _, conf in selections.values()):
        return pending("UNDETERMINED_TYPED_ANSWER")
    matched = [
        r for r in book["rules"]
        if all(selections[qid][0] == expected for qid, expected in r["when"].items())
    ]
    if not matched:
        return pending("NO_MATCHING_RULE")
    priority = max(r["priority"] for r in matched)
    top = [r for r in matched if r["priority"] == priority]
    if len(top) != 1:
        return pending("CONFLICTING_RULES")
    rule = top[0]
    key = hashlib.sha256(
        (tenant_id + "|" + event_id + "|" + digest + "|" + rule["id"]).encode("utf-8")
    ).hexdigest()
    # Rulebook never claims idempotency without a persistent authorized executor.
    return dict(base, status="PROPOSED_ONLY", reason="RULE_MATCH",
                action=rule["action"], rule_id=rule["id"],
                selections={name: {"answer": answer, "model_choice_confidence": confidence}
                            for name, (answer, confidence) in selections.items()},
                requires_independent_approval=(rule["action"] != "NO_ACTION"),
                idempotency_key=key, idempotency_persisted=False)
