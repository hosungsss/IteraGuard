/* IteraGuard / 의심계 v4.5 — on-device Korean NLP (no network, no API key).
 *
 * KoELECTRA-small-v3 discriminator encoder (int8 weights, pure JavaScript forward pass)
 *   -> [CLS ; mean] 512-d features -> speech-act head (encoder features + char n-grams)
 * char 1-3 gram hashed features -> action-category head (lexical; NOT deep semantics)
 * -> typed System One contract -> the existing advisory policy (dmsg-engine.js).
 *
 * The model output is an advisory label. It is never a fraud determination, never a
 * safety clearance, and never an instruction to transfer, freeze or open anything.
 * Python reference: tools/nlp/electra_ref.py + tools/nlp/train_heads.py (parity-tested).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DmsgNLP = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var H = 256, HEADS = 4, LAYERS = 12, EMB = 128, FF = 1024, EPS = 1e-12, MAX_LEN = 128;
  var SPEECH = ['DIRECT_REQUEST', 'INDIRECT_REQUEST', 'WARNING', 'QUOTATION', 'INFORMATION'];
  var ACTION = ['transfer', 'otp', 'remote_install', 'personal_data', 'link', 'secrecy', 'none'];

  // ---------- Python-compatible character classes ----------
  var PY_SPACE = new Set([9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004,
    0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000]);
  // Rust char::is_whitespace (Unicode White_Space) — used by the HF BERT normalizer / pre-tokenizer.
  var RS_SPACE = new Set([9, 10, 11, 12, 13, 32, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006,
    0x2007, 0x2008, 0x2009, 0x200a, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000]);
  var RX_OTHER = /\p{C}/u, RX_PUNCT = /\p{P}/u;
  function isAsciiPunct(c) { return (c >= 33 && c <= 47) || (c >= 58 && c <= 64) || (c >= 91 && c <= 96) || (c >= 123 && c <= 126); }
  function isCJK(c) {
    return (c >= 0x4E00 && c <= 0x9FFF) || (c >= 0x3400 && c <= 0x4DBF) || (c >= 0x20000 && c <= 0x2A6DF) || (c >= 0x2A700 && c <= 0x2B73F) ||
      (c >= 0x2B740 && c <= 0x2B81F) || (c >= 0x2B820 && c <= 0x2CEAF) || (c >= 0xF900 && c <= 0xFAFF) || (c >= 0x2F800 && c <= 0x2FA1F);
  }

  // ---------- WordPiece tokenizer (HF BertNormalizer(clean_text, chinese chars, no lowercase) + BertPreTokenizer) ----------
  function Tokenizer(vocabList) {
    this.vocab = new Map(); for (var i = 0; i < vocabList.length; i++) this.vocab.set(vocabList[i], i);
    this.unk = this.vocab.get('[UNK]'); this.cls = this.vocab.get('[CLS]'); this.sep = this.vocab.get('[SEP]');
  }
  Tokenizer.prototype.normalize = function (text) {
    var out = '';
    for (var ch of text) {
      var c = ch.codePointAt(0);
      if (c === 0 || c === 0xFFFD) continue;
      if (c !== 9 && c !== 10 && c !== 13 && RX_OTHER.test(ch)) continue;
      if (RS_SPACE.has(c)) { out += ' '; continue; }
      out += isCJK(c) ? ' ' + ch + ' ' : ch;
    }
    return out;
  };
  Tokenizer.prototype.preTokenize = function (text) {
    var words = [], cur = '';
    for (var ch of text) {
      var c = ch.codePointAt(0);
      if (RS_SPACE.has(c)) { if (cur) words.push(cur); cur = ''; }
      else if (isAsciiPunct(c) || RX_PUNCT.test(ch)) { if (cur) words.push(cur); words.push(ch); cur = ''; }
      else cur += ch;
    }
    if (cur) words.push(cur);
    return words;
  };
  Tokenizer.prototype.wordpiece = function (word, out) {
    var cps = Array.from(word);
    if (cps.length > 100) { out.push(this.unk); return; }
    var start = 0, pieces = [];
    while (start < cps.length) {
      var end = cps.length, found = -1;
      while (start < end) {
        var sub = cps.slice(start, end).join(''); if (start > 0) sub = '##' + sub;
        var id = this.vocab.get(sub);
        if (id !== undefined) { found = id; break; }
        end--;
      }
      if (found < 0) { out.push(this.unk); return; }
      pieces.push(found); start = end;
    }
    for (var p of pieces) out.push(p);
  };
  Tokenizer.prototype.encode = function (text) {
    var ids = [this.cls], words = this.preTokenize(this.normalize(text));
    for (var w of words) this.wordpiece(w, ids);
    ids.push(this.sep);
    if (ids.length > MAX_LEN) { ids = ids.slice(0, MAX_LEN - 1); ids.push(this.sep); }
    return ids;
  };

  // ---------- weights (DMSGNLP1 container, see electra_ref.write_bin) ----------
  function readBin(buf) {
    var u8 = new Uint8Array(buf), magic = String.fromCharCode.apply(null, u8.subarray(0, 8));
    if (magic !== 'DMSGNLP1') throw new Error('NLP_WEIGHTS_BAD_MAGIC');
    var hl = new DataView(buf).getUint32(8, true);
    var header = JSON.parse(new TextDecoder().decode(u8.subarray(12, 12 + hl))), base = 12 + hl, T = {};
    Object.keys(header.tensors).forEach(function (k) {
      var e = header.tensors[k], n = e.shape.reduce(function (a, b) { return a * b; }, 1);
      var data = e.dtype === 'i8' ? new Int8Array(buf, base + e.offset, n) : new Float32Array(buf.slice(base + e.offset, base + e.offset + n * 4));
      var scale = e.scale_offset !== undefined ? new Float32Array(buf.slice(base + e.scale_offset, base + e.scale_offset + e.scale_len * 4)) : null;
      T[k] = { dtype: e.dtype, shape: e.shape, data: data, scale: scale, axis: e.scale_axis };
    });
    return T;
  }
  // Linear layer: stored [in, out] int8 with per-output scale. Transposed once to [out, in] for contiguous dot products.
  function makeLinear(T, wname, bname) {
    var w = T[wname], b = T[bname].data, nin = w.shape[0], nout = w.shape[1], t = new Int8Array(nin * nout);
    for (var i = 0; i < nin; i++) for (var j = 0; j < nout; j++) t[j * nin + i] = w.data[i * nout + j];
    return { nin: nin, nout: nout, w: t, s: w.scale, b: b };
  }
  function linear(L, x, rows, out) {
    var nin = L.nin, nout = L.nout, w = L.w, s = L.s, b = L.b;
    for (var r = 0; r < rows; r++) {
      var xo = r * nin, oo = r * nout;
      for (var j = 0; j < nout; j++) {
        var acc = 0, wo = j * nin;
        for (var i = 0; i < nin; i++) acc += x[xo + i] * w[wo + i];
        out[oo + j] = acc * s[j] + b[j];
      }
    }
    return out;
  }
  function layerNorm(x, rows, n, g, b) {
    for (var r = 0; r < rows; r++) {
      var o = r * n, mu = 0, v = 0, i;
      for (i = 0; i < n; i++) mu += x[o + i]; mu /= n;
      for (i = 0; i < n; i++) { var d = x[o + i] - mu; v += d * d; } v /= n;
      var inv = 1 / Math.sqrt(v + EPS);
      for (i = 0; i < n; i++) x[o + i] = (x[o + i] - mu) * inv * g[i] + b[i];
    }
  }
  function erf(x) { // Abramowitz-Stegun 7.1.26 refined (W. J. Cody style) — |err| < 1.2e-7
    var s = x < 0 ? -1 : 1; x = Math.abs(x);
    var t = 1 / (1 + 0.5 * x);
    var y = 1 - t * Math.exp(-x * x - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 +
      t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
    return s * y;
  }

  function Encoder(T) {
    this.word = T['embeddings.word_embeddings.weight']; this.pos = T['embeddings.position_embeddings.weight'].data;
    this.tt = T['embeddings.token_type_embeddings.weight'].data;
    this.lnE = [T['embeddings.LayerNorm.weight'].data, T['embeddings.LayerNorm.bias'].data];
    this.proj = makeLinear(T, 'embeddings_project.weight', 'embeddings_project.bias');
    this.layers = [];
    for (var i = 0; i < LAYERS; i++) {
      var p = 'encoder.layer.' + i + '.';
      this.layers.push({
        q: makeLinear(T, p + 'attention.self.query.weight', p + 'attention.self.query.bias'),
        k: makeLinear(T, p + 'attention.self.key.weight', p + 'attention.self.key.bias'),
        v: makeLinear(T, p + 'attention.self.value.weight', p + 'attention.self.value.bias'),
        o: makeLinear(T, p + 'attention.output.dense.weight', p + 'attention.output.dense.bias'),
        ln1: [T[p + 'attention.output.LayerNorm.weight'].data, T[p + 'attention.output.LayerNorm.bias'].data],
        f1: makeLinear(T, p + 'intermediate.dense.weight', p + 'intermediate.dense.bias'),
        f2: makeLinear(T, p + 'output.dense.weight', p + 'output.dense.bias'),
        ln2: [T[p + 'output.LayerNorm.weight'].data, T[p + 'output.LayerNorm.bias'].data]
      });
    }
  }
  Encoder.prototype.forward = function (ids) {
    var L = ids.length, e = new Float32Array(L * EMB), wd = this.word.data, ws = this.word.scale, i, j;
    for (i = 0; i < L; i++) {
      var id = ids[i], sc = ws[id];
      for (j = 0; j < EMB; j++) e[i * EMB + j] = wd[id * EMB + j] * sc + this.pos[i * EMB + j] + this.tt[j];
    }
    layerNorm(e, L, EMB, this.lnE[0], this.lnE[1]);
    var x = linear(this.proj, e, L, new Float32Array(L * H));
    var q = new Float32Array(L * H), k = new Float32Array(L * H), v = new Float32Array(L * H), ctx = new Float32Array(L * H),
      a = new Float32Array(L * H), f = new Float32Array(L * FF), f2 = new Float32Array(L * H), sc2 = new Float32Array(L), dh = H / HEADS,
      inv = 1 / Math.sqrt(dh);
    for (var li = 0; li < LAYERS; li++) {
      var Ly = this.layers[li];
      linear(Ly.q, x, L, q); linear(Ly.k, x, L, k); linear(Ly.v, x, L, v);
      for (var h = 0; h < HEADS; h++) {
        var ho = h * dh;
        for (i = 0; i < L; i++) {
          var mx = -Infinity, t, d;
          for (j = 0; j < L; j++) {
            var s = 0; for (d = 0; d < dh; d++) s += q[i * H + ho + d] * k[j * H + ho + d];
            s *= inv; sc2[j] = s; if (s > mx) mx = s;
          }
          var sum = 0; for (j = 0; j < L; j++) { t = Math.exp(sc2[j] - mx); sc2[j] = t; sum += t; }
          for (d = 0; d < dh; d++) {
            var acc = 0; for (j = 0; j < L; j++) acc += sc2[j] * v[j * H + ho + d];
            ctx[i * H + ho + d] = acc / sum;
          }
        }
      }
      linear(Ly.o, ctx, L, a);
      for (i = 0; i < L * H; i++) x[i] += a[i];
      layerNorm(x, L, H, Ly.ln1[0], Ly.ln1[1]);
      linear(Ly.f1, x, L, f);
      for (i = 0; i < L * FF; i++) { var z = f[i]; f[i] = 0.5 * z * (1 + erf(z * Math.SQRT1_2)); }
      linear(Ly.f2, f, L, f2);
      for (i = 0; i < L * H; i++) x[i] += f2[i];
      layerNorm(x, L, H, Ly.ln2[0], Ly.ln2[1]);
    }
    return x;
  };
  function pooled(x, L) {
    var out = new Float32Array(2 * H), i, j;
    for (j = 0; j < H; j++) out[j] = x[j];
    for (i = 0; i < L; i++) for (j = 0; j < H; j++) out[H + j] += x[i * H + j];
    for (j = 0; j < H; j++) out[H + j] /= L;
    return out;
  }

  // ---------- char n-gram features (mirrors train_heads.ngram_vec) ----------
  var CRC = (function () { var t = new Uint32Array(256); for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  var ENC = new TextEncoder();
  function crc32(str) { var b = ENC.encode(str), c = 0xFFFFFFFF; for (var i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function stripPySpace(text) { var o = ''; for (var ch of text) if (!PY_SPACE.has(ch.codePointAt(0))) o += ch; return o; }
  function ngramVec(text, cfg) {
    var cps = Array.from(' ' + stripPySpace(text.toLowerCase()) + ' '), v = new Float32Array(cfg.buckets);
    for (var n of cfg.n) for (var i = 0; i + n <= cps.length; i++) v[crc32(cps.slice(i, i + n).join('')) % cfg.buckets] += 1;
    for (var j = 0; j < v.length; j++) v[j] = Math.log1p(v[j]);
    return v;
  }
  function headProbs(head, x) {
    var W = head.W, b = head.b, n = W.length, z = new Array(n), mx = -Infinity, i;
    for (i = 0; i < n; i++) { var s = b[i], w = W[i]; for (var j = 0; j < x.length; j++) s += w[j] * x[j]; z[i] = s / head.T; if (z[i] > mx) mx = z[i]; }
    var sum = 0; for (i = 0; i < n; i++) { z[i] = Math.exp(z[i] - mx); sum += z[i]; }
    for (i = 0; i < n; i++) z[i] /= sum;
    return z;
  }
  function wordSpans(text) { // code-point spans of maximal non-(Python)-whitespace runs
    var cps = Array.from(text), out = [], s = -1;
    for (var i = 0; i <= cps.length; i++) {
      var sp = i === cps.length || PY_SPACE.has(cps[i].codePointAt(0));
      if (!sp && s < 0) s = i; else if (sp && s >= 0) { out.push([s, i]); s = -1; }
    }
    return { cps: cps, spans: out };
  }
  function typedRaw(ps, pa) {
    var s = {}, a = {}; SPEECH.forEach(function (k, i) { s[k] = ps[i]; }); ACTION.forEach(function (k, i) { a[k] = pa[i]; });
    var act = {}; ACTION.forEach(function (k) { act[k] = a[k]; }); act.unclear = 0;
    var present = 1 - a.none, req = s.DIRECT_REQUEST + s.INDIRECT_REQUEST;
    var sp = { direct_request: req * present, reported_or_quoted: s.QUOTATION, negated_or_warning: s.WARNING, unclear: 0, informational: s.INFORMATION + req * a.none };
    return { answers: { q_action: { type: 'choice', probabilities: act }, q_speech: { type: 'choice', probabilities: sp },
      q_scam: { type: 'noul', noul: req * present }, q_pressure: { type: 'noul', noul: req * present } } };
  }

  var SAFE_NEXT = {
    PAUSE_AND_VERIFY: '송금·인증번호 입력·앱 설치를 잠시 멈추고, 공식 대표번호로 직접 다시 확인하세요.',
    CAUTION: '링크를 누르거나 회신하기 전에 보낸 곳을 공식 경로로 확인하세요.',
    ASK_HUMAN: '자동 판단이 불확실합니다. 가족·은행 공식 창구 등 사람에게 함께 확인해 보세요.',
    NO_STRONG_SIGNAL: '강한 위험 신호는 찾지 못했지만 안전 판정은 아닙니다. 평소처럼 출처를 확인하세요.'
  };
  var UNCERTAINTY = {
    MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS: '모델 확신도가 기준보다 낮음', UNGROUNDED_RISK_INDICATOR: '모델이 위험 신호를 봤지만 원문에서 구조적 근거를 찾지 못함',
    CROSS_TASK_RISK_NOT_CLEARED: '다른 판단(의도·요청 행동)이 위험을 가리켜 해제하지 않음', NO_GROUNDED_ACTION_ANCHOR: '근거 구간을 찾지 못함',
    MODEL_NONE_BUT_ACTION_TERMS_PRESENT: '모델 판단과 문장 속 행동 단어가 충돌', CONFLICTING_MODEL_QUESTIONS: '모델 질문 간 판단 충돌'
  };

  var V46_SPEECH_TO_V45 = ['DIRECT_REQUEST', 'INDIRECT_REQUEST', 'WARNING_OR_NEGATION', 'QUOTATION_OR_REPORT', 'INFORMATIONAL'];
  var RISKY_INTENT = ['PAYMENT_SOLICITATION', 'CREDENTIAL_SOLICITATION'];
  var RISKY_REQ = ['MONEY_TRANSFER', 'CREDENTIAL_DISCLOSURE', 'PERSONAL_DATA_DISCLOSURE', 'INSTALL_APPLICATION', 'CLICK_LINK', 'MOVE_TO_EXTERNAL_MESSENGER', 'CONTACT_UNKNOWN_PERSON'];
  function argmax(a) { var b = 0; for (var i = 1; i < a.length; i++) if (a[i] > a[b]) b = i; return b; }
  function dot(w, x, off) { var s = 0; for (var j = 0; j < x.length; j++) s += w[(off || 0) + j] * x[j]; return s; }

  function Model(assets, engine) {
    if (!assets || !assets.weights || !assets.vocab || !assets.heads) throw new Error('MODEL_UNAVAILABLE');
    this.E = engine; this.heads = assets.heads; this.schema = assets.heads.schema; this.tok = new Tokenizer(assets.vocab);
    this.enc = new Encoder(readBin(assets.weights));
    var prov = assets.heads.provenance || {};
    this.model_id = this.schema === 'dmsg-nlp-heads/3' ? 'koelectra-small-v3-ft' + (assets.heads.encoder_trainable_top_layers || '') + '-int8+dmsg-multitask' : 'koelectra-small-v3-int8+dmsg-heads';
    this.model_revision = ((prov.weights_int8_sha256 || prov.encoder_weights_sha256 || '').slice(0, 16)) + '/' + (assets.heads_sha256 || 'unknown').slice(0, 16);
    if (this.schema !== 'dmsg-nlp-heads/3') { this.mu = Float32Array.from(assets.heads.mu); this.sd = Float32Array.from(assets.heads.sd); }
    this.threshold = typeof assets.heads.threshold === 'number' ? assets.heads.threshold : 0.5;
    this.guardP = typeof assets.heads.guard_probability === 'number' ? assets.heads.guard_probability : 0.6;
    // v4.7: 'dra' = decision-relevant arbiter (expected-cost choice); 'v46' = previous threshold/veto advisory
    this.arbiter = assets.arbiter === 'v46' ? 'v46' : 'dra';
  }
  Model.prototype.features = function (text) {
    var ids = this.tok.encode(text.trim() ? text : '.'), x = this.enc.forward(ids), p = pooled(x, ids.length);
    if (this.mu) for (var i = 0; i < p.length; i++) p[i] = (p[i] - this.mu[i]) / this.sd[i];
    return { ids: ids, z: p };
  };
  // Returns per-task "parts": the neural logit is fixed, the n-gram part can be recomputed for occlusion.
  Model.prototype.parts = function (text, feat) {
    var H = this.heads, cfg = H.ngram, g = cfg ? ngramVec(text, cfg) : null, out = {};
    if (this.schema !== 'dmsg-nlp-heads/3') {
      var sp = H.speech, ac = H.action, sw = cfg.speech_weight;
      out.speech = { classes: sp.classes, type: 'softmax', T: sp.T, b: sp.b, neural: sp.W.map(function (w) { return dot(w, feat.z, 0); }), Wg: sp.W.map(function (w) { return w.slice(512).map(function (v) { return v * sw; }); }), g: g };
      out.topic = { classes: ac.classes, type: 'softmax', T: ac.T, b: ac.b, neural: ac.W.map(function () { return 0; }), Wg: ac.W, g: g };
      return out;
    }
    var fused = !!cfg && H.ngram_fused_heads !== false;
    var tasks = Object.keys(H.tasks).map(function (k) { return [k, H.tasks[k]]; }).concat([['indicators', H.indicators]]);
    tasks.forEach(function (kv) {
      var t = kv[0], h = kv[1];
      if (h.features === 'ngram') { out[t] = { classes: h.classes, type: h.type, T: h.T, b: h.b, neural: h.W.map(function () { return 0; }), Wg: h.W, g: g }; return; }
      out[t] = { classes: h.classes, type: h.type, T: h.T, b: h.b, neural: h.W.map(function (w) { return dot(w, feat.z, 0); }),
        Wg: fused ? h.W.map(function (w) { return w.slice(512).map(function (v) { return v * cfg.fusion_weight; }); }) : null, g: fused ? g : null };
    });
    return out;
  };
  function partProb(part, g) {
    g = g || part.g; var n = part.neural.length, z = new Array(n), i;
    for (i = 0; i < n; i++) z[i] = part.neural[i] + part.b[i] + (part.Wg && g ? dot(part.Wg[i], g, 0) : 0);
    if (part.type === 'sigmoid') return z.map(function (v, k) { var T = Array.isArray(part.T) ? part.T[k] : part.T; return 1 / (1 + Math.exp(-v / T)); });
    var mx = -Infinity; for (i = 0; i < n; i++) { z[i] /= part.T; if (z[i] > mx) mx = z[i]; }
    var sum = 0; for (i = 0; i < n; i++) { z[i] = Math.exp(z[i] - mx); sum += z[i]; }
    return z.map(function (v) { return v / sum; });
  }
  Model.prototype.occlusionPart = function (text, part, k) {
    if (!part.Wg || !part.g) return null;
    var ws = wordSpans(text), cfg = this.heads.ngram, base = partProb(part)[k], best = null;
    for (var s of ws.spans) {
      var rest = ws.cps.slice(0, s[0]).join('') + ws.cps.slice(s[1]).join('');
      var drop = base - partProb(part, ngramVec(rest, cfg))[k];
      if (best === null || drop > best[0]) best = [drop, s[0], s[1]];
    }
    if (!best || best[0] <= 0) return null;
    return [best[1], best[2], ws.cps.slice(best[1], best[2]).join('')];
  };
  // kept for v4.5-compatible callers (topic/action head occlusion)
  Model.prototype.occlusion = function (text, action) {
    var parts = this.parts(text, { z: new Float32Array(512) }), k = parts.topic.classes.indexOf(action);
    if (k < 0 || action === 'none') return null;
    return this.occlusionPart(text, parts.topic, k);
  };
  Model.prototype.analyze = function (text) {
    var t0 = (typeof performance !== 'undefined' ? performance : Date).now();
    var feat = this.features(text), parts = this.parts(text, feat), P = {};
    Object.keys(parts).forEach(function (t) { P[t] = partProb(parts[t]); });
    var v46 = this.schema === 'dmsg-nlp-heads/3', speechMap = {}, ps45;
    if (v46) {
      parts.speech.classes.forEach(function (c, i) { speechMap[c] = P.speech[i]; });
      ps45 = V46_SPEECH_TO_V45.map(function (c) { return speechMap[c]; });
    } else {
      ps45 = P.speech; var m45 = { DIRECT_REQUEST: 'DIRECT_REQUEST', INDIRECT_REQUEST: 'INDIRECT_REQUEST', WARNING: 'WARNING_OR_NEGATION', QUOTATION: 'QUOTATION_OR_REPORT', INFORMATION: 'INFORMATIONAL' };
      parts.speech.classes.forEach(function (c, i) { speechMap[m45[c]] = P.speech[i]; });
    }
    var pa = P.topic, top = parts.topic.classes[argmax(pa)];
    var anchor = (text.trim() && top !== 'none') ? this.occlusionPart(text, parts.topic, argmax(pa)) : null;
    var adv, unc = [], base;
    try {
      base = this.arbiter === 'dra' && this.E.decisionRelevantAdvisory
        ? this.E.decisionRelevantAdvisory(text, typedRaw(ps45, pa), { source: 'ON_DEVICE_NLP', model_anchor: anchor })
        : this.E.advisory(text, typedRaw(ps45, pa), { source: 'ON_DEVICE_NLP', threshold: this.threshold, model_anchor: anchor });
      adv = base;
    }
    catch (e) { adv = { action: 'ASK_HUMAN', reason: 'CONTRACT_' + (e.code || 'ERROR'), evidence: [], grounding: 'NO_ACTION_ANCHOR' }; unc.push('CONTRACT_ERROR'); }
    var res = { speech: speechMap, topic: zipRaw(parts.topic.classes, pa) };
    if (v46 && base) {
      res.intent = zipRaw(parts.intent.classes, P.intent); res.req_action = zipRaw(parts.req_action.classes, P.req_action);
      var ip = zipRaw(parts.indicators.classes, P.indicators), thr = {}, self = this;
      this.heads.indicators.classes.forEach(function (c, i) { thr[c] = self.heads.indicators.threshold[i]; });
      res.indicators = ip;
      var spans = {};
      parts.indicators.classes.forEach(function (c, j) { if (ip[c] >= thr[c]) { var s = self.occlusionPart(text, parts.indicators, j); if (s) spans[c] = s; } });
      adv = this.E.indicatorAdvisory(text, base, ip, { thresholds: thr, model_spans: spans });
      var mx = ['speech', 'intent', 'req_action', 'topic'].map(function (t) { return Math.max.apply(null, P[t]); });
      if (Math.min.apply(null, mx) < 0.4) unc.push('LOW_TASK_CONFIDENCE');
      var it = keyMax(res.intent), ra = keyMax(res.req_action), sp = keyMax(speechMap);
      var reported = sp === 'WARNING_OR_NEGATION' || sp === 'QUOTATION_OR_REPORT';
      if (reported && RISKY_REQ.indexOf(ra) >= 0 && res.req_action[ra] >= this.guardP) unc.push('SPEECH_VS_REQUESTED_ACTION');
      if (adv.action === 'NO_STRONG_SIGNAL' && !reported &&
          ((RISKY_INTENT.indexOf(it) >= 0 && res.intent[it] >= this.guardP) || (RISKY_REQ.indexOf(ra) >= 0 && res.req_action[ra] >= this.guardP))) {
        adv = Object.assign({}, adv, { action: 'ASK_HUMAN', reason: 'CROSS_TASK_RISK_NOT_CLEARED', message: this.E.messages.ASK_HUMAN }); unc.push('CROSS_TASK_RISK_NOT_CLEARED');
      }
    }
    var ms = (typeof performance !== 'undefined' ? performance : Date).now() - t0;
    var spTop = keyMax(speechMap), risk = [];
    if (top !== 'none') risk.push('ACTION:' + top);
    (adv.indicators || []).forEach(function (r) { risk.push('INDICATOR:' + r.label + (r.grounded ? '' : '(MODEL_ONLY)')); });
    return {
      engine: 'ON_DEVICE_NLP', arbiter: this.arbiter, model_id: this.model_id, model_revision: this.model_revision, verified_inference: true, schema: this.schema,
      speech_act: Math.max.apply(null, ps45) < 0.4 ? 'UNKNOWN' : spTop, speech_probs: roundMap(speechMap), action_probs: roundMap(res.topic),
      intent_probs: res.intent ? roundMap(res.intent) : null, requested_action_probs: res.req_action ? roundMap(res.req_action) : null,
      indicator_probs: res.indicators ? roundMap(res.indicators) : null, raw: res,
      risk_signals: risk, evidence_spans: adv.evidence || [], indicators: adv.indicators || [], structural_evidence: adv.structural_evidence || this.E.structuralEvidence(text),
      sender_identity: 'UNVERIFIED', grounding: adv.grounding, topic_anchor: anchor,
      model_label_confidence: { speech: round(Math.max.apply(null, ps45)), action: round(Math.max.apply(null, pa)), calibrated_on: 'author synthetic calib split (not a real-world fraud probability)' },
      uncertainty: unc, uncertainty_reason: UNCERTAINTY[adv.reason] || (adv.action === 'ASK_HUMAN' ? adv.reason : null),
      policy_action: adv.action, reason: adv.reason, safe_next_step: SAFE_NEXT[adv.action], latency_ms: Math.round(ms), tokens: feat.ids.length,
      advisory: adv
    };
  };
  function keyMax(o) { var b = null; Object.keys(o).forEach(function (k) { if (b === null || o[k] > o[b]) b = k; }); return b; }
  function zipRaw(ks, vs) { var o = {}; ks.forEach(function (k, i) { o[k] = vs[i]; }); return o; }
  function roundMap(o) { var r = {}; Object.keys(o).forEach(function (k) { r[k] = round(o[k]); }); return r; }
  function zip(ks, vs) { var o = {}; ks.forEach(function (k, i) { o[k] = round(vs[i]); }); return o; }
  function round(x) { return Math.round(x * 1e4) / 1e4; }
  function b64ToBuf(b64) {
    if (typeof Buffer !== 'undefined') { var b = Buffer.from(b64, 'base64'); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength); }
    var s = atob(b64), u = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u.buffer;
  }
  return { Tokenizer: Tokenizer, Model: Model, ngramVec: ngramVec, crc32: crc32, wordSpans: wordSpans, typedRaw: typedRaw, readBin: readBin,
    b64ToBuf: b64ToBuf, Encoder: Encoder, pooled: pooled, SPEECH: SPEECH, ACTION: ACTION, MAX_LEN: MAX_LEN, version: '4.6', partProb: partProb };
});
