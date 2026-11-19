'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ROOT = path.resolve(__dirname, '..');
const E = require(path.join(ROOT, 'apps/shared/dmsg-engine.js'));
const V51 = require(path.join(ROOT, 'apps/shared/v51-contract.js'));
const C = { ...V51, selectedProfile: () => 'v50-baseline' };

function host(overrides = {}, remoteFetch) {
  let handler;
  const env = { DMSG_MODEL_ENABLED: '1', DMSG_SYSTEMONE_ENDPOINT: 'http://127.0.0.1:8008/v1/systemone',
    DMSG_MODEL_ID: 'model-A', DMSG_SEND_MODEL_FIELD: '1', ...overrides };
  const context = { URL, Response, Buffer, AbortController, performance, setTimeout, clearTimeout,
    console: { log() {} }, fetch: remoteFetch || (() => { throw Error('UNEXPECTED_NETWORK'); }),
    process: { env, argv: ['bun', 'server.js', '--port=9981', '--no-browser'], on() {}, platform: 'linux' },
    require(name) {
      if (name.endsWith('dmsg-engine.js')) return E;
      if (name.endsWith('v51-contract.js')) return C;
      if (name.endsWith('assets.gen.js')) return {};
      if (name === 'node:child_process') return { spawn() { throw Error('NO_BROWSER_LAUNCH'); } };
      throw Error('UNEXPECTED_REQUIRE:' + name);
    },
    Bun: { serve(options) { handler = options.fetch; return { port: 9981, stop() {} }; } } };
  vm.runInNewContext(fs.readFileSync(path.join(ROOT, 'apps/desktop/server.js'), 'utf8'), context);
  async function rawRequest(url, body, extraHeaders = {}) {
    const headers = { host: '127.0.0.1:9981', origin: 'http://127.0.0.1:9981' };
    if (body !== undefined) Object.assign(headers, { 'content-type': 'application/json', 'content-length': typeof body === 'string' ? String(Buffer.byteLength(body)) : '1' });
    Object.assign(headers, extraHeaders);
    return handler(new Request('http://127.0.0.1:9981' + url, { method: body === undefined ? 'GET' : 'POST', headers, body, duplex: 'half' }), { port: 9981 });
  }
  async function request(url, data) { return rawRequest(url, data === undefined ? undefined : JSON.stringify(data)); }
  return { request, rawRequest };
}

test('remote endpoint remains disabled even with legacy consent and allowlist environment', async () => {
  const h = host({ DMSG_SYSTEMONE_ENDPOINT: 'https://example.org/v1/systemone', DMSG_REMOTE_TEXT_CONSENT: '1',
    DMSG_REMOTE_HOST_ALLOWLIST: 'example.org', DMSG_ALLOW_UI_REMOTE: '1' });
  const health = await (await h.request('/api/health')).json();
  assert.equal(health.model.configured, false);
  const r = await (await h.request('/api/model', { text: '합성 입력' })).json();
  assert.equal(r.ok, false); assert.match(r.code, /REMOTE_RELAY_DISABLED_V50/);
  const cfg = await (await h.request('/api/config', { endpoint: 'https://example.org/v1/systemone', model_id: 'x', timeout_s: 20 })).json();
  assert.equal(cfg.ok, false); assert.equal(cfg.code, 'REMOTE_RELAY_DISABLED_V50');
});

test('endpoint changes during inference cannot relabel the original response', async () => {
  let release, sent;
  const h = host({}, async (url, options) => {
    sent = { url, body: JSON.parse(options.body) };
    return new Promise(resolve => { release = () => resolve(new Response(JSON.stringify({ model: 'model-A', answers: {} }), { headers: { 'content-type': 'application/json' } })); });
  });
  const pending = h.request('/api/model', { text: '합성 입력' });
  await new Promise(setImmediate);
  const changed = await (await h.request('/api/config', { endpoint: 'http://127.0.0.1:8010/v1/systemone', model_id: 'model-B', timeout_s: 10 })).json();
  assert.equal(changed.ok, true); release();
  const r = await (await pending).json();
  assert.equal(sent.url, 'http://127.0.0.1:8008/v1/systemone'); assert.equal(sent.body.model, 'model-A');
  assert.equal(r.ok, true); assert.equal(r.model_id_echo, 'MATCH_UNAUTHENTICATED');
});

test('URL credentials and parameters are rejected before relay', async () => {
  const h = host();
  for (const endpoint of ['http://user:pass@127.0.0.1:8008/v1/systemone',
    'http://127.0.0.1:8008/v1/systemone?key=x', 'http://127.0.0.1:8008/other']) {
    const r = await (await h.request('/api/config', { endpoint, model_id: 'x', timeout_s: 20 })).json();
    assert.equal(r.ok, false); assert.equal(r.code, 'INVALID_MODEL_ENDPOINT');
  }
});

test('2000 Korean code points and astral characters fit the desktop UTF-8 body limit', async () => {
  let calls = 0;
  const h = host({}, async () => { calls++; return new Response(JSON.stringify({ model: 'model-A', answers: {} }), { headers: { 'content-type': 'application/json' } }); });
  for (const text of ['한'.repeat(2000), '😀'.repeat(2000)]) {
    assert.equal(Array.from(text).length, 2000);
    assert.ok(Buffer.byteLength(JSON.stringify({ text })) > 5000);
    const response = await h.request('/api/model', { text });
    assert.equal(response.status, 200); assert.equal((await response.json()).ok, true);
  }
  const tooLong = await h.request('/api/model', { text: '한'.repeat(2001) });
  assert.equal(tooLong.status, 400); assert.equal((await tooLong.json()).error, 'INVALID_MODEL_TEXT');
  assert.equal(calls, 2);
});

test('declared and streamed oversized bodies are rejected before any provider request', async () => {
  const h = host();
  const response = await h.rawRequest('/api/model', 'x'.repeat(16385));
  assert.equal(response.status, 413);
  let cancelled = false;
  const stream = new ReadableStream({
    start(controller) { controller.enqueue(Buffer.alloc(10000, 120)); controller.enqueue(Buffer.alloc(10000, 120)); },
    cancel() { cancelled = true; }
  });
  const streamed = await h.rawRequest('/api/model', stream, { 'content-length': '100' });
  assert.equal(streamed.status, 413); assert.equal(cancelled, true);
  assert.equal((await streamed.json()).error, 'INVALID_PAYLOAD_SIZE');
});

test('false content lengths are rejected even when the body is below the byte cap', async () => {
  const h = host(), body = JSON.stringify({ text: '합성 입력' }), actual = Buffer.byteLength(body);
  for (const length of [actual - 1, actual + 1]) {
    const r = await h.rawRequest('/api/model', body, { 'content-length': String(length) });
    assert.equal(r.status, 400); assert.equal((await r.json()).error, 'CONTENT_LENGTH_MISMATCH');
  }
});
