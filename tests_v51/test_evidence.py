"""Author-written semantic counterexamples; no locked data or model calls."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest

from integration.v51_evidence import enrich_evidence, SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]


def result_with_anchor(text, quote=None, action="ASK_HUMAN"):
    result = {"action": action, "reason": "UPSTREAM_POLICY_REASON", "message": "기존 안내",
              "guidance": {"label": "원래 안내", "pause_required": True},
              "selected_action": "otp", "selected_speech": "unclear",
              "execution_trace": {"final_action": action, "evidence_spans": []}, "evidence": []}
    if quote is not None:
        start = text.index(quote)
        result["evidence"] = [{"start": start, "end": start + len(quote), "quote": quote,
                               "kind": "otp", "origin": "MODEL_SCHEMA_CHECKED", "directness": "unclear"}]
    return result


CASES = [
    ("인증번호를 알려주세요.", "주세요"),
    ("인증번호를 주세요.", "주세요"),
    ("인증번호를 알려주지 마세요.", "인증번호"),
    ("'인증번호를 알려주세요'라고 말했습니다.", "주세요"),
    ("예시: OTP를 보내세요.", "OTP"),
    ("인증번호를 알려주지 마세요. 하지만 지금 OTP를 보내주세요.", "인증번호"),
    ("서류를 가져오세요.", "서류"),
    ("수업 준비물 안내입니다.", None),
    ("주세요.", "주세요"),
    ("그것을 보내주세요.", "주세요"),
    ("인증번호가 도착했습니다.", "인증번호"),
    ("인증번호를 알려주지 마세요 지금 OTP를 보내주세요.", None),
    ("‘OTP를 보내세요’라는 문자를 보고 인증번호를 알려주세요.", None),
    ("‘인증번호를 알려주세요.", None),
    ("교육 예시:\n인증번호를 알려주세요.", None),
    ("🧑🏽‍💻🙂 서류를 가져오세요.\r\n🔒 OTP를 보내지 마세요.", "서류"),
    ("일상 비용 2만원을 보내주세요.", "주세요"),
    ("가족에게 말하지 마세요.", "마세요"),
    ("링크 https://example.invalid/a 를 열어 주세요.", None),
    ("Do not send OTP.", "OTP"),
    ("Please send OTP.", "OTP"),
    ("Don't send OTP.", None),
    ("‘인증번호’라는 단어를 읽어 보세요.", "인증번호"),
    ("회의는 내일 시작합니다.", None),
    ("예시: 송금하세요. OTP를 보내주세요.", None),
    ("경고: 사기 메시지 예시입니다. OTP를 보내주세요.", None),
    ("예시: 송금하세요. 예시 끝. OTP를 보내주세요.", None),
    ("교육 자료를 보내주세요.", None),
    ("예시 OTP를 보내주세요.", None),
    ("", None),
]


class EvidenceDisplayTests(unittest.TestCase):
    def assert_span_matches(self, text, output):
        for e in output["evidence"]:
            self.assertEqual(e["quote"], text[e["start"]:e["end"]])
            self.assertLess(e["start"], e["end"])
            self.assertFalse(e["semantic_verified"])

    def test_suffix_expands_to_topic_and_action_same_clause(self):
        text = "인증번호를 알려주세요. 서류를 가져오세요."
        out = enrich_evidence(text, result_with_anchor(text, "주세요"))
        anchor = [e for e in out["evidence"] if e["original_anchor_indexes"]][0]
        self.assertEqual(anchor["quote"], "인증번호를 알려주세요")
        self.assertEqual(anchor["clause_mode"], "DIRECT_REQUEST_CUE")
        self.assertNotIn("서류", anchor["quote"])
        self.assert_span_matches(text, out)

    def test_explicit_object_plus_give_suffix_is_displayable(self):
        text = "인증번호를 주세요."
        out = enrich_evidence(text, result_with_anchor(text, "주세요"))
        self.assertEqual(out["evidence"][0]["quote"], "인증번호를 주세요")

    def test_suffix_and_pronoun_do_not_manufacture_an_object(self):
        for text in ("주세요.", "그것을 보내주세요."):
            with self.subTest(text=text):
                out = enrich_evidence(text, result_with_anchor(text, "주세요"))
                self.assertEqual(out["evidence"], [])
                self.assertEqual(out["evidence_display"]["upstream_span_unavailable_rate"], 1)
                self.assertIn("NO_SUPPORTED_TOPIC_ACTION_PAIR", out["evidence_display"]["reason_codes"])

    def test_warning_and_quote_are_not_displayed_as_direct_request(self):
        for text, wanted in [("인증번호를 알려주지 마세요.", "NEGATED_OR_WARNING_CUE"),
                             ("'인증번호를 알려주세요'라고 말했습니다.", "QUOTED_OR_REPORTED"),
                             ("예시: OTP를 보내세요.", "QUOTED_OR_REPORTED")]:
            with self.subTest(text=text):
                out = enrich_evidence(text, result_with_anchor(text))
                self.assertEqual(out["evidence"][0]["clause_mode"], wanted)

    def test_report_word_as_requested_object_is_not_a_quotation(self):
        text = "교육 자료를 보내주세요."
        out = enrich_evidence(text, result_with_anchor(text))
        self.assertEqual(out["evidence"][0]["clause_mode"], "DIRECT_REQUEST_CUE")
        text = "예시 OTP를 보내주세요."
        out = enrich_evidence(text, result_with_anchor(text))
        self.assertEqual(out["evidence"], [])
        self.assertIn("REPORT_SCOPE_UNRESOLVED", out["evidence_display"]["reason_codes"])

    def test_warning_then_new_request_are_separate(self):
        text = "인증번호를 알려주지 마세요. 하지만 지금 OTP를 보내주세요."
        out = enrich_evidence(text, result_with_anchor(text, "인증번호"))
        self.assertEqual([e["clause_mode"] for e in out["evidence"]],
                         ["NEGATED_OR_WARNING_CUE", "DIRECT_REQUEST_CUE"])
        self.assert_span_matches(text, out)

    def test_unseparated_conflicting_cues_are_unavailable(self):
        for text in ("인증번호를 알려주지 마세요 지금 OTP를 보내주세요.",
                     "‘OTP를 보내세요’라는 문자를 보고 인증번호를 알려주세요."):
            with self.subTest(text=text):
                out = enrich_evidence(text, result_with_anchor(text))
                self.assertEqual(out["evidence"], [])
                self.assertEqual(out["evidence_display"]["status"], "UNAVAILABLE")

    def test_unclosed_quote_or_separate_report_heading_is_unresolved(self):
        for text in ("‘인증번호를 알려주세요.", "교육 예시:\n인증번호를 알려주세요."):
            out = enrich_evidence(text, result_with_anchor(text))
            self.assertEqual(out["evidence"], [])
            self.assertEqual(out["evidence_display"]["unavailable_clause_rate"], 1)

    def test_example_scope_does_not_end_at_punctuation(self):
        for text in ("예시: 송금하세요. OTP를 보내주세요.",
                     "경고: 사기 메시지 예시입니다. OTP를 보내주세요."):
            out = enrich_evidence(text, result_with_anchor(text))
            self.assertNotIn("DIRECT_REQUEST_CUE", [e["clause_mode"] for e in out["evidence"]])
            self.assertIn("PRECEDING_CONTEXT_HEADING_SCOPE_UNRESOLVED", out["evidence_display"]["reason_codes"])
        text = "예시: 송금하세요. 예시 끝. OTP를 보내주세요."
        out = enrich_evidence(text, result_with_anchor(text))
        self.assertEqual(out["evidence"][-1]["clause_mode"], "DIRECT_REQUEST_CUE")

    def test_whitespace_contract_for_nel_bom_and_control_separators(self):
        for prefix, expected_start in [("\u0085", 1), ("\ufeff", 0), ("\u001c", 0), ("\u2007", 1)]:
            text = prefix + "OTP를 보내주세요."
            out = enrich_evidence(text, result_with_anchor(text))
            self.assertEqual(out["evidence"][0]["start"], expected_start)
            self.assert_span_matches(text, out)

    def test_ordinary_request_is_display_context_not_risk(self):
        text = "서류를 가져오세요."
        out = enrich_evidence(text, result_with_anchor(text, "서류", "NO_STRONG_SIGNAL"))
        self.assertEqual(out["action"], "NO_STRONG_SIGNAL")
        self.assertEqual(out["evidence"][0]["topic_cues"], ["ORDINARY_OBJECT_TOPIC"])
        self.assertEqual(out["evidence_display"]["risk_classification"], "NOT_PERFORMED")

    def test_money_and_secrecy_words_do_not_classify_pause_or_risk(self):
        for text in ("일상 비용 2만원을 보내주세요.", "가족에게 말하지 마세요."):
            for action in ("NO_STRONG_SIGNAL", "CAUTION", "ASK_HUMAN", "PAUSE_AND_VERIFY"):
                original = result_with_anchor(text, None, action)
                out = enrich_evidence(text, original)
                self.assertEqual(out["action"], action)
                self.assertEqual(out["reason"], original["reason"])
                self.assertFalse(out["evidence_display"]["policy_changed"])

    def test_preserves_all_policy_fields_originals_and_caller_data(self):
        text = "🙂 OTP를 보내주세요."
        original = result_with_anchor(text, "주세요")
        snapshot = deepcopy(original)
        out = enrich_evidence(text, original)
        for key in snapshot:
            if key != "evidence":
                self.assertEqual(out[key], snapshot[key])
        self.assertEqual(out["original_evidence"], snapshot["evidence"])
        self.assertEqual(original, snapshot)
        out["original_evidence"][0]["quote"] = "caller-owned-copy"
        self.assertEqual(original, snapshot)

    def test_unicode_cp_offsets_crlf_and_quote_spanning_newline(self):
        for text in ("🧑🏽‍💻🙂 서류를 가져오세요.\r\n🔒 OTP를 보내지 마세요.",
                     "“OTP를\n보내주세요”라고 했습니다."):
            out = enrich_evidence(text, result_with_anchor(text))
            self.assert_span_matches(text, out)
        text = "😀 OTP를 보내주세요."
        out = enrich_evidence(text, result_with_anchor(text, "OTP"))
        self.assertEqual(out["original_evidence"][0]["start"], 2)

    def test_missing_or_invalid_anchor_is_not_relocated(self):
        text = "인증번호를 알려주세요."
        original = result_with_anchor(text)
        original["evidence"] = [{"start": True, "end": 4, "quote": "개인 원문"},
                                {"start": 1, "end": 3, "quote": "다른 문장"}]
        out = enrich_evidence(text, original)
        self.assertEqual(out["evidence_display"]["invalid_upstream_span_count"], 2)
        self.assertEqual(out["evidence_display"]["upstream_span_displayed_count"], 0)
        self.assertEqual(out["evidence"][0]["method"], "LOCAL_TOPIC_ACTION_CLAUSE_CONTEXT")
        self.assertEqual(out["original_evidence"], original["evidence"])

    def test_duplicate_anchors_one_clause_one_context_span(self):
        text = "인증번호를 알려주세요."
        original = result_with_anchor(text, "주세요")
        original["evidence"] *= 2
        out = enrich_evidence(text, original)
        self.assertEqual(len(out["evidence"]), 1)
        self.assertEqual(out["evidence"][0]["original_anchor_indexes"], [0, 1])
        self.assertEqual(out["evidence_display"]["upstream_span_unavailable_count"], 0)

    def test_cross_clause_original_cannot_be_promoted(self):
        text = "인증번호를 알려주세요. 서류를 가져오세요."
        original = result_with_anchor(text, text)
        out = enrich_evidence(text, original)
        self.assertEqual(out["evidence_display"]["invalid_upstream_span_count"], 1)
        self.assertEqual(out["evidence_display"]["upstream_span_unavailable_rate"], 1)
        self.assertEqual(len(out["evidence"]), 2)

    def test_partial_or_no_display_counts_are_explicit(self):
        text = "인증번호를 알려주세요. 그것을 보내주세요."
        out = enrich_evidence(text, result_with_anchor(text))
        m = out["evidence_display"]
        self.assertEqual((m["candidate_clause_count"], m["displayed_clause_count"], m["unavailable_clause_count"]), (2, 1, 1))
        self.assertEqual((m["candidate_clause_coverage"], m["unavailable_clause_rate"]), (.5, .5))
        self.assertEqual(m["status"], "PARTIAL")
        empty = enrich_evidence("회의는 내일입니다.", result_with_anchor("회의는 내일입니다."))
        self.assertIsNone(empty["evidence_display"]["candidate_clause_coverage"])
        self.assertEqual(empty["evidence_display"]["status"], "NOT_APPLICABLE")

    def test_safe_trace_does_not_copy_raw_quote_or_untrusted_metadata(self):
        text = "표식SECRET_XYZ OTP를 보내주세요."
        original = result_with_anchor(text, "주세요")
        original["evidence"][0].update(kind="SECRET_KIND", origin="SECRET_ORIGIN", payload="SECRET_PAYLOAD")
        out = enrich_evidence(text, original)
        safe = json.dumps(out["evidence_display_trace"], ensure_ascii=False)
        for token in ("SECRET", "quote", "original_evidence", text, "보내주세요"):
            self.assertNotIn(token, safe)
        self.assertFalse(out["evidence_display_trace"]["raw_text_stored"])

    def test_idempotent_and_no_unbounded_expansion(self):
        for text in ("인증번호를 알려주세요.", "가" * 250 + " 인증번호를 알려주세요."):
            out = enrich_evidence(text, result_with_anchor(text, "주세요"))
            self.assertEqual(enrich_evidence(text, out), out)
            if len(text) > 240:
                self.assertEqual(out["evidence"], [])
                self.assertIn("CLAUSE_TOO_LONG_FOR_LOCAL_DISPLAY", out["evidence_display"]["reason_codes"])

    def test_input_contract_errors(self):
        for text, result in [(None, {}), ("a" * 2001, {}), ("valid", []), ("valid", None)]:
            with self.assertRaisesRegex(ValueError, "INVALID_EVIDENCE_INPUT"):
                enrich_evidence(text, result)

    def test_python_js_full_output_parity_for_semantic_cases(self):
        requests = [{"text": t, "result": result_with_anchor(t, anchor)} for t, anchor in CASES]
        requests += [{"text": "🙂 " + t, "result": result_with_anchor("🙂 " + t, anchor)} for t, anchor in CASES]
        requests += [{"text": prefix + "OTP를 보내주세요.", "result": result_with_anchor(prefix + "OTP를 보내주세요.")}
                     for prefix in ("\u0085", "\ufeff", "\u001c", "\u2007", "\u2028", "\u202f")]
        run = subprocess.run(["node", str(ROOT / "tests_v51/evidence_js_test.js"), "--stdin"],
                             input=json.dumps(requests, ensure_ascii=False), text=True, capture_output=True, check=True)
        actual = json.loads(run.stdout)
        expected = [enrich_evidence(r["text"], r["result"]) for r in requests]
        self.assertEqual(len(actual), 66)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
