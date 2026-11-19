"""Stdlib experiment entrypoint. No network/model call unless an operator adapter is explicitly selected."""
import argparse
import csv
import hashlib
import importlib
import json
from pathlib import Path

from .contracts import ContractError, fingerprint, safe_trace, strict_json, validate_case, validate_trace
from .metrics import summarize
from .policy_probe import evaluate


def load_cases(path):
    cases = [strict_json(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    seen, groups = set(), {}
    for case in cases:
        validate_case(case)
        if case["case_id"] in seen: raise ContractError("Duplicate case ID")
        seen.add(case["case_id"])
        if case["family_id"] in groups and groups[case["family_id"]] != case["split"]:
            raise ContractError("Scenario family crosses splits")
        groups[case["family_id"]] = case["split"]
    if not cases: raise ContractError("Empty dataset")
    return cases


def model_input(case):
    # Gold labels, scenario family, risk_context, fixture_trace are never passed to a real adapter.
    return {"request_id":"kit-"+fingerprint(case["text"])[:16], "session_version":1,
            "latest_turn_id":1,"turns":[{"turn_id":1,"speaker":"caller","text":case["text"]}]}


def execute(cases, mode, adapter=None, replay=None, threshold=.70, margin=0.0):
    rows, logs = [], []
    for case in cases:
        if mode == "fixture":
            from .fixtures import trace_for
            trace = trace_for(case)
        elif mode == "adapter":
            trace = adapter(model_input(case))
            if trace.get("inference_mode") == "FIXTURE": raise ContractError("Adapter cannot masquerade a fixture as a model run")
        else:
            if case["case_id"] not in replay: raise ContractError("Replay missing a case")
            trace = replay[case["case_id"]]
        validate_trace(trace,case["text"])
        decision = evaluate(trace,threshold,margin)
        row = {"case_id":case["case_id"],"family_id":case["family_id"],"split":case["split"],
               "expected":case["expected"],"risk_context":case["risk_context"],**decision,
               "matched":decision["outcome"] in case["expected"],"inference_mode":trace["inference_mode"],
               "model_status":trace["model_status"],"latency_ms":trace["latency_ms"]}
        if "reference_outcome" in trace:
            row["reference_outcome"]=trace["reference_outcome"]
            row["changed_from_reference"]=decision["outcome"]!=trace["reference_outcome"]
            row["reference_reason"]=trace.get("reference_reason")
        rows.append(row)
        logs.append({"case_id":case["case_id"],"trace":safe_trace(trace),"decision":decision})
    return rows, logs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=["fixture","replay","adapter"],required=True)
    p.add_argument("--dataset",type=Path,default=Path("data/development.jsonl"))
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--trace",type=Path)
    p.add_argument("--adapter",help="Operator-authored module:function; imports trusted local code")
    p.add_argument("--allow-synthetic-model-call",action="store_true")
    p.add_argument("--allow-locked",action="store_true",help="Explicitly record a locked evaluation")
    p.add_argument("--threshold",type=float,default=.70)
    p.add_argument("--margin",type=float,default=0)
    args=p.parse_args()
    if args.output.exists(): p.error("Output exists: use a new run directory")
    cases=load_cases(args.dataset)
    splits=sorted({c["split"] for c in cases})
    if len(splits)!=1: p.error("Use one split per run; do not pool development and held-out results")
    if splits==["locked"] and not args.allow_locked: p.error("Locked evaluation requires --allow-locked")
    if args.mode=="fixture" and splits!=["development"]: p.error("Fixtures are development-only")
    adapter, replay = None, None
    if args.mode=="adapter":
        if not args.adapter or not args.allow_synthetic_model_call: p.error("Adapter requires explicit model-call opt-in")
        mod,fun=args.adapter.split(":",1)
        adapter=getattr(importlib.import_module(mod),fun)
    if args.mode=="replay":
        if not args.trace: p.error("Replay requires --trace")
        replay={}
        for line in args.trace.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip(): continue
            item=strict_json(line)
            if item["case_id"] in replay: raise ContractError("Duplicate replay ID")
            replay[item["case_id"]]=item["trace"]
        if set(replay)!={c["case_id"] for c in cases}: raise ContractError("Replay IDs must match dataset exactly")
    # Freeze inputs/config BEFORE executing an operator model adapter.
    from .contracts import finite
    finite(args.threshold); finite(args.margin)
    args.output.mkdir(parents=True)
    frozen={"schema_version":"dmsg-kit-run-v1","mode":args.mode,"split":splits[0],"case_count":len(cases),
            "dataset_sha256":hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
            "threshold":args.threshold,"margin":args.margin,"adapter":args.adapter,
            "replay_trace_sha256":hashlib.sha256(args.trace.read_bytes()).hexdigest() if args.mode=="replay" else None,
            "adapter_module_sha256":hashlib.sha256(Path(importlib.import_module(args.adapter.split(":",1)[0]).__file__).read_bytes()).hexdigest() if args.mode=="adapter" else None,
            "code_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path(__file__).parent.glob('*.py'))},
            "model_call_opt_in":args.allow_synthetic_model_call,"locked_run_explicit":args.allow_locked}
    write=lambda name,data:(args.output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write("protocol.json",frozen)
    try:
        rows,logs=execute(cases,args.mode,adapter,replay,args.threshold,args.margin)
    except Exception:
        write("failure.json",{"status":"FAILED","detail":"Run aborted; no fixture fallback and no partial success metrics. Inspect local exception securely."})
        raise
    write("results.json",rows); write("summary.json",summarize(rows))
    reference_rows=[{**r,"outcome":r["reference_outcome"],"matched":r["reference_outcome"] in r["expected"]}
                    for r in rows if "reference_outcome" in r]
    if reference_rows:
        write("reference_policy_summary.json",summarize(reference_rows))
        write("policy_differences.json",[{k:r[k] for k in ("case_id","reference_outcome","reference_reason","outcome","all_fired_rules")}
                                        for r in rows if r.get("changed_from_reference")])
    (args.output/"gate_trace.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in logs),encoding="utf-8")
    with (args.output/"results.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f);w.writerow(["case_id","outcome","matched","mode","status","all_fired_rules"])
        for r in rows:w.writerow([r["case_id"],r["outcome"],r["matched"],r["inference_mode"],r["model_status"],";".join(r["all_fired_rules"])])
    summary=summarize(rows)
    (args.output/"REPORT.md").write_text("# DMSG experiment run\n\nMode: "+args.mode+"\n\nNot a live model quality claim when FIXTURE.\n\n```json\n"+json.dumps(summary,ensure_ascii=False,indent=2)+"\n```\n",encoding="utf-8")
    print(json.dumps({"output":str(args.output),"cases":len(rows),"mode":args.mode},ensure_ascii=False))


if __name__=="__main__":
    main()
