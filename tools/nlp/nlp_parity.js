#!/usr/bin/env node
/* JS on-device NLP vs Python reference (tools/nlp/nlp_v46.py via make_nlp_reference.py):
   tokenizer ids (exact), n-gram features (exact), pooled features (cosine / max abs vs ORT and NumPy),
   every task probability (max abs), argmax labels, topic attribution span, uncertainty flags and final policy.
   Exit 1 on failure. Usage: node tools/nlp/nlp_parity.js [reference.json] */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.resolve(__dirname, '..', '..');
const E = require(path.join(ROOT, 'apps/shared/dmsg-engine.js'));
const N = require(path.join(ROOT, 'apps/shared/dmsg-nlp.js'));
const ctx = { self: {} }; vm.createContext(ctx);
for (const f of ['dmsg-nlp-weights.js', 'dmsg-nlp-vocab.js', 'dmsg-nlp-heads.js'])
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'apps/shared/nlp', f), 'utf8'), ctx);
const A = ctx.self;
const R = JSON.parse(fs.readFileSync(process.argv[2] || path.join(__dirname, 'nlp_reference_vectors.json'), 'utf8'));
const mem0 = process.memoryUsage().rss; let t0 = Date.now();
const M = new N.Model({ weights: N.b64ToBuf(A.DMSG_NLP_WEIGHTS_B64), vocab: A.DMSG_NLP_VOCAB, heads: A.DMSG_NLP_HEADS, heads_sha256: A.DMSG_NLP_HEADS_SHA256, arbiter: 'v46' }, E);  // v4.6 snapshot: pinned to the v4.6 arbiter
const loadMs = Date.now() - t0;
const rep = { n: R.n, schema: M.schema, tokenizer_exact: 0, ngram_exact: 0, pooled_min_cos_ort: 1, pooled_max_abs_ort: 0, pooled_min_cos_numpy: 1, numpy_n: 0,
  prob_max_abs: 0, label_match: 0, anchor_match: 0, uncertainty_match: 0, action_match: 0, mismatches: [], latency_ms: [], load_ms: loadMs };
const cos = (a, b) => { let d = 0, x = 0, y = 0; for (let i = 0; i < a.length; i++) { d += a[i] * b[i]; x += a[i] * a[i]; y += b[i] * b[i]; } return d / Math.sqrt(x * y); };
const am = o => Object.keys(o).reduce((a, b) => (o[a] >= o[b] ? a : b));
for (const v of R.vectors) {
  const tt = v.text.trim() ? v.text : '.';
  const ids = M.tok.encode(tt);
  if (JSON.stringify(ids) === JSON.stringify(v.ids)) rep.tokenizer_exact++; else rep.mismatches.push({ kind: 'ids', text: v.text });
  if (v.ngram_nonzero) {
    const g = N.ngramVec(v.text, M.heads.ngram), nz = {};
    g.forEach((x, j) => { if (x) nz[j] = Math.round(x * 1e6) / 1e6; });
    const ok = Object.keys(nz).length === Object.keys(v.ngram_nonzero).length && Object.entries(v.ngram_nonzero).every(([k, x]) => Math.abs((nz[k] || 0) - x) < 2e-6);
    if (ok) rep.ngram_exact++; else rep.mismatches.push({ kind: 'ngram', text: v.text });
  } else rep.ngram_exact++;
  const x = M.enc.forward(ids), p = N.pooled(x, ids.length);
  rep.pooled_min_cos_ort = Math.min(rep.pooled_min_cos_ort, cos(p, v.pooled_ort));
  for (let i = 0; i < p.length; i++) rep.pooled_max_abs_ort = Math.max(rep.pooled_max_abs_ort, Math.abs(p[i] - v.pooled_ort[i]));
  if (v.pooled_numpy) { rep.numpy_n++; rep.pooled_min_cos_numpy = Math.min(rep.pooled_min_cos_numpy, cos(p, v.pooled_numpy)); }
  if (!v.text.trim()) { rep.label_match++; rep.anchor_match++; rep.uncertainty_match++; rep.action_match++; continue; }
  const r = M.analyze(v.text); rep.latency_ms.push(r.latency_ms);
  let labelsOk = true;
  for (const [task, probs] of Object.entries(v.probs)) {
    const js = r.raw[task]; if (!js) { labelsOk = false; continue; }
    for (const [c, q] of Object.entries(probs)) rep.prob_max_abs = Math.max(rep.prob_max_abs, Math.abs(js[c] - q));
    if (am(js) !== am(probs)) labelsOk = false;
  }
  if (labelsOk) rep.label_match++; else rep.mismatches.push({ kind: 'labels', text: v.text });
  const ancOk = JSON.stringify(r.topic_anchor || null) === JSON.stringify(v.anchor || null), jsAnc = r.topic_anchor, pyAnc = v.anchor;
  if (ancOk) rep.anchor_match++; else rep.mismatches.push({ kind: 'anchor', text: v.text, js: jsAnc, py: pyAnc });
  if (JSON.stringify(r.uncertainty) === JSON.stringify(v.uncertainty)) rep.uncertainty_match++; else rep.mismatches.push({ kind: 'uncertainty', text: v.text, js: r.uncertainty, py: v.uncertainty });
  if (r.policy_action === v.policy[0] && r.reason === v.policy[1]) rep.action_match++; else rep.mismatches.push({ kind: 'action', text: v.text, js: [r.policy_action, r.reason], py: v.policy });
}
const L = rep.latency_ms.slice().sort((a, b) => a - b), q = f => L[Math.min(L.length - 1, Math.floor(f * L.length))];
rep.latency = { p50_ms: q(0.5), p95_ms: q(0.95), max_ms: L[L.length - 1], n: L.length, env: 'node ' + process.version + ' (CPU, single thread)' }; delete rep.latency_ms;
rep.memory = { rss_before_model_mb: Math.round(mem0 / 1048576), rss_after_mb: Math.round(process.memoryUsage().rss / 1048576), note: 'Node RSS incl. base64 asset strings; not an Android measurement' };
rep.status = (rep.tokenizer_exact === rep.n && rep.ngram_exact === rep.n && rep.pooled_min_cos_ort > 0.999 && rep.label_match === rep.n &&
  rep.action_match === rep.n && rep.anchor_match === rep.n && rep.uncertainty_match === rep.n && rep.prob_max_abs < 0.02) ? 'PASS' : 'FAIL';
rep.mismatches = rep.mismatches.slice(0, 15);
console.log(JSON.stringify(rep, null, 1));
process.exit(rep.status === 'PASS' ? 0 : 1);
