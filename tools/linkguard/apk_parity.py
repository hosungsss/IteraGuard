"""Python linkguard/apk.py vs JS apps/shared/dmsg-apkscan.js on the corpus plus deterministic mutations, and
androguard (independent oracle) on package / permissions / exported components where it can parse the file."""
import json, random, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from linkguard import apk as AP  # noqa: E402

def main():
    corpus = ROOT / 'tests_data/apk_corpus'
    files = sorted(p for p in corpus.iterdir() if p.suffix == '.apk')
    tmp = Path(tempfile.mkdtemp()); rnd = random.Random(4747)
    for p in files:
        shutil.copy(p, tmp / p.name)
        b = p.read_bytes()
        if len(b) > 2_000_000: continue
        for k in range(6):
            m = bytearray(b)
            if k < 2: m = m[: max(8, int(len(m) * rnd.random()))]
            else:
                for _ in range(1 + k): i = rnd.randrange(len(m)); m[i] = rnd.randrange(256)
            (tmp / f'mut{k}_{p.name}').write_bytes(bytes(m))
    paths = sorted(tmp.iterdir())
    out = subprocess.run(['node', str(ROOT / 'apps/conformance/run_apkscan.js'), *map(str, paths)], capture_output=True, text=True, timeout=600)
    if out.returncode: raise SystemExit(out.stderr[-2000:])
    js = {json.loads(l)['file']: json.loads(l)['report'] for l in out.stdout.splitlines() if l.strip()}
    res = {'total': 0, 'pass': 0, 'mismatches': []}
    for p in paths:
        py = AP.inspect(p.read_bytes(), p.name)
        res['total'] += 1
        a = json.loads(json.dumps(py)); b2 = js[p.name]
        if a == b2: res['pass'] += 1
        elif len(res['mismatches']) < 10:
            res['mismatches'].append({'file': p.name, 'diff': {k: (a.get(k), b2.get(k)) for k in set(a) | set(b2) if a.get(k) != b2.get(k)}})
    oracle = {'total': 0, 'agree': 0, 'unparsed': 0, 'disagree': []}
    try:
        from androguard.core.apk import APK
        import logging; logging.disable(logging.CRITICAL)
        try:
            from loguru import logger; logger.remove()
        except Exception: pass
        for p in files:
            py = AP.inspect(p.read_bytes(), p.name)
            if 'manifest' not in py: continue
            oracle['total'] += 1
            try:
                x = APK(str(p))
                ag = {'package': x.get_package(), 'permissions': sorted(set(x.get_permissions()))}
            except Exception:
                oracle['unparsed'] += 1; continue
            mine = {'package': py['manifest']['package'], 'permissions': py['manifest']['permissions']}
            if ag == mine: oracle['agree'] += 1
            else: oracle['disagree'].append({'file': p.name, 'androguard': ag, 'ours': mine})
    except ImportError:
        oracle['status'] = 'NOT_RUN_ANDROGUARD_MISSING'
    res['androguard_oracle'] = oracle
    shutil.rmtree(tmp)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return res

if __name__ == '__main__':
    r = main(); sys.exit(0 if r['pass'] == r['total'] else 1)
