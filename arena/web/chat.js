'use strict';
/* In-memory incident conversation display; structured follow-up scenarios only.
 * It is NOT GPT, NOT a Zoro re-inference, and NOT a new safety decision.
 * The raw follow-up question is displayed locally, but NEVER sent to the
 * server: only {session_id,version,scenario,synthetic_only} is transmitted.
 */
(function () {
  const $ = id => document.getElementById(id);
  const feed = $('conversationFeed');
  const field = $('followupText');
  const send = $('sendFollowup');
  const info = $('conversationNotice');
  if (!feed || !field || !send || !info) return;

  const SCENARIOS = Object.freeze({
    link_only: '링크만 누르면 괜찮을까요?',
    clicked: '이미 링크를 눌렀어요.',
    downloaded: '파일을 다운로드했어요.',
    installed: '앱을 설치했어요.',
    entered_secret: '인증번호 또는 비밀번호를 입력했어요.',
    paid: '이미 송금하거나 결제했어요.',
    verify: '어떻게 공식적으로 확인하나요?',
    not_clicked: '아직 링크를 누르지 않았어요.',
    unknown: '무엇을 했는지 잘 모르겠어요.'
  });
  const riskLabels = Object.freeze({
    NO_STRONG_SIGNAL: '현재 강한 위험 신호 미감지 · 안전 보증 아님',
    CAUTION: '추가 확인 필요',
    PAUSE_AND_VERIFY: '중단 및 독립 확인 권고',
    ASK_HUMAN: '사람 확인 필요 · 판단 보류'
  });
  const MAX_BUBBLES = 60;
  let active = null, inflight = false, revision = 0, shown = 0;
  const buttons = [...(document.querySelectorAll?.('[data-followup]') || [])];

  function append(role, label, content, meta, steps, sources) {
    const wrap = document.createElement('article');
    wrap.className = 'conversation-bubble conversation-' + role;
    const title = document.createElement('p');
    title.className = 'conversation-bubble-label';
    title.textContent = label;
    wrap.appendChild(title);
    const message = document.createElement('p');
    message.className = 'conversation-bubble-text';
    message.textContent = String(content || '');
    wrap.appendChild(message);
    if (Array.isArray(steps) && steps.length) {
      const list = document.createElement('ol');
      list.className = 'conversation-steps';
      for (const step of steps.slice(0, 5)) {
        const item = document.createElement('li');
        item.textContent = String(step);
        list.appendChild(item);
      }
      wrap.appendChild(list);
    }
    if (Array.isArray(sources) && sources.length) {
      const cite = document.createElement('p');
      cite.className = 'conversation-sources';
      cite.textContent = '참고: ';
      for (const source of sources.slice(0, 2)) {
        if (!source || typeof source.url !== 'string' ||
            !/^https:\/\/(www\.)?(boho\.or\.kr|consumer\.ftc\.gov)\//.test(source.url)) continue;
        const link = document.createElement('a');
        link.textContent = String(source.name || '공식 자료');
        link.href = source.url;
        link.rel = 'noopener noreferrer';
        link.target = '_blank';
        cite.appendChild(link);
      }
      wrap.appendChild(cite);
    }
    const origin = document.createElement('p');
    origin.className = 'conversation-bubble-meta';
    origin.textContent = String(meta || '');
    wrap.appendChild(origin);
    feed.appendChild(wrap);
    shown += 1;
    while (shown > MAX_BUBBLES && feed.firstChild) {
      feed.removeChild(feed.firstChild);
      shown -= 1;
    }
    if (typeof feed.scrollHeight === 'number') feed.scrollTop = feed.scrollHeight;
  }

  function setReady() {
    const ready = !!active && !inflight;
    send.disabled = !ready || !field.value.trim();
    for (const button of buttons) button.disabled = !ready;
  }
  function status(message) { info.textContent = message; }
  function reset(message) {
    revision += 1;
    active = null;
    field.value = '';
    feed.textContent = '';
    shown = 0;
    inflight = false;
    status(message || '원본 합성 문장을 먼저 판단해 주세요.');
    setReady();
  }
  function invalidate(reason) {
    revision += 1;
    active = null;
    status(reason === 'input_changed'
      ? '원본 문장이 변경됐습니다. 새 문장을 다시 판단해야 후속 질문을 할 수 있습니다.'
      : '판단·세션 상태가 변경됐습니다. 저장 상태를 확인하고 새 판단을 진행하세요.');
    setReady();
  }
  function inferScenario(raw) {
    const q = String(raw || '').replace(/\s+/g, ' ').trim();
    if (!q || q.length > 300) return null;
    // Respond only when wording unambiguously refers to a bounded situation.
    // This is not semantic inference or a general language-model conversation.
    if (/송금했|이체했|입금했|결제했|돈을?\s*보냈|돈\s*보내버렸/.test(q)) return 'paid';
    if (/(인증번호|비밀번호|OTP|인증\s*코드|패스워드).{0,18}(입력했|보냈|알려줬|전달했|공유했)/i.test(q) ||
        /(입력했|보냈|알려줬|공유했).{0,18}(인증번호|비밀번호|OTP|인증\s*코드)/i.test(q)) return 'entered_secret';
    if (/설치했|앱\s*깔았|프로그램\s*실행했|원격.{0,8}허용했/.test(q)) return 'installed';
    if (/다운로드했|내려받았|파일을?\s*받았/.test(q)) return 'downloaded';
    if (/(링크|주소|사이트).{0,20}(안\s*눌렀|안\s*열었|클릭하지\s*않았|누르지\s*않았)/.test(q)) return 'not_clicked';
    if (/(이미|방금|실수로).{0,18}(링크|주소|사이트).{0,20}(눌렀|클릭했|열었|접속했)/.test(q) ||
        /(링크|주소|사이트).{0,18}(눌렀어|눌렀어요|클릭했어|클릭했어요|열었어|접속했어)/.test(q)) return 'clicked';
    if (/링크만|링크.{0,12}(누르면|눌러도|클릭하면|클릭해도|열면|열어도)/.test(q)) return 'link_only';
    if (/공식.{0,10}(확인|문의|전화)|어떻게.{0,12}(확인|신고|검증)|확인\s*방법/.test(q)) return 'verify';
    if (/잘\s*모르겠|무엇을\s*했는지\s*모르|기억이\s*안/.test(q)) return 'unknown';
    return null;
  }

  async function followup(scenario, userText) {
    if (!active || inflight || !Object.hasOwn(SCENARIOS, scenario)) return;
    const snapshot = { ...active };
    const clock = revision;
    inflight = true;
    setReady();
    status('저장된 세션 버전과 상황을 확인하는 중입니다…');
    append('user', '사용자의 후속 질문', userText, '이 브라우저에서만 표시 · 서버로는 상황 코드만 전송');
    try {
      const r = await fetch('/api/conversation/followup', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: snapshot.session_id,
          version: snapshot.version, scenario, synthetic_only: true }),
        cache: 'no-store'
      });
      const result = await r.json();
      if (clock !== revision || !active ||
          snapshot.session_id !== active.session_id || snapshot.version !== active.version) return;
      if (!r.ok || !result || result.schema !== 'iteraguard-guided-conversation/1' ||
          result.mode !== 'RULE_BASED_FOLLOWUP_NOT_GENERATIVE' ||
          result.session_id !== snapshot.session_id || result.version !== snapshot.version ||
          result.scenario !== scenario || result.decision_changed !== false ||
          result.action_taken !== false || result.task_updated !== false ||
          result.risk_cleared !== false) {
        throw new Error(r.ok ? 'INVALID_FOLLOWUP_RESPONSE' : String(result?.error || 'FOLLOWUP_UNAVAILABLE'));
      }
      append('assistant', result.title,
        result.introduction + '\n\n' + result.risk_notice,
        '공식 자료 기반 규칙 안내 · Zoro 재추론·생성형 GPT 답변 아님 · 이력 변경 없음',
        result.steps, result.sources);
      status('후속 상황 안내를 확인했습니다. 새로운 행동이 생기면 아래에서 선택하세요.');
      field.value = '';
    } catch (_) {
      if (clock !== revision) return;
      append('assistant', '확인 보류',
        '후속 안내를 현재 세션과 연결해 검증하지 못했습니다. 저장 상태를 다시 조회하고 원본 문장을 재판단해 주세요. 이전 위험이 해제된 것은 아닙니다.',
        '규칙 기반 안내 실패 · 저장된 세션 내용 변경 없음');
      status('상황 확인 실패 · 이전 위험 유지 · 자동 재시도하지 않음');
      active = null;
    } finally {
      inflight = false;
      setReady();
    }
  }

  function onDecision(data) {
    if (!data || typeof data.session_id !== 'string' ||
        !Number.isInteger(data.version) || typeof data.text !== 'string') return;
    revision += 1;
    active = { session_id: data.session_id, version: data.version };
    const failed = data.model_status !== 'VALID';
    const fixture = data.provenance === 'CONTROLLED_CLIENT';
    const source = failed ? '모델 연결/응답 검증 실패 · 실제 추론 결과 없음' :
      fixture ? '통제 응답(FIXTURE) · 실제 Zoro 추론 아님' :
      '로컬 모델 응답(체크포인트 신원 미인증) + 독립 정책';
    append('user', '검토할 합성 메시지', data.text, '현재 메시지만 평가 · 원문 대화는 SQLite에 저장하지 않음');
    const action = riskLabels[data.action] || '결과 확인 필요';
    const kept = data.prior_pause ? '\n기존 위험 보류 이력은 유지됩니다.' : '';
    append('assistant', '현재 판단 및 다음 단계',
      action + '\n' + String(data.message || '판단 근거를 확인해 주세요.') +
      kept + '\n남은 확인 업무: ' + Number(data.task_count || 0) + '건',
      source + ' · 채팅형 요약은 별도 모델 생성이 아님');
    status('지금까지의 판단을 유지하면서 상황별 후속 질문을 할 수 있습니다. 문장형 질문은 제한된 표현만 인식합니다.');
    setReady();
  }
  document.addEventListener('iteraguard:reset', event => reset('새 세션입니다. 원본 합성 문장을 먼저 판단해 주세요.'));
  document.addEventListener('iteraguard:invalidate', event => invalidate(event?.detail?.reason));
  document.addEventListener('iteraguard:pending', () => {
    revision += 1; active = null;
    status('원본 메시지 재판단 중 · 이전 후속 안내는 현재 판단으로 확정되지 않았습니다.');
    setReady();
  });
  document.addEventListener('iteraguard:decision', event => onDecision(event.detail));

  for (const button of buttons) {
    button.addEventListener('click', () => {
      const scenario = button.dataset.followup;
      if (!Object.hasOwn(SCENARIOS, scenario)) return;
      void followup(scenario, SCENARIOS[scenario]);
    });
  }
  field.addEventListener('input', setReady);
  field.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      send.click();
    }
  });
  send.addEventListener('click', () => {
    if (!active || inflight) return;
    const prompt = field.value.trim();
    const scenario = inferScenario(prompt);
    if (!scenario) {
      status('자유 질문의 상황을 확정할 수 없습니다. 아래의 상황 버튼 중 하나를 선택해 주세요. 새 모델 판단을 임의로 만들지 않습니다.');
      return;
    }
    void followup(scenario, prompt);
  });
  reset('원본 합성 문장을 먼저 판단해 주세요. 상담 원문은 브라우저 메모리에만 유지됩니다.');
}());
