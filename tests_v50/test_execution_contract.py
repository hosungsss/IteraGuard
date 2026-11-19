"""Contract/regression tests using synthetic raw replies only; no model or network calls."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration.v50 import (ContractError, apply_local_layers, bridge, evaluate_current,
                             execution_manifest, question_signature, unavailable_current)


def raw(action="none", speech="informational", p=.95, aux=.05, evidence=.95):
    def choice(options, winner):
        return {"type": "choice", "probabilities": {o: p if o == winner else (1 - p) / (len(options) - 1) for o in options}}
    answers = {"q_action": choice(bridge.ACTION_OPTIONS, action), "q_speech": choice(bridge.SPEECH_OPTIONS, speech),
               "q_scam": {"type": "noul", "noul": aux}, "q_pressure": {"type": "noul", "noul": aux},
               "q_evidence": {"type": "noul", "noul": evidence}}
    return {"model": "trillionlabs/Zoro-1", "answers": answers}


def js(payload):
    output = subprocess.check_output(["node", str(ROOT / "tests_v50/contract_runner.js")], input=json.dumps(payload, ensure_ascii=False).encode(), cwd=ROOT)
    return json.loads(output)


def rounded(value):
    if isinstance(value, float): return round(value, 10)
    if isinstance(value, dict): return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, list): return [rounded(v) for v in value]
    return value


class ExecutionContractTest(unittest.TestCase):
    def test_generated_manifest_and_question_order(self):
        subprocess.check_call([sys.executable, "tools/export_v50_contract.py", "--check"], cwd=ROOT)
        m = execution_manifest()
        self.assertEqual(m, js({"cases": []})["manifest"])
        self.assertEqual(m["question_signature"], question_signature(bridge.questions("")["questions"]))
        self.assertEqual(m["default_policy_id"], "legacy")
        self.assertFalse(m["runtime"]["model_attested"])
        self.assertEqual(m["runtime"]["expected_temperature"], 1.52)
        self.assertTrue(js({"operation": "drift"})["rejected"])
        original = bridge.questions
        def changed(text):
            q = original(text)
            q["questions"]["q_action"]["criteria"] = dict(reversed(list(q["questions"]["q_action"]["criteria"].items())))
            return q
        with patch.object(bridge, "questions", changed):
            with self.assertRaisesRegex(ContractError, "QUESTION_CONTRACT_DRIFT"): execution_manifest()

    def test_original_policy_and_cross_language_trace(self):
        cases = []
        texts = ["지금 당장 송금하세요. 비밀로 하세요.", "송금하지 마세요. 하지만 OTP 인증번호를 알려주세요.",
                 "다른 사람이 송금하라는 문자를 보냈다고 신고합니다.", "오늘 일정 안내입니다."]
        for text in texts:
            for action, speech, p, ev in [("none", "direct_request", .95, .05), ("none", "informational", .95, .95),
                ("transfer", "direct_request", .95, .95), ("transfer", "negated_or_warning", .95, .05),
                ("otp", "reported_or_quoted", .55, .95), ("unclear", "unclear", .95, .05), ("link", "informational", .95, .05)]:
                for policy in ("legacy", "dra"):
                    cases.append({"text": text, "raw": raw(action, speech, p, .95 if "당장" in text else .05, ev), "policy": policy})
        actual = js({"cases": cases})["results"]
        for case, node in zip(cases, actual):
            with self.subTest(text=case["text"], policy=case["policy"], answer=case["raw"]["answers"]["q_action"]):
                got = evaluate_current(case["text"], case["raw"], case["policy"], source="FIXTURE")
                fn = bridge.advisory if case["policy"] == "legacy" else bridge.decision_relevant_advisory
                original = fn(case["text"], case["raw"], source="FIXTURE")
                self.assertEqual({k: got[k] for k in original}, original)
                self.assertEqual(rounded(node), rounded({"ok": got}))
                encoded = json.dumps(got["execution_trace"], ensure_ascii=False)
                self.assertNotIn(case["text"], encoded)
                self.assertNotIn('"quote"', encoded)
                self.assertEqual(got["execution_trace"]["final_rule"], got["reason"])

    def test_overlapping_conditions_and_optional_drop(self):
        r = evaluate_current("송금하세요", raw("none", "direct_request", .55, .95, .05), source="FIXTURE")
        trace = r["execution_trace"]
        self.assertIn("MODEL_NONE_BUT_ACTION_TERMS_PRESENT", trace["condition_ids"])
        self.assertIn("NONE_DIRECT_REQUEST_CONFLICT", trace["condition_ids"])
        self.assertIn("MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS", trace["condition_ids"])
        self.assertEqual(trace["applied_rule_ids"], ["MODEL_NONE_BUT_ACTION_TERMS_PRESENT"])
        self.assertEqual(trace["dropped_optional_questions"], ["q_claim", "q_risk"])
        self.assertFalse(next(p for p in trace["predicates"] if p["id"] == "MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS")["eligible"])

    def test_existing_policy_vectors_preserved(self):
        vectors = json.loads((ROOT / "apps/conformance/vectors.json").read_text())
        manifest = execution_manifest()
        # Verify the manifest once, then reuse it only inside this large offline regression.
        # model_anchor belongs to the separate NLP profile and is intentionally outside this API.
        with patch("integration.v50.execution_manifest", return_value=manifest):
            for group, policy_id, function in (("advisory", "legacy", bridge.advisory), ("dra", "dra", bridge.decision_relevant_advisory)):
                for vector in vectors[group]:
                    if vector.get("anchor") is not None: continue
                    expected = function(vector["text"], vector["raw"], source="FIXTURE")
                    actual = evaluate_current(vector["text"], vector["raw"], policy_id, source="FIXTURE")
                    self.assertEqual({k: actual[k] for k in expected}, expected)

    def test_invalid_contract_failure_and_privacy(self):
        broken = raw(); del broken["answers"]["q_action"]
        with self.assertRaises(ContractError): evaluate_current("안내", broken)
        for failure in ("INVALID_RESPONSE_JSON", "a secret token or URL", "ModelUnavailable:MODEL_TRANSPORT_ERROR_TimeoutError", "V50_LOOPBACK_ONLY", "REMOTE_RELAY_DISABLED_V50"):
            py = unavailable_current(failure)
            self.assertEqual(py, js({"cases": [{"failure": failure, "policy": "legacy"}]})["results"][0]["ok"])
            self.assertEqual(py["action"], "ASK_HUMAN")
            self.assertNotIn("a secret token", json.dumps(py))
        for policy in (None, False, "", "other"):
            with self.assertRaisesRegex(ContractError, "UNSUPPORTED_POLICY_ID"): evaluate_current("안내", raw(), policy)
            self.assertEqual(js({"cases": [{"text": "안내", "raw": raw(), "policy": policy}]})["results"][0], {"error": "UNSUPPORTED_POLICY_ID"})
        for consent in (False, "", {"external_reputation": "yes"}, {"extra": False}):
            with self.assertRaisesRegex(ContractError, "INVALID_LOCAL_LAYER_CONSENT"):
                apply_local_layers("안내", unavailable_current("EMPTY"), consent=consent)
            self.assertEqual(js({"cases": [{"failure": "EMPTY", "policy": "legacy", "text": "안내", "local": {"consent": consent}}]})["results"][0], {"error": "INVALID_LOCAL_LAYER_CONSENT"})

    def test_local_layers_parity_and_never_clear(self):
        cases = []
        for text in ("일정 안내입니다.", "https://127.0.0.1/check?token=private 입력 안내"):
            for review in (False, True):
                for policy in ("legacy", "dra"):
                    cases.append({"text": text, "raw": raw(), "policy": policy,
                                  "local": {"user_review": review, "consent": {"external_reputation": True, "web_analysis": True}}})
        nodes = js({"cases": cases})["results"]
        for case, node in zip(cases, nodes):
            base = evaluate_current(case["text"], case["raw"], case["policy"], source="FIXTURE")
            original = deepcopy(base)
            out = apply_local_layers(case["text"], base, **case["local"])
            self.assertEqual(base, original)
            self.assertEqual(rounded(node), rounded({"ok": out}))
            self.assertNotIn("127.0.0.1", json.dumps(out["execution_trace"]))
            self.assertNotIn("private", json.dumps(out["link_summary"]))
            self.assertFalse(out["link_summary"]["network_used"])
            with self.assertRaisesRegex(ContractError, "LOCAL_LAYERS_ALREADY_APPLIED"): apply_local_layers(case["text"], out)
        failed = apply_local_layers("일정 안내", unavailable_current("MODEL_NOT_CONFIGURED"))
        self.assertEqual(failed["action"], "ASK_HUMAN")
        pause = evaluate_current("OTP 인증번호를 알려주세요", raw("otp", "direct_request"))
        self.assertEqual(apply_local_layers("https://example.com", pause, user_review=True)["action"], "PAUSE_AND_VERIFY")

    def test_linkguard_absence_is_explicit(self):
        result = {"action": "NO_STRONG_SIGNAL", "reason": "LOCAL_FIXTURE", "evidence": []}
        missing = js({"operation": "missing_linkguard", "result": result})
        self.assertEqual(missing["link_summary"]["status"], "NOT_AVAILABLE")
        self.assertEqual(missing["action"], "ASK_HUMAN")
        self.assertEqual(missing["execution_trace"]["trace_scope"], "LOCAL_POSTPROCESS_ONLY")


if __name__ == "__main__": unittest.main()
