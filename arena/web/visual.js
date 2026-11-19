'use strict';
// IteraGuard Arena v5.9 presentation layer. It only observes requests and DOM text that
// main.js already owns; it never changes a payload, a decision or stored state.
(function () {
  const $ = id => document.getElementById(id);
  const el = $;
  const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const body = document.body;

  const VERDICT = {
    NO_STRONG_SIGNAL: { title: '뚜렷한 위험 요청은 보이지 않아요', core: '신호 약함', kicker: '현재 안내 · 안전 보증은 아니에요' },
    CAUTION: { title: '한 번 더 확인해 주세요', core: '확인 필요', kicker: '현재 안내' },
    PAUSE_AND_VERIFY: { title: '잠깐 멈추고, 공식 경로로 확인하세요', core: '멈춤', kicker: '현재 안내 · 강한 위험 신호' },
    ASK_HUMAN: { title: '지금은 자동으로 판단하지 않아요', core: '사람 확인', kicker: '현재 안내 · 판단 보류' }
  };
  const SHORT = { NO_STRONG_SIGNAL: '신호 약함', CAUTION: '확인 필요', PAUSE_AND_VERIFY: '멈춤·확인', ASK_HUMAN: '사람 확인' };

  // Connection is a recent validated API response, not checkpoint identity attestation.
  let connectionTimer;
  function modelConnection(state) {
    clearTimeout(connectionTimer);
    body.dataset.modelConnection = state;
    const label = $('coreLabel');
    if (label) {
      label.textContent = state === 'connected' ? 'ZORO-1 연결 완료' : state === 'failed' ? '연결 확인 필요' : state === 'fixture' ? '테스트 응답' : '대기';
      label.title = state === 'connected' ? '최근 실제 모델 API 응답 확인 · 모델 신원 미인증 · 60초 후 재확인 필요' : '';
    }
    if (state === 'connected') connectionTimer = setTimeout(() => modelConnection('waiting'), 60000);
  }
  function observeModelConnection(d) {
    const p = d && d.provenance;
    modelConnection(d && d.model_status === 'VALID' && p && p.execution_source === 'LOCAL_HTTP_MODEL_UNATTESTED' &&
      /^[a-f0-9]{64}$/i.test(p.response_sha256 || '') ? 'connected' :
      p && p.execution_source === 'CONTROLLED_CLIENT' ? 'fixture' : 'failed');
  }

  // ---------- pipeline ----------
  const stages = {};
  document.querySelectorAll('.stage').forEach(li => { stages[li.dataset.stage] = li; });
  const ORDER = ['input', 'model', 'contract', 'policy', 'task'];
  const defaults = {};
  ORDER.forEach(k => { defaults[k] = stages[k] && stages[k].querySelector('[data-detail]').textContent; });
  let timers = [];
  const later = (fn, ms) => { timers.push(setTimeout(fn, reduce ? 0 : ms)); };
  function setStage(k, state, detail) {
    const li = stages[k]; if (!li) return;
    if (state) li.dataset.state = state; else delete li.dataset.state;
    if (detail !== undefined) li.querySelector('[data-detail]').textContent = detail;
  }
  function resetStages() { timers.forEach(clearTimeout); timers = []; ORDER.forEach(k => setStage(k, null, defaults[k])); }
  function pipelineStart(payload) {
    resetStages();
    const panel = $('pipelinePanel');
    if (panel) panel.hidden = false;
    body.dataset.phase = 'running';
    core.busy = true;
    const n = Array.from((payload && payload.text) || '').length;
    setStage('input', 'done', n + '자 · 검토 요청');
    setStage('model', 'active', '서버의 판단 응답을 기다리는 중 · 모델 출처는 응답 후 확인');
    $('pipeMeta').textContent = '응답 대기 중 · 실제 진행률은 제공되지 않습니다';
  }

  function sourceLabel(d) {
    const src = d.provenance && d.provenance.execution_source;
    return src === 'CONTROLLED_CLIENT' ? '통제 응답 · 실제 추론 아님' : 'Zoro-1 응답 · 신원 미인증';
  }
  function pipelineFinish(d) {
    // The HTTP response has actually arrived; never animate imagined internal
    // model/contract/policy timings or claim stream events that were not emitted.
    observeModelConnection(d);
    timers.forEach(clearTimeout); timers = [];
    const failed = d.model_status === 'FAILED';
    lastModelFailed = failed;
    syncVerdict();
    setStage('input', 'done', Array.from(el('text').value).length + '자 · 요청 접수');
    setStage('model', failed ? 'fail' : 'done',
      failed ? '모델 결과를 확인할 수 없음' : sourceLabel(d));
    setStage('contract', failed ? 'warn' : 'done',
      failed ? '계약 판단 보류' : '서버가 응답 계약 처리 결과를 반환함');
    const action = d.current_turn_action || d.action;
    setStage('policy', failed ? 'warn' : 'done',
      failed ? '사람 확인 권고' : '서버 정책 결과 수신 · ' + (SHORT[action] || '추가 확인'));
    const n = Number.isInteger(d.open_task_count) ? d.open_task_count : (d.open_tasks || []).length;
    setStage('task', n ? 'warn' : 'done',
      n ? '공식 경로에서 확인할 항목 ' + n + '건' : '추가 항목 정보 없음');
    $('pipeMeta').textContent = failed ? '모델 결과 검증 불가 · 사람 확인 안내' :
      '서버 응답 수신 · 화면 반영 중';
    setMode(failed ? 'warn' : 'ok',
      failed ? '모델 응답 검증 실패' : sourceLabel(d));
    later(() => {
      const panel = $('pipelinePanel');
      if (panel) panel.hidden = true;
      body.dataset.phase = 'idle';
      core.busy = false;
    }, 650);
  }

  function pipelineFail(message) {
    modelConnection('failed');
    timers.forEach(clearTimeout); timers = [];
    const active = ORDER.find(k => stages[k] && stages[k].dataset.state === 'active') || 'model';
    setStage(active, 'fail', '요청 실패 · ' + message);
    $('pipeMeta').textContent = '서버 응답을 확인하지 못했습니다';
    later(() => {
      const panel = $('pipelinePanel');
      if (panel) panel.hidden = true;
      body.dataset.phase = 'idle';
      core.busy = false;
    }, 650);
  }


  // ---------- observe requests made by main.js (read-only) ----------
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async function (url, options) {
    const path = typeof url === 'string' ? url : (url && url.url) || '';
    const isEval = path === '/api/evaluate';
    let payload = null;
    if (isEval) { try { payload = JSON.parse(options && options.body); } catch (_) { payload = null; } pipelineStart(payload); }
    let response;
    try { response = await nativeFetch(url, options); }
    catch (e) { if (isEval) pipelineFail('네트워크 오류'); throw e; }
    if (isEval || path === '/api/manifest') {
      response.clone().json().then(d => {
        if (path === '/api/manifest') { if (response.ok) setMode(null, '계약 로드됨 · 판단 시 모델 확인'); else setMode('warn', '실행 계약을 불러오지 못함'); return; }
        if (response.ok) pipelineFinish(d); else pipelineFail(d && d.error ? d.error : 'HTTP ' + response.status);
      }).catch(() => { if (isEval) pipelineFail('응답 해석 실패'); });
    }
    return response;
  };

  function setMode(state, text) { const p = $('modePill'); if (!p) return; p.textContent = text; if (state) p.dataset.state = state; else delete p.dataset.state; }

  // ---------- verdict presentation (mirrors #action set by main.js) ----------
  const action = $('action');
  // Protective "what not to do yet" line. Presentation only: the server decision is unchanged.
  const HINT = {
    PAUSE_AND_VERIFY: '확인이 끝나기 전에는 송금·인증번호 전달·앱 설치·링크 로그인을 하지 마세요.',
    ASK_HUMAN: '판단이 보류된 동안에도 송금·인증번호 전달·앱 설치는 미뤄 두세요.',
    CAUTION: '메시지 속 연락처가 아니라, 원래 알고 있던 공식 경로로 확인하세요.'
  };
  let lastModelFailed = false;
  function syncVerdict() {
    const code = action.textContent.trim();
    const v = VERDICT[code];
    const reason = ($('reason').textContent || '').trim();
    // main.js marks a stale/unknown result with this exact source line (currentInputRequired).
    const stale = /재평가 후 확인/.test($('executionSource').textContent || '');
    if (stale) {
      body.dataset.verdict = 'idle';
      $('verdictTitle').textContent = '문장이 바뀌었어요. 다시 판단해 주세요';
      $('verdictKicker').textContent = '현재 안내';

      const h = $('verdictHint'); if (h) { h.textContent = ''; h.hidden = true; }
      core.setAccent();
      return;
    }
    body.dataset.verdict = v ? code : 'idle';
    let title = v ? v.title : (code === '평가 전' ? '문장을 넣고 판단을 시작하세요' : '판단 결과를 다시 확인하세요');
    if (code === 'ASK_HUMAN' && reason === 'PRIOR_RISK_UNRESOLVED') title = '앞서 감지한 위험이 아직 남아 있어요';
    else if (code === 'ASK_HUMAN' && lastModelFailed) title = '모델 응답을 받지 못해 판단을 보류했어요';
    $('verdictTitle').textContent = title;
    const hint = $('verdictHint');
    if (hint) { hint.textContent = HINT[code] || ''; hint.hidden = !HINT[code]; }
    $('verdictKicker').textContent = v ? v.kicker : '현재 안내';

    core.setAccent();
    body.dataset.flash = '0'; void body.offsetWidth; body.dataset.flash = '1';
  }
  new MutationObserver(syncVerdict).observe(action, { childList: true, characterData: true, subtree: true });
  new MutationObserver(syncVerdict).observe($('reason'), { childList: true, characterData: true, subtree: true });
  new MutationObserver(syncVerdict).observe($('executionSource'), { childList: true, characterData: true, subtree: true });

  // ---------- tasks panel only when work exists ----------
  const queue = $('taskQueue'), panel = $('taskPanel');
  const TASK_KO = { PAUSE_AND_INDEPENDENT_CHECK: '멈추고 공식 경로로 확인', CLARIFY_REQUEST: '요청 내용 확인', MODEL_RETRY: '모델 연결 후 다시 판단',
    INDEPENDENT_CHANNEL_CHECK: '독립 경로로 확인' };
  function syncTasks() {
    panel.dataset.empty = queue.options.length ? 'false' : 'true';
    // Display label only; option values (task ids) stay exactly as main.js wrote them.
    Array.from(queue.options).forEach((o, i) => {
      const m = /^([A-Z_]+) · ([0-9a-f]{8})$/.exec(o.textContent);
      if (m) o.textContent = (i + 1) + '. ' + (TASK_KO[m[1]] || m[1]) + ' · ' + m[2];
    });
  }
  new MutationObserver(syncTasks).observe(queue, { childList: true });

  // ---------- character counter ----------
  const text = $('text');
  const count = () => { $('charCount').textContent = Array.from(text.value).length + ' / 2000'; };
  text.addEventListener('input', () => { lastModelFailed = false; count(); });
  document.querySelectorAll('[data-sample]').forEach(b => b.addEventListener('click', () => setTimeout(count, 0)));

  // ---------- sheet ----------
  const sheet = $('sheet'), scrim = $('scrim'), opener = $('openSheet');
  function openSheet() {
    sheet.classList.add('open'); sheet.setAttribute('aria-hidden', 'false'); scrim.hidden = false;
    opener?.setAttribute('aria-expanded', 'true'); setTimeout(() => $('closeSheet').focus(), 50);
  }
  function closeSheet() {
    sheet.classList.remove('open'); sheet.setAttribute('aria-hidden', 'true'); scrim.hidden = true;
    opener?.setAttribute('aria-expanded', 'false'); opener?.focus();
  }
  opener?.addEventListener('click', openSheet);
  $('closeSheet').addEventListener('click', closeSheet);
  scrim.addEventListener('click', closeSheet);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && sheet.classList.contains('open')) closeSheet();
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && document.activeElement === text && !$('run').disabled) $('run').click();
  });

  // ---------- subtle 3D tilt on the composer ----------
  const tilt = document.querySelector('.tilt');
  if (tilt && !reduce && matchMedia('(pointer:fine)').matches) {
    tilt.addEventListener('pointermove', e => {
      const r = tilt.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      tilt.style.transform = 'perspective(1100px) rotateX(' + (-y * 2.4).toFixed(2) + 'deg) rotateY(' + (x * 3.2).toFixed(2) + 'deg)';
    });
    tilt.addEventListener('pointerleave', () => { tilt.style.transform = ''; });
  }

  // ---------- "doubt core": a lit glass sphere with orbiting rings (canvas, no libraries) ----------
  const core = (function () {
    const cv = $('coreCanvas'), ctx = cv && cv.getContext('2d');
    const state = { busy: false, rgb: [124, 156, 255], rgb2: [155, 123, 255], t: 0, running: true, visible: true };
    function css(name) {
      const v = getComputedStyle(body).getPropertyValue(name).trim();
      const m = /^#([0-9a-f]{6})$/i.exec(v);
      return m ? [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16)) : null;
    }
    function setAccent() { state.rgb = css('--accent') || state.rgb; state.rgb2 = css('--accent-2') || state.rgb2; }
    if (!ctx) return { setAccent, set busy(v) {}, get busy() { return false; } };
    const rgba = (c, a) => 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')';
    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2), s = cv.getBoundingClientRect();
      cv.width = Math.max(1, Math.round(s.width * dpr)); cv.height = Math.max(1, Math.round(s.height * dpr));
      if (reduce) { state.running = true; frame(); }
    }
    const rings = [{ tilt: 1.15, spin: .0055, phase: 0, r: .43 }, { tilt: .55, spin: -.0038, phase: 1.7, r: .47 }, { tilt: 1.45, spin: .0029, phase: 3.1, r: .38 }];
    function project(theta, ring, R, cx, cy) {
      const x = Math.cos(theta) * R * ring.r * 2, z = Math.sin(theta) * R * ring.r * 2;
      const y = z * Math.cos(ring.tilt), depth = z * Math.sin(ring.tilt);
      const rot = ring.phase + state.t * .0004;
      return [cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot), depth];
    }
    function frame() {
      if (!state.running) return;
      // Hidden mobile decoration has no drawable area; resume on resize/intersection.
      if (cv.width < 8 || cv.height < 8) { state.running = false; return; }
      const W = cv.width, H = cv.height, cx = W / 2, cy = H / 2, R = Math.min(W, H) * .30;
      const speed = state.busy ? 3.2 : 1;
      state.t += 16 * speed;
      ctx.clearRect(0, 0, W, H);
      // glow
      const g0 = ctx.createRadialGradient(cx, cy, R * .2, cx, cy, R * 1.9);
      g0.addColorStop(0, rgba(state.rgb, state.busy ? .38 : .26)); g0.addColorStop(1, rgba(state.rgb, 0));
      ctx.fillStyle = g0; ctx.fillRect(0, 0, W, H);
      // back halves of rings
      drawRings(cx, cy, R, false);
      // sphere body
      const breathe = 1 + Math.sin(state.t * .0025) * (state.busy ? .035 : .015);
      const r = R * breathe;
      const g = ctx.createRadialGradient(cx - r * .35, cy - r * .45, r * .08, cx, cy, r);
      g.addColorStop(0, 'rgba(255,255,255,.95)'); g.addColorStop(.18, rgba(state.rgb, .85));
      g.addColorStop(.65, rgba(state.rgb2, .55)); g.addColorStop(1, 'rgba(8,10,20,.9)');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = g; ctx.fill();
      // inner swirl
      ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
      for (let i = 0; i < 3; i++) {
        const a = state.t * .0009 * (i % 2 ? -1 : 1) + i * 2.1;
        const sg = ctx.createRadialGradient(cx + Math.cos(a) * r * .45, cy + Math.sin(a) * r * .35, 0, cx + Math.cos(a) * r * .45, cy + Math.sin(a) * r * .35, r * .8);
        sg.addColorStop(0, rgba(i === 1 ? state.rgb2 : state.rgb, .35)); sg.addColorStop(1, rgba(state.rgb, 0));
        ctx.fillStyle = sg; ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
      }
      // specular rim
      const rim = ctx.createLinearGradient(cx - r, cy - r, cx + r, cy + r);
      rim.addColorStop(0, 'rgba(255,255,255,.55)'); rim.addColorStop(.5, 'rgba(255,255,255,0)'); rim.addColorStop(1, 'rgba(255,255,255,.18)');
      ctx.restore();
      ctx.beginPath(); ctx.arc(cx, cy, r - 1, 0, Math.PI * 2); ctx.lineWidth = Math.max(1, W / 360); ctx.strokeStyle = rim; ctx.stroke();
      // highlight
      ctx.beginPath(); ctx.ellipse(cx - r * .38, cy - r * .5, r * .28, r * .14, -.6, 0, Math.PI * 2); ctx.fillStyle = 'rgba(255,255,255,.28)'; ctx.fill();
      drawRings(cx, cy, R, true);
      if (reduce) state.running = false;
      else if (state.visible && !document.hidden) requestAnimationFrame(frame); else state.running = false;
    }
    function drawRings(cx, cy, R, front) {
      rings.forEach((ring, k) => {
        ring.theta = (ring.theta || 0) + ring.spin * (state.busy ? 3 : 1);
        const steps = 90;
        ctx.beginPath(); let started = false;
        for (let i = 0; i <= steps; i++) {
          const th = i / steps * Math.PI * 2, p = project(th, ring, R, cx, cy);
          if ((p[2] >= 0) === front) { if (!started) { ctx.moveTo(p[0], p[1]); started = true; } else ctx.lineTo(p[0], p[1]); }
          else started = false;
        }
        ctx.strokeStyle = rgba(k === 1 ? state.rgb2 : state.rgb, front ? .55 : .18); ctx.lineWidth = Math.max(1, cv.width / 420); ctx.stroke();
        // satellite
        const p = project(ring.theta * 6, ring, R, cx, cy);
        if ((p[2] >= 0) === front) {
          const size = (front ? 1 : .6) * Math.max(2.4, cv.width / 140);
          ctx.beginPath(); ctx.arc(p[0], p[1], size, 0, Math.PI * 2); ctx.fillStyle = rgba(k === 1 ? state.rgb2 : state.rgb, front ? .95 : .45); ctx.fill();
          if (front) { ctx.beginPath(); ctx.arc(p[0], p[1], size * 3.2, 0, Math.PI * 2); ctx.fillStyle = rgba(state.rgb, .12); ctx.fill(); }
        }
      });
    }
    function start() { if (!state.running && state.visible && !document.hidden) { state.running = true; requestAnimationFrame(frame); } }
    resize(); setAccent();
    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', start);
    if ('IntersectionObserver' in window) new IntersectionObserver(es => { state.visible = es[0].isIntersecting; start(); }).observe(cv);
    if (reduce) { state.running = true; frame(); state.running = false; }
    else requestAnimationFrame(frame);
    return {
      setAccent() { setAccent(); if (reduce) { state.running = true; frame(); state.running = false; } },
      get busy() { return state.busy; }, set busy(v) { state.busy = !!v; start(); }
    };
  })();

  modelConnection('waiting');
  count();
})();
