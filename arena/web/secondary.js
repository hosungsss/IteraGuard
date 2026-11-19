/* Secondary observability only. No authority over Arena, tasks or Zoro. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const text = $('text'), status = $('secondaryStatus'), result = $('secondaryResult');
  const source = $('secondarySource'), capability = $('secondaryCapability');
  const offline = $('offlineCheck'), jev = $('jevCheck'), consent = $('jevConsent');
  const meter = $('charCount');
  if (!text || !status || !result || !source || !capability || !offline || !jev || !consent) return;

  let liveAvailable = false;
  let running = false;
  let revision = 0;
  const signalNames = Object.freeze({
    credential_terms: '인증번호·비밀번호 관련 어휘',
    payment_terms: '송금·계좌 관련 어휘',
    remote_access_terms: '원격접속·설치 관련 어휘',
    link_terms: '링크·URL 관련 어휘',
    urgency_terms: '긴급·압박 관련 어휘',
    quotation_or_warning_terms: '인용·과거·예방 경고 관련 어휘'
  });
  const intentNames = Object.freeze({
    active_sensitive_request: '현재 민감한 행동을 요청하는 문장',
    protective_warning: '행동을 하지 말라는 보호 경고',
    historical_report: '과거 요청을 인용·보고하는 문장',
    ordinary_message: '일반 정보·업무 전달',
    unclear: '요청 범위가 불분명한 문장'
  });
  const errorNames = Object.freeze({
    JEV_DISABLED_OR_PAID_CREDITS_NOT_AUTHORIZED: 'Jev 클라우드가 비활성화 상태입니다. API 키 및 서버 운영자의 유료 호출 승인 설정이 필요합니다.',
    JEV_PROCESS_CALL_CAP_REACHED: '서버 프로세스의 Jev 호출 제한에 도달했습니다. 자동 재시도하지 않습니다.',
    PROVIDER_CREDITS_REQUIRED: 'Jev 공급사의 유료 크레딧이 필요합니다. 무료 Jev 응답으로 대체하지 않습니다.',
    PROVIDER_AUTH_OR_ENTITLEMENT_ERROR: 'Jev API 인증 또는 사용 권한을 확인하세요.',
    PROVIDER_RATE_LIMIT: '공급사의 요청 제한에 걸렸습니다. 자동 재시도하지 않습니다.',
    PROVIDER_TRANSPORT_ERROR: 'TypeSafe 연결에 실패했습니다. 현재 Zoro 결과에는 영향이 없습니다.',
    MODEL_VERSION_UNVERIFIED: '응답 모델 버전이 고정된 Jev 1.14와 일치하지 않습니다.',
    INVALID_PROVIDER_ANSWER_SET: 'Jev 응답 질문 계약이 일치하지 않습니다.',
    EXPLICIT_EXTERNAL_CONSENT_REQUIRED: '외부 문장 전송 동의가 필요합니다.',
    INVALID_SYNTHETIC_TEXT: '합성 문장을 1~2,000자 이내로 입력하세요.'
  });
  function updateMeter() {
    if (meter) meter.textContent = Array.from(text.value).length.toLocaleString('ko-KR') + ' / 2,000';
  }
  function reset() {
    revision += 1;
    status.textContent = '입력이 변경되었습니다. 새 문장으로 다시 관측해 주세요.';
    result.textContent = '';
    source.textContent = '이전 보조 관측은 더 이상 현재 입력과 연결되지 않습니다.';
    consent.checked = false;
    updateMeter();
    sync();
  }
  function sync() {
    offline.disabled = running || !text.value.trim();
    jev.disabled = running || !liveAvailable || !consent.checked || !text.value.trim();
  }
  async function request(path, body) {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store'
    });
    const content = await response.json();
    if (!response.ok) {
      const err = new Error('SECONDARY_REQUEST_FAILED');
      err.code = content && content.error;
      throw err;
    }
    return content;
  }
  async function run(mode) {
    if (running) return;
    if (mode === 'jev' && (!liveAvailable || !consent.checked)) return;
    const current = text.value;
    if (!current.trim() || current.length > 2000) {
      status.textContent = '합성 문장을 1~2,000자 이내로 입력하세요.';
      return;
    }
    if (mode === 'jev' && !window.confirm('작성한 합성 문장을 TypeSafe 외부 API로 전송합니다. 요청에 따라 유료 크레딧이 차감될 수 있습니다. 계속하시겠습니까?')) {
      return;
    }
    const marker = revision;
    running = true;
    sync();
    status.textContent = mode === 'jev' ? 'Jev 클라우드 응답 확인 중…' : '무료 로컬 패턴을 확인하는 중…';
    result.textContent = '';
    try {
      const payload = { text: current, synthetic_only: true, mode };
      if (mode === 'jev') payload.consent_external = true;
      const observation = await request('/api/secondary/check', payload);
      if (marker !== revision || current !== text.value) return;
      if (mode === 'offline' && observation.mode === 'OFFLINE_LEXICAL_INDICATORS') {
        const list = (observation.indicators || []).filter(x => Object.hasOwn(signalNames, x)).map(x => '• ' + signalNames[x]);
        status.textContent = '무료 로컬 어휘 관측 · 완료';
        result.textContent = list.length ? list.join('\n') : '등록된 표현 없음. 위험이 없다는 뜻은 아닙니다.';
        source.textContent = '출처: 결정론적 정규식 패턴 · Jev·Zoro 모델 추론 아님 · 안전 판단 불가';
      } else if (mode === 'jev' && observation.mode === 'JEV_PROVIDER_HTTP_UNATTESTED') {
        status.textContent = 'Jev 1.14 응답 수신 · Shadow 전용';
        const confidence = Number(observation.confidence);
        const sensitive = Number(observation.active_sensitive_noul);
        if (!Number.isFinite(confidence) || !Number.isFinite(sensitive)) throw new Error('INVALID_DISPLAY_PROBABILITY');
        result.textContent = '문맥 분류: ' + (intentNames[observation.intent] || '분류 불가')
          + '\n선택 확신도: ' + Math.round(confidence * 1000) / 10 + '%'
          + '\n현재 민감 행동 요청 선택확률: ' + Math.round(sensitive * 1000) / 10 + '%';
        source.textContent = '출처: TypeSafe Jev ' + observation.provider_model_echo
          + ' API 응답 (독립 신원 인증 아님) · Zoro 결과나 업무 상태 변경 없음 · 공급사 과금 가능';
      } else {
        status.textContent = '보조 응답의 형식이 예상과 다릅니다.';
        source.textContent = '실행 결과를 채택하지 않았습니다.';
      }
    } catch (error) {
      if (marker !== revision || current !== text.value) return;
      status.textContent = '보조 관측 실패 · 기존 Zoro 판단 유지';
      result.textContent = errorNames[error.code] || '모델 응답 또는 연결을 확인하지 못했습니다. 비용 발생 가능성이 있으므로 자동 재시도하지 않습니다.';
      source.textContent = '실제 Jev 결과를 받지 못했습니다. 로컬 패턴 분석을 Jev 응답으로 대체하지 않습니다.';
    } finally {
      running = false;
      if (marker === revision && mode === 'jev') consent.checked = false;
      sync();
    }
  }

  updateMeter();
  sync();
  text.addEventListener('input', reset);
  consent.addEventListener('change', sync);
  offline.addEventListener('click', function () { void run('offline'); });
  jev.addEventListener('click', function () { void run('jev'); });
  const runButton = $('run');
  if (runButton) runButton.addEventListener('click', function () {
    status.textContent = '기본 Zoro 정책 판단과 보조 관측은 별도 기능입니다.';
  });
  for (const button of (document.querySelectorAll?.('[data-sample]') || [])) {
    button.addEventListener('click', reset);
  }
  fetch('/api/secondary/capabilities', { cache: 'no-store' })
    .then(function (response) { if (!response.ok) throw new Error('CAPABILITY_UNAVAILABLE'); return response.json(); })
    .then(function (details) {
      liveAvailable = details.jev_live_available === true && details.jev_model === 'jev-1.14.0';
      capability.textContent = liveAvailable
        ? 'Jev 1.14 연결 준비됨 · 운영자 유료 호출 승인 · 합성 문장과 별도 동의 필요'
        : 'Jev 1.14 기본 비활성화 · 무료 API 크레딧 제공되지 않음 · 로컬 패턴 점검은 무료';
      sync();
    })
    .catch(function () {
      liveAvailable = false;
      capability.textContent = 'Jev 설정 조회 실패 · 외부 호출 차단 · 로컬 패턴 점검만 사용 가능';
      sync();
    });
}());
