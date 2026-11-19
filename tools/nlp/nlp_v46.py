"""Python reference of the v4.6 on-device pipeline (the JS runtime apps/shared/dmsg-nlp.js must match it).

encoder (int8 weights, ONNX Runtime with dequantised initialisers) -> pooled 512
 -> heads (dmsg-nlp-heads/3): softmax tasks + sigmoid indicators, optional n-gram fusion
 -> uncertainty layer (Task E): per-task confidence, cross-task contradictions, out-of-distribution hints
 -> policy: model_bridge.advisory (speech/topic, v4.5 contract) -> model_bridge.indicator_advisory (v4.6)
 -> cross-task guard: a confident risky intent / requested action can never end as NO_STRONG_SIGNAL.
v4.5 heads (dmsg-nlp-heads/2) are also supported so the baseline runs through the same harness.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / 'dmsg'))
import electra_ref as R  # noqa: E402
from train_heads import ngram_vec, eojeol_spans, softmax, MAX_LEN, typed_raw as typed_raw_v45  # noqa: E402

V45_TO_V46_SPEECH = {'DIRECT_REQUEST': 'DIRECT_REQUEST', 'INDIRECT_REQUEST': 'INDIRECT_REQUEST', 'WARNING': 'WARNING_OR_NEGATION',
                     'QUOTATION': 'QUOTATION_OR_REPORT', 'INFORMATION': 'INFORMATIONAL'}
RISKY_INTENT = ('PAYMENT_SOLICITATION', 'CREDENTIAL_SOLICITATION')
RISKY_REQ = ('MONEY_TRANSFER', 'CREDENTIAL_DISCLOSURE', 'PERSONAL_DATA_DISCLOSURE', 'INSTALL_APPLICATION', 'CLICK_LINK',
             'MOVE_TO_EXTERNAL_MESSENGER', 'CONTACT_UNKNOWN_PERSON')
GUARD_P = 0.6


def sigmoid(z): return 1 / (1 + np.exp(-z))


def session_from_weights(onnx_path, W):
    import onnx, onnxruntime as ort
    from onnx import numpy_helper
    m = onnx.load(onnx_path)
    role = {'/embeddings_project/MatMul': 'embeddings_project.weight'}
    for i in range(R.LAYERS):
        p = f'/encoder/layer.{i}/'
        for a, b in (('attention/self/query', 'attention.self.query'), ('attention/self/key', 'attention.self.key'), ('attention/self/value', 'attention.self.value'),
                     ('attention/output/dense', 'attention.output.dense'), ('intermediate/dense', 'intermediate.dense'), ('output/dense', 'output.dense')):
            role[f'{p}{a}/MatMul'] = f'encoder.layer.{i}.{b}.weight'
    init = {t.name for t in m.graph.initializer}; src = {}
    for nd in m.graph.node:
        if nd.op_type == 'MatMul' and nd.name in role: src[[x for x in nd.input if x in init][0]] = role[nd.name]
    for t in m.graph.initializer:
        k = src.get(t.name, t.name)
        if k in W: t.CopyFrom(numpy_helper.from_array(np.asarray(W[k], np.float32), t.name))
    return ort.InferenceSession(m.SerializeToString())


def int8_weights(bin_path):
    return {k: R.dequant(v, k) for k, v in R.read_bin(Path(bin_path)).items()}


def pooled(sess, tok, texts, bs=32):
    out = np.zeros((len(texts), 512), np.float32)
    for i in range(0, len(texts), bs):
        enc = [tok.encode(t if t.strip() else '.').ids[:MAX_LEN - 1] for t in texts[i:i + bs]]
        enc = [e if e[-1] == 3 else e + [3] for e in enc]; L = max(len(e) for e in enc)
        ids = np.zeros((len(enc), L), np.int64); mask = np.zeros_like(ids)
        for j, e in enumerate(enc): ids[j, :len(e)] = e; mask[j, :len(e)] = 1
        h = sess.run(None, {'input_ids': ids, 'attention_mask': mask, 'token_type_ids': np.zeros_like(ids)})[0]
        out[i:i + len(enc)] = np.concatenate([h[:, 0], (h * mask[..., None]).sum(1) / mask.sum(1, keepdims=True)], 1)
    return out


class Heads:
    def __init__(self, path):
        self.j = json.loads(Path(path).read_text('utf8')); self.v = self.j['schema']
        if self.v == 'dmsg-nlp-heads/2':
            self.mu = np.array(self.j['mu'], np.float32); self.sd = np.array(self.j['sd'], np.float32)
        self.ng = self.j.get('ngram')

    def logits_parts(self, f, text):
        """Returns per-task (neural_logit, ngram_vec, ngram_W, b, T) so occlusion can recompute only the n-gram part."""
        g = ngram_vec(text)
        if self.v == 'dmsg-nlp-heads/2':
            z = (f - self.mu) / self.sd
            sp, ac = self.j['speech'], self.j['action']
            Ws, Wa = np.array(sp['W'], np.float32), np.array(ac['W'], np.float32)
            return {'speech': (Ws[:, :512] @ z, g, Ws[:, 512:] * self.ng['speech_weight'], np.array(sp['b']), sp['T'], sp['classes'], 'softmax'),
                    'topic': (np.zeros(len(ac['classes'])), g, Wa, np.array(ac['b']), ac['T'], ac['classes'], 'softmax')}
        out = {}
        for t, h in list(self.j['tasks'].items()) + [('indicators', self.j['indicators'])]:
            Wt = np.array(h['W'], np.float32)
            if h.get('features') == 'ngram':          # encoder-independent head (e.g. the v4.5 topic head)
                out[t] = (np.zeros(Wt.shape[0], np.float32), g, Wt, np.array(h['b'], np.float32), h['T'], h['classes'], h['type']); continue
            neural = Wt[:, :512] @ f
            Wg = Wt[:, 512:] * self.ng['fusion_weight'] if (self.ng and self.j.get('ngram_fused_heads', True)) else None
            out[t] = (neural, g if self.ng else None, Wg, np.array(h['b'], np.float32), h['T'], h['classes'], h['type'])
        return out

    @staticmethod
    def prob(part, g=None):
        neural, g0, Wg, b, T, cls, typ = part
        g = g0 if g is None else g
        z = neural + b + (Wg @ g if Wg is not None else 0)
        if typ == 'sigmoid': return sigmoid(z / np.array(T, np.float32))
        z = z / T; z = z - z.max(); e = np.exp(z); return e / e.sum()


def occlusion(part, text, k):
    """Word whose removal most lowers class k (n-gram part only; neural part fixed). None if no n-gram part."""
    if part[2] is None: return None
    sp = eojeol_spans(text)
    if not sp: return None
    base = Heads.prob(part)[k]; best = None
    for s, e in sp:
        q = Heads.prob(part, ngram_vec(text[:s] + text[e:]))[k]
        if best is None or base - q > best[0]: best = (base - q, s, e)
    if best is None or best[0] <= 0: return None
    return (best[1], best[2], text[best[1]:best[2]])


def analyze(text, f, heads: Heads, *, threshold=0.5, use_indicators=True, use_structural=True, use_spans=True, use_guard=True):
    from prototype.model_bridge import advisory, indicator_advisory, INDICATORS
    from prototype.typed_contract import ContractError
    parts = heads.logits_parts(f, text)
    P = {t: Heads.prob(p) for t, p in parts.items()}
    sp_cls = parts['speech'][5]
    if heads.v == 'dmsg-nlp-heads/2':
        ps45 = P['speech']; pa = P['topic']
        speech_v46 = {V45_TO_V46_SPEECH[c]: float(p) for c, p in zip(sp_cls, ps45)}
    else:
        speech_v46 = {c: float(p) for c, p in zip(sp_cls, P['speech'])}
        # v4.6 speech -> v4.5 5-class order expected by typed_raw_v45
        order = ['DIRECT_REQUEST', 'INDIRECT_REQUEST', 'WARNING_OR_NEGATION', 'QUOTATION_OR_REPORT', 'INFORMATIONAL']
        ps45 = np.array([speech_v46[c] for c in order]); pa = P['topic']
    topic_cls = parts['topic'][5]; top = topic_cls[int(np.argmax(pa))]
    anchor = occlusion(parts['topic'], text, int(np.argmax(pa))) if (text.strip() and use_spans and top != 'none') else None
    res = {'speech': speech_v46, 'topic': {c: float(p) for c, p in zip(topic_cls, pa)}}
    try:
        base = advisory(text, typed_raw_v45(ps45, pa), source='ON_DEVICE_NLP', threshold=threshold, model_anchor=anchor)
    except ContractError as e:
        return {**res, 'action': 'ASK_HUMAN', 'reason': 'CONTRACT_' + str(e), 'uncertainty': ['CONTRACT_ERROR']}
    final = base; unc = []
    if 'intent' in P:
        res['intent'] = {c: float(p) for c, p in zip(parts['intent'][5], P['intent'])}
        res['req_action'] = {c: float(p) for c, p in zip(parts['req_action'][5], P['req_action'])}
        ip = {c: float(p) for c, p in zip(INDICATORS, P['indicators'])}
        thr = {c: float(t) for c, t in zip(INDICATORS, heads.j['indicators']['threshold'])}
        threshold_guard = float(heads.j.get('guard_probability', GUARD_P))
        res['indicators'] = ip
        if use_indicators:
            spans = {}
            if use_spans:
                for j, c in enumerate(INDICATORS):
                    if ip[c] >= thr[c]:
                        s = occlusion(parts['indicators'], text, j)
                        if s: spans[c] = s
            if not use_structural:   # ablation: hide structural grounds by passing an empty-structure view
                from prototype import model_bridge as mb
                saved = mb.STRUCTURAL_GROUNDS; mb.STRUCTURAL_GROUNDS = {}
                try: final = indicator_advisory(text, base, ip, thresholds=thr, model_spans=spans)
                finally: mb.STRUCTURAL_GROUNDS = saved
            else:
                final = indicator_advisory(text, base, ip, thresholds=thr, model_spans=spans)
        # Task E: uncertainty
        mx = {t: float(np.max(P[t])) for t in ('speech', 'intent', 'req_action', 'topic')}
        if min(mx.values()) < 0.4: unc.append('LOW_TASK_CONFIDENCE')
        it = max(res['intent'], key=res['intent'].get); ra = max(res['req_action'], key=res['req_action'].get)
        sp = max(speech_v46, key=speech_v46.get)
        if sp in ('WARNING_OR_NEGATION', 'QUOTATION_OR_REPORT') and ra in RISKY_REQ and res['req_action'][ra] >= threshold_guard: unc.append('SPEECH_VS_REQUESTED_ACTION')
        if use_guard and final['action'] == 'NO_STRONG_SIGNAL' and sp not in ('WARNING_OR_NEGATION', 'QUOTATION_OR_REPORT'):
            if (it in RISKY_INTENT and res['intent'][it] >= threshold_guard) or (ra in RISKY_REQ and res['req_action'][ra] >= threshold_guard):
                from prototype.core import MESSAGES, Action
                final = dict(final, action='ASK_HUMAN', reason='CROSS_TASK_RISK_NOT_CLEARED', message=MESSAGES[Action.ASK_HUMAN]); unc.append('CROSS_TASK_RISK_NOT_CLEARED')
    return {**res, 'action': final['action'], 'reason': final['reason'], 'uncertainty': unc,
            'indicator_report': final.get('indicators', []), 'structural': final.get('structural_evidence', []), 'anchor': anchor}
