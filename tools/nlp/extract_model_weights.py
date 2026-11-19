"""Recover the shipped int8 weights (models/v46/*.bin layout) from apps/shared/nlp/dmsg-nlp-weights.js and verify SHA-256.
Usage: python tools/nlp/extract_model_weights.py <out.bin>"""
import base64, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
js = (ROOT / 'apps/shared/nlp/dmsg-nlp-weights.js').read_text('ascii')
b = base64.b64decode(js.split('"', 2)[1])
man = json.loads((ROOT / 'apps/shared/nlp/NLP_ASSETS_MANIFEST.json').read_text('utf8'))
h = hashlib.sha256(b).hexdigest()
if h != man['weights_sha256']: raise SystemExit('SHA256_MISMATCH ' + h)
Path(sys.argv[1]).write_bytes(b); print(json.dumps({'bytes': len(b), 'sha256': h}))
