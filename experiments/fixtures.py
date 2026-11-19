"""Invented fixture distributions, not recorded Zoro output."""
from .contracts import CHOICES, fingerprint


def answer(q, selected, top=.94):
    labels=CHOICES[q]
    return {"selected":selected,"probabilities":{k:top if k==selected else (1-top)/(len(labels)-1) for k in labels}}


def trace_for(case):
    spec=case["fixture_spec"]
    answers={q:answer(q,spec.get(q,"no"),spec.get("top",.94)) for q in CHOICES if q not in {"q_risk","q_action","q_speech"}}
    answers["q_action"]=answer("q_action",spec["q_action"],spec.get("top",.94))
    answers["q_speech"]=answer("q_speech",spec["q_speech"],spec.get("top",.94))
    answers["q_risk"]=answer("q_risk","low")
    evidence=[]
    if spec.get("quote"):
        start=case["text"].index(spec["quote"])
        evidence=[{"start_cp":start,"end_cp":start+len(spec["quote"]),"quote":spec["quote"],
                   "action":spec.get("evidence_action",spec["q_action"]),"directness":spec.get("directness","DIRECT"),"origin":"FIXTURE_ANNOTATED"}]
    return {"schema_version":"dmsg-kit-trace-v1","input_sha256":fingerprint(case["text"]),
            "session_version":1,"inference_mode":"FIXTURE","model_status":spec.get("status","VALID"),
            "latency_ms":0.0,"answers":answers,"evidence":evidence,"context_conflict":spec.get("conflict",False)}
