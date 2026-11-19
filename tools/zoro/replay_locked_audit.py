"""Replay archived model responses with today's policy. No new model calls."""
from collections import Counter
import json
from pathlib import Path
from integration import v51

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "internal/evidence/v51/experiments/stage7_locked_validation24"


def records(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    by_id = {row["id"]: row for row in rows}
    if len(rows) != 24 or len(by_id) != 24:
        raise ValueError("unexpected locked set size or duplicate ID")
    return by_id


def main():
    labels = records(ROOT / "data/v51_validation24.jsonl")
    for arm, profile in [("baseline", "v50-baseline"), ("specified", "v51-specific-candidate")]:
        raw = records(DATA / (arm + "_raw.jsonl"))
        archived = records(DATA / (arm + "_results.jsonl"))
        if labels.keys() != raw.keys() or raw.keys() != archived.keys():
            raise ValueError("unmatched case IDs")
        counts = Counter()
        changes = []
        for key, row in labels.items():
            out = v51.evaluate_current(row["text"], raw[key]["raw"], profile_id=profile,
                                       binding=v51.request_binding(profile_id=profile))
            act = out["action"]
            benign = row["risk"]["context"] == "BENIGN_AUTHORED_CONTEXT"
            counts.update({
                "allowed": int(act in row["expect"]), "ask": int(act == "ASK_HUMAN"),
                "benign": int(benign), "pause_required": int(row["pause_required"]),
                "miss": int(row["pause_required"] and act != "PAUSE_AND_VERIFY"),
                "unnecessary_ask": int(benign and act == "ASK_HUMAN" and act not in row["expect"])
            })
            old = archived[key]
            if (old["action"], old["reason"]) != (act, out["reason"]):
                changes.append([key, old["action"], act, old["reason"], out["reason"]])
        print(json.dumps({"arm": arm, "n": len(labels), "counts": counts, "changes": changes}))


if __name__ == "__main__":
    main()
