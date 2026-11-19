#!/usr/bin/env node
/* Run the shipped on-device NLP (same JS the apps load) over a JSONL file; print JSON lines
   {id, action, reason, speech_act, latency_ms}. Usage: node tools/nlp/run_nlp_batch.js <in.jsonl> */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.resolve(__dirname, '..', '..');
const E = require(path.join(ROOT, 'apps/shared/dmsg-engine.js')), N = require(path.join(ROOT, 'apps/shared/dmsg-nlp.js'));
const ctx = { self: {} }; vm.createContext(ctx);
for (const f of ['dmsg-nlp-weights.js', 'dmsg-nlp-vocab.js', 'dmsg-nlp-heads.js']) vm.runInContext(fs.readFileSync(path.join(ROOT, 'apps/shared/nlp', f), 'utf8'), ctx);
const A = ctx.self, t0 = Date.now();
const M = new N.Model({ weights: N.b64ToBuf(A.DMSG_NLP_WEIGHTS_B64), vocab: A.DMSG_NLP_VOCAB, heads: A.DMSG_NLP_HEADS, heads_sha256: A.DMSG_NLP_HEADS_SHA256, arbiter: process.env.DMSG_ARBITER || 'dra' }, E);
process.stderr.write(JSON.stringify({ load_ms: Date.now() - t0, model_revision: M.model_revision }) + '\n');
for (const line of fs.readFileSync(process.argv[2], 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const r = JSON.parse(line);
  if (!r.text.trim()) { console.log(JSON.stringify({ id: r.id, action: 'ASK_HUMAN', reason: 'EMPTY_OR_INVALID_INPUT', latency_ms: 0 })); continue; }
  const o = M.analyze(r.text);
  console.log(JSON.stringify({ id: r.id, action: o.policy_action, reason: o.reason, speech_act: o.speech_act, latency_ms: o.latency_ms, model_revision: o.model_revision, arbiter: o.arbiter }));
}
