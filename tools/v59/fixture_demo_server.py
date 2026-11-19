"""Local visual-QA server for the Arena UI. Responses are REPLAYED FIXTURES from tests_data/v51 (execution_source=CONTROLLED_CLIENT), NOT model inference. usage: python tools/v59/fixture_demo_server.py . 8791"""
import sys, json, copy, tempfile
from pathlib import Path
repo = Path(sys.argv[1]); sys.path.insert(0, str(repo))
from http.server import ThreadingHTTPServer
from arena.server import Handler
from arena.store import Arena
from integration import v51
from integration.v48 import bridge
cases = [c for c in json.loads((repo/'tests_data/v51/execution_cases.json').read_text(encoding='utf-8')) if c.get('raw')]
by_text = {c['text']: c['raw'] for c in cases}
class Fixture:
    def infer(self, text, *, question_payload=None):
        if text.startswith('FAIL'): raise bridge.ModelUnavailable('MODEL_TRANSPORT_ERROR_TimeoutError')
        raw = by_text.get(text) or cases[int(sys.argv[3]) if len(sys.argv) > 3 else 0]['raw']
        return copy.deepcopy(raw), 41.0
d = tempfile.mkdtemp()
arena = Arena(Path(d)/'demo.db', client=Fixture(), profile_id=v51.selected_profile())
port = int(sys.argv[2])
with ThreadingHTTPServer(('127.0.0.1', port), Handler) as s:
    s.arena = arena; print('ready', port, flush=True); s.serve_forever()
