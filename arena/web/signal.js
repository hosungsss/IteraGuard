'use strict';

const signalLabels = {
  red: '빨강 · 피싱 의심 매우 높음',
  orange: '주황 · 피싱 의심 높음',
  green: '초록 · 뚜렷한 위험 신호 미감지',
  gray: '회색 · 판단 어려움'
};
const signalForm = document.getElementById('signalForm');
const signalText = document.getElementById('text');
const signalRun = document.getElementById('run');
const signalStatus = document.getElementById('signalStatus');
const signalResult = document.getElementById('inlineSignal');
const signalGrade = document.getElementById('inlineSignalGrade');
const requestedAction = document.getElementById('inlineRequestedAction');
const signalConfirmation = document.getElementById('inlineConfirmation');
const signalConfirmationText = document.getElementById('inlineConfirmationText');
const signalCount = document.getElementById('charCount');
let signalRevision = 0;

function clearConfirmationExcerpt() {
  if (!signalConfirmation || !signalConfirmationText) return;
  signalConfirmation.hidden = true;
  signalConfirmationText.textContent = '';
}

function renderConfirmationExcerpt(text, excerpt) {
  if (!signalConfirmation || !signalConfirmationText) return;
  const start = excerpt?.start;
  const end = excerpt?.end;
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start >= end) return;
  const characters = Array.from(text);
  if (end > characters.length) return;
  const original = characters.slice(start, end).join('');
  if (!original.trim()) return;
  signalConfirmationText.textContent = original;
  signalConfirmation.hidden = false;
}

signalText.addEventListener('input', () => {
  signalRevision += 1;
  signalResult.hidden = true;
  clearConfirmationExcerpt();
  globalThis.renderSignalChoiceScores?.();
  signalStatus.textContent = '';
  signalCount.textContent = Array.from(signalText.value).length + ' / 2000';
});

signalForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (signalRun.disabled) return;
  const text = signalText.value;
  if (!text.trim()) {
    signalStatus.textContent = '확인할 문장을 입력해 주세요.';
    signalText.focus();
    return;
  }
  const revision = signalRevision;
  const isCurrent = () => revision === signalRevision && text === signalText.value;
  signalResult.hidden = true;
  clearConfirmationExcerpt();
  globalThis.renderSignalChoiceScores?.();
  signalRun.disabled = true;
  signalStatus.textContent = '조로가 문장을 판단 중이에요.';

  try {
    const options = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, synthetic_only: true })
    };
    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
      options.signal = AbortSignal.timeout(60000);
    }
    const response = await fetch('/api/signal', options);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      if (isCurrent()) {
        signalStatus.textContent = response.status === 429
          ? '다른 요청을 분석하고 있습니다. 잠시 뒤 다시 시도하세요.'
          : error?.error === 'SIGNAL_MODEL_UNAVAILABLE'
            ? '로컬 모델이 응답하지 않았거나 결과 형식이 맞지 않아 판단을 보류했어요.'
            : '분석 요청을 처리하지 못했습니다. 입력과 연결 상태를 확인해 주세요.';
      }
      return;
    }
    const { grade, scores, requested_action: action, explanation, context_review, confirmation_excerpt } =
      await response.json();
    if (!Object.hasOwn(signalLabels, grade) || typeof action?.label !== 'string' || !action.label.trim()) {
      throw new Error('INVALID_SIGNAL_RESULT');
    }
    if (isCurrent()) {
      signalResult.dataset.grade = grade;
      signalGrade.textContent = signalLabels[grade];
      requestedAction.textContent = action.label;
      if (grade === 'red' || grade === 'orange') renderConfirmationExcerpt(text, confirmation_excerpt);
      const note = document.getElementById('signalExplanation');
      if (note) note.textContent = typeof explanation === 'string' ? explanation : '본문 기반 판단이며 신원과 안전은 확인되지 않았습니다.';
      globalThis.renderSignalChoiceScores?.(scores, grade, context_review?.original?.grade);
      signalResult.hidden = false;
      const sensitive = ['share_auth_secret', 'grant_remote_access', 'pay_to_changed_account', 'pay_unlock_fee'];
      signalStatus.textContent = grade === 'green' && sensitive.includes(action.id)
        ? '두 답이 엇갈립니다. 민감한 행동은 보류하고 평소 사용하던 공식 연락처에서 요청을 확인하세요.'
        : '';
      const ordered = Object.keys(signalLabels).map(k => scores?.[k]).sort((a,b) => b-a);
      if (!context_review?.adjusted && ordered.every(v => Number.isFinite(v) && v >= 0 && v <= 1) &&
          Math.round(100 * ordered[0]) === Math.round(100 * ordered[1])) {
        signalStatus.textContent += ' 상위 두 선택 점수는 정수 백분율로 반올림하면 같습니다. 등급을 단정하기 어렵습니다.';
      }
    }
  } catch {
    if (isCurrent()) signalStatus.textContent = '조로 응답을 받지 못했어요. 잠시 후 다시 판단해 주세요.';
  } finally {
    signalRun.disabled = false;
  }
});


(() => {
  const opener = document.getElementById('openSignalBenchmark');
  const dialog = document.getElementById('signalBenchmark');
  const input = document.getElementById('signalBenchmarkCsv');
  const status = document.getElementById('benchmarkCsvStatus');
  if (!opener || !dialog || !input || !status) return;

  const run = document.getElementById('runSignalBenchmark');
  const runStatus = document.getElementById('benchmarkRunStatus');
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(globalThis.location?.hostname);
  let requestPending = false;
  let running = false;
  let refreshOnly = false;
  let poll;

  function showBenchmarkResult(result) {
    const grades = ['red', 'orange', 'green', 'gray'];
    const normal = result.counts?.normal;
    const phishing = result.counts?.phishing;
    const finish = new Date(result.finished_at);
    const valid = (row, total) => grades.every(grade => Number.isInteger(row?.[grade]) && row[grade] >= 0) &&
      grades.reduce((sum, grade) => sum + row[grade], 0) === total;
    if (!valid(normal, 501) || !valid(phishing, 50) ||
        typeof result.finished_at !== 'string' || !Number.isFinite(finish.getTime()) ||
        !Number.isInteger(result.elapsed_ms) || result.elapsed_ms < 0) {
      throw new Error('INVALID_BENCHMARK_RESULT');
    }

    for (const [id, row] of [['benchmarkNormal', normal], ['benchmarkPhishing', phishing]]) {
      const { cells } = document.getElementById(id);
      grades.forEach((grade, index) => { cells[index + 1].textContent = String(row[grade]); });
    }
    const detected = phishing.red + phishing.orange;
    const normalWithoutAlert = normal.green + normal.gray;
    const metrics = [
      ['benchmarkRecall', detected, 50],
      ['benchmarkNormalRate', normalWithoutAlert, 501],
      ['benchmarkStrict', normal.green + detected, 551],
      ['benchmarkBinary', normalWithoutAlert + detected, 551]
    ];
    for (const [id, numerator, denominator] of metrics) {
      const node = document.getElementById(id);
      node.querySelector('strong').textContent = (100 * numerator / denominator).toFixed(1) + '%';
      node.querySelector('span').textContent = '(' + numerator + '/' + denominator + ')';
    }
    const date = new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short' }).format(finish);
    document.getElementById('benchmarkResultMeta').textContent =
      '한국어 메신저피싱 테스트 CSV 551건 · ' + date + ' 측정 결과';
    const profile = ['baseline', 'short', 'verify', 'high-recall'].includes(result.profile) ? ' · 프로필 ' + result.profile : '';
    document.getElementById('benchmarkModelMeta').textContent =
      '로컬 Arena' + profile + ' · 실행 ' + (result.elapsed_ms / 1000).toFixed(1) + '초';
  }

  function showBenchmarkDisabled() {
    running = false;
    refreshOnly = false;
    run.disabled = true;
    run.textContent = '재측정 시작';
    runStatus.textContent = '로컬 조로를 연결하고 Arena를 --signal-benchmark-csv 옵션으로 시작하면 재측정할 수 있어요.';
  }

  async function requestBenchmark(method = 'GET') {
    if (requestPending) return;
    clearTimeout(poll);
    requestPending = true;
    run.disabled = true;
    if (method === 'POST') runStatus.textContent = '로컬 Arena에 재측정을 요청하고 있어요.';
    try {
      const options = { method };
      if (method === 'POST') {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = '{}';
      }
      if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
        options.signal = AbortSignal.timeout(10000);
      }
      const response = await fetch('/api/signal/benchmark', options);
      const state = await response.json();
      if (response.status === 404 && state?.error === 'BENCHMARK_DISABLED') {
        showBenchmarkDisabled();
        return;
      }
      if (!response.ok || typeof state?.available !== 'boolean' ||
          !['idle', 'running', 'completed', 'failed'].includes(state.status) ||
          state.total !== 551 || !Number.isInteger(state.completed) ||
          state.completed < 0 || state.completed > state.total ||
          (state.status === 'completed' && (state.completed !== state.total || !state.result))) {
        throw new Error('INVALID_BENCHMARK_STATE');
      }
      if (state.result) showBenchmarkResult(state.result);
      if (!state.available) {
        showBenchmarkDisabled();
        return;
      }
      running = state.status === 'running';
      refreshOnly = false;
      run.disabled = running;
      run.textContent = '재측정 시작';
      if (running) {
        runStatus.textContent = '재측정 중 · ' + state.completed + '/' + state.total + '건 완료';
      } else if (state.status === 'failed') {
        if (state.error === 'BENCHMARK_CSV_INVALID') {
          runStatus.textContent = '설정한 CSV 원본을 확인하지 못했어요. Arena의 CSV 경로를 확인하고 다시 측정해 주세요.';
        } else if (state.error === 'BENCHMARK_MODEL_UNAVAILABLE') {
          runStatus.textContent = '조로 응답을 확인하지 못했어요. 로컬 모델 연결 상태를 확인하고 다시 측정해 주세요.';
        } else {
          runStatus.textContent = '재측정을 마치지 못했어요. 잠시 후 다시 측정해 주세요.';
        }
      } else {
        runStatus.textContent = state.status === 'completed' ? '551건 재측정을 완료했어요.' : '원본 CSV 551건을 로컬 조로로 측정해요.';
      }
    } catch {
      refreshOnly = true;
      run.disabled = running;
      run.textContent = '상태 다시 확인';
      runStatus.textContent = running ? '진행 상태를 다시 확인하고 있어요.' : '로컬 Arena 상태를 확인하지 못했어요. 상태를 다시 확인해 주세요.';
    } finally {
      requestPending = false;
      if (running && dialog.open) poll = setTimeout(() => requestBenchmark(), 1500);
    }
  }

  opener.addEventListener('click', () => {
    if (dialog.open) return;
    dialog.showModal();
    if (!local || !run || !runStatus) return;
    runStatus.textContent = '로컬 Arena 상태를 확인하고 있어요.';
    return requestBenchmark();
  });
  if (local && run && runStatus) {
    run.addEventListener('click', () => {
      if (!run.disabled) return requestBenchmark(refreshOnly ? 'GET' : 'POST');
    });
    dialog.addEventListener('close', () => clearTimeout(poll));
  }

  let selection = 0;
  function showStatus(message, state = '') {
    status.textContent = message;
    status.dataset.state = state;
  }

  input.addEventListener('change', async () => {
    const revision = ++selection;
    const file = input.files[0];
    if (!file) {
      showStatus('');
      return;
    }
    const mismatch = '2026-11-20 측정에 사용한 원본 CSV와 다른 파일이에요.';
    if (file.size !== Number(input.dataset.bytes)) {
      showStatus(mismatch, 'mismatch');
      return;
    }
    showStatus('선택한 CSV의 지문을 확인하고 있어요.');
    try {
      const bytes = await file.arrayBuffer();
      const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
      const hex = Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, '0')).join('');
      if (revision !== selection) return;
      if (hex === input.dataset.sha256) {
        showStatus('저장된 551건 결과에 사용한 원본 CSV와 일치해요.', 'match');
      } else {
        showStatus(mismatch, 'mismatch');
      }
    } catch {
      if (revision === selection) showStatus('이 브라우저에서 파일 지문을 확인하지 못했어요.', 'error');
    }
  });
})();
