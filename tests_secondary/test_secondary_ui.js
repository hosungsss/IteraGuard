'use strict';
// A minimal DOM contract test for the secondary.js browser component.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class El {
  constructor() {
    this.value = ''; this.checked = false; this.disabled = false;
    this.handlers = {}; this.textContent = '';
  }
  addEventListener(name, fn) { (this.handlers[name] ||= []).push(fn); }
  dispatch(name) { for (const fn of this.handlers[name] || []) fn(); }
}
const settle = async () => { await new Promise(setImmediate); await new Promise(setImmediate); };
function app({ enabled = false, confirm = true, delayed = false, failure = null } = {}) {
  const elements = {}; const get = id => elements[id] ||= new El();
  get('text').value = '지금 계좌로 송금하세요';
  const calls = []; const pending = [];
  const response = body => {
    if (body.mode === 'offline') return {
      mode: 'OFFLINE_LEXICAL_INDICATORS', indicators: ['payment_terms'], external_call: false
    };
    return {
      mode: 'JEV_PROVIDER_HTTP_UNATTESTED', provider_model_echo: 'jev-1.14.0',
      intent: 'active_sensitive_request', confidence: .78, active_sensitive_noul: .91
    };
  };
  const fetch = async (url, options) => {
    calls.push({url, options});
    if (url === '/api/secondary/capabilities') return {
      ok: true, json: async () => ({ jev_model: 'jev-1.14.0', jev_live_available: enabled })
    };
    if (url === '/api/secondary/check') {
      const body = JSON.parse(options.body);
      if (delayed) return new Promise(resolve => pending.push(() => resolve({ok: !failure, json: async () => failure ? {error: failure} : response(body)})));
      return {ok: !failure, json: async () => failure ? {error: failure} : response(body)};
    }
    throw new Error('Unexpected URL');
  };
  const ctx = {
    document: { getElementById: get, querySelectorAll: () => [] },
    window: { confirm: () => confirm }, fetch, console
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../arena/web/secondary.js'), 'utf8'), ctx);
  return { get, calls, pending };
}

test('initialises with offline available, Jev disabled if operator has no billing grant', async () => {
  const a = app();
  await settle();
  assert.equal(a.get('offlineCheck').disabled, false);
  assert.equal(a.get('jevCheck').disabled, true);
  assert.match(a.get('secondaryCapability').textContent, /무료/);
  assert.equal(a.calls.filter(x => x.url === '/api/secondary/check').length, 0);
});

test('offline button uses local endpoint without external consent and is never labelled Jev', async () => {
  const a = app();
  await settle();
  a.get('offlineCheck').dispatch('click');
  await settle();
  const calls = a.calls.filter(x => x.url === '/api/secondary/check');
  assert.equal(calls.length, 1);
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    text: '지금 계좌로 송금하세요', synthetic_only: true, mode: 'offline'
  });
  assert.match(a.get('secondaryStatus').textContent, /무료 로컬/);
  assert.match(a.get('secondarySource').textContent, /Jev·Zoro 모델 추론 아님/);
});

test('Jev button requires provider configured and user checkbox', async () => {
  const a = app({enabled:true});
  await settle();
  assert.equal(a.get('jevCheck').disabled, true);
  a.get('jevCheck').dispatch('click');
  await settle();
  assert.equal(a.calls.filter(x => x.url === '/api/secondary/check').length, 0);
  a.get('jevConsent').checked = true;
  a.get('jevConsent').dispatch('change');
  assert.equal(a.get('jevCheck').disabled, false);
});

test('Jev remote call has separate consent and no local policy action', async () => {
  const a = app({enabled:true});
  await settle();
  a.get('jevConsent').checked = true; a.get('jevConsent').dispatch('change');
  a.get('jevCheck').dispatch('click');
  await settle();
  const call = a.calls.find(x => x.url === '/api/secondary/check');
  assert.deepEqual(JSON.parse(call.options.body), {
    text: '지금 계좌로 송금하세요', synthetic_only: true, mode: 'jev', consent_external: true
  });
  assert.match(a.get('secondaryStatus').textContent, /Jev 1.14 응답 수신/);
  assert.match(a.get('secondarySource').textContent, /독립 신원 인증 아님/);
  assert.equal(a.get('jevConsent').checked, false);
});

test('cancelled confirm does not issue chargeable API call', async () => {
  const a = app({enabled:true, confirm:false});
  await settle();
  a.get('jevConsent').checked = true; a.get('jevConsent').dispatch('change');
  a.get('jevCheck').dispatch('click');
  await settle();
  assert.equal(a.calls.filter(x => x.url === '/api/secondary/check').length, 0);
});

test('HTTP 402 is not masked with fabricated model response', async () => {
  const a = app({enabled:true, failure:'PROVIDER_CREDITS_REQUIRED'});
  await settle();
  a.get('jevConsent').checked = true; a.get('jevConsent').dispatch('change');
  a.get('jevCheck').dispatch('click');
  await settle();
  assert.match(a.get('secondaryResult').textContent, /유료 크레딧/);
  assert.match(a.get('secondarySource').textContent, /실제 Jev 결과를 받지 못했습니다/);
});

test('late result cannot be shown as current after text changed', async () => {
  const a = app({enabled:true,delayed:true});
  await settle();
  a.get('jevConsent').checked = true; a.get('jevConsent').dispatch('change');
  a.get('jevCheck').dispatch('click');
  await settle();
  assert.equal(a.pending.length, 1);
  a.get('text').value = '다른 합성 문장';
  a.get('text').dispatch('input');
  assert.equal(a.get('jevConsent').checked, false);
  a.pending.shift()();
  await settle();
  assert.equal(a.get('secondaryResult').textContent, '');
  assert.match(a.get('secondaryStatus').textContent, /입력이 변경/);
});

test('zero auto-Jev calls on text input and sample input', async () => {
  const a = app({enabled:true});
  await settle();
  a.get('text').value = '다른 입력'; a.get('text').dispatch('input');
  await settle();
  assert.equal(a.calls.filter(x => x.url === '/api/secondary/check').length, 0);
});
