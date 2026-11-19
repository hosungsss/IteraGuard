"""Offline development-only sweep. Does not select or deploy a winning threshold."""
import argparse
import json
import hashlib
from pathlib import Path
from .run import load_cases, execute
from .metrics import summarize
from .contracts import strict_json


def main():
    p=argparse.ArgumentParser();p.add_argument("--dataset",type=Path,default=Path("data/development.jsonl"))
    p.add_argument("--trace",type=Path);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();cases=load_cases(args.dataset)
    if any(c["split"]!="development" for c in cases):p.error("Never sweep validation/locked data")
    if args.output.exists():p.error("Output exists")
    replay=None
    if args.trace:
        replay={}
        for line in args.trace.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():continue
            item=strict_json(line)
            if item["case_id"] in replay:raise ValueError("Duplicate replay ID")
            replay[item["case_id"]]=item["trace"]
        if set(replay)!={c["case_id"] for c in cases}:raise ValueError("Replay IDs differ")
    results=[]
    for threshold in (.5,.6,.7,.8,.9):
        rows,_=execute(cases,"replay" if replay else "fixture",replay=replay,threshold=threshold)
        results.append({"threshold":threshold,"summary":summarize(rows)})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({"scope":"DEVELOPMENT ONLY; policy probe; not deployment recommendation",
        "dataset_sha256":hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "replay_trace_sha256":hashlib.sha256(args.trace.read_bytes()).hexdigest() if args.trace else None,
        "policy_sha256":hashlib.sha256(Path(__file__).with_name('policy_probe.py').read_bytes()).hexdigest(),
        "results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print(str(args.output))


if __name__=="__main__":main()
