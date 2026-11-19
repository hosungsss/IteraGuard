"""Review-only policy candidate. Does not replace the approved product policy."""
from .contracts import finite

HIGH = {"money_transfer", "credential_or_otp", "remote_app_install", "personal_data"}


def evaluate(trace, threshold=0.70, margin=0.0):
    finite(threshold); finite(margin)
    fired = []
    answers = trace["answers"]
    trusted = [e for e in trace["evidence"] if e["origin"] != "MODEL_PROPOSED" and e["directness"] == "DIRECT"]
    high = any(e["action"] in HIGH for e in trusted)
    linked = any(e["action"] in {"verification_link", "secrecy"} for e in trusted)
    if high: fired.append("independent_high_action")
    if trace["model_status"] != "VALID": fired.append("model_unavailable_or_invalid")
    if trace["context_conflict"]: fired.append("context_guard_conflict")
    gates = {}
    for q in ("q_action", "q_speech"):
        if q not in answers: continue
        values = sorted(answers[q]["probabilities"].values(), reverse=True)
        gates[q] = {"top_probability": values[0], "margin": values[0]-values[1]}
        if values[0] < threshold: fired.append(q+"_low_probability")
        if values[0]-values[1] < margin: fired.append(q+"_low_margin")
    if answers.get("q_evidence", {}).get("selected") == "no": fired.append("model_evidence_insufficient")
    action = answers.get("q_action", {}).get("selected")
    speech = answers.get("q_speech", {}).get("selected")
    if action == "other_unclear" or speech == "unclear": fired.append("semantic_uncertainty")
    if action not in {None,"none","other_unclear"} and speech == "direct_request" and not any(e["action"]==action for e in trusted):
        fired.append("model_action_without_validated_evidence")
    if action == "none" and trusted: fired.append("none_conflicts_with_direct_evidence")
    if high:
        outcome, final = "PAUSE_AND_VERIFY", "independent_high_action"
    elif fired:
        outcome, final = "ASK_HUMAN", fired[0]
    elif linked:
        outcome, final = "CAUTION", "validated_caution_request"
    else:
        outcome, final = "NO_STRONG_SIGNAL", "no_validated_risky_request"
    return {"outcome": outcome, "all_fired_rules": fired, "final_rule": final, "gates": gates,
            "policy_id": "review-probe-v1", "threshold": threshold, "margin": margin}
