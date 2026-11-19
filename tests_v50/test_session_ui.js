'use strict';
// Full production Arena script in a minimal DOM, fake HTTP only; not a browser render test.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const SID = 'a'.repeat(32), OLD = 'b'.repeat(32), TID = 'c'.repeat(32);
class Element {
  constructor() { this.value = ''; this.checked = false; this.disabled = false; this.listeners = {}; this.children = []; this._text = ''; }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text; }
  focus() {}
  appendChild(v) { this.children.push(v); }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  async dispatch(name) {
    if (this.disabled && name === 'click') return;
    for (const f of this.listeners[name] || []) await f();
    if (this['on' + name]) await this['on' + name]();
  }
}
const settle = async () => { await new Promise(setImmediate); await new Promise(setImmediate); };
async function app({ remembered = null, closed = false, deferEvaluation = false, rememberedHistory = [], policy = 'legacy' } = {}) {
  const elements = {}, calls = [], pending = [], storage = new Map(); let seq = 0;
  if (remembered) storage.set('dmsg-arena-v5-session', remembered);
  storage.set('dmsg-arena-v5-session-ids', JSON.stringify(rememberedHistory));
  const get = id => elements[id] ||= new Element();
  const html = fs.readFileSync(path.join(__dirname, '../arena/web/index.html'), 'utf8');
  get('text').defaultValue = html.match(/<textarea id="text"[^>]*>([^<]*)<\/textarea>/u)[1];
  const samples = Object.fromEntries(Array.from(html.matchAll(/data-sample="([^"]+)"/gu), ([, name]) => {
    const button = new Element();
    button.dataset = { sample: name };
    return [name, button];
  }));
  get('text').value = '지금 송금하세요.';
  get('observation').value = 'NOT_CHECKED';
  const state = { id: remembered || SID, version: closed ? 2 : 0, prior_pause: closed ? 1 : 0,
    lifecycle: closed ? 'CLOSED_UNRESOLVED' : 'OPEN', tasks: [], events: [] };
  const makeEvaluation = (payload, override = {}) => {
    state.version += 1; state.prior_pause = 1;
    const d = { action: 'PAUSE_AND_VERIFY', current_turn_action: 'PAUSE_AND_VERIFY', reason: 'DIRECT',
      message: '확인하세요.', policy_id: policy, session_id: state.id, version: state.version,
      request_id: payload.request_id, lifecycle: 'OPEN', prior_pause: true, evidence: [], mode: 'MODEL_RESPONSE_UNATTESTED',
      next_task: { id: TID, status: 'OPEN', observation: 'NOT_CHECKED', instruction: '확인' }, ...override };
    state.events.push(d); state.tasks = [d.next_task || d.related_task].filter(Boolean); return d;
  };
  const fetch = async (url, options = {}) => {
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push({ url, body });
    let data;
    if (url === '/api/manifest') data = { active_policy_id: policy, execution_manifest: {} };
    else if (url === '/api/start') { state.id = SID; state.version = 0; state.lifecycle = 'OPEN'; state.prior_pause = 0; state.events = []; state.tasks = []; data = { session_id: SID, version: 0, mode: 'NOT_EVALUATED' }; }
    else if (url.startsWith('/api/state')) data = { ...state, id: new URL(url, 'http://local').searchParams.get('session_id') };
    else if (url === '/api/evaluate') {
      if (deferEvaluation) return new Promise(resolve => pending.push(override => resolve({ ok: true, json: async () => makeEvaluation(body, override) })));
      data = makeEvaluation(body);
    } else if (url === '/api/close' || url === '/api/reopen') {
      state.version += 1; state.lifecycle = url.endsWith('close') ? 'CLOSED_UNRESOLVED' : 'OPEN';
      data = { event_type: url.endsWith('close') ? 'CLOSE_UNRESOLVED' : 'REOPEN', version: state.version, lifecycle: state.lifecycle, prior_pause: !!state.prior_pause };
      state.events.push(data);
    } else throw Error('UNEXPECTED_FETCH');
    return { ok: true, json: async () => JSON.parse(JSON.stringify(data)) };
  };
  const context = { document: { getElementById: get, createElement: () => new Element(), querySelectorAll: () => Object.values(samples) }, fetch,
    crypto: { randomUUID: () => 'request-' + ++seq }, localStorage: { getItem: k => storage.get(k) ?? null, setItem: (k,v) => storage.set(k,v) }, console };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../arena/web/main.js'), 'utf8'), context);
  await settle(); return { get, calls, pending, state, storage, context, samples };
}

test('each synthetic example fills the editor and waits for an explicit evaluation', async () => {
  const a = await app();
  const seen = new Set();
  assert.deepEqual(Object.keys(a.samples), ['direct', 'warning', 'ambiguous', 'followup']);
  for (const [name, button] of Object.entries(a.samples)) {
    const before = a.calls.length;
    await button.dispatch('click');
    const value = a.get('text').value;
    assert.ok(value.length > 0 && !seen.has(value));
    if (name === 'direct') assert.equal(value, a.get('text').defaultValue);
    seen.add(value);
    assert.equal(a.calls.length, before);
  }
  await a.get('run').dispatch('click');
  assert.equal(a.calls.filter(c => c.url === '/api/evaluate').length, 1);
  assert.equal(a.calls.at(-1).body.text, a.get('text').value);
});

test('v56 queue selection keeps each task addressable and clears on new session', async () => {
  const a=await app();
  a.state.tasks=[{id:'1'.repeat(32),type:'PAUSE_AND_INDEPENDENT_CHECK',status:'OPEN',instruction:'중단 후 확인'},
                 {id:'2'.repeat(32),type:'CLARIFY_REQUEST',status:'OPEN',instruction:'정보 확인'}];
  await a.get('refresh').dispatch('click');
  assert.match(a.get('queueCount').textContent,/2건/);
  a.get('taskQueue').value='2'.repeat(32);await a.get('taskQueue').dispatch('change');
  assert.match(a.get('task').textContent,/정보 확인/);
  a.get('observation').value='UNRESOLVED';await a.get('run').dispatch('click');
  assert.equal(a.calls.find(c=>c.url==='/api/evaluate').body.task_id,'2'.repeat(32));
});

test('close locks input and reopen preserves risk without restoring current judgment', async () => {
  const a = await app(); await a.get('run').dispatch('click');
  assert.equal(a.get('new').disabled, true);
  await a.get('close').dispatch('click');
  assert.equal(a.get('run').disabled, true); assert.equal(a.get('text').disabled, true);
  assert.equal(a.get('currentTurn').textContent, ''); assert.match(a.get('riskState').textContent, /미해결/);
  assert.match(a.get('lifecycleNotice').textContent, /위험 해제가 아닙니다/);
  const evalCount = a.calls.filter(c => c.url === '/api/evaluate').length;
  await a.get('run').dispatch('click'); assert.equal(a.calls.filter(c => c.url === '/api/evaluate').length, evalCount);
  await a.get('reopen').dispatch('click');
  assert.equal(a.get('run').disabled, false); assert.match(a.get('riskState').textContent, /미해결/);
  assert.equal(a.get('currentTurn').textContent, ''); assert.equal(a.get('observation').disabled, false);
});

test('reload restores closed session without creating session or restoring any text', async () => {
  const a = await app({ remembered: OLD, closed: true });
  assert.equal(a.calls.some(c => c.url === '/api/start' || c.url === '/api/evaluate'), false);
  assert.equal(a.get('run').disabled, true); assert.equal(a.get('currentTurn').textContent, '');
  const stored = JSON.stringify([...a.storage.entries()]);
  assert.equal(stored.includes('송금'), false); assert.equal(stored.includes('PAUSE_AND_VERIFY'), false);
  assert.equal(a.get('sessionHistory').children.length, 1);
});

test('saved identifiers allow returning to a prior archived session', async () => {
  const a = await app({ remembered: SID, rememberedHistory: [OLD, SID, 'invalid'], closed: true });
  assert.equal(a.get('sessionHistory').children.length, 2);
  a.get('sessionHistory').value = OLD; await a.get('loadSession').dispatch('click');
  assert.equal(a.storage.get('dmsg-arena-v5-session'), OLD);
  assert.equal(a.get('text').value, ''); assert.equal(a.get('currentTurn').textContent, '');
  assert.equal(a.calls.some(c => c.url === '/api/start' || c.url === '/api/evaluate'), false);
});

test('late input or review change invalidates result and later refresh', async () => {
  for (const kind of ['input', 'review']) {
    const a = await app({ deferEvaluation: true });
    const inflight = a.get('run').dispatch('click'); await settle();
    if (kind === 'input') { a.get('text').value = '다른 문장'; await a.get('text').dispatch('input'); }
    else { a.get('review').checked = true; await a.get('review').dispatch('change'); }
    a.pending.shift()(); await inflight;
    assert.equal(a.get('action').textContent, 'ASK_HUMAN'); assert.equal(a.get('currentTurn').textContent, '');
    await a.get('refresh').dispatch('click'); assert.equal(a.get('currentTurn').textContent, '');
  }
});

test('policy drift rejects a late result and refresh cannot reapply it', async () => {
  const a = await app({ deferEvaluation: true });
  const inflight = a.get('run').dispatch('click'); await settle();
  a.pending.shift()({ policy_id: 'dra' }); await inflight;
  assert.equal(a.get('currentTurn').textContent, '');
  await a.get('refresh').dispatch('click'); assert.equal(a.get('currentTurn').textContent, '');
});

test('reported task disables new observation and displays current-turn vs retained risk separately', async () => {
  const a = await app({ deferEvaluation: true });
  const inflight = a.get('run').dispatch('click'); await settle();
  a.pending.shift()({ action: 'ASK_HUMAN', current_turn_action: 'NO_STRONG_SIGNAL', reason: 'PRIOR_RISK_UNRESOLVED',
    next_task: undefined, related_task: { id: TID, status: 'REPORTED_COMPLETE', observation: 'USER_REPORTS_CONFIRMED' } });
  await inflight;
  assert.equal(a.get('observation').disabled, true); assert.match(a.get('task').textContent, /기관에서 검증한 결과가 아닙니다/);
  assert.match(a.get('currentTurn').textContent, /미감지/); assert.match(a.get('sessionNotice').textContent, /해제되지 않습니다/);
});


test('model failure and recovery remain distinct from unresolved session risk', async () => {
  const a = await app({ deferEvaluation: true });
  const submit = async override => {
    const inflight = a.get('run').dispatch('click'); await settle();
    a.pending.shift()(override); await inflight;
  };
  const retained = { action: 'ASK_HUMAN', reason: 'PRIOR_RISK_UNRESOLVED' };
  await submit({ ...retained, model_status: 'FAILED', current_turn_action: 'ASK_HUMAN' });
  assert.match(a.get('modelNotice').textContent, /연결 확인 후 같은 문장/);
  assert.match(a.get('sessionNotice').textContent, /해제되지 않습니다/);
  assert.doesNotMatch(a.get('message').textContent, /현재 판단은 완료/);
  await submit({ ...retained, model_status: 'VALID', current_turn_action: 'NO_STRONG_SIGNAL',
    resolved_retry_task_ids: ['retry'], next_task: undefined,
    related_task: { id: TID, status: 'MODEL_RETRY_RESOLVED', observation: 'NOT_CHECKED' } });
  assert.match(a.get('modelNotice').textContent, /기술 재시도 업무를 정리/);
  assert.match(a.get('task').textContent, /모델 재시도 완료/);
  assert.match(a.get('sessionNotice').textContent, /해제되지 않습니다/);
});
