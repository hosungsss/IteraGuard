'use strict';
const byId = id => document.getElementById(id);
const messages = {
  NO_LOCAL_FEED: '로컬 목록이 준비되지 않아 조회하지 못했습니다.',
  NO_KEY: '서버에 ScamAdviser 키가 없어 조회하지 못했습니다.',
  OPERATOR_DISABLED: '이 서버의 외부 조회 기능은 꺼져 있습니다.',
  HOST_NOT_ELIGIBLE: '문자에 포함된 HTTP(S) 링크의 정확한 도메인을 입력해 주세요.',
  CACHE_MISS: '공급자 캐시에 이 도메인의 자료가 없습니다.',
  STALE_OR_UNAVAILABLE: '공급자 자료가 오래됐거나 지금은 조회할 수 없습니다.',
  RATE_LIMIT: '조회 한도에 도달했습니다.', BUSY: '다른 조회가 진행 중입니다.',
  NO_HTTP_URL: '대조할 HTTP(S) 링크를 찾지 못했습니다.',
  NO_EXACT_MATCH: '준비된 목록에서 같은 주소를 찾지 못했습니다. 신규 주소와 다른 경로는 놓칠 수 있습니다.',
  STALE_OR_FUTURE_SNAPSHOT: '목록 시각이 유효하지 않아 대조하지 않았습니다.',
  ACCESS_DENIED: '공급자가 키 또는 조회 권한을 승인하지 않았습니다.'
};
const advice = {verify_first:'평소 이용하던 공식 경로에서 먼저 확인하세요.', ask_context:'누가 무엇을 요청했는지 추가 정보가 필요합니다.',
  no_sensitive_request:'현재 문구에서 민감한 행동 요청을 특정하기 어렵습니다.'};
let revision = 0;
const form = byId('lookup'), output = byId('output');
form.addEventListener('input', () => { revision += 1; output.textContent = ''; });
form.addEventListener('submit', async ev => {
  ev.preventDefault();
  const submit = byId('submitReview');
  if (submit.disabled) return;
  const version = ++revision;
  submit.disabled = true; output.textContent = '조회 중입니다.';
  const body = {text:byId('message').value, share_host:byId('host').value.trim(), synthetic_only:true, local_zoro:byId('second').checked};
  try {
    const response = await fetch('/api/link-review', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    if (!response.ok) throw Error();
    const {observation:o, shadow_model:m} = await response.json();
    if (version !== revision) return;
    let message = messages[o.status] || '조회 결과를 검증할 수 없습니다.';
    if (o.status === 'OBSERVED') message = 'ScamAdviser 도메인 신뢰 점수 ' + o.trust_score + '/100 · ' + o.host + ' · 자료 갱신 ' + o.reviewed_at;
    if (o.status === 'LISTED_EXACT') message = '제공된 목록과 주소가 정확히 일치합니다 (' + o.matched + '/' + o.checked + ').';
    if (o.operator_as_of) message += ' · 목록 확보 시각(운영자 입력) ' + o.operator_as_of;
    if (m.status === 'LOCAL_RESPONSE_UNATTESTED' && advice[m.proposal]) message += ' 로컬 모델의 보조 의견(모델 신원 미인증) — ' + advice[m.proposal];
    else if (m.status === 'TEST_DOUBLE') message += ' 통제 응답으로 시험했습니다.';
    else if (body.local_zoro) message += ' 로컬 모델 보조 의견을 얻지 못했습니다.';
    output.textContent = message + ' 이 결과만으로 문자 발신자나 거래의 안전을 확인할 수 없습니다.';
  } catch {
    if (version === revision) output.textContent = '서버 응답을 확인할 수 없습니다.';
  } finally { submit.disabled = false; }
});
