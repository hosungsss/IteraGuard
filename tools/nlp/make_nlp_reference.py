"""Python reference outputs for the JS on-device NLP parity test (tools/nlp/nlp_parity.js); v4.5 and v4.6 heads.
Usage: python tools/nlp/make_nlp_reference.py <enc_fp32.onnx> <weights_int8.bin> <tokenizer.json> <heads.json> <out.json>"""
import json, sys, random
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nlp_v46 as N, electra_ref as R
from train_heads import ngram_vec, MAX_LEN
from tokenizers import Tokenizer
enc, wb, tj, hj, out = sys.argv[1:6]
tok = Tokenizer.from_file(tj); W = N.int8_weights(wb); sess = N.session_from_weights(enc, W); heads = N.Heads(hj)
load = lambda p: [json.loads(l)['text'] for l in Path(p).read_text('utf8').splitlines() if l.strip()]
texts = load(HERE / 'locked_handwritten.jsonl') + load(HERE / 'locked_handwritten_v2.jsonl') + load(HERE / 'locked_v46_multitask.jsonl')
edge = ['', ' ', 'ㅇㅇ', 'A', '송금', '😀 이모지 🙏🏻 섞인 문장', 'Ｆｕｌｌｗｉｄｔｈ ＡＢＣ', '中文汉字와 한글', 'İstanbul ǅ ß',
        '탭\t줄바꿈\n캐리지\r', '​제로폭‍결합', '가' * 300, 'a' * 120, '...!!!???', 'kb-star-bank.co/login?id=1',
        '지금 바로 송금하세요. 송금하지 마세요라고 했다.', 'Please send OTP now', '　전각공백 nbsp', '라인 아이디 abc_123 으로 연락 주세요 50만원']
rnd = random.Random(46); frags = ['송금', '하세요', '하지 마', '라고 했다', '인증번호', '링크', ' ', '!', '?', '고객님', '😀', 'OTP', '앱을 깔아', '주세요', '.', '\n', '라인', 'sora_09', '[국제발신]', '만나요', '30만원']
texts += edge + [''.join(rnd.choice(frags) for _ in range(rnd.randint(1, 14))) for _ in range(60)]
V = []
for i, t in enumerate(texts):
    tt = t if t.strip() else '.'
    ids = tok.encode(tt).ids[:MAX_LEN - 1]; ids = ids if ids[-1] == 3 else ids + [3]
    f = N.pooled(sess, tok, [tt])[0]
    rec = {'text': t, 'ids': ids, 'pooled_ort': [round(float(x), 6) for x in f]}
    if i < 30: rec['pooled_numpy'] = [round(float(x), 6) for x in R.pooled(R.forward(W, ids))]
    if heads.ng:
        g = ngram_vec(t); rec['ngram_nonzero'] = {str(int(j)): round(float(g[j]), 6) for j in np.nonzero(g)[0]}
    if t.strip():
        o = N.analyze(t, N.pooled(sess, tok, [tt])[0], heads)
        rec['probs'] = {k: {c: round(float(p), 6) for c, p in o[k].items()} for k in ('speech', 'topic', 'intent', 'req_action', 'indicators') if k in o}
        rec['policy'] = [o['action'], o['reason']]; rec['anchor'] = list(o['anchor']) if o['anchor'] else None; rec['uncertainty'] = o['uncertainty']
    else:
        rec['policy'] = ['ASK_HUMAN', 'EMPTY']
    V.append(rec)
Path(out).write_text(json.dumps({'n': len(V), 'schema': heads.v, 'vectors': V}, ensure_ascii=False), 'utf8')
print(len(V))
