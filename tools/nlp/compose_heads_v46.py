"""Compose shipped v4.6 heads: fine-tuned heads + (optionally) the v4.5 n-gram topic head, which is
encoder-independent and therefore still valid after the encoder's top layers are fine-tuned.
Usage: python tools/nlp/compose_heads_v46.py <finetuned heads.json> <v4.5 dmsg_nlp_heads.json> <out.json> [--keep-new-topic]"""
import json, sys, hashlib
a, b, out = sys.argv[1:4]
h = json.load(open(a)); v45 = json.load(open(b))
if '--keep-new-topic' not in sys.argv:
    ac = v45['action']
    h['tasks']['topic'] = {'type': 'softmax', 'features': 'ngram', 'classes': ac['classes'], 'W': ac['W'], 'b': ac['b'], 'T': ac['T'],
                           'origin': 'v4.5 action head (hashed char n-gram LR), sha256 of v4.5 heads ' + hashlib.sha256(open(b, 'rb').read()).hexdigest()}
    if h.get('ngram') is None:
        h['ngram'] = dict(v45['ngram'], fusion_weight=0.5); h['ngram'].pop('speech_weight', None); h['ngram_fused_heads'] = False
h['threshold'] = 0.5          # advisory threshold, same calibration-split procedure as v4.5
h['guard_probability'] = 0.6  # cross-task guard (nlp_v46.GUARD_P)
json.dump(h, open(out, 'w'), separators=(',', ':'))
print(out, hashlib.sha256(open(out, 'rb').read()).hexdigest())
