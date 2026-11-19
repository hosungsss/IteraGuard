'use strict';

const grades = {
  red: ['빨강 · 피싱 의심 매우 높음', '즉시 멈춰야 할 위험 요청이 있는 유형', '요청한 행동을 멈추고 기존에 알고 있던 공식 연락처로 확인하세요.'],
  orange: ['주황 · 피싱 의심 높음', '의심 신호를 추가로 확인해야 하는 유형', '문자 속 링크나 연락처의 사용을 미루고 공식 경로에서 확인하세요.'],
  green: ['초록 · 정상 문자로 보임', '본문에서 뚜렷한 피싱 신호가 감지되지 않은 유형', '링크 접속이나 결제가 필요하면 평소 쓰던 공식 경로를 이용하세요.'],
  gray: ['회색 · 판단 어려움', '본문만으로 등급을 정하기 어려운 경우', '발신자와 요청 목적을 별도로 확인한 뒤 행동하세요.']
};
const unavailable = ['회색 · 결과를 받지 못했어요', '조로 연결 또는 응답 확인이 필요해요.', '요청한 행동을 미루고 잠시 후 다시 판단해 보세요.'];
const byId = (id) => document.getElementById(id);
const form = byId('check');
const message = byId('message');
const submit = byId('submit');
const result = byId('result');
const status = byId('status');

function show(grade, lines) {
  result.dataset.grade = grade;
  [byId('grade').textContent, byId('basis').textContent, byId('next').textContent] = lines;
  result.hidden = false;
}

message.addEventListener('input', () => {
  result.hidden = true;
  status.textContent = '';
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (submit.disabled) return;

  const text = message.value;
  if (!text.trim()) {
    status.textContent = '확인할 문자 내용을 입력하세요.';
    return;
  }

  result.hidden = true;
  message.readOnly = true;
  submit.disabled = true;
  status.textContent = '조로가 문자를 판단 중이에요.';
  try {
    const response = await fetch('/api/signal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, synthetic_only: true })
    });
    if (!response.ok) throw new Error('Model request failed');
    const { grade } = await response.json();
    if (!Object.hasOwn(grades, grade)) throw new Error('Invalid result');
    show(grade, grades[grade]);
  } catch {
    show('gray', unavailable);
  } finally {
    status.textContent = '';
    message.readOnly = false;
    submit.disabled = false;
  }
});
