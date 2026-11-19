"""Dump normalized Arena results for every execution case + multi-turn sequences. usage: equiv.py REPO OUT"""
import sys, json, copy, tempfile, re
from pathlib import Path
repo = Path(sys.argv[1]); sys.path.insert(0, str(repo))
from arena.store import Arena
from integration import v51
from integration.v48 import bridge
cases = [c for c in json.loads((repo/'tests_data/v51/execution_cases.json').read_text(encoding='utf-8')) if c.get('raw')]
VOL = {'request_id','session_id','received_utc','pipeline_ms','latency_ms','id','manifest_fingerprint','execution_manifest','arena_sources',
       'profile_fingerprint','registry_fingerprint','question_binding','observed_task_id','resolved_retry_task_ids','input_fingerprint'}
def norm(x):
    if isinstance(x, dict): return {k: ('<v>' if k in VOL else norm(v)) for k, v in sorted(x.items())}
    if isinstance(x, list): return [norm(v) for v in x]
    if isinstance(x, str) and re.fullmatch(r'[0-9a-f]{32}', x): return '<hex32>'
    return x
class C:
    def __init__(s, seq): s.seq = list(seq)
    def infer(s, text, *, question_payload=None):
        r = s.seq.pop(0)
        if r is None: raise bridge.ModelUnavailable('MODEL_TRANSPORT_ERROR_TimeoutError')
        return copy.deepcopy(r), 0.
out = []
with tempfile.TemporaryDirectory() as d:
    for c in cases:  # single turn
        a = Arena(Path(d)/(c['id']+'.db'), client=C([c['raw']]), profile_id=v51.selected_profile()); sid = a.start()['session_id']
        out.append(norm(a.evaluate(session_id=sid, version=0, request_id='x', text=c['text'], synthetic_only=True)))
    for i in range(len(cases)):  # risky -> ordinary -> failure -> recovery
        seq = [cases[i]['raw'], cases[(i+3) % len(cases)]['raw'], None, cases[(i+3) % len(cases)]['raw']]
        texts = [cases[i]['text'], cases[(i+3) % len(cases)]['text'], cases[(i+3) % len(cases)]['text'], cases[(i+3) % len(cases)]['text']]
        a = Arena(Path(d)/('m%d.db' % i), client=C(seq), profile_id=v51.selected_profile()); sid = a.start()['session_id']
        for v, t in enumerate(texts):
            out.append(norm(a.evaluate(session_id=sid, version=v, request_id='m%d' % v, text=t, synthetic_only=True)))
        st = a.read(sid); out.append(norm({k: st[k] for k in ('version', 'prior_pause', 'lifecycle', 'open_task_count')}))
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True))
print(len(out))
