'use strict';
// Contract-level DOM tests: execute the complete production UI scripts in a VM.
// No network, model inference, external browser, or disk persistence is involved.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ROOT = path.resolve(__dirname, '..');
const Engine = require(path.join(ROOT, 'apps/shared/dmsg-engine.js'));
const V50 = require(path.join(ROOT, 'apps/shared/v50-contract.js'));
const Evidence = require(path.join(ROOT, 'apps/shared/v51-evidence.js'));
// The registry is stubbed to isolate UI binding/race behavior. No provider is called.

class Element {
  constructor(id = '') { this.id = id; this.dataset = {}; this.attributes = {}; this.listeners = {}; this.children = []; this.value = ''; this.checked = false; this.hidden = false; this.disabled = false; this.style = {}; this.parentNode = { dataset: {}, removeChild() {} }; this._text = ''; this.classList = { toggle() {}, add() {}, remove() {} }; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text; }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  dispatch(name) { const event = { target: this, key: '', preventDefault() {} }; const results = (this.listeners[name] || []).map(fn => fn.call(this, event)); if (this['on' + name]) results.push(this['on' + name](event)); return Promise.all(results); }
  appendChild(node) { this.children.push(node); return node; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name]; }
  removeAttribute(name) { delete this.attributes[name]; }
  querySelectorAll() { return []; }
  focus() {}
  scrollIntoView() {}
}
const settle = async () => { await new Promise(setImmediate); await new Promise(setImmediate); };
function dom() {
  const elements = {};
  const get = id => elements[id] ||= new Element(id);
  const sources = ['text', 'fixture'].map(src => { const b = new Element(); b.dataset.src = src; return b; });
  const arbiters = ['dra', 'v46'].map(arb => { const b = new Element(); b.dataset.arb = arb; return b; });
  const intents = ['PLAN_INDEPENDENT_VERIFICATION', 'REQUEST_TRUSTED_HUMAN_HELP'].map(intent => { const b = new Element(); b.dataset.intent = intent; return b; });
  const document = {
    getElementById: get, createElement: () => new Element(), createTextNode: text => ({ textContent: text }), createDocumentFragment: () => new Element(),
    querySelectorAll(selector) {
      if (selector === '.seg-btn') return sources.concat(arbiters);
      if (selector === '.seg-btn[data-src]') return sources;
      if (selector === '#arbSeg .seg-btn') return arbiters;
      if (selector === '#nextRow .ghost') return intents;
      if (selector === '#fixtureChips .chip') return get('fixtureChips').children;
      return [];
    }, head: new Element()
  };
  get('srcFixture').hidden = true; get('resultCard').hidden = true;
  return { elements, get, sources, arbiters, intents, document };
}
function raw(action = 'none', speech = 'informational') {
  const answers = {};
  for (const [q, spec] of Object.entries(Engine.data.model.spec)) {
    if (spec.type === 'choice') {
      const selected = q === 'q_action' ? action : speech;
      answers[q] = { type: 'choice', probabilities: Object.fromEntries(spec.options.map(k => [k, k === selected ? .98 : .02 / (spec.options.length - 1)])) };
    } else if (spec.type === 'noul') answers[q] = { type: 'noul', noul: q === 'q_evidence' ? .98 : .02 };
    else answers[q] = { type: 'score', probabilities: { none: .97, low: .01, moderate: .01, high: .01 } };
  }
  return { answers };
}

function contractStub() {
  const state = { revision: 1, evaluations: [], layersBroken: false, invalid: false, unavailableCodes: [] };
  const selectedProfile = policy => 'test-' + policy + '-' + state.revision;
  const requestBinding = (profile, policy) => ({ profile_id: profile, policy_id: policy,
    question_contract_sha256: 'questions-' + state.revision, questions_sha256: 'wording-' + state.revision,
    profile_fingerprint: 'profile-' + state.revision, registry_fingerprint: 'registry-' + state.revision,
    base_execution_manifest_fingerprint: 'base-stub' });
  const C = { selectedProfile, requestBinding,
    validateBinding(binding, profile, policy) {
      if (state.invalid || JSON.stringify(binding) !== JSON.stringify(requestBinding(profile, policy))) throw Error('PROFILE_BINDING_MISMATCH');
      return binding;
    },
    evaluateCurrent(text, response, policy, options) {
      state.evaluations.push({ text, policy, options });
      const out = V50.evaluateCurrent(text, response, policy, options);
      out.question_profile_id = options.profile_id; out.question_binding = options.binding;
      return Evidence.enrichEvidence(text, out);
    },
    unavailableCurrent(code, policy, options) {
      state.unavailableCodes.push(code);
      const out = V50.unavailableCurrent(code, policy);
      out.question_profile_id = options.profile_id; out.question_binding = requestBinding(options.profile_id, policy);
      return out;
    },
    applyLocalLayers(text, result, options) {
      if (state.layersBroken) throw Error('LAYER_CONTRACT_BROKEN');
      const out = V50.applyLocalLayers(text, result, options);
      return out.evidence_display ? out : Evidence.enrichEvidence(text, out);
    }
  };
  return { C, state };
}
async function app(options = {}) {
  const d = dom(), pending = [], sessions = [], sent = [], calls = { local: 0, nlp: 0 }, stub = contractStub();
  const C = options.missingContract ? undefined : options.contract || stub.C;
  d.get('freeText').value = '급여가 입금되었습니다.'; d.get('useModel').checked = true;
  if (options.nlp) d.get('useNLP').checked = true;
  const E = Object.assign({}, Engine, {
    evaluateTurn(value) { calls.local++; return Engine.evaluateTurn(value); },
    Session: function () { const s = new Engine.Session(); sessions.push(s); return s; }
  });
  const context = { document: d.document, DMSG: E, DMSG_V51: C, DMSG_BUILD: {}, navigator: {}, location: { protocol: 'http:', hash: '', href: 'http://127.0.0.1:9999/', pathname: '/', search: '' },
    history: { state: null, replaceState(s) { this.state = s; }, pushState(s) { this.state = s; } },
    setTimeout, clearTimeout, performance, console, matchMedia: () => ({ matches: false }), requestIdleCallback() {}, addEventListener() {}, scrollTo() {},
    DmsgNLP: { Model: function () { calls.nlp++; throw Error('UNEXPECTED_NLP_LOAD'); } },
    fetch: async (url, opts) => {
      if (url === '/api/health') {
        if (options.offline) throw Error('HOST_UNAVAILABLE');
        return { ok: true, json: async () => ({ app: 'dmsg-desktop', model: { configured: options.configured !== false, endpoint_host: '127.0.0.1' } }) };
      }
      if (url === '/api/config') return { ok: true, json: async () => ({ ok: true }) };
      if (url === '/api/model') {
        const payload = JSON.parse(opts.body); sent.push(payload);
        const binding = JSON.parse(JSON.stringify(C.requestBinding(payload.profile_id, payload.policy_id)));
        return new Promise(resolve => pending.push((value, extra = {}) => resolve({ ok: true, json: async () => ({ ok: true, raw: value, profile_binding: binding, latency_ms: 1, ...extra }) })));
      }
      throw Error('UNEXPECTED_TEST_FETCH');
    } };
  context.window = context; vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'apps/web/app.js'), 'utf8'), context);
  await settle(); return { ...d, pending, sessions, context, stub, sent, calls };
}
async function runAndResolve(a, response = raw(), extra) {
  await a.get('runBtn').dispatch('click'); assert.equal(a.pending.length, 1);
  a.pending.shift()(response, extra); await settle();
}
const lastResult = a => Array.from(a.sessions[0].idem.values()).at(-1)[1];
const allText = el => (el.textContent || '') + (el.children || []).map(allText).join(' ');
test('arbiter buttons do not hide or change the source controls', async () => {
  const a = await app(); await a.arbiters[1].dispatch('click');
  assert.equal(a.get('srcText').hidden, false); assert.equal(a.get('srcFixture').hidden, true);
});
test('human review applies to a valid Zoro no-signal result', async () => {
  const a = await app(); a.get('askReview').checked = true; await runAndResolve(a);
  assert.equal(a.sessions[0].history.at(-1).action, 'ASK_HUMAN');
  assert.equal(a.sessions[0].history.at(-1).reason, 'USER_REQUESTED_REVIEW');
});
test('human review never weakens a Zoro pause', async () => {
  const a = await app(); a.get('askReview').checked = true; a.get('freeText').value = '지금 인증번호를 알려 주세요.';
  await runAndResolve(a, raw('otp', 'direct_request'));
  assert.equal(a.sessions[0].history.at(-1).action, 'PAUSE_AND_VERIFY');
});
test('edited text rejects a late model response even if edited back', async () => {
  const a = await app(), original = a.get('freeText').value; await a.get('runBtn').dispatch('click');
  a.get('freeText').value = '다른 입력'; await a.get('freeText').dispatch('input');
  a.get('freeText').value = original; await a.get('freeText').dispatch('input');
  a.pending.shift()(raw()); await settle();
  assert.equal(a.sessions[0].history.length, 0); assert.equal(a.get('resultCard').hidden, true);
});
test('policy change rejects an in-flight response', async () => {
  const a = await app(); await a.get('runBtn').dispatch('click'); await a.arbiters[0].dispatch('click');
  a.pending.shift()(raw()); await settle(); assert.equal(a.sessions[0].history.length, 0);
});
test('session advancement rejects an in-flight response', async () => {
  const a = await app(); await a.get('runBtn').dispatch('click'); await a.intents[0].dispatch('click');
  a.pending.shift()(raw()); await settle(); assert.equal(a.sessions[0].history.length, 1);
  assert.equal(a.sessions[0].history[0].action, 'INTENT_ONLY');
});
test('changing review option rejects an in-flight response', async () => {
  const a = await app(); await a.get('runBtn').dispatch('click'); a.get('askReview').checked = true; await a.get('askReview').dispatch('change');
  a.pending.shift()(raw()); await settle(); assert.equal(a.sessions[0].history.length, 0);
});
test('clear hides a completed result', async () => {
  const a = await app(); await runAndResolve(a); assert.equal(a.get('resultCard').hidden, false);
  await a.get('clearBtn').dispatch('click'); assert.equal(a.get('resultCard').hidden, true);
});

test('desktop results and history explicitly remain per-text analysis, not session risk clearance', async () => {
  const a = await app();
  a.get('freeText').value = '지금 인증번호를 알려 주세요.';
  await runAndResolve(a, raw('otp', 'direct_request'));
  assert.equal(a.sessions[0].history.at(-1).action, 'PAUSE_AND_VERIFY');
  a.get('freeText').value = '오늘 일정 안내입니다.'; await a.get('freeText').dispatch('input');
  await runAndResolve(a, raw('none', 'informational'));
  assert.equal(a.sessions[0].history.at(-1).action, 'NO_STRONG_SIGNAL');
  assert.equal(a.get('resultScopeNotice').textContent, '현재 문장만 분석하며 이전 문장의 위험은 이어서 판단하지 않습니다.');
  const result = Array.from(a.sessions[0].idem.values()).at(-1)[1];
  assert.equal(result.execution_profile.analysis_scope, 'CURRENT_TEXT_ONLY_NO_SESSION_RISK');
  const html = fs.readFileSync(path.join(ROOT, 'apps/web/index.html'), 'utf8');
  assert.match(html, /id="inputScopeNotice">현재 문장만 분석하며 이전 문장의 위험은 이어서 판단하지 않습니다\./);
  assert.match(html, /id="resultScopeNotice">현재 문장만 분석하며 이전 문장의 위험은 이어서 판단하지 않습니다\./);
  assert.match(html, /문장별 분석 기록/);
  assert.match(html, /이전 문장에서 안내한 위험이 해소됐다는 뜻은 아닙니다/);
  assert.doesNotMatch(html, /이 세션의 기록/);
});


test('selected profile/policy and its seven-field binding accompany the response evaluation', async () => {
  const a = await app(); await runAndResolve(a);
  assert.deepEqual(a.sent[0], { text: a.get('freeText').value, policy_id: 'legacy', profile_id: 'test-legacy-1' });
  assert.equal(a.stub.state.evaluations.length, 1);
  const evaluated = a.stub.state.evaluations[0];
  assert.equal(evaluated.options.profile_id, 'test-legacy-1');
  assert.equal(Object.keys(evaluated.options.binding).length, 7);
  assert.equal(lastResult(a).execution_profile.profile_id, 'test-legacy-1');
  assert.deepEqual(JSON.parse(JSON.stringify(lastResult(a).execution_profile.profile_binding)), a.stub.C.requestBinding('test-legacy-1', 'legacy'));
});
test('missing or mismatched response binding produces an explicit hold without evaluating raw data', async () => {
  for (const binding of [undefined, {}, { profile_id: 'different' }]) {
    const a = await app(); await runAndResolve(a, raw(), { profile_binding: binding });
    assert.equal(lastResult(a).action, 'ASK_HUMAN');
    assert.equal(a.stub.state.unavailableCodes.at(-1), 'PROFILE_OR_RESPONSE_CONTRACT_INVALID');
    assert.equal(a.stub.state.evaluations.length, 0); assert.equal(a.calls.local, 0);
  }
});
test('profile registry changes discard an in-flight result', async () => {
  const a = await app(); await a.get('runBtn').dispatch('click');
  a.stub.state.revision++; a.pending.shift()(raw()); await settle();
  assert.equal(a.sessions[0].history.length, 0); assert.equal(a.get('resultCard').hidden, true);
});
test('source, consent and endpoint settings changes each discard an in-flight result', async () => {
  for (const change of [a => a.sources[1].dispatch('click'), a => { a.get('consentRep').checked = true; return a.get('consentRep').dispatch('change'); }, a => a.get('cfgSave').dispatch('click')]) {
    const a = await app(); await a.get('runBtn').dispatch('click'); await change(a);
    a.pending.shift()(raw()); await settle(); assert.equal(a.sessions[0].history.length, 0);
  }
});
test('Zoro selected while unconfigured/offline gives ASK_HUMAN and never falls back to NLP or local rules', async () => {
  for (const options of [{ configured: false, nlp: true }, { offline: true, nlp: true }]) {
    const a = await app(options); await a.get('runBtn').dispatch('click'); await settle();
    assert.equal(lastResult(a).action, 'ASK_HUMAN'); assert.match(lastResult(a).reason, /MODEL_NOT_CONFIGURED/);
    assert.equal(a.pending.length, 0); assert.equal(a.calls.local, 0); assert.equal(a.calls.nlp, 0);
    assert.equal(a.document.head.children.length, 0); assert.equal(a.get('useModel').disabled, false);
  }
});
test('simulated model failure and server failure remain explicit holds', async () => {
  const a = await app({ nlp: true }); a.get('simFail').checked = true;
  await a.get('runBtn').dispatch('click'); await settle();
  assert.equal(lastResult(a).action, 'ASK_HUMAN'); assert.equal(a.stub.state.unavailableCodes.at(-1), 'SIMULATED_MODEL_FAILURE');
  assert.equal(a.pending.length, 0); assert.equal(a.calls.local, 0); assert.equal(a.calls.nlp, 0);
  const b = await app(); await runAndResolve(b, raw(), { ok: false, code: 'ModelUnavailable:TIMEOUT' });
  assert.equal(lastResult(b).action, 'ASK_HUMAN'); assert.equal(b.stub.state.evaluations.length, 0);
});
test('missing, invalid, or failed local contract remains an explicit visible hold', async () => {
  const absent = await app({ missingContract: true }); await absent.get('runBtn').dispatch('click'); await settle();
  assert.equal(lastResult(absent).action, 'ASK_HUMAN'); assert.equal(absent.get('resultCard').hidden, false);
  assert.equal(absent.pending.length, 0); assert.equal(absent.calls.local, 0);
  const invalid = await app(); invalid.stub.state.invalid = true; await invalid.get('runBtn').dispatch('click'); await settle();
  assert.equal(lastResult(invalid).action, 'ASK_HUMAN'); assert.equal(invalid.pending.length, 0);
  const broken = await app(); broken.stub.state.layersBroken = true; await runAndResolve(broken);
  assert.equal(lastResult(broken).action, 'ASK_HUMAN'); assert.match(lastResult(broken).reason, /V51_LOCAL_LAYER_CONTRACT_INVALID/);
  assert.equal(broken.get('resultCard').hidden, false);
});
test('evidence context and unresolved reasons are visible without claiming verified semantics', async () => {
  const a = await app(); a.get('freeText').value = '예시: 송금하세요. OTP를 보내주세요.';
  await runAndResolve(a, raw('otp', 'reported_or_quoted'));
  const contents = allText(a.get('evidenceBox'));
  assert.match(contents, /모델의 판단 근거나 의미가 검증됐다는 뜻은 아닙니다/);
  assert.match(contents, /앞 예시·경고의 범위가 끝났는지 불분명함/);
  assert.match(contents, /확인하지 못한 구간/);
  const trace = JSON.parse(a.get('executionTrace').textContent);
  assert.equal(trace.evidence_display.semantic_verified, false);
  assert.doesNotMatch(JSON.stringify(trace), /송금하세요|보내주세요/);
});
test('shell retains old assets and loads all eight v5.1 assets in dependency order', () => {
  const html = fs.readFileSync(path.join(ROOT, 'apps/web/index.html'), 'utf8');
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map(x => x[1]);
  const expected = ['v51-profile-data.js', 'v51-semantic-data.js', 'v51-base-engine.js', 'v51-base-contract.js', 'v51-semantic.js', 'v51-evidence.js', 'v51-contract-data.js', 'v51-contract.js'];
  let prior = -1;
  for (const name of expected) { const position = scripts.indexOf(name); assert.ok(position > prior, name); prior = position; }
  assert.ok(scripts.indexOf('app.js') > prior);
  const sw = fs.readFileSync(path.join(ROOT, 'apps/web/sw.js'), 'utf8');
  for (const name of expected.concat(['engine-data.js', 'dmsg-engine.js', 'v50-contract.js', 'v50-contract-data.js'])) { assert.ok(scripts.includes(name), name); assert.ok(sw.includes("'" + name + "'"), name); }
  assert.match(html, /v5\.1 개발 후보/); assert.match(sw, /dmsg-v51-shell/);
  assert.match(JSON.parse(fs.readFileSync(path.join(ROOT, 'apps/web/manifest.webmanifest'), 'utf8')).description, /v5\.1 개발 후보/);
});
test('actual bundled v5.1 scripts load in browser order and produce matching question bindings', () => {
  const html = fs.readFileSync(path.join(ROOT, 'apps/web/index.html'), 'utf8');
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map(x => x[1]);
  const context = { console, TextDecoder, TextEncoder, atob, btoa, URL }; vm.createContext(context);
  for (const name of scripts) {
    if (name === 'app.js' || name === 'build-info.js' || name === 'dmsg-nlp.js') continue;
    const file = path.join(ROOT, 'apps/shared', name);
    if (!fs.existsSync(file)) continue;
    vm.runInContext(fs.readFileSync(file, 'utf8'), context, { filename: name });
  }
  const C = context.DMSG_V51;
  for (const policy of ['legacy', 'dra']) {
    const profile = C.selectedProfile(policy), binding = C.requestBinding(profile, policy);
    assert.equal(Object.keys(binding).length, 7); assert.equal(binding.profile_id, profile);
    assert.equal(C.validateBinding(binding, profile, policy).policy_id, policy);
    assert.ok(Object.keys(C.questionPayload('합성 입력', profile, policy).questions).length >= 7);
  }
});

function actualRaw(C, profile, policy, omit) {
  const answers = {};
  for (const [q, spec] of Object.entries(C.questionPayload('', profile, policy).questions)) {
    if (q === omit) continue;
    if (spec.type === 'choice') {
      const keys = Object.keys(spec.criteria), selected = ({ q_action: 'none', q_speech: 'informational', q_request_scope: 'no_request' })[q] || keys[0];
      answers[q] = { type: 'choice', probabilities: Object.fromEntries(keys.map(k => [k, k === selected ? .98 : .02 / (keys.length - 1)])) };
    } else if (spec.type === 'noul') answers[q] = { type: 'noul', noul: q === 'q_evidence' ? .98 : .02 };
    else answers[q] = { type: 'score', probabilities: { none: .97, low: .01, moderate: .01, high: .01 } };
  }
  return { answers };
}
test('actual selected profile is used end to end without hardcoding a fingerprint', async () => {
  const C = require(path.join(ROOT, 'apps/shared/v51-contract.js'));
  const a = await app({ contract: C }), profile = C.selectedProfile('legacy');
  await runAndResolve(a, actualRaw(C, profile, 'legacy'));
  assert.equal(a.sent[0].profile_id, profile);
  assert.equal(lastResult(a).question_profile_id, profile);
  assert.equal(lastResult(a).action, 'NO_STRONG_SIGNAL');
  assert.equal(lastResult(a).execution_trace.question_binding.question_contract_sha256, C.requestBinding(profile, 'legacy').question_contract_sha256);
});
test('eleven-question candidate validates required fields; missing answers show ASK_HUMAN', async () => {
  const Actual = require(path.join(ROOT, 'apps/shared/v51-contract.js'));
  const profile = 'v51-specific-candidate', C = { ...Actual, selectedProfile: policy => policy === 'legacy' ? profile : Actual.selectedProfile(policy) };
  assert.equal(Object.keys(C.questionPayload('', profile, 'legacy').questions).length, 11);
  const a = await app({ contract: C }); await runAndResolve(a, actualRaw(C, profile, 'legacy'));
  assert.equal(lastResult(a).action, 'NO_STRONG_SIGNAL'); assert.equal(lastResult(a).question_profile_id, profile);
  // q_evidence remains optional for the historical baseline; the four new candidate fields are required.
  for (const missing of ['q_action', 'q_request_scope', 'q_current_exposure', 'q_payment_anomaly', 'q_request_specified']) {
    const b = await app({ contract: C }); await runAndResolve(b, actualRaw(C, profile, 'legacy', missing));
    assert.equal(lastResult(b).action, 'ASK_HUMAN', missing); assert.equal(b.calls.local, 0);
    assert.match(lastResult(b).mode, /MODEL_UNAVAILABLE_OR_INVALID/);
  }
});
