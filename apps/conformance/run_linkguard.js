#!/usr/bin/env node
'use strict';
const fs = require('fs'), path = require('path');
require(path.join(__dirname, '..', 'shared', 'linkguard-data.js'));
const L = require(path.join(__dirname, '..', 'shared', 'dmsg-linkguard.js'));
const V = JSON.parse(fs.readFileSync(path.join(__dirname, 'linkguard_vectors.json'), 'utf8'));
const canon = v => Array.isArray(v) ? v.map(canon) : (v && typeof v === 'object' ? Object.keys(v).sort().reduce((o, k) => (o[k] = canon(v[k]), o), {}) : v);
const eq = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));
const rep = { sections: {}, mismatches: [] };
function check(sec, input, exp, act) {
  const s = rep.sections[sec] || (rep.sections[sec] = { total: 0, pass: 0 }); s.total++;
  if (eq(exp, act)) s.pass++; else if (rep.mismatches.length < 15) rep.mismatches.push({ sec, input, exp, act });
}
for (const x of V.intake) {
  let act; try { act = L.intake(x.text, { message_id: 'm', consent: x.consent }); } catch (e) { act = { error: e.message }; }
  check('intake', x.text, x.error ? { error: x.error } : x.out, x.error ? (act.error ? { error: act.error } : act) : act);
}
for (const x of V.policy) check('policy', x.intake.urls.map(u => u.raw), x.out, L.assessMessage(x.intake, { blocklist: x.blocklist, keys_present: x.keys_present }));
for (const x of V.fuse) check('fuse', [x.adv, x.link, x.apk], x.out, L.fuse(x.adv, x.link, x.apk === null ? undefined : x.apk));
for (const x of V.puny) { check('puny', x.in, [x.enc, x.dec], [L.punycodeEncode(x.in), L.punycodeDecode(L.punycodeEncode(x.in))]); }
let t = 0, p = 0; for (const s of Object.values(rep.sections)) { t += s.total; p += s.pass; }
const ok = t === p;
console.log(JSON.stringify({ status: ok ? 'PASS' : 'FAIL', total: t, pass: p, sections: rep.sections }));
if (!ok) { console.error(JSON.stringify(rep.mismatches.slice(0, 6), null, 1).slice(0, 6000)); process.exit(1); }
