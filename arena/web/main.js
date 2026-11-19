'use strict';
let openTaskQueue = [];
let session = null, task = null, busy = false, editorRevision = 0, lastDecision = null, profile = null, visitedSessions = [];
const el = id => document.getElementById(id);
const SESSION_KEY = 'dmsg-arena-v5-session';
const HISTORY_KEY = 'dmsg-arena-v5-session-ids';
const labels = {
  NO_STRONG_SIGNAL: '뚜렷한 위험 행동 요청 미감지 (안전 보증 아님)',
  CAUTION: '추가 확인 필요', PAUSE_AND_VERIFY: '잠시 멈추고 독립 확인',
  ASK_HUMAN: '판단 보류 · 사람 검토 필요'
};
const signalLabels = {
  red: '빨강 · 피싱 의심 매우 높음',
  orange: '주황 · 피싱 의심 높음',
  green: '초록 · 문구에서 뚜렷한 피싱 신호를 찾지 못했어요',
  gray: '회색 · 판단 어려움'
};
function conversationSignal(type, detail = {}) {
  // Best-effort UI-only notification; old DOM test shims need not implement
  // EventTarget. No raw transcript is written to storage or sent remotely.
  if (typeof CustomEvent === 'function' && typeof document.dispatchEvent === 'function')
    document.dispatchEvent(new CustomEvent('iteraguard:' + type, { detail }));
}
async function apiOnce(path, body) {
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const timer = controller && typeof setTimeout !== 'undefined' ? setTimeout(() => controller.abort(), 70000) : null;
  try {
    const options = body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {};
    if (controller) options.signal = controller.signal;
    const r = await fetch(path, options);
    if (r.status === 401 || r.status === 403) throw Error('접속 인증이 만료되었거나 접근 권한이 없습니다. 시연 접속 화면에서 다시 인증해 주세요.');
    if (r.status === 429) throw Object.assign(Error('모델이 다른 요청을 처리하고 있습니다. 잠시 후 저장 상태를 확인하고 다시 시도해 주세요.'), { recoverable: true });
    const type = r.headers?.get('content-type');
    if (type && !type.toLowerCase().startsWith('application/json')) throw Error('서버가 판단 JSON 대신 다른 페이지를 반환했습니다. 접속 인증과 서버 연결을 확인해 주세요.');
    let d;
    try { d = await r.json(); } catch (_) { throw Error('서버 응답 형식을 확인할 수 없습니다. 저장 상태를 재조회해 주세요.'); }
    if (!r.ok) throw Object.assign(Error(d?.error || 'REQUEST_FAILED'), { recoverable: [502, 504].includes(r.status) });
    if (!d || typeof d !== 'object' || Array.isArray(d)) throw Error('INVALID_API_RESPONSE');
    return d;
  } catch (e) {
    if (e.name === 'AbortError') throw Object.assign(Error('응답 대기 시간이 초과됐습니다. 서버에서 처리가 완료됐을 수 있으므로 저장 상태를 먼저 재조회해 주세요.'), { recoverable: true });
    if (e instanceof TypeError) e.recoverable = true;
    throw e;
  } finally { if (timer !== null) clearTimeout(timer); }
}
function recoveryNotice(message) {
  const node = typeof document.getElementById === 'function' ? el('recoveryStatus') : null;
  if (node) node.textContent = message;
}
async function api(path, body) {
  // Freeze the request: never invent a new ID/version or silently change text.
  const snapshot = body === undefined ? undefined : JSON.parse(JSON.stringify(body));
  const canRecover = snapshot === undefined || (path === '/api/evaluate' &&
    typeof snapshot.session_id === 'string' && typeof snapshot.request_id === 'string' && Number.isInteger(snapshot.version));
  for (let attempt = 0; ; attempt++) {
    try {
      const result = await apiOnce(path, snapshot);
      if (attempt) recoveryNotice('연결 복구 완료 · 동일 요청의 처리 결과를 확인했습니다.');
      return result;
    } catch (error) {
      if (!canRecover || !error.recoverable || attempt >= 2) {
        recoveryNotice('자동 복구 중단 · ' + error.message);
        throw error;
      }
      recoveryNotice(`자동 복구 ${attempt + 1}/2 · 저장 상태를 확인합니다.`);
      if (typeof setTimeout === 'function') await new Promise(resolve => setTimeout(resolve, 400 * (attempt + 1)));
      if (snapshot) {
        // A lost response may already be committed. Reconcile before resending.
        let state;
        try { state = await apiOnce('/api/state?session_id=' + encodeURIComponent(snapshot.session_id)); }
        catch (stateError) {
          recoveryNotice('자동 복구 중단 · 저장 상태를 확인할 수 없어 요청을 다시 보내지 않았습니다.');
          throw stateError;
        }
        if (!Array.isArray(state.events) || !Number.isInteger(state.version)) throw Error('RECOVERY_INVALID_STATE');
        const saved = state.events.find(event => event.request_id === snapshot.request_id);
        if (saved) {
          if (saved.session_id !== snapshot.session_id || saved.version !== snapshot.version + 1 ||
              state.version !== saved.version || !Object.hasOwn(labels, saved.action)) {
            recoveryNotice('자동 복구 중단 · 세션이 변경되었습니다. 저장 상태를 재조회해 주세요.');
            throw Error('RECOVERY_STATE_CHANGED');
          }
          recoveryNotice('자동 복구 완료 · 저장된 결과를 복원했습니다. 새 판단은 실행하지 않았습니다.');
          return saved;
        }
        if (state.version !== snapshot.version || state.lifecycle !== 'OPEN') {
          recoveryNotice('자동 복구 중단 · 세션이 변경되었습니다. 저장 상태를 재조회해 주세요.');
          throw Error('RECOVERY_STATE_CHANGED');
        }
      }
    }
  }
}
function rememberSession(id) {
  visitedSessions = [...new Set([...visitedSessions, id])];
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SESSION_KEY, id);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(visitedSessions));
    }
  } catch (_) {}
  renderSessionHistory();
}
function renderSessionHistory() {
  el('sessionHistory').textContent = '';
  for (const [index, id] of visitedSessions.entries()) {
    const option = document.createElement('option'); option.value = id;
    option.textContent = '기록 ' + (index + 1) + ' · ' + id.slice(0, 8) + (session?.session_id === id ? ' · 현재' : '');
    el('sessionHistory').appendChild(option);
  }
  el('sessionHistory').value = session?.session_id || '';
}
function loadSessionHistory() {
  try {
    const ids = typeof localStorage !== 'undefined' ? JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') : [];
    if (Array.isArray(ids)) visitedSessions = [...new Set(ids.filter(id => typeof id === 'string' && /^[0-9a-f]{32}$/.test(id)))];
  } catch (_) {}
}
function rememberedSession() {
  try { return typeof localStorage !== 'undefined' ? localStorage.getItem(SESSION_KEY) : null; } catch (_) { return null; }
}
function isClosed() { return session?.lifecycle === 'CLOSED_UNRESOLVED'; }
function controls() {
  const closed = isClosed();
  for (const id of ['run', 'text', 'review']) el(id).disabled = busy || closed;
  el('observation').disabled = busy || closed || !task;
  el('taskQueue').disabled = busy || closed || !openTaskQueue.length;
  el('exportEvidence').disabled = busy || !session;
  el('downloadEvidence').disabled = busy || !session;
  el('refresh').disabled = busy || !session;
  el('close').disabled = busy || !session || closed;
  el('reopen').disabled = busy || !closed;
  // Legacy close/new controls remain; the explicit independent-analysis path preserves old incidents.
  el('new').disabled = busy || !!(session && !closed && session.version > 0);
  el('loadSession').disabled = busy || !visitedSessions.length;
  el('sessionHistory').disabled = el('loadSession').disabled;
  if (el('newAnalysis')) el('newAnalysis').disabled = busy;
  if (el('openSheet')) el('openSheet').disabled = busy;
}
function renderLifecycle() {
  el('lifecycle').textContent = isClosed() ? '미해결 상태로 보관 중' : '확인 진행 중';
  el('riskState').textContent = session?.prior_pause ? '세션: 앞서 감지한 위험이 미해결 상태로 남아 있습니다.' : '세션: 기록된 강한 중단 이력 없음 (안전 보증 아님)';
  el('lifecycleNotice').textContent = isClosed() ? '보관은 위험 해제가 아닙니다. 이전 이력을 유지하며 재개할 수 있습니다.' : '확인을 마치지 못해도 미해결 상태로 보관할 수 있습니다. 재개 시 이전 위험과 업무 이력이 유지됩니다.';
}
function currentInputRequired(message) {
  if (el('inlineSignal')) el('inlineSignal').hidden = true;
  globalThis.renderSignalChoiceScores?.();
  if (el('nextAction')) { el('nextAction').textContent = ''; el('nextAction').hidden = true; }
  if (el('verdictPanel')) el('verdictPanel').hidden = false;
  el('executionSource').textContent = '현재 입력의 실행 출처는 재평가 후 확인하세요.';
  el('action').textContent = 'ASK_HUMAN'; el('message').textContent = message;
  for (const id of ['evidence', 'reason', 'currentTurn', 'sessionNotice', 'modelNotice']) el(id).textContent = '';
}
async function showInlineSignal(binding, modelStatus, currentAction) {
  const panel = el('inlineSignal');
  if (!panel) return;
  let grade = 'gray';
  let label = '회색 · 조로 신호등 결과를 받지 못했어요';
  let scoreResponse;
  if (modelStatus === 'VALID') {
    try {
      const signal = await apiOnce('/api/signal', { text: binding.text, synthetic_only: true });
      if (Object.hasOwn(signalLabels, signal.grade)) {
        scoreResponse = signal;
        grade = signal.grade;
        label = signalLabels[grade];
        if ((grade === 'green' && currentAction !== 'NO_STRONG_SIGNAL') ||
            (['red', 'orange'].includes(grade) && currentAction === 'NO_STRONG_SIGNAL')) {
          label += ' · 두 결과가 다릅니다. 아래 행동 안내를 확인하세요.';
        }
      }
    } catch {
      // This observation can fail independently of the already saved decision.
    }
  }
  if (lastDecision !== binding || !matchesCurrentInput(binding) || session.version !== binding.version) return;
  panel.dataset.grade = grade;
  el('inlineSignalGrade').textContent = label;
  globalThis.renderSignalChoiceScores?.(scoreResponse?.scores, grade, scoreResponse?.context_review?.original?.grade);
  panel.hidden = false;
}
// Display-only projection: do not mutate d or infer that user reports clear risk.
function decisionCopy(d) {
  const current = d.current_turn_action || d.action;
  const prior = d.reason === 'PRIOR_RISK_UNRESOLVED' || d.execution_trace?.session?.prior_pause_before === true;
  const failed = d.model_status === 'FAILED';
  const recovered = d.model_status === 'VALID' && Array.isArray(d.resolved_retry_task_ids) && d.resolved_retry_task_ids.length > 0;
  const reason = d.current_turn_reason || d.reason;
  const descriptions = {
    NO_STRONG_SIGNAL: '이번 문장에서 뚜렷한 위험 행동 요청은 감지되지 않았습니다. 안전이 확인됐다는 뜻은 아닙니다.',
    CAUTION: '이번 요청은 추가 확인이 필요합니다. 발신자와 요청의 진위는 이 분석만으로 확인되지 않습니다.',
    PAUSE_AND_VERIFY: '이번 문장에서 실행 전 확인이 필요한 행동 요청이 감지되었습니다.',
    ASK_HUMAN: '이번 요청을 명확히 판단하기 어려워 추가 확인이 필요합니다.'
  };
  const context = {
    V51_EXPLICIT_PROTECTIVE_WARNING: '이번 문장은 인증정보 전달을 금지하는 예방 안내로 해석했습니다.',
    V51_EXPLICIT_CREDENTIAL_WARNING: '이번 문장은 인증정보 전달을 금지하는 예방 안내로 해석했습니다.',
    V51_EXPLICIT_PAST_CREDENTIAL_REPORT: '이번 문장은 과거 요청을 인용한 내용이며, 현재 전달 요구는 확인되지 않았습니다.',
    USER_REQUESTED_REVIEW: '요청하신 대로 이번 문장을 사람의 검토 대상으로 남겼습니다.'
  };
  let title = failed ? '이번 메시지를 분석하지 못했습니다' :
    current === 'PAUSE_AND_VERIFY' ? '요청을 실행하기 전에 확인하세요' :
    prior ? '이전 요청은 확인이 필요합니다' : current === 'ASK_HUMAN' ? '요청 내용을 추가로 확인해 주세요' :
    current === 'CAUTION' ? '요청의 진위를 한 번 더 확인하세요' : '뚜렷한 위험 요청은 감지되지 않았습니다';
  const message = failed ? '모델 응답을 받지 못했거나 응답 검사에 실패했습니다. 이번 문장의 위험 여부는 판단하지 못했습니다.' :
    context[reason] || descriptions[current] || '이번 문장의 판단 정보를 확인할 수 없습니다.';
  let next = failed ? '연결 상태를 확인한 뒤 같은 문장을 다시 분석하세요.' +
    (prior ? ' 이전 요청은 기존 공식 경로로 확인할 때까지 실행을 보류하세요.' : '') :
    (prior || current === 'PAUSE_AND_VERIFY') ? '확인되지 않은 요청은 실행을 보류하고, 기존에 알고 있던 연락처로 요청 내용을 확인하세요.' :
    current === 'ASK_HUMAN' ? '누가 무엇을 요청하는지 확인하고, 필요한 경우 신뢰할 수 있는 담당자에게 검토를 요청하세요.' :
    current === 'CAUTION' ? '메시지에 적힌 연락처 대신 기존에 알고 있던 연락처로 요청 내용을 확인하세요.' : '';
  // Use only validated evidence spans, and only to specialize an existing pause recommendation.
  const cp = Array.from(el('text').value);
  const spans = (d.evidence || []).filter(e => Number.isInteger(e.start) && Number.isInteger(e.end) && e.start >= 0 && e.end > e.start && e.end <= cp.length);
  const evidence = spans.map(e => cp.slice(e.start, e.end).join('')).join(' ');
  if (!failed && current === 'PAUSE_AND_VERIFY') {
    if (/송금|이체|대금/.test(evidence)) { title = '송금하기 전에 요청을 확인하세요'; next = '송금을 보류하고, 기존에 알고 있던 상대방 연락처로 지급 요청과 계좌 정보를 확인하세요.'; }
    else if (/인증번호|비밀번호|OTP/i.test(evidence)) next = '요청받은 인증정보를 전달하지 말고, 본인이 시작한 절차인지 해당 서비스의 공식 경로에서 확인하세요.';
  }
  const tasks = Array.isArray(d.open_tasks) ? d.open_tasks : [];
  const earlier = tasks.filter(t => Number.isInteger(t.created_version) && Number.isInteger(d.version) && t.created_version < d.version);
  const count = Number.isInteger(d.open_task_count) ? d.open_task_count : tasks.length;
  const history = (prior ? '이전 요청 · 확인 대기. 이번 결과나 사용자 완료 보고만으로 이전 위험이 해제되지 않습니다.' : '') +
    (earlier.length ? ' 이전에 생성된 미해결 업무 ' + earlier.length + '건.' : '') +
    (count ? ' 이 분석 기록의 미해결 업무는 총 ' + count + '건입니다. 앱이 대신 확인하거나 자동으로 해결 처리하지는 않습니다.' : '');
  return { title, message, next, history, current, failed, recovered };
}
function renderDecision(d) {
  const copy = decisionCopy(d);
  if (el('verdictPanel')) el('verdictPanel').hidden = false;
  el('action').textContent = d.action; el('reason').textContent = d.reason;
  el('message').textContent = copy.message;
  el('verdictTitle').textContent = copy.title;
  el('verdictKicker').textContent = '분석 결과 · 실행 여부는 별도 확인';
  if (el('nextAction')) { el('nextAction').textContent = copy.next ? '다음 행동 · ' + copy.next : ''; el('nextAction').hidden = !copy.next; }
  if (el('verdictHint')) { el('verdictHint').textContent = ''; el('verdictHint').hidden = true; }
  el('currentTurn').textContent = '현재 문장: ' + (copy.failed ? '분석 실패 · 판단 불가' : labels[copy.current] || '확인 불가');
  el('sessionNotice').textContent = copy.history;
  el('sessionNotice').hidden = !copy.history;
  el('modelNotice').textContent = copy.recovered ? '분석 복구 완료 · 같은 문장을 다시 분석했습니다.' : '';
  el('executionSource').textContent = copy.failed ? '판단 출처: 모델 연결 또는 응답 검증 실패' : d.provenance?.execution_source === 'CONTROLLED_CLIENT' ? '판단 출처: 통제 응답 · 실제 모델 추론 아님' : '판단 출처: 모델 응답 · 체크포인트 신원 미인증';
}
function renderQueue(items) {
  const previousSelection = el('taskQueue').value || task;
  openTaskQueue = (items || []).filter(t => t.status === 'OPEN');
  const select = el('taskQueue'); select.textContent = '';
  for (const t of openTaskQueue) {
    const option = document.createElement('option'); option.value = t.id;
    option.textContent = t.type + ' · ' + t.id.slice(0,8); select.appendChild(option);
  }
  select.value = openTaskQueue.some(t => t.id === previousSelection) ? previousSelection : (openTaskQueue[0]?.id || '');
  el('queueCount').textContent = '미해결 업무 ' + openTaskQueue.length + '건 · 중단 요청 우선';
}
function renderTask(item) {
  task = item?.status === 'OPEN' ? item.id : null;
  if (task && openTaskQueue.some(t => t.id === task)) el('taskQueue').value = task;
  if (task) {
    const observed = item.observation === 'UNRESOLVED' ? ' · 확인했지만 미해결로 보고됨' : '';
    el('task').textContent = '열린 확인 작업' + observed + ' · #' + item.id.slice(0, 8) + '\n' + (item.instruction || '독립적으로 알고 있던 공식 경로에서 확인하세요. 실제 연락은 수행되지 않습니다.');
  } else if (item?.status === 'MODEL_RETRY_RESOLVED') {
    el('task').textContent = '모델 재시도 완료 · #' + item.id.slice(0, 8);
  } else if (item) {
    el('task').textContent = '확인 보고 보관 · #' + item.id.slice(0, 8) + '\n사용자가 입력한 확인 결과입니다. 기관에서 검증한 결과가 아닙니다. 이전 위험 때문에 같은 확인 작업을 자동으로 반복 생성하지 않습니다.';
  } else el('task').textContent = '현재 확인 작업 없음';
  el('observation').value = 'NOT_CHECKED';
}
function matchesCurrentInput(binding) {
  return binding && session && binding.session_id === session.session_id && !isClosed() &&
    binding.revision === editorRevision && binding.text === el('text').value &&
    binding.review === el('review').checked;
}
async function serial(fn) {
  if (busy) return;
  busy = true; controls();
  try { await fn(); }
  catch (e) {
    conversationSignal('invalidate', { reason: 'request_failed' });
    lastDecision = null;
    el('status').textContent = '현재 요청 실패 / CURRENT REQUEST FAILED';
    currentInputRequired('현재 결과를 확정할 수 없습니다. 저장 상태를 재조회해 주세요.');
    el('reason').textContent = e.message; el('result').textContent = '';
    el('task').textContent = '업무 상태는 저장 상태 재조회에서 확인하세요.'; task = null;
  } finally { busy = false; controls(); }
}
async function loadProfile() {
  profile = await api('/api/manifest');
  const model = profile.runtime_model;
  if (el('connectionStatus')) el('connectionStatus').textContent = !model ? '모델 연결 상태 정보 없음 · 실제 판단으로 확인 필요' :
    !model.configured ? '모델 미설정 · 현재 실제 Zoro 판단을 사용할 수 없습니다.' :
    !model.timeout_valid ? '모델 대기 시간 설정 오류 · 운영자 확인 필요' :
    '모델 설정 있음 · 실제 연결과 모델 신원은 아직 확인되지 않았습니다.';
  el('manifest').textContent = JSON.stringify(profile, null, 2);
  const expected = profile.execution_manifest?.runtime?.expected_temperature;
  el('temperatureNote').textContent = Number.isFinite(expected)
    ? `계약의 기준 온도 ${expected} · 실제 서버 적용값은 서버 모델 정보에서 확인하세요.` : '';
}
async function start() {
  const created = await api('/api/start', {});
  if (typeof created.session_id !== 'string' || !created.session_id || !Number.isInteger(created.version)) throw Error('INVALID_SESSION_RESPONSE');
  session = { ...created, lifecycle: 'OPEN', prior_pause: false };
  conversationSignal('reset', { session_id: session.session_id, reason: 'new_session' });
  rememberSession(session.session_id);
  task = null; lastDecision = null; editorRevision += 1; renderQueue([]);
  el('executionSource').textContent = '평가 전 · 현재 세션의 모델 실행 기록 없음';
  el('status').textContent = '새 세션 · ' + session.session_id;
  el('action').textContent = '평가 전'; el('message').textContent = '현재 문장을 판단해 주세요.';
  if (el('verdictPanel')) el('verdictPanel').hidden = true;
  if (el('nextAction')) { el('nextAction').hidden = true; el('nextAction').textContent = ''; }
  for (const id of ['evidence', 'reason', 'task', 'result', 'currentTurn', 'sessionNotice', 'modelNotice']) el(id).textContent = '';

  el('observation').value = 'NOT_CHECKED'; renderLifecycle();
}
async function refresh() {
  if (!session) return;
  const sid = session.session_id;
  const d = await api('/api/state?session_id=' + encodeURIComponent(sid));
  if (!session || session.session_id !== sid) return;
  session = { ...session, version: d.version, lifecycle: d.lifecycle || 'OPEN', prior_pause: !!d.prior_pause };
  el('result').textContent = JSON.stringify(d, null, 2);
  const open = d.tasks.find(t => t.status === 'OPEN');
  renderQueue(d.tasks); renderTask(open || d.tasks.at(-1)); renderLifecycle();
  const latest = d.events.at(-1);
  el('status').textContent = '저장 상태 재조회 · version ' + d.version + ' · ' + sid;
  // SQLite deliberately has no transcript. Only the same editor-bound event is
  // current guidance. Lifecycle events or restored tabs cannot supply that binding.
  if (latest?.action && matchesCurrentInput(lastDecision) && d.version === lastDecision.version &&
      latest.request_id === lastDecision.request_id && latest.version === lastDecision.version) {
    renderDecision(latest);
    el('evidence').textContent = '재조회 결과에는 원문 인용을 저장하지 않습니다.';
  } else {
    lastDecision = null;
    conversationSignal('invalidate', { reason: 'refreshed_or_closed' });
    currentInputRequired(isClosed() ? '미해결 상태로 보관한 기록입니다. 재개 후 현재 문장을 다시 판단할 수 있습니다.' :
      latest ? '저장 기록은 이전 판단입니다. 현재 입력을 다시 판단해 주세요.' : '저장된 판단이 없습니다. 현재 입력을 판단해 주세요.');
  }
}
async function transition(path) {
  if (!session) return;
  const sid = session.session_id;
  await api(path, { session_id: sid, version: session.version, request_id: crypto.randomUUID(), synthetic_only: true });
  if (!session || session.session_id !== sid) return;
  lastDecision = null; editorRevision += 1;
  conversationSignal('invalidate', { reason: 'session_transition' });

  // Read current state even for a cached lifecycle response.
  await refresh();
}
el('new').onclick = () => serial(start);
if (el('newAnalysis')) el('newAnalysis').onclick = () => serial(async () => {
  // A new independent session does not close, resolve or delete the old incident.
  try {
    await start();
    el('text').value = ''; el('review').checked = false;
    if (el('charCount')) el('charCount').textContent = '0 / 2000';
    el('text').focus();
    el('sampleNotice').textContent = '별개의 분석을 시작했습니다. 이전 기록과 미해결 업무는 기록 보기에서 확인할 수 있습니다.';
    el('sampleNotice').hidden = false;
  } catch (e) {
    el('sampleNotice').textContent = '새 분석을 시작하지 못했습니다. 현재 입력과 기존 기록을 유지합니다. ' + e.message;
    el('sampleNotice').hidden = false;
  }
});
el('loadSession').onclick = () => serial(async () => {
  const sid = el('sessionHistory').value;
  if (!visitedSessions.includes(sid) || session?.session_id === sid) return;
  session = { session_id: sid, version: 0, lifecycle: 'OPEN', prior_pause: false };
  conversationSignal('reset', { session_id: sid, reason: 'session_switched' });
  lastDecision = null; editorRevision += 1; el('text').value = '';

  await refresh(); rememberSession(sid);
});
el('refresh').onclick = () => serial(refresh);
el('close').onclick = () => serial(() => transition('/api/close'));
el('reopen').onclick = () => serial(() => transition('/api/reopen'));
el('run').onclick = () => {
  if (!el('text').value.trim()) {
    el('text').focus();
    if (el('sampleNotice')) { el('sampleNotice').hidden = false; el('sampleNotice').textContent = '먼저 검토할 합성 문자·이메일을 붙여넣어 주세요.'; }
    return;
  }
  return serial(async () => {
  if (el('inlineSignal')) el('inlineSignal').hidden = true;
  globalThis.renderSignalChoiceScores?.();
  if (!session) await start();
  if (isClosed()) throw Error('SESSION_CLOSED_UNRESOLVED');
  el('result').textContent = '';
  const binding = { session_id: session.session_id, expected_version: session.version, revision: editorRevision,
    text: el('text').value, review: el('review').checked, policy_id: profile?.active_policy_id };
  const payload = { session_id: session.session_id, version: session.version, request_id: crypto.randomUUID(),
    text: binding.text, synthetic_only: true, observation: el('observation').value, user_review: binding.review };
  if (task) payload.task_id = task;
  conversationSignal('pending', { session_id: binding.session_id, version: binding.expected_version });
  const d = await api('/api/evaluate', payload);
  if (!session || session.session_id !== binding.session_id || session.version !== binding.expected_version) return;
  session.version = d.version; session.lifecycle = d.lifecycle || 'OPEN'; session.prior_pause = !!d.prior_pause;
  el('status').textContent = d.mode + ' · version ' + d.version;
  renderQueue(d.open_tasks || (d.next_task ? [d.next_task] : [])); renderTask(d.next_task || d.related_task); renderLifecycle();
  el('result').textContent = JSON.stringify(d, null, 2);
  if (!matchesCurrentInput(binding) || (binding.policy_id && d.policy_id && binding.policy_id !== d.policy_id)) {
    lastDecision = null;
    currentInputRequired('입력 또는 판단 설정이 변경돼 이전 응답을 현재 문장에 적용하지 않았습니다. 다시 판단해 주세요.');
    if (binding.policy_id && d.policy_id && binding.policy_id !== d.policy_id) await loadProfile();
    return;
  }
  lastDecision = { ...binding, request_id: d.request_id, version: d.version };
  renderDecision(d);
  conversationSignal('decision', { session_id: d.session_id, version: d.version,
    text: binding.text, action: d.action, reason: d.reason,
    current_turn_action: d.current_turn_action || d.action,
    model_status: d.model_status, message: decisionCopy(d).message,
    prior_risk_unresolved: d.reason === 'PRIOR_RISK_UNRESOLVED' || d.execution_trace?.session?.prior_pause_before === true,
    prior_pause: !!d.prior_pause, provenance: d.provenance?.execution_source || 'UNVERIFIED',
    task_count: d.open_task_count || 0 });
  const cp = Array.from(payload.text);
  el('evidence').textContent = (d.evidence || []).filter(e => Number.isInteger(e.start) && Number.isInteger(e.end) &&
    e.start >= 0 && e.start < e.end && e.end <= cp.length).map(e => '원문 어휘 근거: “' + cp.slice(e.start, e.end).join('') + '”').join(' / ');
  await showInlineSignal(lastDecision, d.model_status, d.current_turn_action || d.action);
});
};
function invalidateInput() {
  conversationSignal('invalidate', { reason: 'input_changed' });
  editorRevision += 1; lastDecision = null;

  el('result').textContent = '';
  currentInputRequired('입력이 변경돼 이전 판단을 현재 문장에 적용할 수 없습니다.');
  if (el('verdictPanel')) el('verdictPanel').hidden = true;
  if (el('sampleNotice')) el('sampleNotice').hidden = true;
}
el('text').addEventListener('input', invalidateInput);
el('review').addEventListener('change', invalidateInput);
serial(async () => {
  await loadProfile();
  loadSessionHistory();
  const remembered = rememberedSession();
  if (remembered && /^[0-9a-f]{32}$/.test(remembered)) {
    session = { session_id: remembered, version: 0, lifecycle: 'OPEN', prior_pause: false };
    try { await refresh(); rememberSession(remembered); return; }
    catch (e) { if (e.message !== 'UNKNOWN_SESSION') throw e; }
  }
  await start();
});

el("exportEvidence").onclick = () => serial(async () => { if(session) el("evidenceExport").textContent = JSON.stringify(await api("/api/evidence?session_id="+encodeURIComponent(session.session_id)),null,2); });

el("taskQueue").onchange = () => {
  if (busy || isClosed()) return;
  const selected = openTaskQueue.find(t => t.id === el("taskQueue").value);
  renderTask(selected || null);
  // Do not attribute an earlier user observation to a newly selected task.
  invalidateInput();
  controls();
};
const V58_SYNTHETIC_EXAMPLES = Object.freeze({
  direct: '샘플상사 정산 건입니다. 기존 A-01 계좌는 이번 지급에 쓰지 않습니다. 새 계좌 B-02로 오늘 오후 3시까지 대금을 송금해 주세요.',
  warning: '회계팀에 공유합니다. 최근 거래처를 사칭한 메신저에서 계좌 변경과 인증번호 전송을 요구한 사례가 있었습니다. 메신저로 받은 새 계좌로 송금하거나 인증번호를 전달하지 마세요. 변경 여부는 사내 장부에 등록된 대표번호에서 확인하세요.',
  ambiguous: '샘플상사 11월 정산 건 관련 안내입니다. 등록 정보가 달라 추가 확인이 필요하니, 오늘 안으로 안내에 따라 확인 절차를 진행해 주세요. 무엇을 확인해야 하는지와 제출 방법은 아직 안내되지 않았습니다.',
  followup: '샘플상사 11월 정산 진행 상황을 공유합니다. 지급 요청서는 검토 대기 목록에 있으며, 계좌 정보와 결재 담당자는 기존 등록 내용과 같습니다. 다음 상태 업데이트는 내일 오전에 공유하겠습니다.'
});
for (const button of (document.querySelectorAll?.('[data-sample]') || [])) {
  button.addEventListener('click', () => {
    if (busy || isClosed()) return;
    const sample = V58_SYNTHETIC_EXAMPLES[button.dataset.sample];
    if (!sample) return;
    el('text').value = sample;
    el('review').checked = false;
    invalidateInput();
    el('sampleNotice').textContent = '합성 문장을 채웠습니다. 아래 판단 버튼을 누르세요.';
    el('text').focus();
  });
}
el('downloadEvidence').onclick = () => serial(async () => {
  if (!session) return;
  const sid = session.session_id;
  const report = await api('/api/evidence?session_id=' + encodeURIComponent(sid));
  if (!session || session.session_id !== sid) return;
  // Server evidence endpoint excludes the original transcript; no audit attestation claim.
  const blob = new Blob([JSON.stringify(report, null, 2) + '\n'], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement('a');
    a.href = url; a.download = 'iteraguard-v58-evidence-' + sid.slice(0, 12) + '.json';
    document.body.appendChild(a); a.click(); a.remove();
    el('evidenceExport').textContent = JSON.stringify(report, null, 2);
    el('status').textContent = '로컬 증거 파일 다운로드 요청 · 외부 인증 아님';
  } finally { setTimeout(() => URL.revokeObjectURL(url), 1000); }
});
