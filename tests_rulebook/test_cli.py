"""Custom industry rulebook local CLI checks; not Zoro or external service tests."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CustomDomainCLI(unittest.TestCase):
    def run_cli(self, book_path, answers_path):
        return subprocess.run(
            [sys.executable, "-m", "tools.rulebook_preview_v58",
             "--book-file", str(book_path),
             "--answers", str(answers_path),
             "--tenant", "company_demo",
             "--event", "event_42"],
            cwd=ROOT, capture_output=True, text=True,
        )

    def test_local_company_book_preview(self):
        b = ROOT / "rulebook/presets/refund_intake.json"
        a = ROOT / "tests_rulebook/refund_fixture.json"
        proc = self.run_cli(b, a)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"action": "OPEN_REVIEW_TASK"', proc.stdout)
        self.assertIn('"effects_executed": false', proc.stdout)
        self.assertIn("LOCAL_TYPED_FIXTURE", proc.stdout)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            book = Path(d) / "duplicate.json"
            book.write_text('{"schema_version":"a","schema_version":"b"}', encoding="utf-8")
            a = ROOT / "tests_rulebook/refund_fixture.json"
            proc = self.run_cli(book, a)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("DUPLICATE_JSON_KEY", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_overlarge_rulebook_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            book = Path(d) / "huge.json"
            book.write_text('{"x":"' + ("a" * 70000) + '"}', encoding="utf-8")
            a = ROOT / "tests_rulebook/refund_fixture.json"
            proc = self.run_cli(book, a)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("INVALID_LOCAL_JSON_FILE", proc.stderr)


if __name__ == "__main__":
    unittest.main()
