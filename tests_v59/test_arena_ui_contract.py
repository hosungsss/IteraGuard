"""v5.9 Arena UI: every element main.js needs exists, CSP-safe markup, presentation layer is read-only."""
import json
import re
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WEB = ROOT / 'arena' / 'web'
HTML = (WEB / 'index.html').read_text(encoding='utf-8')
MAIN = (WEB / 'main.js').read_text(encoding='utf-8')
VISUAL = (WEB / 'visual.js').read_text(encoding='utf-8')
IDS = set(re.findall(r'id="([^"]+)"', HTML))


class Markup(unittest.TestCase):
    def test_every_main_js_element_exists_once(self):
        needed = set(re.findall(r"""el\(\s*['"]([A-Za-z]+)['"]\s*\)""", MAIN))
        needed |= set(re.findall(r"""for \(const id of \[([^\]]+)\]""", MAIN) and
                      [x for group in re.findall(r"""for \(const id of \[([^\]]+)\]""", MAIN) for x in re.findall(r"'([A-Za-z]+)'", group)])
        self.assertTrue(needed)
        self.assertEqual(sorted(needed - IDS), [])
        dup = [i for i in IDS if len(re.findall(r'id="%s"' % re.escape(i), HTML)) > 1]
        self.assertEqual(dup, [])

    def test_sample_buttons_and_observation_values_preserved(self):
        self.assertEqual(set(re.findall(r'data-sample="([a-z]+)"', HTML)), {'direct', 'warning', 'ambiguous', 'followup'})
        self.assertEqual(re.findall(r'<option value="([A-Z_]+)"', HTML),
                         ['NOT_CHECKED', 'USER_REPORTS_CONFIRMED', 'USER_REPORTS_DENIED', 'UNRESOLVED'])

    def test_csp_safe_no_inline_script_style_or_external_asset(self):
        self.assertNotRegex(HTML, r'<script(?![^>]*\bsrc=)')
        self.assertNotIn('style=', HTML)
        self.assertNotIn('<style', HTML)
        self.assertNotRegex(HTML + VISUAL + (WEB / 'style.css').read_text(encoding='utf-8'), r'https?://')
        self.assertLess(HTML.index('/visual.js'), HTML.index('/main.js'))

    def test_visual_layer_never_writes_requests_or_decision_fields(self):
        # It may observe fetch, but must pass the original url/options through unchanged.
        self.assertIn('nativeFetch(url, options)', VISUAL)
        self.assertNotRegex(VISUAL, r"\$\('(action|message|reason|result|task|currentTurn|sessionNotice|modelNotice|evidence)'\)\.textContent\s*=")
        self.assertNotIn('localStorage', VISUAL)
        self.assertNotRegex(VISUAL, r'\.value\s*=(?!=)')

    def test_contextual_explanations_kept(self):
        for phrase in ('기관이 검증한 결과가 아니에요', '사기 확률이 아닙니다'):
            self.assertIn(phrase, HTML)


class Served(unittest.TestCase):
    def test_static_assets_served_with_csp(self):
        from arena.server import Handler
        from arena.store import Arena
        from integration import v51
        with tempfile.TemporaryDirectory() as d:
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            server.arena = Arena(Path(d) / 'a.db', client=object(), profile_id=v51.selected_profile())
            t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
            try:
                port = server.server_address[1]
                for path, ctype in (('/', 'text/html'), ('/main.js', 'text/javascript'), ('/visual.js', 'text/javascript'), ('/style.css', 'text/css')):
                    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', headers={'Host': f'127.0.0.1:{port}'})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        self.assertEqual(r.status, 200)
                        self.assertTrue(r.headers['Content-Type'].startswith(ctype))
                        self.assertIn("script-src 'self'", r.headers['Content-Security-Policy'])
                req = urllib.request.Request(f'http://127.0.0.1:{port}/../store.py', headers={'Host': f'127.0.0.1:{port}'})
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(req, timeout=10)
                self.assertEqual(cm.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()


if __name__ == '__main__':
    unittest.main()
