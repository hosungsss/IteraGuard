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
async function api(path, body) {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json();
  if (!r.ok) throw Error(d.error || 'REQUEST_FAILED');
  return d;
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
  for (const id of ['run', 'compare', 'text', 'review']) el(id).disabled = busy || closed;
  el('observation').disabled = busy || closed || !task;
  el('taskQueue').disabled = busy || closed || !openTaskQueue.length;
  el('exportEvidence').disabled = busy || !session;
  el('refresh').disabled = busy || !session;
  el('close').disabled = busy || !session || closed;
  el('reopen').disabled = busy || !closed;
  // Finish/retain the current incident before deliberately starting another one.
  el('new').disabled = busy || !!(session && !closed && session.version > 0);
  el('loadSession').disabled = busy || !!(session && !closed && session.version > 0) || !visitedSessions.length;
  el('sessionHistory').disabled = el('loadSession').disabled;
}
function renderLifecycle() {
  el('lifecycle').textContent = isClosed() ? '미해결 상태로 보관 중' : '확인 진행 중';
  el('riskState').textContent = session?.prior_pause ? '세션: 앞서 감지한 위험이 미해결 상태로 남아 있습니다.' : '세션: 기록된 강한 중단 이력 없음 (안전 보증 아님)';
  el('lifecycleNotice').textContent = isClosed() ? '보관은 위험 해제가 아닙니다. 이전 이력을 유지하며 재개할 수 있습니다.' : '확인을 마치지 못해도 미해결 상태로 보관할 수 있습니다. 재개 시 이전 위험과 업무 이력이 유지됩니다.';
}
function currentInputRequired(message) {
  el('executionSource').textContent = '현재 입력의 실행 출처는 재평가 후 확인하세요.';
  el('action').textContent = 'ASK_HUMAN'; el('message').textContent = message;
  for (const id of ['evidence', 'reason', 'currentTurn', 'sessionNotice']) el(id).textContent = '';
}
function renderDecision(d) {
  el('executionSource').textContent = d.model_status === 'FAILED' ? '판단 출처: 모델 연결 또는 응답 검증 실패' : d.provenance?.execution_source === 'CONTROLLED_CLIENT' ? '판단 출처: 통제 응답 · 실제 모델 추론 아님' : '판단 출처: 모델 응답 · 체크포인트 신원 미인증';
  el('action').textContent = d.action; el('message').textContent = d.message; el('reason').textContent = d.reason;
  if (d.action === 'ASK_HUMAN') {
    el('message').textContent += d.reason === 'PRIOR_RISK_UNRESOLVED'
      ? ' 현재 판단은 완료됐으며 이전 위험에 대한 확인이 남아 있습니다. 아래 확인 업무와 저장 기록을 확인하세요.'
      : ' 보류는 처리 중 상태가 아닙니다. 현재 직접 요청인지 과거 인용·예방 경고인지 확인하고, 확인 업무가 있으면 결과를 기록하세요.';
  }
  el('currentTurn').textContent = '현재 문장: ' + (labels[d.current_turn_action || d.action] || '확인 불가');
  el('sessionNotice').textContent = d.reason === 'PRIOR_RISK_UNRESOLVED' ? '앞서 감지한 위험은 사용자 확인 보고만으로 해제되지 않습니다.' : '';
}
function renderQueue(items) {
  openTaskQueue = (items || []).filter(t => t.status === 'OPEN');
  const select = el('taskQueue'); select.textContent = '';
  for (const t of openTaskQueue) {
    const option = document.createElement('option'); option.value = t.id;
    option.textContent = t.type + ' · ' + t.id.slice(0,8); select.appendChild(option);
  }
  select.value = openTaskQueue[0]?.id || '';
  el('queueCount').textContent = '미해결 업무 ' + openTaskQueue.length + '건 · 중단 요청 우선';
}
function renderTask(item) {
  task = item?.status === 'OPEN' ? item.id : null;
  if (task) {
    const observed = item.observation === 'UNRESOLVED' ? ' · 확인했지만 미해결로 보고됨' : '';
    el('task').textContent = '열린 확인 작업' + observed + ' · ' + item.id + '\n' + (item.instruction || '독립적으로 알고 있던 공식 경로에서 확인하세요. 실제 연락은 수행되지 않습니다.');
  } else if (item) {
    el('task').textContent = '확인 보고 보관 · ' + item.id + '\n사용자가 입력한 확인 결과입니다. 기관에서 검증한 결과가 아닙니다. 이전 위험 때문에 같은 확인 작업을 자동으로 반복 생성하지 않습니다.';
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
    lastDecision = null;
    el('status').textContent = '현재 요청 실패 / CURRENT REQUEST FAILED';
    currentInputRequired('현재 결과를 확정할 수 없습니다. 저장 상태를 재조회해 주세요.');
    el('reason').textContent = e.message; el('result').textContent = '';
    el('task').textContent = '업무 상태는 저장 상태 재조회에서 확인하세요.'; task = null;
  } finally { busy = false; controls(); }
}
async function loadProfile() {
  profile = await api('/api/manifest');
  el('manifest').textContent = JSON.stringify(profile, null, 2);
}
async function start() {
  session = { ...await api('/api/start', {}), lifecycle: 'OPEN', prior_pause: false };
  rememberSession(session.session_id);
  task = null; lastDecision = null; editorRevision += 1; renderQueue([]);
  el('status').textContent = '새 세션 · ' + session.session_id;
  el('action').textContent = '평가 전'; el('message').textContent = '현재 문장을 판단해 주세요.';
  for (const id of ['evidence', 'reason', 'task', 'result', 'currentTurn', 'sessionNotice']) el(id).textContent = '';
  el('generation').textContent = '실행 전 / 생성 서버 별도 필요';
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
  el('generation').textContent = '세션 상태가 변경됐습니다. 생성 비교는 재개 후 실행하세요.';
  // Read current state even for a cached lifecycle response.
  await refresh();
}
el('new').onclick = () => serial(start);
el('loadSession').onclick = () => serial(async () => {
  const sid = el('sessionHistory').value;
  if (!visitedSessions.includes(sid) || session?.session_id === sid) return;
  session = { session_id: sid, version: 0, lifecycle: 'OPEN', prior_pause: false };
  lastDecision = null; editorRevision += 1; el('text').value = '';
  el('generation').textContent = '보관 기록을 불러왔습니다. 생성 비교는 재개 후 실행하세요.';
  await refresh(); rememberSession(sid);
});
el('refresh').onclick = () => serial(refresh);
el('close').onclick = () => serial(() => transition('/api/close'));
el('reopen').onclick = () => serial(() => transition('/api/reopen'));
el('run').onclick = () => serial(async () => {
  if (!session) await start();
  if (isClosed()) throw Error('SESSION_CLOSED_UNRESOLVED');
  el('result').textContent = '';
  const binding = { session_id: session.session_id, expected_version: session.version, revision: editorRevision,
    text: el('text').value, review: el('review').checked, policy_id: profile?.active_policy_id };
  const payload = { session_id: session.session_id, version: session.version, request_id: crypto.randomUUID(),
    text: binding.text, synthetic_only: true, observation: el('observation').value, user_review: binding.review };
  if (task) payload.task_id = task;
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
  const cp = Array.from(payload.text);
  el('evidence').textContent = (d.evidence || []).filter(e => Number.isInteger(e.start) && Number.isInteger(e.end) &&
    e.start >= 0 && e.start < e.end && e.end <= cp.length).map(e => '원문 어휘 근거: “' + cp.slice(e.start, e.end).join('') + '”').join(' / ');
});
el('compare').onclick = () => serial(async () => {
  if (isClosed()) throw Error('SESSION_CLOSED_UNRESOLVED');
  el('generation').textContent = '실제 공개 Zoro 생성 요청 중...';
  const binding = { session_id: session?.session_id, revision: editorRevision, text: el('text').value, review: el('review').checked };
  try {
    const d = await api('/api/generation-compare', { text: binding.text, synthetic_only: true });
    if (!matchesCurrentInput(binding)) {
      el('generation').textContent = '입력 또는 세션이 변경됐습니다. 생성 비교를 다시 실행하세요.'; return;
    }
    el('generation').textContent = JSON.stringify(d, null, 2) + '\n생성 레이블은 정책 판단·사기 확률이 아닙니다.';
  } catch (e) {
    el('generation').textContent = 'GENERATION_UNAVAILABLE / ' + e.message + '\nfixture로 대체하지 않았습니다.';
  }
});
function invalidateInput() {
  editorRevision += 1; lastDecision = null;
  el('generation').textContent = '입력 또는 옵션이 변경됐습니다. 생성 비교를 다시 실행하세요.';
  el('result').textContent = '';
  currentInputRequired('입력이 변경돼 이전 판단을 현재 문장에 적용할 수 없습니다.');
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

el("taskQueue").onchange = () => { if (!busy && !isClosed()) { renderTask(openTaskQueue.find(t => t.id === el("taskQueue").value)); controls(); } };
