"""Python/JS candidate parity using synthetic vectors and optional frozen dev98.
No inference. The optional replay rejects any dataset inventory except the old
V2_48/AI25_previous/AI25_new development sets and verifies their frozen hashes.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration import v50, v51_policy as P, v51_profiles as Q


def profile():
    value = Q.profile(Q.SEMANTIC_CANDIDATE)
    return {"spec": value["response_schema"], "optional": value["optional_questions"]}


def raw(action="none", speech="direct_request", p=.95, scope="other_request", scope_p=.95,
        exposure=.05, payment=.05, aux=.05, evidence=.95):
    spec = profile()["spec"]
    def choice(key, winner, probability):
        return {"type": "choice", "probabilities": {o: probability if o == winner else
                (1 - probability) / (len(spec[key]["options"]) - 1) for o in spec[key]["options"]}}
    return {"answers": {"q_action": choice("q_action", action, p),
        "q_speech": choice("q_speech", speech, p), "q_scam": {"type": "noul", "noul": aux},
        "q_pressure": {"type": "noul", "noul": aux}, "q_evidence": {"type": "noul", "noul": evidence},
        "q_request_scope": choice("q_request_scope", scope, scope_p),
        "q_current_exposure": {"type": "noul", "noul": exposure},
        "q_payment_anomaly": {"type": "noul", "noul": payment}}}


def javascript(cases, selected=None):
    script = (
        "const fs=require('fs');const S=require('./apps/shared/v51-semantic.js');"
        "const input=JSON.parse(fs.readFileSync(0,'utf8'));"
        "const results=input.cases.map(c=>{try{return {ok:true,result:S.advisory(c.text,c.raw,c.profile||input.profile)};}"
        "catch(e){return {ok:false,error:e.code||e.message};}});"
        "process.stdout.write(JSON.stringify(results));")
    return json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT,
        input=json.dumps({"cases": cases, "profile": selected or profile()}, ensure_ascii=False).encode()))


def python(cases, selected=None):
    selected = selected or profile()
    results = []
    for case in cases:
        try:
            results.append({"ok": True, "result": P.advisory(case["text"], case["raw"], case.get("profile", selected))})
        except P.ContractError as error:
            results.append({"ok": False, "error": str(error)})
    return results


class SemanticParityTest(unittest.TestCase):
    def check_cases(self, cases):
        expected, actual = python(cases), javascript(cases)
        self.assertEqual(len(expected), len(actual))
        for i, (py, js) in enumerate(zip(expected, actual)):
            self.assertEqual(py, js, "Full result mismatch at synthetic/development vector " + str(i))
        return expected

    def test_generated_data_matches_source(self):
        subprocess.check_call([sys.executable, "tools/export_v51_base_engine.py", "--check"], cwd=ROOT)
        subprocess.check_call([sys.executable, "tools/export_v51_semantic.py", "--check"], cwd=ROOT)
        value = json.loads(subprocess.check_output(["node", "-e",
            "require('./apps/shared/v51-semantic-data.js');process.stdout.write(JSON.stringify(globalThis.DMSG_V51_RULE_DATA));"], cwd=ROOT))
        for relative, digest in value["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        self.assertEqual(value["rules"], json.loads((ROOT / "configs/v51_semantic_rules.json").read_text()))

    def test_unicode_casefold_fullwidth_and_combining_characters(self):
        cases = [{"text": text, "raw": raw(scope="sensitive_request", exposure=.5)} for text in (
            "paßword를 알려주세요.", "🙂 paßword를 알려주세요.", "PAẞWORD를 알려주세요.",
            "ｐａｓｓｗｏｒｄ를 알려주세요.", "pa\u0301ssword를 알려주세요.",
            "인증번호는 알려주지 마세요. 하지만 paßword를 보내주세요.")]
        results = self.check_cases(cases)
        self.assertEqual(results[0]["result"]["semantic_trace"]["rule_id"], "SCOPED_SENSITIVE_REQUEST")
        self.assertEqual(results[3]["result"]["semantic_trace"]["rule_id"], "BASELINE_FALLBACK")
        self.assertEqual(results[4]["result"]["semantic_trace"]["rule_id"], "BASELINE_FALLBACK")

    def test_base_contract_parity_and_original_namespaces_are_preserved(self):
        cases = []
        for text in ("paßword를 알려주세요.", "🙂 OTP를 알려주세요.",
                     "ｐａｓｓｗｏｒｄ를 알려주세요.", "pa\u0301ssword를 알려주세요."):
            value = raw(scope="sensitive_request", exposure=.5)
            value["answers"] = {k: v for k, v in value["answers"].items() if k in v50.bridge.SPEC}
            cases.append({"text": text, "raw": value})
        script = (
            "const fs=require('fs');const oldE=require('./apps/shared/dmsg-engine.js');"
            "const oldC=require('./apps/shared/v50-contract.js');"
            "const C=require('./apps/shared/v51-base-contract.js');"
            "const cases=JSON.parse(fs.readFileSync(0,'utf8'));"
            "process.stdout.write(JSON.stringify({preserved:globalThis.DMSG===oldE&&globalThis.DMSG_V50===oldC,"
            "results:cases.map(c=>C.evaluateCurrent(c.text,c.raw,'legacy'))}));")
        actual = json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT,
            input=json.dumps(cases, ensure_ascii=False).encode()))
        self.assertTrue(actual["preserved"])
        self.assertEqual(actual["results"], [v50.evaluate_current(c["text"], c["raw"], "legacy") for c in cases])

    def test_generator_rejects_changed_source_shape(self):
        from tools.export_v51_base_engine import replace_once
        self.assertEqual(replace_once("unique source", "unique", "new"), "new source")
        for source in ("missing", "unique unique"):
            with self.assertRaisesRegex(ValueError, "V51_BASE_ENGINE_SOURCE_SHAPE_CHANGED"):
                replace_once(source, "unique", "new")

    def test_compat_engine_existing_full_conformance(self):
        # Execute the existing runner unchanged except for the engine under test.
        # _compile preserves its directory-relative fixture/source resolution.
        script = (
            "const fs=require('fs'),path=require('path'),Module=require('module');"
            "const file=path.resolve('apps/conformance/run_conformance.js');"
            "let source=fs.readFileSync(file,'utf8');"
            "const old='apps/shared/dmsg-engine.js';"
            "if(source.split(old).length!==2)throw new Error('CONFORMANCE_RUNNER_SHAPE_CHANGED');"
            "source=source.replace(old,'apps/shared/v51-base-engine.js');"
            "const m=new Module(file,module);m.filename=file;m.paths=Module._nodeModulePaths(path.dirname(file));m._compile(source,file);")
        report = json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["pass"], report["total"])
        self.assertGreater(report["total"], 24000)

    def test_every_rule_and_codepoint_spans(self):
        cases = [
            {"text": "송금하세요.", "raw": raw(action="transfer")},
            {"text": "🙂 인증번호 알려주세요.", "raw": raw(scope="sensitive_request", exposure=.95)},
            {"text": "수수료 10만원을 보내주세요.", "raw": raw(scope="sensitive_request", payment=.95)},
            {"text": "🙂 인증번호 알려주세요.", "raw": raw(scope="sensitive_request", exposure=.5)},
            {"text": "새 계좌로 송금하세요.", "raw": raw(scope="sensitive_request", payment=.5, aux=.95)},
            {"text": "내일 도서관에 방문해 주세요.", "raw": raw()},
            {"text": "배송이 완료되었습니다.", "raw": raw(speech="informational", p=.6, scope="no_request")},
            {"text": "인증번호를 알려주지 마세요.", "raw": raw(action="otp", speech="negated_or_warning", scope="no_request")},
            {"text": "그것을 해주세요.", "raw": raw(scope="unclear")},
        ]
        results = self.check_cases(cases)
        self.assertEqual([r["result"]["semantic_trace"]["rule_id"] for r in results],
            ["PRESERVE_EXISTING_PAUSE", "CURRENT_SENSITIVE_EXPOSURE", "CURRENT_ANOMALOUS_PAYMENT",
             "SCOPED_SENSITIVE_REQUEST", "SCOPED_PAYMENT_CORROBORATION",
             "EXPLICIT_OTHER_REQUEST", "EXPLICIT_INFORMATION_ONLY", "EXPLICIT_PROTECTIVE_WARNING", "BASELINE_FALLBACK"])
        self.assertEqual(results[1]["result"]["semantic_trace"]["active_exposure_spans"], [{"start": 0, "end": 12}])

    def test_threshold_conflicts_quote_warning_and_unicode_patterns(self):
        texts = [
            "인증번호를 알려주지 마세요. 하지만 지금 OTP를 보내세요.",
            "인증번호를 알려달라는 문자를 받았다고 신고합니다.",
            "가족에게 알리지 마세요. 신분증을 보내세요.",
            "🙂 방문해 주세요.", "준비한 자료를 가져오세요.", "먼저 ١٢ 원을 주세요.",
            "먼저 10\u0085원을 주세요.", "먼저 10\ufeff원을 주세요.",
            "방문하세요 example.kr가", "방문하세요 example.kr!", "방문하세요 WWW.EXAMPLE.COM",
            "방문하세요 example.Kr", "인증이 완료되었습니다.", "그곳으로 해주세요.",
            "회신해 주세요. 오늘 중입니다.", "수수료를 내라고 했어요. 그러나 10만원을 보내주세요.",
        ]
        cases = []
        for text in texts:
            for scope in ("no_request", "other_request", "sensitive_request", "unclear"):
                for confidence in (.699999, .70, .700001):
                    for exposure, payment in ((.05, .05), (.95, .05), (.05, .95)):
                        cases.append({"text": text, "raw": raw(scope=scope, scope_p=confidence,
                                      exposure=exposure, payment=payment)})
        self.check_cases(cases)

    def test_failure_and_optional_behavior_match(self):
        base = raw()
        cases = []
        for key in ("q_request_scope", "q_current_exposure", "q_payment_anomaly"):
            value = deepcopy(base); del value["answers"][key]
            cases.append({"text": "방문해 주세요.", "raw": value})
            value = deepcopy(base); value["answers"][key] = {"type": "unexpected"}
            cases.append({"text": "방문해 주세요.", "raw": value})
        for key in ("q_claim", "q_risk", "q_evidence"):
            value = deepcopy(base); value["answers"][key] = {"type": "unexpected"}
            cases.append({"text": "방문해 주세요.", "raw": value})
        value = deepcopy(base); value["answers"]["q_request_scope"]["probabilities"]["other_request"] = True
        cases.append({"text": "방문해 주세요.", "raw": value})
        self.check_cases(cases)

    def test_specific_request_head_and_expanded_exposure_ontology(self):
        p = Q.profile(Q.SPECIFIED_CANDIDATE)
        selected = {"spec": p["response_schema"], "optional": p["optional_questions"]}
        cases = []
        ordinary = "파란 컵을 책상에 놓아주세요."
        old = raw(scope="other_request", scope_p=.6)
        cases.append({"text": ordinary, "raw": old})
        for text in (ordinary, "그것을 해주세요.", "여권을 보내주세요.", "🙂 주민등록증을 촬영해 보내주세요.",
                     "집 주소를 알려주세요.", "원격지원 접속 코드를 알려주세요.",
                     "여권을 보내지 마세요.", "여권을 보내달라는 문자를 받았다고 신고합니다."):
            for specified in (.299999, .699999, .70, .700001):
                for exposure in (.05, .5, .95):
                    value = raw(scope="other_request", scope_p=.6, exposure=exposure)
                    value["answers"]["q_request_specified"] = {"type": "noul", "noul": specified}
                    cases.append({"text": text, "raw": value, "profile": selected})
        results = self.check_cases(cases)
        self.assertEqual(results[0]["result"]["semantic_trace"]["rule_id"], "BASELINE_FALLBACK")
        self.assertFalse(results[0]["result"]["semantic_trace"]["specified_request"])
        self.assertEqual(results[7]["result"]["semantic_trace"]["rule_id"], "EXPLICIT_OTHER_REQUEST")
        missing = {"text": ordinary, "raw": old, "profile": selected}
        self.assertEqual(self.check_cases([missing])[0], {"ok": False, "error": "ANSWER_KEYS_MISMATCH"})

    def test_v13_actual_response_preserves_ask_and_redirect_trace(self):
        rows = json.loads((ROOT / "tests_data/v51/execution_cases.json").read_text())
        selected_rows = [row for row in rows if row["id"] == "V13"]
        self.assertEqual(len(selected_rows), 1)
        row = selected_rows[0]
        self.assertEqual(row["profile_id"], Q.SPECIFIED_CANDIDATE)
        item = Q.profile(row["profile_id"])
        case = {"text": row["text"], "raw": row["raw"],
                "profile": {"spec": item["response_schema"], "optional": item["optional_questions"]}}
        result = self.check_cases([case])[0]["result"]
        self.assertEqual(result["action"], "ASK_HUMAN")
        self.assertEqual(result["semantic_trace"]["rule_id"], "BASELINE_FALLBACK")
        self.assertTrue(result["semantic_trace"]["indirect_redirect_cue"])

    def test_specified_does_not_override_nonordinary_scope_or_indirect_redirect(self):
        item = Q.profile(Q.SPECIFIED_CANDIDATE)
        selected = {"spec": item["response_schema"], "optional": item["optional_questions"]}
        cases = []
        for scope in ("no_request", "other_request", "sensitive_request", "unclear"):
            value = raw(scope=scope, scope_p=.6)
            value["answers"]["q_request_specified"] = {"type": "noul", "noul": .95}
            cases.append({"text": "파란 컵을 책상에 놓아주세요.", "raw": value, "profile": selected})
        for text in ("아래 주소에서 수정해 주세요.", "첨부 페이지를 확인해 주세요.", "해당 사이트에 들어와 주세요.",
                     "QR을 확인해 주세요.", "qr을 확인해 주세요.", "오픈채팅에서 회신해 주세요."):
            value = raw(scope="other_request", scope_p=.6)
            value["answers"]["q_request_specified"] = {"type": "noul", "noul": .95}
            cases.append({"text": text, "raw": value, "profile": selected})
        results = self.check_cases(cases)
        self.assertEqual([r["result"]["action"] for r in results[:4]],
                         ["ASK_HUMAN", "NO_STRONG_SIGNAL", "ASK_HUMAN", "ASK_HUMAN"])
        for r in results[4:]:
            self.assertEqual(r["result"]["action"], "ASK_HUMAN")
            self.assertTrue(r["result"]["semantic_trace"]["indirect_redirect_cue"])

    @unittest.skipUnless(os.environ.get("V51_SPECIFIED_DEV_PROTOCOL"), "Optional specified dev133 replay path not supplied")
    def test_captured_specified_development133_full_result(self):
        path = Path(os.environ["V51_SPECIFIED_DEV_PROTOCOL"])
        protocol = json.loads(path.read_text())
        hashes = {
            "V2_48": "956467fb0f73312d08afcda6b00970dd4c5c8238ca1f66bb9757df7050cc9593",
            "AI25_previous": "9f7c589ae333201ea65255dc485dbb0587fe1491e3178d2a65b773d8c195798a",
            "AI25_new": "8a759d2e27a3de1593d047c245142678d6dc4a3f6086f7efd7492245bb681d68",
            "AI36_development": "5c1811aa68272ca987c084ef78e148be137ac477e27ffe9fd7de811a91e3fff9"}
        self.assertEqual(set(protocol["datasets"]), set(hashes))
        texts = {}
        for dataset, info in protocol["datasets"].items():
            data = Path(info["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), hashes[dataset])
            for line in data.decode().splitlines():
                row = json.loads(line); texts[dataset, row["id"]] = row["text"]
        item = Q.profile(Q.SPECIFIED_CANDIDATE)
        selected = {"spec": item["response_schema"], "optional": item["optional_questions"]}
        cases = []
        for line in (path.parent / "specified_raw.jsonl").read_text().splitlines():
            row = json.loads(line); text = texts[row["dataset"], row["id"]]
            if text.strip(): cases.append({"text": text, "raw": row["raw"], "profile": selected})
        self.assertEqual(len(cases), 133)
        self.check_cases(cases)

    @unittest.skipUnless(os.environ.get("V51_SEMANTIC_DEV_PROTOCOL"), "Optional old dev98 replay path not supplied")
    def test_captured_old_development_responses_full_result(self):
        path = Path(os.environ["V51_SEMANTIC_DEV_PROTOCOL"])
        protocol = json.loads(path.read_text())
        hashes = {
            "V2_48": "956467fb0f73312d08afcda6b00970dd4c5c8238ca1f66bb9757df7050cc9593",
            "AI25_previous": "9f7c589ae333201ea65255dc485dbb0587fe1491e3178d2a65b773d8c195798a",
            "AI25_new": "8a759d2e27a3de1593d047c245142678d6dc4a3f6086f7efd7492245bb681d68"}
        self.assertEqual(set(protocol["datasets"]), set(hashes))
        texts = {}
        for dataset, info in protocol["datasets"].items():
            data = Path(info["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), hashes[dataset])
            for line in data.decode().splitlines():
                row = json.loads(line); texts[dataset, row["id"]] = row["text"]
        cases = []
        for line in (path.parent / "semantic_raw.jsonl").read_text().splitlines():
            row = json.loads(line)
            text = texts[row["dataset"], row["id"]]
            if text.strip(): cases.append({"text": text, "raw": row["raw"]})
        self.assertEqual(len(cases), 97)
        self.check_cases(cases)


if __name__ == "__main__": unittest.main()
