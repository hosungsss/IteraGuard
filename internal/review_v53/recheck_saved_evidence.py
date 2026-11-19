#!/usr/bin/env python3
"""Read-only recalculation of IteraGuard's saved AI24 evaluation.

Usage: python recheck_saved_evidence.py /path/to/IteraGuard_source_root
Uses Python's standard library. Makes no network/model calls and writes no files.
This verifies saved counts and provenance consistency, not real-world accuracy.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def keyed(rows, label):
    result = {row["id"]: row for row in rows}
    require(len(result) == len(rows), f"Duplicate IDs in {label}")
    return result


def audit(root):
    folder = root / "internal/evidence/v51/experiments/stage7_locked_validation24"
    data_path = root / "data/v51_validation24.jsonl"
    labels = keyed(read_jsonl(data_path), "annotations")
    metrics, protocol = read_json(folder / "metrics.json"), read_json(folder / "protocol.json")
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    require(digest == protocol["datasets"]["AI24_locked"]["sha256"], "Annotation SHA-256 mismatch")
    require(len(labels) == 24, "Expected 24 annotated cases")
    report = {"status": "PASS", "new_model_calls": 0, "read_only": True,
              "dataset_sha256": digest, "n": len(labels),
              "families": dict(Counter(row["family_id"] for row in labels.values())),
              "independent_eval_values": list({row["independent_eval"] for row in labels.values()}),
              "arms": {}}
    keys = ("expected_match", "ask", "benign_ask", "unnecessary_benign_ask",
            "risky_clear", "unknown_clear", "benign_pause", "pause_missed")
    for arm in ("baseline", "specified"):
        results = keyed(read_jsonl(folder / f"{arm}_results.jsonl"), f"{arm} results")
        raw = keyed(read_jsonl(folder / f"{arm}_raw.jsonl"), f"{arm} raw")
        require(set(labels) == set(results) == set(raw), f"{arm}: ID set mismatch")
        ids = {key: [] for key in keys}
        for case_id, label in labels.items():
            action, risk = results[case_id]["action"], label["risky"]
            expected = label["expect"]
            flags = (action in expected, action == "ASK_HUMAN",
                     risk is False and action == "ASK_HUMAN",
                     risk is False and action == "ASK_HUMAN" and action not in expected,
                     risk is True and action == "NO_STRONG_SIGNAL",
                     risk is None and action == "NO_STRONG_SIGNAL",
                     risk is False and action == "PAUSE_AND_VERIFY",
                     label["pause_required"] and action != "PAUSE_AND_VERIFY")
            for key, flag in zip(keys, flags):
                if flag:
                    ids[key].append(case_id)
        counts = {key: len(value) for key, value in ids.items()}
        denominators = {"n": len(labels), "benign_n": sum(x["risky"] is False for x in labels.values()),
                        "pause_required_n": sum(bool(x["pause_required"]) for x in labels.values())}
        recorded = metrics[arm]["AI24_locked"]
        require(all(recorded[k] == v for k, v in denominators.items()), f"{arm}: denominator mismatch")
        require(counts == recorded["counts"], f"{arm}: count mismatch")
        require(all(set(ids[k]) == set(recorded["ids"][k]) for k in keys), f"{arm}: metric ID mismatch")
        report["arms"][arm] = {**denominators, "counts": counts, "ids": ids,
            "actions": dict(Counter(row["action"] for row in results.values())),
            "pause_missed_actions": {i: results[i]["action"] for i in ids["pause_missed"]},
            "raw_statuses": dict(Counter(row["status"] for row in raw.values())),
            "model_attested_values": list({row["model_attested"] for row in results.values()})}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path, help="Product source root containing data/ and internal/")
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.source_root), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
