#!/usr/bin/env node
/* Replays Python-generated vectors through the JS engine; exits 1 on any mismatch.
   Also checks that the exported data was generated from the current Python sources. */
'use strict';
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const ROOT = path.resolve(__dirname, '..', '..');
const E = require(path.join(ROOT, 'apps/shared/dmsg-engine.js'));
const V = JSON.parse(fs.readFileSync(path.join(__dirname, 'vectors.json'), 'utf8'));

function canon(v) {
  if (Array.isArray(v)) return v.map(canon);
  if (v && typeof v === 'object') { const o = {}; for (const k of Object.keys(v).sort()) o[k] = canon(v[k]); return o; }
  return v;
}
const eq = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));
const report = { sections: {}, mismatches: [] };
function check(section, input, expected, actual) {
  const s = report.sections[section] || (report.sections[section] = { total: 0, pass: 0 });
  s.total++;
  if (eq(expected, actual)) s.pass++;
  else if (report.mismatches.length < 40) report.mismatches.push({ section, input, expected, actual });
}
function run(fn) {
  try { return { ok: fn() }; }
  catch (e) {
    if (e && (e.name === 'ContractError' || e.name === 'PaylockError')) return { error: e.code };
    return { error_other: e && e.name === 'TypeError' ? 'TypeError' : 'ValueError' };
  }
}
const pick = (o, ks) => { const r = {}; ks.forEach(k => { r[k] = o[k]; }); return r; };

// Source drift: exported data must match the Python files currently on disk.
for (const [rel, sha] of Object.entries(E.data.source_sha256)) {
  const now = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, 'dmsg', rel))).digest('hex');
  check('source_drift', rel, sha, now);
}
for (const t of V.turns) {
  const r = E.evaluateTurn(t.in);
  check('turns', t.in, t.out, pick(r, ['action', 'reason', 'message', 'mode', 'evidence']));
}
for (const t of V.spans) {
  const r = E.decide(t.text, t.spans, { status: t.status, user_asks_review: t.review });
  check('spans', { text: t.text, spans: t.spans }, t.out, pick(r, ['action', 'reason', 'message', 'mode', 'evidence']));
}
for (const g of V.guard) {
  const prof = E.clauseProfile(g.text).map(c => ({ start: c.start, end: c.end, flags: c.flags, clean_action: c.clean_action, clean_imperative: c.clean_imperative }));
  check('guard', g.text, { flags: g.flags, clauses: g.clauses }, { flags: E.contextFlags(g.text), clauses: prof });
}
const ADV = ['action', 'reason', 'evidence', 'grounding', 'dropped_optional_questions', 'selected_action', 'selected_speech', 'message', 'mode'];
for (const a of V.advisory) {
  let r = run(() => E.advisory(a.text, a.raw)); if (r.ok) r = { ok: pick(r.ok, ADV) };
  check('advisory', { text: a.text, sel: [a.raw.answers.q_action, a.raw.answers.q_speech].map(q => Object.entries(q.probabilities).sort((x, y) => y[1] - x[1])[0][0]) }, a.out, r);
}
for (const a of (V.anchor || [])) {
  let r = run(() => E.advisory(a.text, a.raw, { source: 'ON_DEVICE_NLP', model_anchor: a.anchor }));
  if (r.ok) r = { ok: pick(r.ok, ['action', 'reason', 'evidence', 'grounding', 'mode']) };
  check('anchor', { text: a.text, anchor: a.anchor }, a.out, r);
}
for (const x of (V.structural || [])) check('structural', x.text, x.out, E.structuralEvidence(x.text));
for (const x of (V.indicator || [])) {
  let r = run(() => E.indicatorAdvisory(x.text, x.base, x.probs, { thresholds: x.thresholds, model_spans: x.spans }));
  if (r.ok) r = { ok: pick(r.ok, ['action', 'reason', 'indicators', 'structural_evidence', 'sender_identity', 'base_action']) };
  check('indicator', { text: x.text, probs: x.probs }, x.out, r);
}
const DRA_KEYS = ['action', 'reason', 'guidance_distribution', 'expected_cost', 'margin', 'trace', 'evidence', 'grounding', 'selected_action', 'selected_speech'];
for (const x of (V.dra || [])) {
  let r = run(() => E.decisionRelevantAdvisory(x.text, x.raw, { model_anchor: x.anchor }));
  if (r.ok) r = { ok: pick(r.ok, DRA_KEYS) };
  check('dra', { text: x.text }, x.out, r);
}
for (const n of V.normalize) {
  let r = run(() => E.advisory('지금 송금하세요', n.raw)); if (r.ok) r = { ok: pick(r.ok, ['action', 'reason', 'dropped_optional_questions']) };
  check('normalize', n.raw, n.out, r);
}
for (const j of V.json) {
  let r; try { r = { ok: E.strictJSON(j.text) }; } catch (e) { r = { error: 'INVALID' }; }
  check('json', j.text, j.out, r);
}
for (const p of V.paylock) {
  let r = run(() => E.assessRequest(p.in)); if (r.ok) r = { ok: r.ok.reasons ? { disposition: r.ok.disposition, reasons: r.ok.reasons } : r.ok };
  check('paylock', p.in, p.out, r);
}
for (const x of V.external) check('external', x.text, x.out, E.externalDirectiveFlags(x.text));

let total = 0, pass = 0;
for (const s of Object.values(report.sections)) { total += s.total; pass += s.pass; }
report.total = total; report.pass = pass; report.status = pass === total ? 'PASS' : 'FAIL';
report.scope = 'Python reference vs JS port on synthetic vectors; implementation equality only, not detection accuracy.';
const out = process.argv[2];
if (out) fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ status: report.status, total, pass, sections: report.sections }));
if (report.mismatches.length) console.log(JSON.stringify(report.mismatches.slice(0, 6), null, 1));
process.exit(report.status === 'PASS' ? 0 : 1);
