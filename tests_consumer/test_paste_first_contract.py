"""Static and source-contract regression for the consumer paste-first surface.

These checks cannot establish real browser pixels, actual Zoro accuracy or
synthetic/PII detection. Existing Arena and Node contract suites run separately.
"""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "arena/web/index.html"
CSS = ROOT / "arena/web/style.css"
MAIN = ROOT / "arena/web/main.js"
VISUAL = ROOT / "arena/web/visual.js"
CHAT = ROOT / "arena/web/chat.js"


class DOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.by_id = {}
        self.classes = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.by_id[d["id"]] = (tag, d)
        if "class" in d:
            self.classes.append((tag, d))


class ConsumerUXContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.visual = VISUAL.read_text(encoding="utf-8")
        cls.chat = CHAT.read_text(encoding="utf-8")
        cls.dom = DOM()
        cls.dom.feed(cls.html)

    def test_initial_textarea_is_empty_not_preapproved_fixture(self):
        self.assertRegex(self.html, r'<textarea id="text"[^>]*></textarea>')
        self.assertIn('id="pastePrivacy"', self.html)
        self.assertIn("합성·비식별 테스트 전용", self.html)

    def test_paste_review_action_exists(self):
        self.assertIn('id="run"', self.html)
        self.assertIn("판단하기", self.html)
        self.assertIn("if (!el('text').value.trim())", self.main)
        self.assertIn("el('text').focus()", self.main)

    def test_internal_panels_inert_hidden_from_consumer(self):
        for uid in ("taskPanel",):
            name, attrs = self.dom.by_id[uid]
            self.assertEqual(name, "section")
            self.assertIn("hidden", attrs)
            self.assertIn("inert", attrs)
        for class_name in ("reference-panel", "secondary-lab"):
            matches = [attrs for tag, attrs in self.dom.classes
                       if tag == "section" and class_name in attrs.get("class", "").split()]
            self.assertEqual(len(matches), 1, class_name)
            self.assertIn("hidden", matches[0])
            self.assertIn("inert", matches[0])
        self.assertRegex(self.css, r":where\(\[hidden\]\)\s*\{display:none!important\}")

    def test_internal_experiment_not_automatically_sent_to_paid_jev(self):
        # Source-level only; server verifies authorization independently.
        self.assertNotIn("'/api/secondary/check'", self.main)
        self.assertNotIn("'/api/secondary/check'", self.visual)
        self.assertNotIn("'/api/secondary/check'", self.chat)
        self.assertIn('id="jevConsent"', self.html)

    def test_transient_progress_is_hidden_idle(self):
        _, attrs = self.dom.by_id["pipelinePanel"]
        self.assertIn("hidden", attrs)
        self.assertIn('body.dataset.phase = "running"', self.visual.replace("'", '"'))
        self.assertIn("panel.hidden = false", self.visual)
        self.assertIn("panel.hidden = true", self.visual)
        self.assertIn("서버의 판단 응답을 기다리는 중", self.visual)
        self.assertNotIn("steps.forEach((fn, i) => later(fn", self.visual)
        self.assertIn("실제 진행률은 제공되지", self.visual)

    def test_verdict_is_displayed_only_after_actual_result_or_error(self):
        _, attrs = self.dom.by_id["verdictPanel"]
        self.assertIn("hidden", attrs)
        self.assertIn("el('verdictPanel').hidden = false", self.main)
        self.assertIn("el('verdictPanel').hidden = true", self.main)
        self.assertIn("대신 확인하지는 않습니다", self.main)
        self.assertIn("nextAction", self.dom.by_id)
        self.assertIn("d.next_task.instruction", self.main)
        self.assertIn("el('nextAction').hidden = !next", self.main)

    def test_chat_panel_not_visible_before_decision(self):
        _, attrs = self.dom.by_id["conversationPanel"]
        self.assertIn("hidden", attrs)
        self.assertIn("if (panel) panel.hidden = true", self.chat)
        self.assertIn("if (panel) panel.hidden = false", self.chat)
        self.assertIn("RULE_BASED_FOLLOWUP_NOT_GENERATIVE", self.chat)
        self.assertIn("규칙 기반 안내", self.chat)

    def test_original_core_and_privacy_survive(self):
        for id_ in ("coreCanvas", "text", "review", "run", "sessionHistory",
                    "taskQueue", "conversationFeed", "followupText", "ambient3d"):
            self.assertIn(id_, self.dom.by_id)
        self.assertNotIn("<script src=\"https://", self.html)
        self.assertIn("실제 계좌번호", self.html)
        self.assertIn("안전 보증", self.html)


if __name__ == "__main__":
    unittest.main()
