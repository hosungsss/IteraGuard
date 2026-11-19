"""Review-only reproductions; supplied typed outcomes, zero real model calls.

Run after the review copy's exact contract dependency files have been fetched.
Does not edit product files. SQLite is created in a temporary directory.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sys
import tempfile

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent / "v53"
sys.path.insert(0, str(ROOT))
from integration import v51
from integration.v48 import bridge
from arena.store import Arena


def controlled_raw():
    profile = v51.P.profile("v51-specific-candidate", "legacy")
    winners = {"q_action": "unclear", "q_speech": "unclear", "q_request_scope": "unclear", "q_risk": "low"}
    a = {}
    for key, spec in profile["response_schema"].items():
        if spec["type"] == "noul":
            a[key] = {"type": "noul", "noul": 0.1}
        else:
            winner = winners.get(key, spec["options"][0])
            item = {"type": spec["type"], "probabilities": {x: 0.96 if x == winner else 0.04 / (len(spec["options"]) - 1) for x in spec["options"]}}
            item["choice" if spec["type"] == "choice" else "score"] = winner
            a[key] = item
    return {"answers": a}


class ControlledClient:
    """Fixture injection, explicitly not a Zoro call."""
    def __init__(self, raw):
        self.raw = raw
        self.calls = []

    def infer(self, text, *, question_payload=None):
        self.calls.append({"text": text, "question_payload": deepcopy(question_payload)})
        return deepcopy(self.raw), 0.0


def main():
    manifest = v51.execution_manifest()
    results = {"mode": "OFFLINE_CONTROLLED_TYPED_RESPONSES", "actual_model_calls": 0,
               "manifest_verified": True, "manifest_fingerprint": manifest["manifest_fingerprint"],
               "active_profile": v51.selected_profile(), "checks": []}
    client = ControlledClient(controlled_raw())
    first_text = "그 자료를 안내받은 곳으로 보내 주세요."
    second_text = "다른 문서도 새로 받은 번호로 보내 주세요."
    with tempfile.TemporaryDirectory() as td:
        arena = Arena(Path(td) / "workflow.sqlite3", client=client, profile_id="v51-specific-candidate")
        start = arena.start()
        one = arena.evaluate(session_id=start["session_id"], version=0, request_id="first_unclear", text=first_text, synthetic_only=True)
        two = arena.evaluate(session_id=start["session_id"], version=1, request_id="second_unclear", text=second_text,
                             task_id=one["next_task"]["id"], observation="USER_REPORTS_CONFIRMED", synthetic_only=True)
        state = arena.read(start["session_id"])
        assert one["current_turn_action"] == two["current_turn_action"] == "ASK_HUMAN"
        assert one["task_disposition"] == "OPEN_TASK_AVAILABLE"
        assert two["task_disposition"] == "REPORTED_TASK_RETAINED_NOT_VERIFIED"
        assert "next_task" not in two
        assert all(t["status"] != "OPEN" for t in state["tasks"])
        results["checks"].append({"id": "NEW_UNCERTAIN_INPUT_NO_NEW_TASK", "status": "REPRODUCED",
            "first_action": one["current_turn_action"], "second_action": two["current_turn_action"],
            "second_reason": two["current_turn_reason"], "second_disposition": two["task_disposition"],
            "open_task_count": sum(t["status"] == "OPEN" for t in state["tasks"]),
            "different_inputs": first_text != second_text,
            "fixture_injection_count": len(client.calls),
            "all_model_states_are_current_text_only": [c["question_payload"]["state"] for c in client.calls] == [first_text, second_text]})
    c = bridge.ModelClient(endpoint="http://127.0.0.1:8008/v1/decide", model_id="trillionlabs/Zoro-1", enabled=True)
    try:
        c._check_target()
    except bridge.ModelUnavailable as e:
        results["checks"].append({"id": "NEW_DECIDE_ENDPOINT_PREFLIGHT", "status": "REPRODUCED", "error": str(e), "network_calls": 0})
    else:
        raise AssertionError("Expected existing client to reject /v1/decide")
    results["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               [ROOT / "arena/store.py", ROOT / "integration/v51.py", ROOT / "integration/v51_policy.py", ROOT / "vendor/dmsg/prototype/model_bridge.py"]}
    output = Path(tempfile.mkdtemp(prefix="iteraguard-review-")) / "code_audit_repro_results.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
