'use strict';

const signalLabels = {
  red: '빨강 · 피싱 의심 매우 높음',
  orange: '주황 · 피싱 의심 높음',
  green: '초록 · 정상 문자로 보임',
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
    if (!response.ok) throw new Error('SIGNAL_REQUEST_FAILED');
    const { grade, requested_action: action } = await response.json();
    if (!Object.hasOwn(signalLabels, grade) || typeof action?.label !== 'string' || !action.label.trim()) {
      throw new Error('INVALID_SIGNAL_RESULT');
    }
    if (isCurrent()) {
      signalResult.dataset.grade = grade;
      signalGrade.textContent = signalLabels[grade];
      requestedAction.textContent = action.label;
      signalResult.hidden = false;
      signalStatus.textContent = '';
    }
  } catch {
    if (isCurrent()) signalStatus.textContent = '조로 응답을 받지 못했어요. 잠시 후 다시 판단해 주세요.';
  } finally {
    signalRun.disabled = false;
  }
});
