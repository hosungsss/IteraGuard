"""Arena pipeline benchmark with controlled responses (no model). usage: python bench_arena.py REPO OUT.json N"""
import sys, json, tempfile, time, statistics, copy, cProfile, pstats, io
from pathlib import Path
repo = Path(sys.argv[1]); sys.path.insert(0, str(repo))
from arena.store import Arena
from integration import v51
cases = json.loads((repo/'tests_data/v51/execution_cases.json').read_text(encoding='utf-8'))
cases = [c for c in cases if c.get('raw')]
class C:
    def __init__(s): s.i = 0
    def infer(s, text, *, question_payload=None):
        r = cases[s.i % len(cases)]; s.i += 1; return copy.deepcopy(r['raw']), 0.
N = int(sys.argv[3])
with tempfile.TemporaryDirectory() as d:
    a = Arena(Path(d)/'b.db', client=C(), profile_id=v51.selected_profile())
    pipe, wall, actions = [], [], []
    sid = a.start()['session_id']; ver = 0
    for i in range(N):
        if ver >= 60:  # stay below the 64 open-task cap
            sid = a.start()['session_id']; ver = 0
        c = cases[i % len(cases)]
        t = time.perf_counter()
        r = a.evaluate(session_id=sid, version=ver, request_id='r%d' % i, text=c['text'], synthetic_only=True)
        wall.append((time.perf_counter() - t) * 1000); pipe.append(r['provenance']['pipeline_ms']); ver += 1
        actions.append((c['id'], r['current_turn_action'], r['action'], r['reason']))
    rt = []
    for _ in range(200):
        t = time.perf_counter(); a.read(sid); rt.append((time.perf_counter() - t) * 1000)
    pr = cProfile.Profile(); pr.enable()
    for i in range(50):
        sid2 = a.start()['session_id']
        a.evaluate(session_id=sid2, version=0, request_id='p%d' % i, text=cases[i % len(cases)]['text'], synthetic_only=True)
    pr.disable(); s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(14)
def q(x, p): x = sorted(x); return round(x[min(len(x)-1, int(round(p/100*len(x)+.5))-1)], 3)
out = {'n': N, 'cases': len(cases), 'evaluate_wall_ms': {'p50': q(wall, 50), 'p95': q(wall, 95), 'mean': round(statistics.mean(wall), 3)},
       'pipeline_ms': {'p50': q(pipe, 50), 'p95': q(pipe, 95)}, 'read_ms': {'p50': q(rt, 50), 'p95': q(rt, 95)}, 'actions': actions}
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != 'actions'}))
print(s.getvalue()[:3500])
