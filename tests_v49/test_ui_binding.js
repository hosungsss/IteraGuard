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
const V51 = require(path.join(ROOT, 'apps/shared/v51-contract.js'));
// Seven-question legacy fixtures keep their explicit baseline meaning.
const V51Baseline = { ...V51, selectedProfile: () => 'v50-baseline' };

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
async function app() {
  const d = dom(), pending = [], sessions = [];
  d.get('freeText').value = '급여가 입금되었습니다.'; d.get('useModel').checked = true;
  const E = Object.assign({}, Engine, { Session: function () { const s = new Engine.Session(); sessions.push(s); return s; } });
  const context = { document: d.document, DMSG: E, DMSG_V51: V51Baseline, DMSG_BUILD: {}, navigator: {}, location: { protocol: 'http:', hash: '', href: 'http://127.0.0.1:9999/', pathname: '/', search: '' },
    history: { state: null, replaceState(s) { this.state = s; }, pushState(s) { this.state = s; } },
    setTimeout, clearTimeout, performance, console, matchMedia: () => ({ matches: false }), requestIdleCallback() {}, addEventListener() {}, scrollTo() {},
    fetch: async (url, opts) => {
      if (url === '/api/health') return { ok: true, json: async () => ({ app: 'dmsg-desktop', model: { configured: true, endpoint_host: '127.0.0.1' } }) };
      if (url === '/api/model') {
        const payload = JSON.parse(opts.body), binding = V51Baseline.requestBinding(payload.profile_id, payload.policy_id);
        return new Promise(resolve => pending.push(value => resolve({ ok: true, json: async () => ({ ok: true, raw: value, profile_binding: binding, latency_ms: 1 }) })));
      }
      throw Error('UNEXPECTED_TEST_FETCH');
    } };
  context.window = context; vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'apps/web/app.js'), 'utf8'), context);
  await settle(); return { ...d, pending, sessions, context };
}
async function runAndResolve(a, response = raw()) { await a.get('runBtn').dispatch('click'); assert.equal(a.pending.length, 1); a.pending.shift()(response); await settle(); }

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

async function arena(responseOverrides = {}) {
  const d = dom(); let n = 0, latest = null;
  d.get('text').value = '급여가 입금되었습니다.'; d.get('observation').value = 'NOT_CHECKED';
  const context = { document: d.document, crypto: { randomUUID: () => 'req-' + (++n) }, console,
    fetch: async (url, opts) => ({ ok: true, json: async () => {
      if (url === '/api/manifest') return { active_policy_id: 'legacy', execution_manifest: {} };
      if (url === '/api/start') { latest = null; return { session_id: 'session', version: 0 }; }
      if (url === '/api/evaluate') { const payload = JSON.parse(opts.body); return latest = { session_id: payload.session_id, version: payload.version + 1, request_id: payload.request_id, mode: 'MODEL_RESPONSE_UNATTESTED', action: 'NO_STRONG_SIGNAL', message: 'stored notice', reason: 'MODEL_INFORMATIONAL_NOT_REQUEST', evidence: [], ...responseOverrides }; }
      if (url.startsWith('/api/state')) return { version: latest ? latest.version : 0, tasks: [], events: latest ? [latest] : [] };
      throw Error('UNEXPECTED_TEST_FETCH');
    } }) };
  vm.createContext(context); vm.runInContext(fs.readFileSync(path.join(ROOT, 'arena/web/main.js'), 'utf8'), context); await settle(); return d;
}
test('arena refresh does not restore a result after input editing', async () => {
  const a = await arena(); await a.get('run').dispatch('click'); assert.equal(a.get('action').textContent, 'NO_STRONG_SIGNAL');
  a.get('text').value = '새로운 위험 문장'; await a.get('text').dispatch('input'); await a.get('refresh').dispatch('click');
  assert.equal(a.get('action').textContent, 'ASK_HUMAN');
});
test('arena refresh can show the unchanged input result', async () => {
  const a = await arena(); await a.get('run').dispatch('click'); await a.get('refresh').dispatch('click');
  assert.equal(a.get('action').textContent, 'NO_STRONG_SIGNAL');
});

test('arena explains current-turn no-signal separately from a prior-risk hold, including refresh', async () => {
  const a = await arena({ action: 'ASK_HUMAN', current_turn_action: 'NO_STRONG_SIGNAL', reason: 'PRIOR_RISK_UNRESOLVED' });
  await a.get('run').dispatch('click');
  assert.equal(a.get('action').textContent, 'ASK_HUMAN');
  assert.equal(a.get('reason').textContent, 'PRIOR_RISK_UNRESOLVED');
  assert.match(a.get('currentTurn').textContent, /현재 문장:.*위험 행동 요청 미감지.*안전 보증 아님/);
  assert.match(a.get('sessionNotice').textContent, /앞서 감지한 위험.*사용자 확인 보고만으로 해제되지 않습니다/);
  const current = a.get('currentTurn').textContent, notice = a.get('sessionNotice').textContent;
  await a.get('refresh').dispatch('click');
  assert.equal(a.get('currentTurn').textContent, current); assert.equal(a.get('sessionNotice').textContent, notice);
});
test('arena prior-risk explanation follows the actual current-turn action', async () => {
  const a = await arena({ action: 'ASK_HUMAN', current_turn_action: 'ASK_HUMAN', reason: 'PRIOR_RISK_UNRESOLVED' });
  await a.get('run').dispatch('click');
  assert.match(a.get('currentTurn').textContent, /현재 문장:.*판단 보류/);
  assert.doesNotMatch(a.get('currentTurn').textContent, /미감지/);
});
test('arena clears prior-risk explanation after edits, stale refresh, and a new session', async () => {
  const a = await arena({ action: 'ASK_HUMAN', current_turn_action: 'NO_STRONG_SIGNAL', reason: 'PRIOR_RISK_UNRESOLVED' });
  await a.get('run').dispatch('click'); assert.notEqual(a.get('sessionNotice').textContent, '');
  a.get('text').value = '다른 문장'; await a.get('text').dispatch('input');
  assert.equal(a.get('currentTurn').textContent, ''); assert.equal(a.get('sessionNotice').textContent, '');
  await a.get('refresh').dispatch('click');
  assert.equal(a.get('currentTurn').textContent, ''); assert.equal(a.get('sessionNotice').textContent, '');
  await a.get('run').dispatch('click'); assert.notEqual(a.get('sessionNotice').textContent, '');
  await a.get('new').dispatch('click');
  assert.equal(a.get('currentTurn').textContent, ''); assert.equal(a.get('sessionNotice').textContent, '');
});

