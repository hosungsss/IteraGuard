/*
 * 의심계 desktop host (compiled with `bun build --compile` for macOS, Windows, Linux).
 *
 * Serves the embedded app on 127.0.0.1 only and, when configured, relays typed-decision
 * requests to an operator's kev /v1/systemone server. The relay applies the same transport
 * local rules: exact path, loopback only, no redirects, JSON-only, size cap,
 * strict JSON and model-echo rule. v5 disables remote endpoints even through environment settings.
 * Judgments are produced by the shared engine in the page, never by this host.
 */
'use strict';
const E = require('../shared/dmsg-engine.js');
const ASSETS = require('./assets.gen.js');
const C = require('../shared/v51-contract.js');
const { spawn } = require('node:child_process');

const VERSION = '5.1-development';
const env = process.env;
const args = process.argv.slice(2);
const argPort = (args.find(a => a.startsWith('--port=')) || '').split('=')[1];
const noBrowser = args.includes('--no-browser') || env.DMSG_NO_BROWSER === '1';

const cfg = {
  endpoint: env.DMSG_SYSTEMONE_ENDPOINT || '',
  model_id: env.DMSG_MODEL_ID || '',
  enabled: env.DMSG_MODEL_ENABLED === '1' || !!env.DMSG_SYSTEMONE_ENDPOINT,
  timeout_s: Number(env.DMSG_MODEL_TIMEOUT_S || 20),
};
const LOOPBACK = new Set(['127.0.0.1', 'localhost']);
const SAFE_ID = /^[A-Za-z0-9._\/:-]{1,128}$/;
const MAX_REQUEST_BYTES = 16384; // 2,000 Unicode code points, UTF-8 and JSON overhead.

async function readBoundedBody(req, declaredLength) {
  if (!req.body) return { error: 'INVALID_PAYLOAD_SIZE', status: 413 };
  const reader = req.body.getReader(), chunks = []; let size = 0;
  try {
    for (;;) {
      const part = await reader.read();
      if (part.done) break;
      size += part.value.byteLength;
      if (size > MAX_REQUEST_BYTES) {
        await reader.cancel().catch(() => {});
        return { error: 'INVALID_PAYLOAD_SIZE', status: 413 };
      }
      chunks.push(Buffer.from(part.value));
    }
  } catch {
    return { error: 'INVALID_REQUEST_BODY', status: 400 };
  } finally { reader.releaseLock(); }
  if (size !== declaredLength) return { error: 'CONTENT_LENGTH_MISMATCH', status: 400 };
  return { text: Buffer.concat(chunks, size).toString('utf8') };
}

function checkEndpoint(raw, fromUi) {
  let u; try { u = new URL(raw); } catch { return 'INVALID_MODEL_ENDPOINT'; }
  if (u.username || u.password || u.search || u.hash || u.pathname.replace(/\/+$/, '') !== '/v1/systemone') return 'INVALID_MODEL_ENDPOINT';
  if (!['http:', 'https:'].includes(u.protocol) || !u.hostname) return 'INVALID_MODEL_ENDPOINT';
  const h = u.hostname.toLowerCase();
  if (u.protocol === 'http:' && !LOOPBACK.has(h)) return 'HTTPS_REQUIRED';
  if (!LOOPBACK.has(h)) return 'REMOTE_RELAY_DISABLED_V50';
  return null;
}
function timeoutOk(t) { return typeof t === 'number' && isFinite(t) && t >= 0.5 && t <= 60; }
function status() {
  let host = null; try { host = cfg.endpoint ? new URL(cfg.endpoint).hostname : null; } catch {}
  return { configured: !!(cfg.enabled && cfg.endpoint && cfg.model_id && !checkEndpoint(cfg.endpoint, false) && timeoutOk(cfg.timeout_s)),
    endpoint: cfg.endpoint, endpoint_host: host, model_id: cfg.model_id, timeout_s: cfg.timeout_s, verified_model: false, calibrated: false,
    send_model_field: env.DMSG_SEND_MODEL_FIELD === '1', require_model_echo: env.DMSG_REQUIRE_MODEL_ECHO === '1',
    provider_temperature: 1.52, provider_temperature_provenance: 'LOCAL_EXPORT_CONFIGURATION_NOT_REMOTE_ATTESTATION',
    domain_calibration: 'NOT_ESTABLISHED', transport_scope: 'LOOPBACK_ONLY', execution_manifest: C.executionManifest(), selected_profiles: { legacy: C.selectedProfile('legacy'), dra: C.selectedProfile('dra') } };
}
async function relay(text, policyId, requestedProfile) {
  const fail = c => ({ ok: false, code: 'ModelUnavailable:' + c });
  // Bind every asynchronous request to the endpoint/configuration that started it.
  const requestCfg = Object.freeze({ ...cfg, send_model_field: env.DMSG_SEND_MODEL_FIELD === '1',
    require_model_echo: env.DMSG_REQUIRE_MODEL_ECHO === '1', api_key: env.DMSG_MODEL_API_KEY || '' });
  const policy = policyId === undefined ? 'legacy' : policyId;
  if (!['legacy', 'dra'].includes(policy)) return fail('UNSUPPORTED_POLICY_ID');
  let profile, profileBinding, payload;
  try {
    profile = C.selectedProfile(policy);
    if (requestedProfile !== undefined && requestedProfile !== profile) return fail('UNSUPPORTED_PROFILE_POLICY_COMBINATION');
    // Registry selection, binding and questions are one synchronous snapshot.
    profileBinding = Object.freeze(JSON.parse(JSON.stringify(C.requestBinding(profile, policy))));
    if (C.validateBinding(profileBinding, profile, policy) === false) return fail('PROFILE_BINDING_MISMATCH');
    payload = JSON.parse(JSON.stringify(C.questionPayload(text, profile, policy)));
  } catch { return fail('PROFILE_CONTRACT_UNAVAILABLE'); }
  if (!(requestCfg.enabled && requestCfg.endpoint && requestCfg.model_id)) return fail('MODEL_NOT_CONFIGURED');
  if (!timeoutOk(requestCfg.timeout_s)) return fail('INVALID_TIMEOUT_CONFIG');
  const bad = checkEndpoint(requestCfg.endpoint, false); if (bad) return fail(bad);
  if (requestCfg.send_model_field) payload.model = requestCfg.model_id;
  const body = JSON.stringify(payload);
  if (Buffer.byteLength(body) > 30000) return fail('REQUEST_TOO_LARGE');
  const headers = { 'Content-Type': 'application/json' };
  if (requestCfg.api_key) headers.Authorization = 'Bearer ' + requestCfg.api_key;
  const ctl = new AbortController(), t0 = performance.now();
  const timer = setTimeout(() => ctl.abort(), requestCfg.timeout_s * 1000);
  let res, raw;
  try {
    res = await fetch(requestCfg.endpoint, { method: 'POST', headers, body, redirect: 'manual', signal: ctl.signal });
    if (res.status !== 200) return fail('HTTP_STATUS_NOT_OK');
    if ((res.headers.get('content-type') || '').split(';')[0].trim().toLowerCase() !== 'application/json') return fail('UNEXPECTED_MODEL_CONTENT_TYPE');
    const reader = res.body.getReader(), chunks = []; let n = 0;
    for (;;) { const { done, value } = await reader.read(); if (done) break; n += value.length; if (n > 120000) { ctl.abort(); return fail('RESPONSE_TOO_LARGE'); } chunks.push(value); }
    raw = Buffer.concat(chunks).toString('utf8');
  } catch (e) {
    return fail('MODEL_TRANSPORT_ERROR_' + transportName(e));
  } finally { clearTimeout(timer); }
  let value;
  try { value = E.strictJSON(raw); } catch { return fail('INVALID_RESPONSE_JSON'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return fail('INVALID_RESPONSE_JSON');
  let echo;
  if (Object.prototype.hasOwnProperty.call(value, 'model')) {
    if (value.model !== requestCfg.model_id) return fail('MODEL_ID_MISMATCH');
    echo = 'MATCH_UNAUTHENTICATED';
  } else if (requestCfg.require_model_echo) return fail('MODEL_ID_ECHO_REQUIRED');
  else echo = 'ABSENT';
  return { ok: true, raw: value, profile_binding: profileBinding, latency_ms: Math.round((performance.now() - t0) * 100) / 100, model_id_echo: echo };
}

// Same names as the Python bridge (type(exc).__name__ of the OS error) so codes agree across hosts.
function transportName(e) {
  if (e && e.name === 'AbortError') return 'TimeoutError';
  const code = String((e && (e.code || (e.cause && e.cause.code))) || '');
  if (/REFUSED/i.test(code)) return 'ConnectionRefusedError';
  if (/RESET/i.test(code)) return 'ConnectionResetError';
  if (/ENOTFOUND|EAI_AGAIN|DNS/i.test(code)) return 'gaierror';
  if (/CERT|SSL|TLS/i.test(code)) return 'SSLError';
  return 'OSError';
}
const SEC = {
  'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'",
  'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Resource-Policy': 'same-origin'
};
const json = (code, data) => new Response(JSON.stringify(data), { status: code, headers: { ...SEC, 'Content-Type': 'application/json; charset=utf-8' } });

function startServer(port) {
  return Bun.serve({
    hostname: '127.0.0.1', port,
    async fetch(req, server) {
      const url = new URL(req.url), p = server.port;
      // DNS-rebinding defense: exactly one Host, and it must be this loopback origin.
      const host = (req.headers.get('host') || '').toLowerCase();
      if (host.includes(',') || ![`127.0.0.1:${p}`, `localhost:${p}`].includes(host)) return json(403, { error: 'LOCAL_HOST_ONLY' });
      if (req.method === 'GET') {
        if (url.pathname === '/api/health') return json(200, { app: 'dmsg-desktop', version: VERSION, model: status() });
        const path = url.pathname === '/' ? '/index.html' : url.pathname;
        const a = ASSETS[path];
        if (!a) return json(404, { error: 'NOT_FOUND' });
        return new Response(Buffer.from(a.b64, 'base64'), { headers: { ...SEC, 'Content-Type': a.type } });
      }
      if (req.method !== 'POST') return json(405, { error: 'METHOD' });
      const origin = req.headers.get('origin');
      if (origin !== null && ![`http://127.0.0.1:${p}`, `http://localhost:${p}`].includes(origin)) return json(403, { error: 'UNTRUSTED_REQUEST_CONTEXT' });
      const sfs = req.headers.get('sec-fetch-site');
      if (sfs !== null && !['same-origin', 'none'].includes(sfs)) return json(403, { error: 'UNTRUSTED_REQUEST_CONTEXT' });
      if ((req.headers.get('content-type') || '').split(';')[0].trim() !== 'application/json') return json(415, { error: 'JSON_ONLY' });
      const lengthHeader = req.headers.get('content-length') || '';
      const len = Number(lengthHeader);
      if (!/^[1-9][0-9]*$/.test(lengthHeader) || !(len <= MAX_REQUEST_BYTES)) return json(413, { error: 'INVALID_PAYLOAD_SIZE' });
      const body = await readBoundedBody(req, len);
      if (body.error) return json(body.status, { error: body.error });
      let b; try { b = E.strictJSON(body.text); } catch { return json(400, { error: 'INVALID_JSON' }); }
      if (!b || typeof b !== 'object' || Array.isArray(b)) return json(400, { error: 'OBJECT_REQUIRED' });
      if (url.pathname === '/api/model') {
        if (Object.keys(b).some(k => !['text', 'policy_id', 'profile_id'].includes(k)) || typeof b.text !== 'string' || !b.text.trim() || E.cpLen(b.text) > 2000) return json(400, { error: 'INVALID_MODEL_TEXT' });
        if (b.policy_id !== undefined && (typeof b.policy_id !== 'string' || !['legacy', 'dra'].includes(b.policy_id))) return json(400, { ok: false, code: 'UNSUPPORTED_POLICY_ID' });
        if (b.profile_id !== undefined && (typeof b.profile_id !== 'string' || !SAFE_ID.test(b.profile_id))) return json(400, { ok: false, code: 'INVALID_PROFILE_ID' });
        return json(200, await relay(b.text, b.policy_id, b.profile_id));
      }
      if (url.pathname === '/api/config') {
        if (Object.keys(b).some(k => !['endpoint', 'model_id', 'timeout_s'].includes(k))) return json(400, { ok: false, code: 'UNKNOWN_FIELD' });
        const bad = checkEndpoint(String(b.endpoint || ''), true); if (bad) return json(200, { ok: false, code: bad });
        if (!SAFE_ID.test(String(b.model_id || ''))) return json(200, { ok: false, code: 'INVALID_MODEL_ID' });
        if (!timeoutOk(b.timeout_s)) return json(200, { ok: false, code: 'INVALID_TIMEOUT_CONFIG' });
        Object.assign(cfg, { endpoint: b.endpoint, model_id: b.model_id, timeout_s: b.timeout_s, enabled: true });
        return json(200, { ok: true, model: status() });
      }
      return json(404, { error: 'NOT_FOUND' });
    }
  });
}

function openBrowser(url) {
  if (noBrowser) return;
  const plat = process.platform;
  const cmd = plat === 'darwin' ? ['open', [url]] : plat === 'win32' ? ['cmd', ['/c', 'start', '', url]] : ['xdg-open', [url]];
  try { const c = spawn(cmd[0], cmd[1], { stdio: 'ignore', detached: true }); c.on('error', () => {}); c.unref(); } catch {}
}

const server = startServer(argPort ? Number(argPort) : Number(env.DMSG_PORT || 0));
const url = `http://127.0.0.1:${server.port}/`;
console.log(`\n  의심계 v${VERSION} — IteraGuard Doubt Meter (synthetic demo, not a fraud verdict)`);
console.log(`  열기: ${url}`);
console.log(`  모델: ${status().configured ? '설정됨 (진품 미인증)' : '미설정 — 조로 선택 시 판단 보류'}`);
console.log('  종료: 이 창을 닫거나 Ctrl+C\n');
openBrowser(url);
process.on('SIGINT', () => { server.stop(); process.exit(0); });
