import math


def fraction(k, n):
    return {"numerator": k, "denominator": n, "rate": k/n if n else None}


def percentile(values, p):
    if not values: return None
    data = sorted(values)
    return data[max(0, math.ceil(p * len(data))-1)]


def summarize(rows):
    normal = [r for r in rows if not r["risk_context"]]
    nonhold = [r for r in rows if r["outcome"] != "ASK_HUMAN"]
    pause = [r for r in rows if r["expected"] == ["PAUSE_AND_VERIFY"]]
    times = [r["latency_ms"] for r in rows if r["model_status"] == "VALID"]
    modes = sorted({r["inference_mode"] for r in rows})
    return {
        "unit": "synthetic_single_turn_case", "inference_modes": modes,
        "allowed_guidance_match": fraction(sum(r["matched"] for r in rows), len(rows)),
        "always_ask_human_match": fraction(sum("ASK_HUMAN" in r["expected"] for r in rows), len(rows)),
        "abstention": fraction(len(rows)-len(nonhold),len(rows)),
        "coverage": fraction(len(nonhold),len(rows)),
        "nonabstained_match": fraction(sum(r["matched"] for r in nonhold),len(nonhold)),
        "normal_strong_pause": fraction(sum(r["outcome"]=="PAUSE_AND_VERIFY" for r in normal),len(normal)),
        "normal_abstention": fraction(sum(r["outcome"]=="ASK_HUMAN" for r in normal),len(normal)),
        "required_pause_missed": fraction(sum(r["outcome"]!="PAUSE_AND_VERIFY" for r in pause),len(pause)),
        "invalid_or_unavailable": fraction(sum(r["model_status"]!="VALID" for r in rows),len(rows)),
        "latency_ms": {"scope":"provider-reported; valid responses only; failures counted separately", "count":len(times),
                       "p50_nearest_rank":percentile(times,.50),"p95_nearest_rank":percentile(times,.95)},
        "notice": "FIXTURE latency and scores are artificial. This is not independent accuracy or model identity attestation.",
    }
