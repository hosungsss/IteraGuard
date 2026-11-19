"""Package the on-device NLP assets as plain JS files (works under file:// in WebView/desktop).
Usage: python tools/nlp/build_nlp_assets.py <weights.bin> <vocab.txt> <dmsg_nlp_heads.json> <outdir>"""
import base64, hashlib, json, sys
from pathlib import Path
wb, vocab, heads, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
w = wb.read_bytes(); h = heads.read_bytes(); v = vocab.read_text('utf8').split('\n')
v = v[:-1] if v and v[-1] == '' else v
assert len(v) == 35000, len(v)
(out / 'dmsg-nlp-weights.js').write_text('self.DMSG_NLP_WEIGHTS_B64="' + base64.b64encode(w).decode() + '";\n', 'ascii')
(out / 'dmsg-nlp-vocab.js').write_text('self.DMSG_NLP_VOCAB=' + json.dumps(v, ensure_ascii=False) + ';\n', 'utf8')
(out / 'dmsg-nlp-heads.js').write_text('self.DMSG_NLP_HEADS=' + h.decode('utf8') + ';\nself.DMSG_NLP_HEADS_SHA256="' + hashlib.sha256(h).hexdigest() + '";\n', 'utf8')
man = {'weights_sha256': hashlib.sha256(w).hexdigest(), 'weights_bytes': len(w), 'vocab_sha256': hashlib.sha256(vocab.read_bytes()).hexdigest(),
       'heads_sha256': hashlib.sha256(h).hexdigest(), 'files': {}}
for f in ('dmsg-nlp-weights.js', 'dmsg-nlp-vocab.js', 'dmsg-nlp-heads.js'):
    b = (out / f).read_bytes(); man['files'][f] = {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
(out / 'NLP_ASSETS_MANIFEST.json').write_text(json.dumps(man, indent=1), 'utf8')
print(json.dumps(man, indent=1))
