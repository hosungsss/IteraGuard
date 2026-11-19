"""WCAG 2.x contrast of the app's text tokens, read from apps/web/styles.css.

Text colors are composited over the light/dark glass card (glass alpha over page bg).
Fails (exit 1) if any small-text token is below 4.5:1. Approximation: backdrop blur and
the coloured background orbs are not modelled; screenshots are reviewed separately.
"""
import json, re, sys
from pathlib import Path
CSS = (Path(__file__).resolve().parents[1] / 'apps/web/styles.css').read_text('utf8')
light = CSS.split('@media (prefers-color-scheme: dark)')[0]
dark = CSS.split('@media (prefers-color-scheme: dark) {', 1)[1].split('}\n}', 1)[0]
def var(block, name):
    m = re.search(r'--' + re.escape(name) + r':\s*([^;]+);', block); return m.group(1).strip()
def color(v):
    if v.startswith('#'): return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)), 1.0
    n = [float(x) for x in re.findall(r'[\d.]+', v)]; return tuple(int(x) for x in n[:3]), n[3]
def over(fg, a, bg): return tuple(f * a + b * (1 - a) for f, b in zip(fg, bg))
def lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    r, g, b = map(f, c); return .2126 * r + .7152 * g + .0722 * b
def ratio(a, b): x, y = sorted((lum(a), lum(b)), reverse=True); return round((x + .05) / (y + .05), 2)
report, ok = {}, True
for name, block in (('light', light), ('dark', dark)):
    bg = color(var(block, 'bg-0'))[0]; g, ga = color(var(block, 'glass')); card = over(g, ga, bg)
    res = {}
    for tok in ('ink', 'ink-2', 'ink-3', 's-none', 's-caution', 's-pause', 's-ask', 'tint'):
        c, a = color(var(block, tok) if tok in block or name == 'light' else var(light, tok))
        res[tok] = ratio(over(c, a, card), card)
    res['white_on_btn1'] = ratio((255, 255, 255), color(var(block, 'btn-1'))[0]); res['white_on_btn2'] = ratio((255, 255, 255), color(var(block, 'btn-2'))[0])
    report[name] = res; ok &= all(v >= 4.5 for v in res.values())
print(json.dumps({'status': 'PASS' if ok else 'FAIL', 'min_required': 4.5, 'themes': report}, indent=1))
sys.exit(0 if ok else 1)
