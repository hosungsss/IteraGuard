"""Frozen, local-only question ablations on authored synthetic development text.

No automatic promotion, threshold tuning, downloads, or external model calls.
The vendor model client owns transport/validation. Saved raw responses are parsed
JSON returned by that client, not exact HTTP bytes or authenticated attestation.
This portable-input revision follows the completed experiment. Its original
runner is preserved with that experiment's replay_inputs; do not replace it.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.request

SOURCE = Path(__file__).resolve().parents[1]
WORKSPACE = SOURCE.parents[1]
OLD = WORKSPACE / "deliverables/zoro_iteration_20261104"
BUNDLED_INPUTS = SOURCE / "internal/evidence/v50/question_ablation/replay_inputs"
DEFAULT_OUTPUT = SOURCE / "runs/v50_ablation"
MODEL = WORKSPACE / "models/Zoro-1-kev"
RUNNER_REVISION = "v50-ablation-portable-inputs-1"
INPUT_FILES = ("V2_48.jsonl", "AI25.jsonl", "candidate_questions.json")
MODEL_FILES = ("head.pt", "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json")
ENDPOINT = "http://127.0.0.1:8008/v1/systemone"
STATES = {"NO_STRONG_SIGNAL", "CAUTION", "PAUSE_AND_VERIFY", "ASK_HUMAN"}
TARGETS = {"action_only": "q_action", "speech_only": "q_speech", "evidence_only": "q_evidence"}


def encoded(value):
    """Exactly the insertion-order JSON serializer used by ModelClient.infer."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def append_event(stream, value):
    stream.write(encoded(value).decode("utf-8") + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def resolve_input_dir(input_dir=None):
    """Explicit paths never silently fall back; bundled evidence precedes workspace history."""
    roots = [Path(input_dir)] if input_dir is not None else [BUNDLED_INPUTS, OLD]
    for root in roots:
        for candidate in (root, root / "previous_inputs"):
            if all((candidate / name).is_file() for name in INPUT_FILES):
                return candidate.resolve()
    raise FileNotFoundError("Missing ablation inputs: " + ", ".join(INPUT_FILES)
                            + "; pass --input-dir with these files or a replay_inputs directory")


def bridge_module():
    sys.path.insert(0, str(SOURCE / "vendor/dmsg"))
    from prototype import model_bridge
    if Path(model_bridge.__file__).resolve() != SOURCE / "vendor/dmsg/prototype/model_bridge.py":
        raise RuntimeError("Wrong vendor module imported")
    return model_bridge


def build_variants(base, candidate):
    variants = {"baseline": copy.deepcopy(base)}
    if list(base) != list(candidate):
        raise ValueError("Question order changed")
    for name, target in TARGETS.items():
        q = copy.deepcopy(base)
        q[target] = copy.deepcopy(candidate[target])
        if q[target]["type"] != base[target]["type"]:
            raise ValueError("Question type changed")
        if "criteria" in q[target] and list(q[target]["criteria"]) != list(base[target]["criteria"]):
            raise ValueError("Option order/labels changed")
        if q[target] == base[target]:
            raise ValueError("Ablation has no change")
        variants[name] = q
    return variants


def validate_development(rows):
    if len(rows) != 25 or len({r["id"] for r in rows}) != 25:
        raise ValueError("Expected 25 unique new development cases")
    for r in rows:
        if (r.get("authorship") != "AI_GENERATED" or r.get("independent_eval") is not False
                or r.get("split") != "development" or not r.get("synthetic")):
            raise ValueError("Invalid provenance")
        if not r["text"].strip() or len(r["text"]) > 2000:
            raise ValueError("Invalid text")
        if not r["expect"] or not set(r["expect"]) <= STATES or r["expect"] != r["allowed_guidance"]:
            raise ValueError("Invalid guidance labels")
        if type(r["pause_required"]) is not bool or r["pause_required"] != (r["expect"] == ["PAUSE_AND_VERIFY"]):
            raise ValueError("Inconsistent pause label")
        if r["risky"] is not None and type(r["risky"]) is not bool:
            raise ValueError("Invalid risk-context label")
        if not r["requested_action"] or not r["speech"] or not r["rationale"] or not r["evidence"]:
            raise ValueError("Incomplete annotation")
        for s in r["evidence"]:
            a, b = s["start_cp"], s["end_cp"]
            if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(r["text"]) or r["text"][a:b] != s["quote"]:
                raise ValueError("Invalid code-point evidence span")


def metrics(rows, items, policy):
    actions = {i["id"]: i[policy]["action"] for i in items}
    if set(actions) != {r["id"] for r in rows} or len(items) != len(rows):
        raise ValueError("Missing, duplicate, or extra evaluated cases")
    def ids(test):
        return [r["id"] for r in rows if test(r, actions[r["id"]])]
    lists = {
        "expected_match": ids(lambda r, a: a in r["expect"]),
        "abstain": ids(lambda r, a: a == "ASK_HUMAN"),
        "nonabstained_expected_match": ids(lambda r, a: a != "ASK_HUMAN" and a in r["expect"]),
        "risky_cleared": ids(lambda r, a: r["risky"] is True and a == "NO_STRONG_SIGNAL"),
        "benign_abstain": ids(lambda r, a: r["risky"] is False and a == "ASK_HUMAN"),
        "benign_pause": ids(lambda r, a: r["risky"] is False and a == "PAUSE_AND_VERIFY"),
        "unknown_cleared": ids(lambda r, a: r["risky"] is None and a == "NO_STRONG_SIGNAL"),
        "pause_required_missed": ids(lambda r, a: r.get("pause_required", r["expect"] == ["PAUSE_AND_VERIFY"]) and a != "PAUSE_AND_VERIFY"),
    }
    n = len(rows)
    coverage = n - len(lists["abstain"])
    return {"n": n, **{k: len(v) for k, v in lists.items()}, "ids": lists,
            "risky_n": sum(r["risky"] is True for r in rows),
            "benign_n": sum(r["risky"] is False for r in rows),
            "unknown_n": sum(r["risky"] is None for r in rows),
            "pause_required_n": sum(r.get("pause_required", r["expect"] == ["PAUSE_AND_VERIFY"]) for r in rows),
            "coverage_n": coverage, "coverage": coverage / n if n else None,
            "nonabstained_expected_match_rate": len(lists["nonabstained_expected_match"]) / coverage if coverage else None}


def identity(expected_model=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("http://127.0.0.1:8008/v1/models", timeout=10) as r:
        value = json.load(r)
    m = value["models"][0]
    if m["run"] != str(expected_model or MODEL) or m["temperature"] != 1.52 or m["dtype"] != "bfloat16":
        raise RuntimeError("Serving runtime differs from registered setup")
    return value


def configure_client(bridge):
    # These nonsecret settings prevent an ambient environment from redirecting the experiment.
    for key, value in {"DMSG_MODEL_ENABLED": "1", "DMSG_SYSTEMONE_ENDPOINT": ENDPOINT,
                       "DMSG_MODEL_ID": "trillionlabs/Zoro-1", "DMSG_SEND_MODEL_FIELD": "1",
                       "DMSG_REQUIRE_MODEL_ECHO": "1", "DMSG_MODEL_TIMEOUT_S": "20"}.items():
        os.environ[key] = value
    client = bridge.ModelClient()
    if not client.status()["configured"] or client.status()["remote_text_transfer"]:
        raise RuntimeError("Not the configured local-only model")
    return client


def prepare(output, input_dir=None, model_dir=None):
    output.mkdir(parents=True, exist_ok=True)
    if (output / "protocol.json").exists():
        raise FileExistsError("Refusing to replace a frozen protocol")
    input_dir = resolve_input_dir(input_dir)
    model_dir = Path(model_dir or MODEL).resolve()
    model_files = [model_dir / name for name in MODEL_FILES]
    model_registered = all(path.is_file() for path in model_files)
    if not model_registered and any(path.exists() for path in model_files):
        raise FileNotFoundError("Incomplete model export; all five model files are required")
    bridge = bridge_module()
    candidate_file = input_dir / "candidate_questions.json"
    candidate = next(c["questions"] for c in json.loads(candidate_file.read_text())["candidates"] if c["candidate_id"] == "EN_SCOPE_V1")
    variants = build_variants(bridge.questions("")["questions"], candidate)
    paths = {"V2_48": input_dir / "V2_48.jsonl", "AI25_previous": input_dir / "AI25.jsonl", "AI25_new": SOURCE / "data/v50_ai_development25.jsonl"}
    validate_development(read_rows(paths["AI25_new"]))
    datasets = {label: {"path": str(p), "sha256": file_hash(p), "n": len(read_rows(p)),
                        "nonempty": sum(bool(r["text"].strip()) for r in read_rows(p)),
                        "status": "AI_AUTHORED_DEVELOPMENT_NOT_INDEPENDENT" if label != "V2_48" else "PREVIOUSLY_SEEN_AUTHORED_DEVELOPMENT_NOT_INDEPENDENT"}
                for label, p in paths.items()}
    protected = [SOURCE / "vendor/dmsg/prototype" / n for n in ("model_bridge.py", "typed_contract.py", "context_guard.py", "core.py")]
    protected += [Path(__file__).resolve(), candidate_file, *paths.values()]
    protocol = {"registered_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "source": str(SOURCE),
        "runner_revision": RUNNER_REVISION, "input_directory": str(input_dir),
        "model_export_dir": str(model_dir),
        "model_export_status": "LOCAL_FILES_HASHED_NOT_ATTESTED" if model_registered else "MODEL_EXPORT_NOT_REGISTERED_RUN_BLOCKED",
        "datasets": datasets, "variants": variants, "ordered_questions_sha256": {k: digest(q) for k, q in variants.items()},
        "protected_hashes": {str(p): file_hash(p) for p in protected},
        "model_export_hashes": {str(p): file_hash(p) for p in model_files} if model_registered else {},
        "official_model": "trillionlabs/Zoro-1", "official_revision": "ab05e6c025deb0eed102f42b736dc1589848e6c9",
        "endpoint": ENDPOINT, "temperature": 1.52, "dtype": "bfloat16", "tokenizer_patch": False,
        "fresh_calls_per_variant": sum(d["nonempty"] for d in datasets.values()), "variant_order": list(variants),
        "calls_planned": 4 * sum(d["nonempty"] for d in datasets.values()),
        "policies": ["legacy_advisory_threshold_0.70", "existing_dra_1.2_costs_unchanged"],
        "question_scope": "Single-axis English wording changes; action_only also clarifies existing none description. Other questions/options and their insertion order remain unchanged.",
        "input_policy": "Only case text as state; never labels, expected guidance, rationale, family or case ID.",
        "failure_policy": "No retry. Persist parsed provider raw before normalization; failures remain explicit with ASK_HUMAN fallback. Blank V34 has no inference. Never fabricate a valid response.",
        "evaluation_unit": "98 cases per variant (97 calls plus blank V34), same raw response consumed by both unchanged policies. Not the whole arena/LinkGuard/session pipeline.",
        "acceptance": {"automatic_promotion": False,
          "screen": "For EACH dataset and EACH policy, no newly cleared risky/unknown cases, no newly paused benign cases, no newly missed required pause, no lost expected-match cases, and no provider/contract failures; at least one expected-match gain required to recommend a combination follow-up.",
          "otherwise": "Hold candidate; preserve baseline wording. Report all gains/losses and sentinel cases. Passing this development screen still is not an independent evaluation or release gate.",
          "combination": "Only after this report; freeze a separate protocol and fresh calls before evaluating any combination."},
        "latency": "Record client/provider latency per call and first request separately. Sequential variant blocks share a warm server; timing is descriptive, not a controlled speed comparison.",
        "provenance_boundary": "All data synthetic, seen/devised for development. New25 authored before these calls but not independent or human-validated. Model ID echo is not authenticated attestation. T1.52 is serving metadata, not established product probability calibration.",
        "no_external_calls": True, "product_default_modified": False}
    save_new(output / "protocol.json", protocol)
    print(json.dumps({"prepared": True, "protocol_sha256": file_hash(output / "protocol.json"),
                     "model_export_status": protocol["model_export_status"], "calls_planned": protocol["calls_planned"],
                     "datasets": datasets}, ensure_ascii=False), flush=True)


def check_protected(protocol, model=False):
    checks = dict(protocol["protected_hashes"])
    if model:
        if not protocol.get("model_export_hashes"):
            raise RuntimeError("Model export not registered; prepare a fresh output with --model-dir before run")
        checks.update(protocol["model_export_hashes"])
    changed = [p for p, h in checks.items() if file_hash(p) != h]
    if changed:
        raise RuntimeError("Frozen input changed: " + ", ".join(changed))


def evaluate_row(row, questions, client, bridge, raw_stream, call_index, dataset, variant):
    item = {"id": row["id"], "dataset": dataset, "variant": variant,
            "input_sha256": hashlib.sha256(row["text"].encode()).hexdigest(),
            "expected": row["expect"], "risky": row["risky"]}
    fallback = {"action": "ASK_HUMAN", "reason": "EMPTY_NO_INFERENCE"}
    if not row["text"].strip():
        return {**item, "status": "EMPTY_NO_INFERENCE", "legacy": dict(fallback), "dra": dict(fallback),
                "client_latency_ms": None, "provider_latency_ms": None}
    payload = {"state": row["text"], "questions": questions}
    wire = {**payload, "model": "trillionlabs/Zoro-1"}
    item.update(call_index=call_index, request_sha256=digest(wire), request_bytes=len(encoded(wire)), first_request=call_index == 1)
    start = time.perf_counter()
    try:
        raw, elapsed = client.infer(row["text"], question_payload=payload)
        # Keep even a response later rejected by typed normalization; flush before derived judgments.
        append_event(raw_stream, {**item, "event": "PARSED_PROVIDER_RESPONSE", "response_sha256": digest(raw), "response": raw})
        normalized = bridge.normalize_response(raw, bridge.SPEC, optional=bridge.OPTIONAL_QUESTIONS)
        item.update(status="VALID", normalized=normalized, client_latency_ms=elapsed,
                    provider_latency_ms=raw.get("latency_ms"), model_echo=raw.get("model"),
                    legacy=bridge.advisory(row["text"], raw, threshold=.70),
                    dra=bridge.decision_relevant_advisory(row["text"], raw),
                    abstention_diagnostic=bridge.abstention_cause(row["text"], raw, threshold=.70))
    except (bridge.ModelUnavailable, bridge.ContractError) as exc:
        item.update(status="FAILED", error_type=type(exc).__name__, error_code=str(exc),
                    elapsed_failure_ms=(time.perf_counter()-start)*1000, client_latency_ms=None, provider_latency_ms=None)
        fallback["reason"] = "MODEL_OR_CONTRACT_FAILURE"
        item.update(legacy=dict(fallback), dra=dict(fallback))
        append_event(raw_stream, {**item, "event": "FAILURE_NO_IMPUTED_RESPONSE"})
    return item


def run_variant(output, name, protocol, bridge):
    check_protected(protocol)
    prefix = output / name
    if prefix.exists():
        raise FileExistsError("Variant evidence already exists; no overwrite or hidden retry")
    prefix.mkdir()
    before = identity(protocol.get("model_export_dir"))
    save_new(prefix / "server_before.json", before)
    client = configure_client(bridge)
    save_new(prefix / "start.json", {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                                    "protocol_sha256": file_hash(output / "protocol.json"), "client_status": client.status()})
    sets = {}
    calls = 0
    with (prefix / "raw.jsonl").open("x", encoding="utf-8") as raw_stream, (prefix / "results.jsonl").open("x", encoding="utf-8") as result_stream:
        for label, info in protocol["datasets"].items():
            rows = read_rows(info["path"])
            items = []
            for row in rows:
                if row["text"].strip():
                    calls += 1
                item = evaluate_row(row, protocol["variants"][name], client, bridge, raw_stream, calls, label, name)
                append_event(result_stream, item)
                items.append(item)
                if len(items) % 12 == 0:
                    print(json.dumps({"variant": name, "dataset": label, "completed": len(items), "calls": calls, "failures": sum(i["status"] == "FAILED" for i in items)}), flush=True)
            sets[label] = {"n": len(items), "valid": sum(i["status"] == "VALID" for i in items),
                "failed": sum(i["status"] == "FAILED" for i in items), "metrics": {p: metrics(rows, items, p) for p in ("legacy", "dra")},
                "always_ask": metrics(rows, [{"id": r["id"], "always": {"action": "ASK_HUMAN"}} for r in rows], "always")}
    after = identity(protocol.get("model_export_dir"))
    save_new(prefix / "server_after.json", after)
    check_protected(protocol)
    summary = {"variant": name, "fresh_actual_model_calls": calls, "sets": sets,
               "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "independent_eval": False,
               "server_request_count_delta": after["models"][0]["batches"]["requests"] - before["models"][0]["batches"]["requests"],
               "raw_sha256": file_hash(prefix / "raw.jsonl"), "results_sha256": file_hash(prefix / "results.jsonl")}
    save_new(prefix / "summary.json", summary)
    print(json.dumps({"completed_variant": name, "fresh_calls": calls, "metrics": {s: x["metrics"] for s, x in sets.items()}}, ensure_ascii=False), flush=True)


def summarize(output, protocol):
    reports = {name: json.loads((output / name / "summary.json").read_text()) for name in protocol["variant_order"]}
    items = {name: {(i["dataset"], i["id"]): i for i in read_rows(output / name / "results.jsonl")} for name in reports}
    comparisons = {}
    for name in TARGETS:
        changes = []
        for dataset, info in protocol["datasets"].items():
            for row in read_rows(info["path"]):
                base, cand = items["baseline"][(dataset, row["id"])], items[name][(dataset, row["id"])]
                for policy in ("legacy", "dra"):
                    b, c = base[policy]["action"], cand[policy]["action"]
                    if b == c:
                        continue
                    changes.append({"dataset": dataset, "id": row["id"], "policy": policy, "baseline": b, "candidate": c,
                        "baseline_reason": base[policy]["reason"], "candidate_reason": cand[policy]["reason"],
                        "expected": row["expect"], "risky": row["risky"],
                        "expected_gain": b not in row["expect"] and c in row["expect"],
                        "expected_loss": b in row["expect"] and c not in row["expect"],
                        "new_risky_clear": row["risky"] is True and c == "NO_STRONG_SIGNAL",
                        "new_unknown_clear": row["risky"] is None and c == "NO_STRONG_SIGNAL",
                        "new_benign_pause": row["risky"] is False and c == "PAUSE_AND_VERIFY",
                        "new_required_pause_miss": row.get("pause_required", row["expect"] == ["PAUSE_AND_VERIFY"]) and b == "PAUSE_AND_VERIFY" and c != "PAUSE_AND_VERIFY"})
        blocking = [c for c in changes if any(c[k] for k in ("expected_loss", "new_risky_clear", "new_unknown_clear", "new_benign_pause", "new_required_pause_miss"))]
        failures = sum(s["failed"] for s in reports[name]["sets"].values())
        gains = sum(c["expected_gain"] for c in changes)
        comparisons[name] = {"changes": changes, "expected_gains": gains, "blocking_regressions": blocking, "failed": failures,
                              "development_screen": "ELIGIBLE_FOR_FROZEN_COMBINATION_FOLLOWUP" if gains and not blocking and not failures else "HOLD_KEEP_BASELINE"}
    latency = {}
    for name, data in items.items():
        vals = sorted(i["client_latency_ms"] for i in data.values() if i["status"] == "VALID")
        latency[name] = {"n": len(vals), "p50_ms": vals[len(vals)//2] if vals else None,
                         "p95_ms": vals[max(0, math.ceil(.95*len(vals))-1)] if vals else None,
                         "first_request_ms": next((i["client_latency_ms"] for i in data.values() if i.get("first_request")), None)}
    sentinels = {name: [i for (dataset, case), i in data.items() if case in {"V47", "V38", "V33", "V02", "AI-JM-02", "AI-JM-19", "AI-JM-22", "AI-JM-24", "V50-AI-18", "V50-AI-19", "V50-AI-22"}] for name, data in items.items()}
    save_new(output / "sentinels.json", sentinels)
    report = {"protocol_sha256": file_hash(output / "protocol.json"), "fresh_actual_model_calls": sum(r["fresh_actual_model_calls"] for r in reports.values()),
              "reports": reports, "comparisons": comparisons, "latency": latency, "independent_eval": False,
              "product_default_modified": False, "scope": "Question-only ablation plus two offline policies on each response; no integrated pipeline or mobile evaluation."}
    save_new(output / "comparison.json", report)
    print(json.dumps({"total_calls": report["fresh_actual_model_calls"], "screens": {n: x["development_screen"] for n, x in comparisons.items()}}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "summarize"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--input-dir", type=Path, help="prepare: directory with V2_48.jsonl, AI25.jsonl and candidate_questions.json, or replay_inputs")
    parser.add_argument("--model-dir", type=Path, help="prepare: local five-file export; without files preparation is offline and run is blocked")
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.output, args.input_dir, args.model_dir)
        return
    if args.input_dir is not None or args.model_dir is not None:
        parser.error("--input-dir and --model-dir belong to prepare; run uses the frozen protocol")
    protocol = json.loads((args.output / "protocol.json").read_text())
    check_protected(protocol, model=args.phase == "run")
    if args.phase == "run":
        bridge = bridge_module()
        for name in protocol["variant_order"]:
            run_variant(args.output, name, protocol, bridge)
        check_protected(protocol, model=True)
    summarize(args.output, protocol)


if __name__ == "__main__":
    main()
