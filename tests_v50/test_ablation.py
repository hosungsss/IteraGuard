import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments import v50_ablation as a


class AblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = a.bridge_module()
        cls.base = cls.bridge.questions("")["questions"]
        # Contract tests are self-contained; archived real candidate wording is
        # separately frozen with the actual run protocol, not a test dependency.
        cls.candidate = copy.deepcopy(cls.base)
        for key in a.TARGETS.values():
            cls.candidate[key]["instructions"] += " Synthetic contract-test clarification."
        cls.candidate["q_action"]["criteria"]["none"] = "Synthetic none clarification"

    def test_one_question_only_and_order_preserved(self):
        variants = a.build_variants(self.base, self.candidate)
        self.assertEqual(variants["baseline"], self.base)
        for name, target in a.TARGETS.items():
            q = variants[name]
            self.assertEqual([k for k in self.base if q[k] != self.base[k]], [target])
            self.assertEqual(list(q), list(self.base))
            for key in ("q_action", "q_speech", "q_risk"):
                self.assertEqual(list(q[key]["criteria"]), list(self.base[key]["criteria"]))

    def test_reordered_candidate_rejected(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["q_action"]["criteria"] = dict(reversed(list(candidate["q_action"]["criteria"].items())))
        with self.assertRaises(ValueError):
            a.build_variants(self.base, candidate)

    def test_order_sensitive_wire_hash(self):
        self.assertNotEqual(a.digest({"a": 1, "b": 2}), a.digest({"b": 2, "a": 1}))

    def test_dataset_provenance_labels_spans(self):
        rows = a.read_rows(a.SOURCE / "data/v50_ai_development25.jsonl")
        a.validate_development(rows)
        self.assertEqual(sum(r["risky"] is False for r in rows), 12)
        self.assertEqual(sum(r["risky"] is True for r in rows), 10)
        self.assertEqual(sum(r["risky"] is None for r in rows), 3)

    def test_bad_span_and_independent_claim_rejected(self):
        rows = a.read_rows(a.SOURCE / "data/v50_ai_development25.jsonl")
        bad = copy.deepcopy(rows)
        bad[0]["evidence"][0]["end_cp"] += 1
        with self.assertRaises(ValueError):
            a.validate_development(bad)
        bad = copy.deepcopy(rows)
        bad[0]["independent_eval"] = True
        with self.assertRaises(ValueError):
            a.validate_development(bad)

    def test_protocol_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "protocol.json"
            a.save_new(p, {"frozen": True})
            with self.assertRaises(FileExistsError):
                a.save_new(p, {"frozen": False})
            self.assertEqual(json.loads(p.read_text()), {"frozen": True})

    def make_inputs(self, directory):
        directory.mkdir(parents=True)
        case = {"id": "SYNTHETIC", "text": "합성 테스트 안내입니다.",
                "expect": ["NO_STRONG_SIGNAL"], "risky": False}
        for name in ("V2_48.jsonl", "AI25.jsonl"):
            (directory / name).write_text(json.dumps(case, ensure_ascii=False) + "\n")
        (directory / "candidate_questions.json").write_text(json.dumps(
            {"candidates": [{"candidate_id": "EN_SCOPE_V1", "questions": self.candidate}]}))

    def test_explicit_input_dir_accepts_flat_or_preserved_replay_layout(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "replay_inputs"
            self.make_inputs(root / "previous_inputs")
            self.assertEqual(a.resolve_input_dir(root), (root / "previous_inputs").resolve())
            self.assertEqual(a.resolve_input_dir(root / "previous_inputs"), (root / "previous_inputs").resolve())

    def test_bundled_inputs_precede_history_and_explicit_missing_never_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundled, old = root / "bundle", root / "history"
            self.make_inputs(bundled / "previous_inputs")
            self.make_inputs(old)
            with patch.object(a, "BUNDLED_INPUTS", bundled), patch.object(a, "OLD", old):
                self.assertEqual(a.resolve_input_dir(), (bundled / "previous_inputs").resolve())
                with self.assertRaisesRegex(FileNotFoundError, "--input-dir"):
                    a.resolve_input_dir(root / "missing-explicit")
                with patch.object(a, "BUNDLED_INPUTS", root / "absent-bundle"):
                    self.assertEqual(a.resolve_input_dir(), old.resolve())

    def test_standalone_prepare_without_model_is_offline_and_run_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, bundled = root / "standalone", root / "bundle"
            self.make_inputs(bundled / "previous_inputs")
            (source / "data").mkdir(parents=True)
            (source / "data/v50_ai_development25.jsonl").write_bytes(
                (a.SOURCE / "data/v50_ai_development25.jsonl").read_bytes())
            for name in ("model_bridge.py", "typed_contract.py", "context_guard.py", "core.py"):
                p = source / "vendor/dmsg/prototype" / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("synthetic protected-source fixture\n")
            with patch.object(a, "SOURCE", source), patch.object(a, "BUNDLED_INPUTS", bundled), \
                    patch.object(a, "OLD", root / "nonexistent-history"), \
                    patch.object(a, "MODEL", root / "no-model"), \
                    patch.object(a, "bridge_module", return_value=self.bridge), \
                    patch.object(a.urllib.request, "build_opener", side_effect=AssertionError("No network during prepare")), \
                    redirect_stdout(io.StringIO()):
                a.prepare(root / "out")
            protocol = json.loads((root / "out/protocol.json").read_text())
            self.assertEqual(protocol["input_directory"], str((bundled / "previous_inputs").resolve()))
            self.assertEqual(protocol["model_export_hashes"], {})
            self.assertEqual(protocol["model_export_status"], "MODEL_EXPORT_NOT_REGISTERED_RUN_BLOCKED")
            a.check_protected(protocol)
            with self.assertRaisesRegex(RuntimeError, "prepare a fresh output with --model-dir"):
                a.check_protected(protocol, model=True)

    def test_partial_model_export_fails_preparation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_inputs(root / "inputs")
            model = root / "model"
            model.mkdir()
            (model / "head.pt").write_bytes(b"small synthetic fixture")
            with self.assertRaisesRegex(FileNotFoundError, "Incomplete model export"):
                a.prepare(root / "out", input_dir=root / "inputs", model_dir=model)
            self.assertFalse((root / "out/protocol.json").exists())

    def test_unknown_risk_not_counted_as_benign_and_failure_not_dropped(self):
        rows = [{"id": "U", "risky": None, "expect": ["ASK_HUMAN"]},
                {"id": "R", "risky": True, "expect": ["PAUSE_AND_VERIFY"]}]
        items = [{"id": "U", "p": {"action": "NO_STRONG_SIGNAL"}},
                 {"id": "R", "p": {"action": "ASK_HUMAN"}, "status": "FAILED"}]
        m = a.metrics(rows, items, "p")
        self.assertEqual((m["n"], m["unknown_n"], m["benign_n"], m["unknown_cleared"], m["pause_required_missed"]), (2, 1, 0, 1, 1))
        with self.assertRaises(ValueError):
            a.metrics(rows, items[:1], "p")

    def test_blank_never_calls_model(self):
        class Never:
            def infer(self, *args, **kwargs):
                raise AssertionError("Blank must not call model")
        result = a.evaluate_row({"id": "B", "text": " ", "expect": ["ASK_HUMAN"], "risky": None},
                                {}, Never(), self.bridge, io.StringIO(), 0, "stub", "baseline")
        self.assertEqual(result["status"], "EMPTY_NO_INFERENCE")

    def test_transport_failure_retained_no_retry(self):
        bridge = self.bridge
        class Failed:
            calls = 0
            def infer(self, *args, **kwargs):
                self.calls += 1
                raise bridge.ModelUnavailable("STUB_TIMEOUT")
        client = Failed()
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stream:
            result = a.evaluate_row({"id": "F", "text": "synthetic", "expect": ["ASK_HUMAN"], "risky": None},
                                    self.base, client, bridge, stream, 1, "stub", "baseline")
            stream.seek(0)
            event = json.loads(stream.read())
        self.assertEqual(client.calls, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(event["error_code"], "STUB_TIMEOUT")
        self.assertNotIn("response", event)
        self.assertEqual(result["legacy"]["action"], "ASK_HUMAN")

    def test_raw_saved_before_typed_contract_rejection(self):
        class Invalid:
            def infer(self, *args, **kwargs):
                return {"answers": {}, "model": "trillionlabs/Zoro-1"}, 2.0
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stream:
            result = a.evaluate_row({"id": "I", "text": "synthetic", "expect": ["ASK_HUMAN"], "risky": None},
                                    self.base, Invalid(), self.bridge, stream, 1, "stub", "baseline")
            stream.seek(0)
            events = [json.loads(s) for s in stream.read().splitlines()]
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(events[0]["event"], "PARSED_PROVIDER_RESPONSE")
        self.assertEqual(events[1]["event"], "FAILURE_NO_IMPUTED_RESPONSE")


if __name__ == "__main__":
    unittest.main()
