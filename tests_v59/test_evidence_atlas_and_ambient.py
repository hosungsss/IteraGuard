"""Verify source-bound evidence atlas and v5.9 display-only assets."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/research/SCAM_EVIDENCE_ATLAS_2026_KO.md"
HTML = ROOT / "arena/web/index.html"
SERVER = ROOT / "arena/server.py"


class EvidenceAtlasTests(unittest.TestCase):
    def test_atlas_has_exactly_30_reconstructed_patterns(self):
        text = ATLAS.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^### (?:KR|US)\d\d ·", text, re.M)), 30)
        self.assertIn("실제 원문 아님", text)
        self.assertIn("NOT_LABELED", text)

    def test_hard_negatives_do_not_claim_ground_truth(self):
        text = ATLAS.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^\| N\d\d \|", text, re.M)), 12)
        for phrase in ("WARNING", "PAST_QUOTE", "INFORMATION", "AMBIGUOUS", "학습"):
            self.assertIn(phrase, text)

    def test_all_public_source_ids_have_https_urls(self):
        text = ATLAS.read_text(encoding="utf-8")
        urls = re.findall(r"\]\((https?://[^)]+)\)", text)
        self.assertGreaterEqual(len(urls), 45)
        self.assertTrue(all(u.startswith("https://") for u in urls))
        self.assertNotIn("http://xx", text)

    def test_no_unverified_accuracy_claim(self):
        text = ATLAS.read_text(encoding="utf-8")
        self.assertIn("정답 레이블", text)
        self.assertIn("독립", text)

    def test_new_scripts_served_and_display_only(self):
        html = HTML.read_text(encoding="utf-8")
        server = SERVER.read_text(encoding="utf-8")
        for script in ("ambient3d.js", "secondary.js", "research.js"):
            self.assertIn('src="/'+script+'"', html)
            self.assertIn("'/"+script+"':'"+script+"'", server)
        self.assertIn('id="ambient3d"', html)
        self.assertIn('aria-hidden="true"', html)

    def test_existing_3d_core_and_pipeline_preserved(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn('id="coreCanvas"', html)
        self.assertIn('id="stages"', html)
        self.assertIn('id="taskPanel"', html)
        self.assertIn('id="sheet"', html)
        for script in ("main.js", "visual.js"):
            self.assertIn('src="/'+script+'"', html)


if __name__ == "__main__":
    unittest.main()
