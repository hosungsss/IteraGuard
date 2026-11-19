"""PRD v3.3 §9 / System Prompting L2: user-facing text must not reassure, accuse, or claim real-world effects.
Scans every string a user can see (web shell, engine messages, NLP next-step text). Exit 1 on a hit.
Usage: python tools/check_forbidden_phrases.py [--json out.json]"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = [r'안전합니다', r'안전한\s*(?:통화|문자|메시지)입니다', r'정상\s*통화입니다', r'사기범입니다', r'보이스피싱으로\s*판정', r'사기로\s*판정',
             r'(?:계좌\s*동결|송금\s*차단|통화\s*종료)\s*(?:완료|했습니다)', r'사기\s*확률\s*\d', r'가족\s*암호를?\s*물어', r'100\s*%\s*(?:탐지|차단|안전)',
             r'피해를?\s*(?:막았|예방했)습니다']
FILES = ['apps/web/index.html', 'apps/web/app.js', 'apps/shared/dmsg-nlp.js', 'apps/shared/engine-data.js', 'dmsg/prototype/core.py', 'apps/shared/dmsg-linkguard.js', 'apps/shared/dmsg-apkscan.js', 'apps/shared/dmsg-domainintel.js', 'arena/web/index.html', 'arena/web/main.js', 'arena/store.py']
hits = []
for f in FILES:
    t = (ROOT / f).read_text('utf8')
    for pat in FORBIDDEN:
        for m in re.finditer(pat, t):
            hits.append({'file': f, 'pattern': pat, 'text': t[max(0, m.start() - 20):m.end() + 20]})
rep = {'status': 'PASS' if not hits else 'FAIL', 'files': FILES, 'patterns': len(FORBIDDEN), 'hits': hits}
if '--json' in sys.argv: Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(rep, ensure_ascii=False, indent=1), 'utf8')
print(json.dumps(rep, ensure_ascii=False, indent=1)); sys.exit(0 if not hits else 1)
