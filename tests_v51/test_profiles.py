"""Offline contract tests. No inference or validation-set access."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration import v50, v51_profiles as P


def raw():
    answers = {}
    for name, spec in v50.bridge.SPEC.items():
        if spec["type"] == "noul":
            answers[name] = {"type": "noul", "noul": .8}
        else:
            options = spec["options"]
            answers[name] = {"type": spec["type"], "probabilities": {
                key: .9 if i == 0 else .1 / (len(options) - 1)
                for i, key in enumerate(options)}}
    return {"answers": answers}


class ProfilesTest(unittest.TestCase):
    def test_generated_files_and_js_question_order(self):
        subprocess.check_call([sys.executable, "tools/export_v51_profiles.py", "--check"], cwd=ROOT)
        source = (
            "require('./apps/shared/engine-data.js');"
            "require('./apps/shared/dmsg-engine.js');"
            "require('./apps/shared/v51-profile-data.js');"
            "const d=globalThis.DMSG_V51_PROFILE_DATA;"
            "const baseline=d.profiles['v50-baseline'].questions;"
            "const candidate=d.profiles['v51-evidence-legacy'].questions;"
            "const generated=globalThis.DMSG.questions('').questions;"
            "const signature=q=>Object.keys(q).map(k=>{const x=q[k],c=x.criteria;return[k,x.type,x.instructions,"
            "Array.isArray(c)?'levels':c?'choice':'absent',Array.isArray(c)?c:c?Object.entries(c):null];});"
            "process.stdout.write(JSON.stringify({"
            "data:d,baseline_same:JSON.stringify(signature(baseline))===JSON.stringify(signature(generated)),"
            "order_same:JSON.stringify(Object.keys(candidate))===JSON.stringify(Object.keys(generated))}));")
        result = json.loads(subprocess.check_output(["node", "-e", source], cwd=ROOT))
        self.assertEqual(P.registry(), result["data"])
        self.assertTrue(result["baseline_same"])
        self.assertTrue(result["order_same"])

    def test_baseline_wire_bytes_match_and_only_registered_profiles_exist(self):
        self.assertEqual(tuple(P.registry()["profiles"]),
                         ("v50-baseline", "v51-evidence-legacy", "v51-semantic-candidate", "v51-specific-candidate"))
        for text in ("", " 합성 문장 — 인용 \"문자\"\n🙂 ", "state questions <script>"):
            old = v50.bridge.questions(text)
            new = P.questions(text)
            self.assertEqual(P.wire_bytes(old), P.wire_bytes(new))
            self.assertEqual(list(new), ["state", "questions"])
        item = P.profile()
        self.assertEqual(item["question_contract_sha256"], v50.execution_manifest()["question_contract_sha256"])
        self.assertEqual(item["empty_state_payload_sha256"], hashlib.sha256(P.wire_bytes(P.questions(""))).hexdigest())

    def test_exact_evidence_candidate_and_protected_questions(self):
        baseline = P.questions("")["questions"]
        candidate = P.questions("", P.EVIDENCE_LEGACY)["questions"]
        frozen = json.loads((ROOT / P.CANDIDATE_SOURCE).read_text())
        source = next(c for c in frozen["candidates"] if c["candidate_id"] == "EN_SCOPE_V1")
        self.assertEqual(candidate["q_evidence"], source["questions"]["q_evidence"])
        self.assertNotEqual(baseline["q_evidence"], candidate["q_evidence"])
        self.assertEqual(list(baseline), list(candidate))
        for key in baseline:
            if key != "q_evidence":
                self.assertEqual(P.wire_bytes(baseline[key]), P.wire_bytes(candidate[key]))
        self.assertEqual(P.profile()["response_schema"], P.profile(P.EVIDENCE_LEGACY)["response_schema"])

    def test_unknown_profile_policy_and_candidate_dra_are_rejected(self):
        for ident, policy in (("unknown", "legacy"), ([], "legacy"), (P.BASELINE, "unknown"),
                              (P.BASELINE, []), (P.EVIDENCE_LEGACY, "dra"), (P.SEMANTIC_CANDIDATE, "dra"),
                              (P.SPECIFIED_CANDIDATE, "dra")):
            with self.subTest(profile=ident, policy=policy), self.assertRaises(P.ContractError):
                P.questions("", ident, policy)
        P.questions("", P.BASELINE, "dra")

    def test_bindings_reject_stale_swapped_missing_and_extra_metadata(self):
        baseline = P.binding()
        candidate = P.binding(P.EVIDENCE_LEGACY)
        self.assertEqual(P.validate_binding(candidate, P.EVIDENCE_LEGACY), candidate)
        changed = deepcopy(candidate)
        changed["question_contract_sha256"] = "0" * 64
        extra = dict(candidate, extra="not allowed")
        missing = dict(candidate)
        del missing["registry_fingerprint"]
        for value in (baseline, changed, extra, missing, None):
            with self.subTest(value=value), self.assertRaisesRegex(P.ContractError, "PROFILE_BINDING_MISMATCH"):
                P.validate_binding(value, P.EVIDENCE_LEGACY)

    def test_payload_rejects_question_or_choice_reorder_or_added_metadata(self):
        valid = P.questions("synthetic")
        self.assertEqual(P.validate_payload(valid), valid)
        bad = []
        x = deepcopy(valid); x["questions"] = dict(reversed(list(x["questions"].items()))); bad.append(x)
        x = deepcopy(valid); c = x["questions"]["q_action"]["criteria"]
        x["questions"]["q_action"]["criteria"] = dict(reversed(list(c.items()))); bad.append(x)
        x = deepcopy(valid); x["profile_id"] = P.BASELINE; bad.append(x)
        x = P.questions("synthetic", P.EVIDENCE_LEGACY); bad.append(x)
        for value in bad:
            with self.assertRaisesRegex(P.ContractError, "PROFILE_PAYLOAD_MISMATCH"):
                P.validate_payload(value)

    def test_registry_tampering_even_with_recomputed_fingerprint_is_rejected(self):
        original_read = P._read_json
        mutations = []
        value = P.registry(); value["profiles"][P.EVIDENCE_LEGACY]["allowed_policy_ids"].append("dra"); mutations.append(value)
        value = P.registry(); q = value["profiles"][P.BASELINE]["questions"]
        value["profiles"][P.BASELINE]["questions"] = dict(reversed(list(q.items()))); mutations.append(value)
        value = P.registry(); value["profiles"]["unregistered"] = deepcopy(value["profiles"][P.BASELINE]); mutations.append(value)
        for value in mutations:
            value["registry_fingerprint"] = P._hash({k: v for k, v in value.items() if k != "registry_fingerprint"})
            def read(path):
                return value if path == P.REGISTRY_PATH else original_read(path)
            with patch.object(P, "_read_json", side_effect=read), self.assertRaisesRegex(P.ContractError, "PROFILE_REGISTRY_DRIFT"):
                P.registry()

    def test_source_and_baseline_manifest_drift_fail_closed(self):
        original_hash = P._file_hash
        def altered(path):
            return "0" * 64 if path == P.CANDIDATE_SOURCE else original_hash(path)
        with patch.object(P, "_file_hash", side_effect=altered), self.assertRaisesRegex(P.ContractError, "PROFILE_CANDIDATE_SOURCE_DRIFT"):
            P.registry()
        def changed_source(path):
            return "0" * 64 if path == "integration/v51_profiles.py" else original_hash(path)
        with patch.object(P, "_file_hash", side_effect=changed_source), self.assertRaisesRegex(P.ContractError, "PROFILE_REGISTRY_DRIFT"):
            P.registry()
        manifest = v50.execution_manifest(); manifest["manifest_fingerprint"] = "0" * 64
        with patch.object(v50, "execution_manifest", return_value=manifest), self.assertRaisesRegex(P.ContractError, "PROFILE_BASE_MANIFEST_DRIFT"):
            P.registry()

    def test_response_schema_and_optional_behavior_are_unchanged(self):
        original = raw()
        for ident in (P.BASELINE, P.EVIDENCE_LEGACY):
            for value in (original, {"answers": {k: v for k, v in original["answers"].items() if k != "q_evidence"}}):
                expected = v50.bridge.normalize_response(value, v50.bridge.SPEC, optional=v50.bridge.OPTIONAL_QUESTIONS)
                self.assertEqual(P.normalize_response(value, ident), expected)
            bad = deepcopy(original); bad["answers"]["q_request_presence"] = {"type": "noul", "noul": .9}
            with self.assertRaisesRegex(P.ContractError, "ANSWER_KEYS_MISMATCH"): P.normalize_response(bad, ident)
            bad = deepcopy(original); bad["answers"]["q_action"]["probabilities"]["other_action"] = .1
            with self.assertRaisesRegex(P.ContractError, "INVALID_OPTIONS"): P.normalize_response(bad, ident)

    def test_semantic_profile_preserves_seven_questions_and_requires_three_new_answers(self):
        prior = P.questions("synthetic", P.EVIDENCE_LEGACY)["questions"]
        item = P.profile(P.SEMANTIC_CANDIDATE)
        new = item["questions"]
        names = ["q_request_scope", "q_current_exposure", "q_payment_anomaly"]
        self.assertEqual(list(new), list(prior) + names)
        for key, value in prior.items():
            self.assertEqual(P.wire_bytes(new[key]), P.wire_bytes(value))
        self.assertEqual(list(new["q_request_scope"]["criteria"]),
                         ["no_request", "other_request", "sensitive_request", "unclear"])
        self.assertTrue(set(names) <= set(item["required_questions"]))
        self.assertFalse(set(names) & set(item["optional_questions"]))
        extended = raw()
        extended["answers"].update({
            "q_request_scope": {"type": "choice", "probabilities": {
                "no_request": .05, "other_request": .85, "sensitive_request": .05, "unclear": .05}},
            "q_current_exposure": {"type": "noul", "noul": .1},
            "q_payment_anomaly": {"type": "noul", "noul": .1}})
        self.assertEqual(P.normalize_response(extended, P.SEMANTIC_CANDIDATE)["q_request_scope"]["choice"], "other_request")
        for key in names:
            missing = deepcopy(extended); del missing["answers"][key]
            with self.assertRaisesRegex(P.ContractError, "ANSWER_KEYS_MISMATCH"):
                P.normalize_response(missing, P.SEMANTIC_CANDIDATE)
            malformed = deepcopy(extended); malformed["answers"][key] = {"type": "unsupported"}
            with self.assertRaises(P.ContractError):
                P.normalize_response(malformed, P.SEMANTIC_CANDIDATE)
        with self.assertRaisesRegex(P.ContractError, "ANSWER_KEYS_MISMATCH"):
            P.normalize_response(extended, P.EVIDENCE_LEGACY)

    def test_returns_are_detached(self):
        first = P.questions("")
        first["questions"]["q_action"]["instructions"] = "modified by caller"
        self.assertNotEqual(first, P.questions(""))
        with self.assertRaisesRegex(P.ContractError, "TEXT_REQUIRED"): P.questions(None)

    def test_specific_profile_appends_required_question_and_preserves_frozen_profiles(self):
        frozen = {
            P.BASELINE: "3a0d4a80c67111193ad58802a4d4d7b4e6901213d8302092729067a8524c7b42",
            P.EVIDENCE_LEGACY: "419c9464b4874d7e949382807674b74021ca1b0b7fecc892453851c10840ca81",
            P.SEMANTIC_CANDIDATE: "7f762479f1d760c52e3f4d4f460356588a45a795aa977c983d465383e3f73dd5"}
        for ident, fingerprint in frozen.items():
            self.assertEqual(P.profile(ident)["profile_fingerprint"], fingerprint)
        prior = P.profile(P.SEMANTIC_CANDIDATE)
        item = P.profile(P.SPECIFIED_CANDIDATE)
        self.assertEqual(list(item["questions"]), list(prior["questions"]) + ["q_request_specified"])
        for key, value in prior["questions"].items():
            self.assertEqual(P.wire_bytes(item["questions"][key]), P.wire_bytes(value))
        self.assertEqual(item["questions"]["q_request_specified"], {
            "type": "noul", "instructions": "Does the current message explicitly specify what the listener is being asked to do now? Count everyday non-sensitive tasks as well as sensitive actions. Answer no if there is no current request, only a report or quotation, or the requested act is left as do that / follow my instructions without saying what that act is. Do not infer missing facts."})
        self.assertEqual(item["response_schema"]["q_request_specified"], {"type": "noul"})
        self.assertIn("q_request_specified", item["required_questions"])
        self.assertNotIn("q_request_specified", item["optional_questions"])
        extended = raw()
        extended["answers"].update({
            "q_request_scope": {"type": "choice", "probabilities": {
                "no_request": .05, "other_request": .85, "sensitive_request": .05, "unclear": .05}},
            "q_current_exposure": {"type": "noul", "noul": .1},
            "q_payment_anomaly": {"type": "noul", "noul": .1},
            "q_request_specified": {"type": "noul", "noul": .9}})
        self.assertEqual(P.normalize_response(extended, P.SPECIFIED_CANDIDATE)["q_request_specified"]["probabilities"]["yes"], .9)
        missing = deepcopy(extended); del missing["answers"]["q_request_specified"]
        with self.assertRaisesRegex(P.ContractError, "ANSWER_KEYS_MISMATCH"):
            P.normalize_response(missing, P.SPECIFIED_CANDIDATE)
        for value in ({"type": "noul", "noul": True}, {"type": "choice", "noul": .9}):
            malformed = deepcopy(extended); malformed["answers"]["q_request_specified"] = value
            with self.assertRaises(P.ContractError): P.normalize_response(malformed, P.SPECIFIED_CANDIDATE)
        with self.assertRaisesRegex(P.ContractError, "ANSWER_KEYS_MISMATCH"):
            P.normalize_response(extended, P.SEMANTIC_CANDIDATE)


if __name__ == "__main__":
    unittest.main()
