#!/usr/bin/env node
/* Golden snapshot of the SHIPPED on-device pipeline on the v4.6 locked set (taken after the one-time locked evaluation).
   Any model, heads or policy change that alters one of these outcomes fails until the snapshot is deliberately regenerated
   (node tools/nlp/regress_cases_v46.js --write). CASE A/B are reconstructions (original screenshots not provided). */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.resolve(__dirname, '..', '..');
const E = require(path.join(ROOT, 'apps/shared/dmsg-engine.js')), N = require(path.join(ROOT, 'apps/shared/dmsg-nlp.js'));
const ctx = { self: {} }; vm.createContext(ctx);
for (const f of ['dmsg-nlp-weights.js', 'dmsg-nlp-vocab.js', 'dmsg-nlp-heads.js']) vm.runInContext(fs.readFileSync(path.join(ROOT, 'apps/shared/nlp', f), 'utf8'), ctx);
const A = ctx.self, M = new N.Model({ weights: N.b64ToBuf(A.DMSG_NLP_WEIGHTS_B64), vocab: A.DMSG_NLP_VOCAB, heads: A.DMSG_NLP_HEADS, heads_sha256: A.DMSG_NLP_HEADS_SHA256, arbiter: 'v46' }, E);  // v4.6 snapshot: pinned to the v4.6 arbiter
const rows = fs.readFileSync(path.join(__dirname, 'locked_v46_multitask.jsonl'), 'utf8').split('\n').filter(Boolean).map(JSON.parse);
const snapPath = path.join(__dirname, 'eval', 'v46_golden_snapshot.json');
const got = {}; for (const r of rows) { const o = M.analyze(r.text); got[r.id] = [o.policy_action, o.reason]; }
if (process.argv.includes('--write')) { fs.writeFileSync(snapPath, JSON.stringify({ heads_sha256: A.DMSG_NLP_HEADS_SHA256, items: got }, null, 1)); console.log('written'); process.exit(0); }
const snap = JSON.parse(fs.readFileSync(snapPath, 'utf8')); const diff = [];
for (const [id, v] of Object.entries(snap.items)) if (JSON.stringify(got[id]) !== JSON.stringify(v)) diff.push({ id, expected: v, got: got[id] });
const caseAB = rows.filter(r => r.cat === 'caseA' || r.cat === 'caseB').map(r => ({ id: r.id, action: got[r.id][0] }));
const rep = { status: diff.length ? 'FAIL' : 'PASS', n: rows.length, diff, case_ab_not_cleared: caseAB.every(x => x.action !== 'NO_STRONG_SIGNAL'), case_ab: caseAB };
console.log(JSON.stringify(rep)); process.exit(rep.status === 'PASS' && rep.case_ab_not_cleared ? 0 : 1);
