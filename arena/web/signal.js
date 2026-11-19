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
const signalCount = document.getElementById('charCount');
let signalRevision = 0;

signalText.addEventListener('input', () => {
  signalRevision += 1;
  signalResult.hidden = true;
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
    const { grade, scores, requested_action: action, explanation, context_review } = await response.json();
    if (!Object.hasOwn(signalLabels, grade) || typeof action?.label !== 'string' || !action.label.trim()) {
      throw new Error('INVALID_SIGNAL_RESULT');
    }
    if (isCurrent()) {
      signalResult.dataset.grade = grade;
      signalGrade.textContent = signalLabels[grade];
      requestedAction.textContent = action.label;
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

  opener.addEventListener('click', () => {
    if (!dialog.open) dialog.showModal();
  });

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
