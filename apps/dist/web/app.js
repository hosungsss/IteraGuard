/* 의심계 app shell. Selected Zoro responses use the profile-bound v5.1 contract. */
(function () {
  'use strict';
  var E = window.DMSG, C = window.DMSG_V51, B = window.DMSG_BUILD || {};
  var $ = function (id) { return document.getElementById(id); };
  var session = new E.Session(), turnSeq = 0, host = 'browser', modelReady = false;
  var editorRevision = 0;
  var ANALYSIS_SCOPE = 'CURRENT_TEXT_ONLY_NO_SESSION_RISK';
  var SCOPE_NOTICE = '현재 문장만 분석하며 이전 문장의 위험은 이어서 판단하지 않습니다.';

  // ---------- v4.5 on-device NLP (lazy, offline; assets are plain JS so file:// works) ----------
  var NLP = { state: 'idle', model: null, promise: null, error: null, loadMs: null };
  // One baseline across desktop/web/arena. DRA remains an explicitly selected comparison.
  var ARB = { mode: 'v46' };
  function policyId() { return ARB.mode === 'dra' ? 'dra' : 'legacy'; }
  function bindingKey(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return '';
    return JSON.stringify(Object.keys(value).sort().map(function (key) { return [key, value[key]]; }));
  }
  function modelSnapshot(id) {
    try {
      if (!C) throw new Error('CONTRACT_MISSING');
      var profile = C.selectedProfile(id), expected = C.requestBinding(profile, id);
      if (C.validateBinding(expected, profile, id) === false) throw new Error('PROFILE_BINDING_MISMATCH');
      return { policy_id: id, profile_id: profile, profile_binding: JSON.parse(JSON.stringify(expected)), profile_key: bindingKey(expected) };
    } catch (e) { return { policy_id: id, profile_id: null, profile_binding: null, profile_key: '', profile_error: true }; }
  }
  function modelFailure(code, snapshot) {
    var id = snapshot && snapshot.policy_id || policyId();
    try { if (C) return C.unavailableCurrent(code, id, { profile_id: snapshot && snapshot.profile_id }); } catch (e) { /* display a static hold when the contract itself cannot load */ }
    var out = E.modelUnavailable('ContractError:V51_PROFILE_CONTRACT_UNAVAILABLE');
    out.policy_id = id; out.mode = 'MODEL_UNAVAILABLE_OR_INVALID'; return out;
  }
  var LG = window.LinkGuard || null, AS = window.ApkScan || null;
  function consent() { var a = $('consentRep'), b = $('consentWeb'); return { external_reputation: !!(a && a.checked), web_analysis: !!(b && b.checked) }; }
  function loadScript(src) {
    return new Promise(function (ok, bad) { var sc = document.createElement('script'); sc.src = src; sc.async = true; sc.onload = ok; sc.onerror = function () { bad(new Error('LOAD_FAILED:' + src)); }; document.head.appendChild(sc); });
  }
  function loadNLP() {
    if (NLP.promise) return NLP.promise;
    if (!window.DmsgNLP) { NLP.state = 'unavailable'; NLP.error = 'NLP_RUNTIME_MISSING'; nlpHint(); return (NLP.promise = Promise.resolve(null)); }
    NLP.state = 'loading'; nlpHint(); var t = Date.now();
    NLP.promise = loadScript('nlp/dmsg-nlp-vocab.js').then(function () { return loadScript('nlp/dmsg-nlp-heads.js'); })
      .then(function () { return loadScript('nlp/dmsg-nlp-weights.js'); })
      .then(function () {
        NLP.model = new window.DmsgNLP.Model({ weights: window.DmsgNLP.b64ToBuf(window.DMSG_NLP_WEIGHTS_B64), vocab: window.DMSG_NLP_VOCAB,
          heads: window.DMSG_NLP_HEADS, heads_sha256: window.DMSG_NLP_HEADS_SHA256, arbiter: ARB.mode }, E);
        window.DMSG_NLP_WEIGHTS_B64 = null;   // free ~20 MB of string memory
        NLP.state = 'ready'; NLP.loadMs = Date.now() - t; nlpHint(); return NLP.model;
      })
      .catch(function (e) { NLP.state = 'unavailable'; NLP.error = (e && e.message) || 'MODEL_UNAVAILABLE'; nlpHint(); return null; });
    return NLP.promise;
  }
  function nlpHint() {
    var h = document.getElementById('nlpHint'); if (!h) return;
    var rb = document.getElementById('nlpRetry'); if (rb) rb.hidden = NLP.state !== 'unavailable';
    h.textContent = NLP.state === 'ready' ? '(준비됨 · 이 기기에서 실행 · 외부 전송 없음)' : NLP.state === 'loading' ? '(모델 준비 중…)' :
      NLP.state === 'unavailable' ? '(불러오지 못함: ' + (NLP.error || '원인 미상') + ' · 로컬 기본 점검으로 대체)' : '(모델 준비 전)';
  }

  var STATE = {
    NO_STRONG_SIGNAL: { ko: '뚜렷한 위험 행동 요청 미감지 (안전 보증 아님)', icon: '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 12h7"/>' },
    CAUTION: { ko: '주의: 응하기 전 독립 경로로 확인하세요', icon: '<path d="M12 4 21 19H3z"/><path d="M12 10v4M12 16.8v.2"/>' },
    PAUSE_AND_VERIFY: { ko: '잠시 멈추고 공식 경로에서 직접 확인하세요', icon: '<rect x="6.5" y="5" width="3.6" height="14" rx="1.2"/><rect x="13.9" y="5" width="3.6" height="14" rx="1.2"/>' },
    ASK_HUMAN: { ko: '판단 보류: 신뢰할 수 있는 경로로 확인하세요', icon: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c.9-3.6 3.7-5.5 7-5.5s6.1 1.9 7 5.5"/>' },
    HOLD: { ko: '지급 보류 · 독립 확인', icon: '<rect x="5" y="10.5" width="14" height="9.5" rx="2.2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>' },
    READY: { ko: '내부 검토 준비 (지급 승인 아님)', icon: '<path d="M5 12.5 10 17l9-10"/>' }
  };
  var KO = {};
  var SUB = { NO_STRONG_SIGNAL: '안전이 확인된 것은 아닙니다.', CAUTION: '추가 확인을 권해요.', PAUSE_AND_VERIFY: '위험할 수 있는 행동을 잠시 멈추세요.', ASK_HUMAN: '자동 판단을 보류했어요.' };
  var INTENT_KO = { ORDINARY_INFORMATION: '일반 안내·대화', LEGITIMATE_REQUEST: '일상적 요청', COMMERCIAL_PROMOTION: '상업 광고', CONTACT_SOLICITATION: '연락·접촉 유도',
    PAYMENT_SOLICITATION: '금전 요구', CREDENTIAL_SOLICITATION: '계정·인증정보 요구', IMPERSONATION_CLAIM: '기관·지인 사칭 가능성' };
  var REQ_KO = { MONEY_TRANSFER: '송금', CREDENTIAL_DISCLOSURE: '인증정보 제공', PERSONAL_DATA_DISCLOSURE: '개인정보 제공', INSTALL_APPLICATION: '앱 설치',
    CLICK_LINK: '링크 열기', MOVE_TO_EXTERNAL_MESSENGER: '다른 메신저로 이동', CONTACT_UNKNOWN_PERSON: '모르는 사람과 연락·만남', NO_EXPLICIT_ACTION: '명시적 요구 없음' };
  var IND_KO = { OFF_PLATFORM_CONTACT: '다른 메신저로 이동 유도', UNVERIFIED_IDENTITY: '확인되지 않은 신원', URGENCY_OR_PRESSURE: '서두름·압박', FINANCIAL_INDUCEMENT: '금전 유인',
    CREDENTIAL_REQUEST: '인증정보 요구', ACCOUNT_CHANGE_REQUEST: '계좌 변경 요청', IMPERSONATION_SIGNAL: '사칭 정황', MALICIOUS_LINK_SUSPICION: '의심스러운 링크', UNWANTED_SOLICITATION: '원치 않는 접근·권유' };
  var STRUCT_KO = { MESSENGER_HANDOFF: '외부 메신저 ID', MESSENGER_HANDLE: '메신저 핸들', URL: '링크 주소', PHONE: '전화번호', MONEY_AMOUNT: '금액', OVERSEAS_SENDER_TAG: '해외발신 표시', ACCOUNT_CHANGE_PHRASE: '계좌 변경 문구' };
  var UNC_KO = { LOW_TASK_CONFIDENCE: '모델 점수가 전반적으로 낮음', SPEECH_VS_REQUESTED_ACTION: '문장 유형과 요구 행동 판단이 엇갈림', CROSS_TASK_RISK_NOT_CLEARED: '의도·요구 행동 판단이 위험을 가리킴', CONTRACT_ERROR: '결과 형식 오류' };
  var SPEECH_KO = { DIRECT_REQUEST: '직접 요청', INDIRECT_REQUEST: '간접 요청', WARNING: '경고·금지', QUOTATION: '인용·전달', INFORMATION: '안내·서술',
    WARNING_OR_NEGATION: '경고·금지', QUOTATION_OR_REPORT: '인용·전달', INFORMATIONAL: '안내·서술', UNKNOWN: '판단 어려움' };
  var REASON = {
    CONFIRMED_DIRECT_RISK_REQUEST: '송금·인증정보·원격제어 같은 위험 행동을 직접 요구하는 문장이 주석으로 확인됐어요.',
    CONFIRMED_CAUTIONARY_REQUEST: '확인되지 않은 링크나 비밀 유지를 직접 요구해요.',
    REPORTED_ACTION_NOT_DIRECT_REQUEST: '위험 행동이 언급되지만, 지금 직접 요구하는 게 아니라 인용·신고된 내용이에요.',
    NO_VALIDATED_DIRECT_REQUEST: '직접적인 위험 행동 요구가 확인되지 않았어요. 안전하다는 뜻은 아니에요.',
    MODEL_NOT_AVAILABLE: '의미 분석 모델이 실행되지 않아 로컬 기본 점검만 했어요. 의미 분석 불가 — 추가 확인을 권해요.',
    MODEL_INFORMATIONAL_NOT_REQUEST: '모델이 행동을 요구하지 않는 안내·서술 문장으로 봤어요. 안전 판정은 아니에요.',
    INFORMATIONAL_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE: '모델은 안내문이라 했지만, 위험 행동을 시키는 문장이 따로 있어요.',
    AUX_COERCION_BLOCKS_INFORMATIONAL_CLEARANCE: '안내문처럼 보이지만 서두름·비밀 유지 압박이 함께 있어 해제하지 않았어요.',
    USER_REQUESTED_REVIEW: '사람 확인 요청으로 표시했어요.',
    MODEL_EVIDENCE_INSUFFICIENT: '모델이 스스로 근거가 부족하다고 답해 판단을 보류했어요.',
    RISK_INDICATORS_WITHOUT_EXPLICIT_ACTION: '직접적인 송금·인증 요구는 없지만, 원문에서 확인되는 위험 신호(다른 메신저 이동 유도·금전 유인 등)가 있어요.',
    GROUNDED_HIGH_SEVERITY_INDICATOR: '인증정보나 계좌 변경을 직접 요구하는 정황이 원문에서 확인돼요.',
    UNGROUNDED_RISK_INDICATOR: '모델이 위험 신호를 강하게 봤지만 원문에서 구조적 근거를 찾지 못해 판단을 보류했어요.',
    CROSS_TASK_RISK_NOT_CLEARED: '의도나 요구 행동 판단이 위험을 가리켜 "위험 없음"으로 끝내지 않았어요.',
    AMBIGUOUS_DIRECTNESS: '요청인지 아닌지 문장만으로는 분명하지 않아요.',
    EMPTY_OR_INVALID_INPUT: '입력이 비어 있거나 너무 길어요.',
    CONFLICTING_EVIDENCE_ANNOTATIONS: '같은 위치에 서로 다른 해석이 붙어 있어요.',
    UNVERIFIED_MODEL_EVIDENCE: '모델이 제안한 근거는 사람이 확인하기 전까지 쓰지 않아요.',
    MODEL_DIRECT_ACTION_ADVISORY: '모델이 위험 행동의 직접 요청으로 봤고, 문장 안에서 해당 표현을 찾았어요.',
    MODEL_DIRECT_CAUTION_ADVISORY: '모델이 링크·비밀 유지 등 주의가 필요한 직접 요청으로 봤어요.',
    MODEL_REPORTED_REQUEST: '모델이 인용·전달된 요청으로 봤어요.',
    MODEL_WARNING_NOT_REQUEST: '모델이 하지 말라는 경고문으로 봤고, 문장에도 경고 표현이 있어요.',
    NO_ACTION_CANDIDATE_NOT_SAFETY_CLEARANCE: '모델이 요청된 행동을 찾지 못했어요. 안전 판정은 아니에요.',
    MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS: '모델의 확신이 기준보다 낮거나 판단을 보류했어요.',
    CONFLICTING_MODEL_QUESTIONS: '모델 답변끼리 서로 맞지 않아요(행동 없음 vs 강한 압박 신호).',
    NO_GROUNDED_ACTION_ANCHOR: '모델이 말한 행동을 문장 안에서 찾을 수 없어요.',
    AUX_COERCION_BLOCKS_WARNING_CLEARANCE: '경고문처럼 보이지만 압박·비밀 유지 신호가 함께 있어 해제하지 않았어요.',
    MODEL_NONE_BUT_ACTION_TERMS_PRESENT: '모델은 요청이 없다고 했지만 송금·인증 같은 단어가 있어요.',
    NONE_DIRECT_REQUEST_CONFLICT: '모델의 두 답(행동 없음, 직접 요청)이 서로 모순이에요.',
    DIRECT_REQUEST_CONTRADICTS_CONTEXT: '모델은 직접 요청이라 했지만, 위험 표현이 모두 경고나 인용 안에 있어요.',
    WARNING_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE: '모델은 경고문이라 했지만, 부정·인용 없이 위험 행동을 시키는 문장이 따로 있어요.',
    REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE: '모델은 인용이라 했지만, 직접 시키는 문장이 따로 있어요.',
    UNSUPPORTED_WARNING_LABEL: '모델은 경고문이라 했지만 문장에 경고 표현이 없어요.',
    UNSUPPORTED_QUOTATION_LABEL: '모델은 인용이라 했지만 문장에 인용 표현이 없어요.',
    UNKNOWN_VENDOR_INVOICE_PAIR: '등록된 거래처·청구서 짝이 아니에요.',
    SENDER_CLAIM_DIFFERS_FROM_DIRECTORY: '발신 주소가 등록된 주소와 달라요.',
    BANK_ACCOUNT_CHANGED: '요청 계좌가 등록된 계좌와 달라요.',
    INVOICE_AMOUNT_MISMATCH: '금액이 청구서와 달라요.',
    LEXICAL_URGENCY_ONLY_UNVERIFIED: '긴급·비밀 같은 압박 표현이 있어요.',
    UNTRUSTED_MESSAGE_INSTRUCTION_CUE: '메일 본문이 시스템·승인 절차를 지시하려 해요. 본문은 지시가 아니라 데이터예요.',
    LINKGUARD_KNOWN_MALICIOUS: '문장 속 링크가 불러온 차단 목록에 있어요. 링크를 열지 말고 공식 경로로 확인하세요.',
    LINKGUARD_SUSPICIOUS: '문장 속 링크에서 위험 구조(유사 도메인·사설 IP·APK 다운로드 등)가 확인돼 주의 단계로 올렸어요.',
    DRA_MIN_EXPECTED_COST_CLEAR: '모델 답을 종합하면 위험 행동 요청일 가능성이 낮아요. 안전 판정은 아니에요.',
    DRA_MIN_EXPECTED_COST_CAUTION: '모델 답을 종합하면 응하기 전에 확인이 필요한 요청으로 보여요.',
    DRA_MIN_EXPECTED_COST_PAUSE: '모델 답을 종합하면 위험 행동의 직접 요청일 가능성이 커요. 문장 속 표현 위치도 찾았어요.',
    DRA_DECISION_RELEVANT_UNCERTAINTY: '모델 답이 서로 다른 안내로 갈려 있어, 자동으로 고르지 않고 사람 확인을 권해요.',
    DIRECTORY_FIELDS_MATCH_UNVERIFIED_SENDER: '등록 기록과 일치해요. 그래도 발신자 진위는 확인되지 않았어요.',
    V51_CURRENT_SENSITIVE_EXPOSURE: '민감정보 제공 또는 원격 제어를 요구하는 내용으로 분석됐어요.',
    V51_SCOPED_SENSITIVE_REQUEST: '문장 안에서 현재 민감정보 제공 또는 원격 제어를 요구하는 표현을 찾았어요.',
    V51_CURRENT_ANOMALOUS_PAYMENT: '송금 요구와 계좌 변경·압박 등 확인이 필요한 단서가 함께 보여요.',
    V51_SCOPED_PAYMENT_CORROBORATION: '현재 송금 요구와 비정상 조건·압박 표현이 함께 보여요.',
    V51_EXPLICIT_OTHER_REQUEST: '일상적인 요청으로 분석됐고, 민감한 행동 요구는 뚜렷하지 않아요. 안전 보증은 아니에요.',
    V51_EXPLICIT_INFORMATION_ONLY: '현재 문장은 정보를 알리는 내용으로 분석됐어요. 신원은 검증하지 않았어요.',
    V51_EXPLICIT_PROTECTIVE_WARNING: '민감한 행동을 하지 말라는 경고로 분석됐어요.'
  };
  function reasonText(code) {
    if (REASON[code]) return REASON[code];
    if (/^CONTRACT_/.test(code)) return '분석 결과 형식을 확인하지 못했어요. 중요한 행동은 멈추고 공식 경로로 확인하세요.';
    if (/^(ModelUnavailable|ContractError):/.test(code)) return '모델 응답을 받지 못했거나 형식이 맞지 않아요. 중요한 행동은 멈추고 공식 경로로 확인하세요.';
    return '판단 근거가 충분하지 않아요.';
  }
  function svg(path) { return '<svg viewBox="0 0 24 24">' + path + '</svg>'; }
  function el(tag, attrs, text) { var n = document.createElement(tag); if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]); if (text != null) n.textContent = text; return n; }
  function toast(msg) { var t = $('toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(function () { t.hidden = true; }, 2600); }

  // ---------- tabs ----------
  document.querySelectorAll('.tab').forEach(function (b) {
    b.addEventListener('click', function () { showView(b.dataset.view); });
    b.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      var tabs = Array.from(document.querySelectorAll('.tab')), i = tabs.indexOf(b) + (e.key === 'ArrowRight' ? 1 : -1);
      var nb = tabs[(i + tabs.length) % tabs.length]; nb.focus(); showView(nb.dataset.view);
    });
  });
  function showView(v, fromHistory) {
    if (!fromHistory && (!history.state || history.state.view !== v)) { try { history.pushState({ view: v }, ''); } catch (e) { /* file:// may refuse */ } }
    document.querySelectorAll('.tab').forEach(function (t) { var on = t.dataset.view === v; t.classList.toggle('on', on); t.setAttribute('aria-selected', on); t.tabIndex = on ? 0 : -1; });
    document.querySelectorAll('.view').forEach(function (s) { var on = s.id === 'view-' + v; s.hidden = !on; s.classList.toggle('active', on); });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  window.addEventListener('popstate', function (e) { showView((e.state && e.state.view) || 'analyze', true); });
  try { history.replaceState({ view: 'analyze' }, ''); } catch (e) { /* ignore */ }

  // ---------- analyze: source ----------
  var src = 'text', fixtureId = E.fixtures[0].id;
  document.querySelectorAll('.seg-btn[data-src]').forEach(function (b, i) {
    b.addEventListener('click', function () {
      invalidateAnalysis();
      src = b.dataset.src; b.parentNode.dataset.pos = i;
      document.querySelectorAll('.seg-btn[data-src]').forEach(function (x) { x.classList.toggle('on', x === b); x.setAttribute('aria-checked', x === b); });
      $('srcFixture').hidden = src !== 'fixture'; $('srcText').hidden = src !== 'text';
      if (src === 'text') $('freeText').focus();
    });
  });
  E.fixtures.forEach(function (f) {
    var c = el('button', { class: 'chip', role: 'option', 'aria-selected': f.id === fixtureId ? 'true' : 'false' }, f.title);
    c.addEventListener('click', function () { invalidateAnalysis(); fixtureId = f.id; document.querySelectorAll('#fixtureChips .chip').forEach(function (x) { x.setAttribute('aria-selected', x === c); }); showFixture(); });
    $('fixtureChips').appendChild(c);
  });
  function showFixture() {
    var f = E.fixtures.find(function (x) { return x.id === fixtureId; }), q = $('fixtureText');
    q.textContent = f.transcript; var s = el('span', { class: 'story' }, '합성 시나리오 · ' + f.story); q.appendChild(s);
  }
  showFixture();
  function invalidateAnalysis() {
    editorRevision += 1;
    $('resultCard').hidden = true;
    $('nextRow').hidden = true;
  }
  function analysisBinding(text) {
    var model = $('useModel').checked, snapshot = model ? modelSnapshot(policyId()) : null;
    return { session: session, version: session.version, revision: editorRevision, text: text, source: src,
      fixture: fixtureId, policy: ARB.mode, review: $('askReview').checked, failure: $('simFail').checked,
      nlp: $('useNLP').checked, model: model, model_snapshot: snapshot, consent: JSON.stringify(consent()) };
  }
  function bindingCurrent(b) {
    return b.session === session && b.version === session.version && b.revision === editorRevision &&
      b.text === $('freeText').value && b.source === src && b.fixture === fixtureId && b.policy === ARB.mode &&
      b.review === $('askReview').checked && b.failure === $('simFail').checked &&
      b.nlp === $('useNLP').checked && b.model === $('useModel').checked && b.consent === JSON.stringify(consent()) &&
      (!b.model || b.model_snapshot.profile_key === modelSnapshot(policyId()).profile_key);
  }
  $('freeText').addEventListener('input', function () { invalidateAnalysis(); $('count').textContent = E.cpLen(this.value); });
  ['askReview', 'simFail', 'useNLP', 'useModel', 'consentRep', 'consentWeb'].forEach(function (id) {
    if ($(id)) $(id).addEventListener('change', invalidateAnalysis);
  });
  $('pasteBtn').addEventListener('click', function () {
    if (!navigator.clipboard || !navigator.clipboard.readText) { toast('이 환경에서는 길게 눌러 붙여넣어 주세요.'); $('freeText').focus(); return; }
    navigator.clipboard.readText().then(function (t) { invalidateAnalysis(); $('freeText').value = t.slice(0, 4000); $('count').textContent = E.cpLen($('freeText').value); $('freeText').focus(); })
      .catch(function () { toast('클립보드 접근이 막혀 있어요. 길게 눌러 붙여넣어 주세요.'); $('freeText').focus(); });
  });
  $('clearBtn').addEventListener('click', function () { invalidateAnalysis(); $('freeText').value = ''; $('count').textContent = '0'; $('freeText').focus(); });

  // ---------- analyze: run ----------
  $('runBtn').addEventListener('click', run);
  $('freeText').addEventListener('keydown', function (e) { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') run(); });
  function run() {
    var btn = $('runBtn'); if (btn.getAttribute('aria-busy') === 'true') return;
    var review = $('askReview').checked, fail = $('simFail').checked;
    if (src === 'fixture') {
      var f = E.fixtures.find(function (x) { return x.id === fixtureId; });
      commit(f.transcript, ['F', fixtureId, review, fail], function () { return E.evaluateTurn({ fixture_id: fixtureId, user_asks_review: review, simulate_failure: fail }); }, 'fixture');
      return;
    }
    var text = $('freeText').value;
    if (!text.trim()) { toast('문장을 입력해 주세요.'); $('freeText').focus(); return; }
    if (E.cpLen(text) > 2000) { toast('2000자 이하로 입력해 주세요.'); return; }
    var binding = analysisBinding(text);
    // A deliberate Zoro selection never silently becomes NLP/local judgement.
    if ($('useModel').checked) {
      var snapshot = binding.model_snapshot;
      if (fail || !modelReady || snapshot.profile_error) {
        var code = fail ? 'SIMULATED_MODEL_FAILURE' : snapshot.profile_error ? 'PROFILE_CONTRACT_UNAVAILABLE' : 'MODEL_NOT_CONFIGURED';
        commit(text, ['M_UNAVAILABLE', text, review, fail], function () { return modelFailure(code, snapshot); }, 'zoro', binding);
        return;
      }
      btn.setAttribute('aria-busy', 'true'); $('runLabel').textContent = '조로 판단 중…';
      callModel(text, snapshot).then(function (r) {
        commit(text, ['M', text, review, fail, snapshot.profile_key], function () { return r; }, 'zoro', binding);
      }).finally(function () { btn.removeAttribute('aria-busy'); $('runLabel').textContent = '분석하기'; });
      return;
    }
    if ($('useNLP').checked && !fail) {
      btn.setAttribute('aria-busy', 'true'); $('runLabel').textContent = NLP.state === 'ready' ? '분석 중…' : '모델 준비 중…';
      loadNLP().then(function (m) {
        return new Promise(function (ok) { setTimeout(function () { ok(m); }, 16); });   // let the busy state paint
      }).then(function (m) {
        if (!bindingCurrent(binding)) return;
        if (!m) { commit(text, ['T', text, review, fail], function () { return E.evaluateTurn({ text: text, user_asks_review: review, simulate_failure: false }); }, 'local', binding); return; }
        var res; try { res = m.analyze(text); } catch (e) { res = null; NLP.error = 'INFERENCE_FAILED'; }
        if (!res) { commit(text, ['T', text, review, fail], function () { return E.evaluateTurn({ text: text, user_asks_review: review, simulate_failure: false }); }, 'local', binding); return; }
        var adv = res.advisory; adv.nlp = res; adv.mode = 'ON_DEVICE_NLP / ADVISORY_ONLY';
        commit(text, ['N', text, review], function () { return adv; }, 'nlp', binding);
      }).finally(function () { btn.removeAttribute('aria-busy'); $('runLabel').textContent = '분석하기'; });
      return;
    }
    commit(text, ['T', text, review, fail], function () { return E.evaluateTurn({ text: text, user_asks_review: review, simulate_failure: fail }); }, 'local');
  }
  function callModel(text, requestSnapshot) {
    var snapshot = requestSnapshot || modelSnapshot(policyId()), id = snapshot.policy_id;
    if (!C || snapshot.profile_error) return Promise.resolve(modelFailure('PROFILE_CONTRACT_UNAVAILABLE', snapshot));
    return fetch('/api/model', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, policy_id: id, profile_id: snapshot.profile_id }) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) return modelFailure(j && (j.code || j.error) || 'MODEL_UNAVAILABLE', snapshot);
        try {
          if (C.validateBinding(j.profile_binding, snapshot.profile_id, id) === false) throw new Error('PROFILE_BINDING_MISMATCH');
          if (bindingKey(j.profile_binding) !== snapshot.profile_key) throw new Error('PROFILE_BINDING_MISMATCH');
          var a = C.evaluateCurrent(text, j.raw, id, { profile_id: snapshot.profile_id,
            binding: j.profile_binding, source: 'MODEL_RESPONSE_UNATTESTED' });
          a.latency_ms = j.latency_ms; a.model_id_echo = j.model_id_echo; return a;
        } catch (e) { return modelFailure('PROFILE_OR_RESPONSE_CONTRACT_INVALID', snapshot); }
      })
      .catch(function () { return modelFailure('LOCAL_APP_UNREACHABLE', snapshot); });
  }
  function withLinks(text, compute) {
    return function () {
      var r = compute();
      if (C && C.applyLocalLayers) {
        var out;
        try { out = C.applyLocalLayers(text, r, { user_review: $('askReview').checked, consent: consent() }); }
        catch (e) {
          // A broken local contract is an explicit hold, never an alternate classifier.
          out = E.modelUnavailable('ContractError:V51_LOCAL_LAYER_CONTRACT_INVALID');
          out.policy_id = r.policy_id || policyId(); out.mode = 'MODEL_UNAVAILABLE_OR_INVALID';
        }
        out.execution_profile = { mode: out.mode || r.mode || 'LOCAL', policy_id: out.policy_id || r.policy_id || policyId(),
          profile_id: r.question_profile_id || null, profile_binding: r.question_binding || null, analysis_scope: ANALYSIS_SCOPE, indicator: r.nlp ? 'ON_DEVICE_NLP_ONLY' : 'NOT_APPLIED', linkguard: 'OFFLINE_ONLY', external_lookup: 'NOT_RUN' };
        return out;
      }
      if (r.mode === 'MODEL_UNAVAILABLE_OR_INVALID') return r;
      if (!LG || typeof text !== 'string') return r;
      var lg; try { lg = LG.assessMessage(LG.intake(text, { consent: consent() })); } catch (e) { return r; }
      var f = LG.fuse({ policy_action: r.action }, lg);
      var out = Object.assign({}, r, { linkguard: lg, linkguard_fusion: f });
      if (f.escalated) { out.base_action = r.action; out.base_reason = r.reason; out.action = f.policy_action; out.reason = f.escalation_reasons[0]; out.message = E.messages[f.policy_action]; }
      return out;
    };
  }
  function commit(text, digest, compute, viaModel, binding) {
    if (binding && !bindingCurrent(binding)) { toast('입력이나 설정이 변경돼 이전 응답을 적용하지 않았어요. 다시 분석해 주세요.'); return; }
    var r;
    try { r = session.record('T' + (++turnSeq), binding ? binding.version : session.version, digest.concat([JSON.stringify(consent()), ARB.mode]), withLinks(text, compute)); }
    catch (e) { toast('기록 오류: ' + e.message); return; }
    r.execution_profile = Object.assign({}, r.execution_profile || {}, { analysis_scope: ANALYSIS_SCOPE });
    render(text, r, viaModel); renderHistory();
  }

  function render(text, r, viaModel) {
    var card = $('resultCard'), st = STATE[r.action];
    card.hidden = false; card.dataset.state = r.action;
    $('stateIcon').innerHTML = svg(st.icon); $('stateLabel').textContent = st.ko; $('stateCode').textContent = r.action + ' · ' + r.reason;
    $('stateSub').textContent = SUB[r.action] || '';
    $('message').textContent = r.message;
    $('resultScopeNotice').textContent = SCOPE_NOTICE;
    var box = $('evidenceBox'); box.textContent = '';
    var q = el('blockquote', { class: 'transcript' }), cps = Array.from(text), ev = (r.evidence || []).concat([].concat.apply([], (r.indicators || []).map(function (x) { return x.grounded ? x.evidence.filter(function (e) { return e.origin === 'STRUCTURAL'; }) : []; }))).sort(function (a, b) { return a.start - b.start || b.end - a.end; }), pos = 0;
    ev.forEach(function (e) { if (e.start < pos) return; q.appendChild(document.createTextNode(cps.slice(pos, e.start).join(''))); q.appendChild(el('mark', { title: e.kind + (e.directness ? ' · ' + e.directness : '') }, cps.slice(e.start, e.end).join(''))); pos = e.end; });
    q.appendChild(document.createTextNode(cps.slice(pos).join(''))); box.appendChild(q);
    if (r.evidence_display) {
      var display = r.evidence_display;
      box.appendChild(el('p', { class: 'fine' }, '밑줄은 원문에서 찾은 행동 맥락입니다. 모델의 판단 근거나 의미가 검증됐다는 뜻은 아닙니다.'));
      var shown = display.displayed_clause_count || 0, total = display.candidate_clause_count || 0;
      box.appendChild(el('p', { class: 'fine' }, total ? '표시 가능한 구간 ' + shown + '/' + total + ' · 확인하지 못한 구간 ' + (display.unavailable_clause_count || 0) + '개' : '표시할 행동 맥락을 확인하지 못했습니다.'));
      var cause = { NO_SUPPORTED_TOPIC_ACTION_PAIR: '행동과 대상을 함께 확인하기 어려움', SPEECH_CONTEXT_UNRESOLVED: '요청·설명 맥락이 불분명함', REPORT_SCOPE_UNRESOLVED: '인용 범위가 불분명함',
        MIXED_QUOTED_AND_UNQUOTED_ACTION_CUES: '인용과 현재 요구가 섞여 있음', MIXED_NEGATED_AND_REQUEST_CUES: '금지 표현과 새 요구가 섞여 있음', WARNING_SCOPE_UNRESOLVED: '경고 범위가 불분명함',
        UNBALANCED_QUOTATION: '인용 구간의 끝을 확인하기 어려움', PRECEDING_CONTEXT_HEADING_SCOPE_UNRESOLVED: '앞 예시·경고의 범위가 끝났는지 불분명함',
        CLAUSE_TOO_LONG_FOR_LOCAL_DISPLAY: '구간이 길어 근거를 좁히기 어려움', INVALID_OR_CROSS_CLAUSE_UPSTREAM_SPAN: '기존 근거 위치를 확인하기 어려움' };
      var notes = (display.reason_codes || []).map(function (key) { return cause[key]; }).filter(Boolean);
      if (notes.length) box.appendChild(el('p', { class: 'fine' }, '일부 근거 구간 확인 불가: ' + notes.join(' · ')));
    }
    box.appendChild(previewCard(text, r));
    var facts = $('facts'); facts.textContent = '';
    function structuralFact(list) {
      if (!list || !list.length) return;
      var seen = {}, items = list.filter(function (e) { var k = e.kind + e.quote; if (seen[k]) return false; seen[k] = 1; return true; });
      facts.appendChild(el('dt', null, '원문에서 찾은 단서')); var d = el('dd'); var ul = el('ul', { class: 'signals' });
      items.forEach(function (e) { var li = el('li'); li.appendChild(el('b', null, STRUCT_KO[e.kind] || e.kind)); li.appendChild(el('span', null, ' “' + e.quote + '”')); ul.appendChild(li); });
      d.appendChild(ul); d.appendChild(el('small', { class: 'fine' }, '위치를 찾은 사실일 뿐, 위험 판정이 아니에요.')); facts.appendChild(d);
    }
    function fact(k, v, badges) { facts.appendChild(el('dt', null, k)); var d = el('dd', null, v); (badges || []).forEach(function (b) { d.appendChild(el('span', { class: 'badge' + (b[1] ? ' warn' : '') }, b[0])); }); facts.appendChild(d); }
    fact('이유', reasonText(r.reason));
    var n = r.nlp;
    if (viaModel === 'nlp' && n) {
      fact('실행 방식', '', [['AI 분석 · 온디바이스 NLP 실행됨', false], [n.model_id, false], ['외부 전송 없음', false]]);
      fact('발신자 신원', '확인되지 않음 — 문자 속 이름·기관·번호는 주장일 뿐입니다.');
      // section 1: sentence type
      facts.appendChild(el('dt', { class: 'sec' }, '문장 유형')); var d1 = el('dd', { class: 'sec' });
      d1.appendChild(el('b', null, (n.speech_act === 'UNKNOWN' ? '판단 어려움' : (SPEECH_KO[n.speech_act] || n.speech_act))));
      var bars = el('div', { class: 'nlp-bars' });
      Object.keys(n.speech_probs).forEach(function (k) { bars.appendChild(el('span', null, SPEECH_KO[k] || k)); var bb = el('i'); bb.style.width = Math.round(n.speech_probs[k] * 100) + '%'; var w = el('span'); w.appendChild(bb); bars.appendChild(w); bars.appendChild(el('span', null, n.speech_probs[k].toFixed(2))); });
      d1.appendChild(bars); d1.appendChild(el('small', { class: 'fine' }, '막대는 모델 점수입니다. 사기일 확률이 아닙니다.')); facts.appendChild(d1);
      if (n.intent_probs) {
        var it = Object.keys(n.intent_probs).reduce(function (a, b) { return n.intent_probs[a] >= n.intent_probs[b] ? a : b; });
        var ra = Object.keys(n.requested_action_probs).reduce(function (a, b) { return n.requested_action_probs[a] >= n.requested_action_probs[b] ? a : b; });
        fact('의도', (INTENT_KO[it] || it) + ' · 점수 ' + n.intent_probs[it].toFixed(2));
        fact('요구하는 행동', (REQ_KO[ra] || ra) + (ra === 'NO_EXPLICIT_ACTION' ? ' (명시적 요구가 없다는 뜻이지, 안전하다는 뜻이 아니에요)' : ''));
      }
      // section 2: risk signals with original-text evidence
      facts.appendChild(el('dt', { class: 'sec' }, '위험 신호')); var d2 = el('dd', { class: 'sec' });
      if (n.indicators && n.indicators.length) {
        var ul = el('ul', { class: 'signals' });
        n.indicators.forEach(function (x) {
          var li = el('li'); li.appendChild(el('b', null, IND_KO[x.label] || x.label));
          li.appendChild(el('span', { class: 'badge' + (x.grounded ? ' warn' : '') }, x.grounded ? '원문 근거 있음' : (x.grounded_by === 'MODEL_ONLY' ? '모델 추정 (원문 구조 근거 없음)' : '모델 추정')));
          var qs = x.evidence.map(function (e) { return '“' + e.quote + '”'; }).filter(function (q, i, arr) { return arr.indexOf(q) === i; });
          if (qs.length) li.appendChild(el('div', { class: 'fine' }, '근거: ' + qs.join(', ')));
          ul.appendChild(li);
        });
        d2.appendChild(ul);
      } else d2.appendChild(el('span', null, '모델이 기준 이상의 위험 신호를 찾지 못했어요. 신호가 없다는 것이 안전하다는 뜻은 아니에요.'));
      facts.appendChild(d2);
      structuralFact(n.structural_evidence);
      fact('다음 행동', n.safe_next_step);
      if (n.uncertainty_reason) fact('불확실성', n.uncertainty_reason);
      if (n.uncertainty && n.uncertainty.length) fact('추가 확인 필요', n.uncertainty.map(function (u) { return UNC_KO[u] || u; }).join(' · '));
      fact('지연', n.latency_ms + ' ms · 토큰 ' + n.tokens + (NLP.loadMs != null ? ' · 모델 로드 ' + NLP.loadMs + ' ms' : ''));
    } else if (viaModel === 'zoro') {
      fact('실행 방식', '', [[r.mode, false], ['모델 응답 진품 미인증', true]]);
    } else if (viaModel === 'local') {
      fact('실행 방식', '', [['로컬 기본 점검', false], ['의미 분석 불가 · 추가 확인 권고', true]]);
      fact('발신자 신원', '확인되지 않음');
      structuralFact(E.structuralEvidence(text));
      if (NLP.state === 'unavailable') fact('AI 분석', '온디바이스 모델을 불러오지 못했어요 (' + NLP.error + ').');
    } else fact('실행 방식', '', [[r.mode, false], ['합성 시나리오 · 로컬 엔진', false]]);
    if (r.grounding && r.grounding !== 'NONE' && r.grounding !== 'NO_ACTION_ANCHOR') fact('근거', r.grounding === 'LEXICAL_ANCHOR_NOT_SEMANTIC_VERIFICATION' ? '문장 속 표현 위치 (의미 인증 아님)' :
      r.grounding === 'MODEL_ATTRIBUTION_SPAN_NOT_SEMANTIC_PROOF' ? '모델 판단에 가장 크게 기여한 단어 (설명 보조 · 의미 증명 아님)' : '문장에서 근거 위치를 찾지 못함');
    if (r.selected_action && viaModel !== 'nlp') {
      fact('모델의 행동 선택', r.selected_action + (Number.isFinite(r.action_probability) ? ' · 선택 확률 ' + r.action_probability.toFixed(3) : ''));
      fact('모델의 발화 유형 선택', (r.selected_speech || '응답 없음') + (Number.isFinite(r.speech_probability) ? ' · 선택 확률 ' + r.speech_probability.toFixed(3) : ''));
      fact('선택과 최종 안내', '모델 선택은 완료됐습니다. 최종 안내는 문맥·근거·정책을 함께 적용한 결과입니다. 선택 확률은 실제 사기 확률이나 API confidence와 다릅니다.');
    }
    if (r.action === 'ASK_HUMAN') fact('보류 후 다음 단계', '요청이 현재 직접 요구인지, 과거 인용·예방 경고인지 확인해 주세요. 불분명하면 독립적으로 알고 있던 공식 경로 또는 신뢰하는 사람에게 확인하세요. 보류는 처리 중 상태가 아닙니다.');
    if (r.guidance_distribution && viaModel !== 'nlp') {
      var gd = r.guidance_distribution;
      fact('안내별 모델 확률 (판단 중재)', '미감지 ' + gd.NO_STRONG_SIGNAL.toFixed(2) + ' · 주의 ' + gd.CAUTION.toFixed(2) + ' · 잠시 멈춤 ' + gd.PAUSE_AND_VERIFY.toFixed(2) + ' · 불명 ' + gd.UNKNOWN.toFixed(2) + ' (보정 안 됨, 사기 확률 아님)');
    }
    if (r.latency_ms != null && viaModel !== 'nlp') fact('지연', r.latency_ms + ' ms');
    if (r.model_id_echo) fact('모델 이름 반향', r.model_id_echo === 'ABSENT' ? '응답에 없음 (인증 아님)' : '일치 (인증 아님)');
    if (r.policy_id) fact('판단 방식', r.policy_id === 'legacy' ? '기준 정책 · 0.70 (보정 미확립)' : 'DRA 비교 · 실험 정책');
    if ($('executionTrace')) $('executionTrace').textContent = JSON.stringify({ profile: r.execution_profile || null,
      trace: r.execution_trace || null, evidence_display: r.evidence_display_trace || null, manifest_fingerprint: r.manifest_fingerprint || null }, null, 2);
    if (r.linkguard) renderLinks(facts, r.linkguard);
    var list = $('clauseList'); list.textContent = '';
    E.clauseProfile(text).forEach(function (c) {
      var li = el('li', null, cps.slice(c.start, c.end).join('').trim());
      [['위험 행동', c.flags.action_mentioned], ['경고', c.flags.warning_cue], ['인용', c.flags.report_cue], ['요청형', c.flags.request_cue], ['압박', c.flags.pressure_cue]]
        .forEach(function (x) { if (x[1]) li.appendChild(el('span', { class: 'badge cue' + (x[0] === '압박' || x[0] === '위험 행동' ? ' warn' : '') }, x[0])); });
      list.appendChild(li);
    });
    $('clauseBox').hidden = !list.children.length;
    // Reference-only: summarizes clause cues when no model judged the free text. Never changes r.action.
  function previewCard(text, r) {
    var frag = document.createDocumentFragment();
    if (r.reason !== 'MODEL_NOT_AVAILABLE') return frag;
    var cl = E.clauseProfile(text), items = [];
    var imp = cl.filter(function (c) { return c.clean_imperative; }).length;
    var warn = cl.filter(function (c) { return c.flags.action_mentioned && c.flags.warning_cue; }).length;
    var rep = cl.filter(function (c) { return c.flags.action_mentioned && c.flags.report_cue; }).length;
    var press = cl.filter(function (c) { return c.flags.pressure_cue; }).length;
    if (imp) items.push('경고·인용 없이 위험 행동을 시키는 문장 ' + imp + '개');
    if (press) items.push('서두름·비밀 유지 같은 압박 표현 ' + press + '곳');
    if (warn) items.push('하지 말라는 경고 문장 ' + warn + '개');
    if (rep) items.push('남의 말을 전하는 인용 문장 ' + rep + '개');
    if (!items.length) items.push('송금·인증번호·원격제어 같은 위험 행동 표현을 찾지 못했어요');
    var d = el('div', { class: 'preview' }); d.appendChild(el('b', null, '단어 단서 (참고용 · 판단 아님)'));
    var ul = el('ul'); items.forEach(function (t) { ul.appendChild(el('li', null, t)); }); d.appendChild(ul);
    frag.appendChild(d); return frag;
  }
  document.querySelectorAll('#nextRow .ghost').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
    $('nextRow').hidden = r.action === 'NO_STRONG_SIGNAL';
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  document.querySelectorAll('#nextRow .ghost').forEach(function (b) {
    b.addEventListener('click', function () {
      try { session.record('A' + (++turnSeq), session.version, ['ACK', b.dataset.intent], function () { return { action: 'INTENT_ONLY', reason: b.dataset.intent, mode: 'INTENT_ONLY_NOT_VERIFIED' }; }); }
      catch (e) { toast(e.message); return; }
      b.setAttribute('aria-pressed', 'true'); renderHistory(); toast('계획만 기록했어요. 실제 확인은 직접 해 주세요.');
    });
  });
  function renderHistory() {
    var l = $('historyList'); l.textContent = ''; $('historyCard').hidden = !session.history.length;
    session.history.slice().reverse().forEach(function (h) {
      var label = h.action === 'INTENT_ONLY' ? (h.reason === 'PLAN_INDEPENDENT_VERIFICATION' ? '확인 계획' : '도움 요청 계획') : (STATE[h.action] ? STATE[h.action].ko : h.action);
      var li = el('li'); li.appendChild(el('span', null, label)); li.appendChild(el('b', null, 'v' + h.version)); l.appendChild(li);
    });
  }


  // ---------- v4.7 LinkGuard rendering ----------
  var LSTATE = { KNOWN_MALICIOUS: ['차단 목록에 있음', true], SUSPICIOUS: ['의심 구조 확인', true], INCONCLUSIVE: ['결론 없음', false],
    NO_KNOWN_THREAT_FOUND: ['알려진 위협 없음 (안전 보증 아님)', false], NOT_SCANNED: ['형식만 확인 · 평판 조회 안 함', false], SCAN_FAILED: ['검사 실패', true] };
  var LFLAG = { HOMOGLYPH_BRAND: '유명 브랜드와 비슷한 글자를 섞은 주소', BRAND_NOT_OFFICIAL_DOMAIN: '브랜드 이름이 있지만 공식 도메인이 아님', NON_PUBLIC_IP: '내부망·사설 IP 주소',
    OBFUSCATED_IP: '숫자를 변형한 IP 주소', USERINFO_AT: '@ 앞에 다른 주소를 끼워 넣은 형태', DANGEROUS_SCHEME: '실행형 주소(javascript 등)', APK_DOWNLOAD: '앱 설치 파일(APK) 다운로드 링크',
    MIXED_SCRIPT: '여러 문자 체계를 섞은 주소', SHORTENER: '단축 주소 (실제 목적지 숨김)', MESSENGER_LINK: '메신저로 이동하는 링크', MESSENGER_OR_APP_DEEPLINK: '앱을 바로 여는 주소',
    IP_LITERAL: '도메인 대신 IP 주소', PUNYCODE: '국제화 도메인(xn--) 표기', NONSTANDARD_PORT: '흔하지 않은 포트', DEEP_SUBDOMAIN: '하위 도메인이 지나치게 많음',
    SENSITIVE_QUERY: '주소에 인증 토큰·개인정보 형태 값 (화면·외부 조회에서 가림)', DEFANGED: '무력화 표기(hxxp, [.])', NON_HTTP_SCHEME: '웹 주소가 아님 (열지 않음)', IDN: '한글 등 국제화 도메인',
    OPAQUE_PATH_TOKEN: '경로에 긴 토큰 (가림)', RESERVED_TLD: '테스트용 예약 도메인', APP_STORE_LINK: '앱 마켓 링크', INVALID_PORT: '잘못된 포트' };
  var LSTAGE = { intake: '형식 검사', local_reputation: '기기 내 차단 목록', safe_browsing: 'Google Safe Browsing', virustotal: 'VirusTotal', web_analysis: '격리 웹 분석' };
  var LSTATUS = { DONE: '수행', NOT_RUN: '미실행', BLOCKED: '차단(이 버전에 없음)', FAILED: '실패' };
  function stageList(stages) {
    var ol = el('ol', { class: 'timeline' });
    Object.keys(LSTAGE).forEach(function (k) { var v = stages[k] || 'NOT_RUN'; var li = el('li', { class: 'st-' + v.toLowerCase() }); li.appendChild(el('b', null, LSTAGE[k])); li.appendChild(el('span', null, LSTATUS[v] || v)); ol.appendChild(li); });
    return ol;
  }
  function linkBlock(u) {
    var d = el('div', { class: 'link-item' }), s = LSTATE[u.state] || [u.state, false];
    var h = el('div', { class: 'link-head' }); h.appendChild(el('code', null, u.display_url || '(주소 없음)')); h.appendChild(el('span', { class: 'badge' + (s[1] ? ' warn' : '') }, s[0])); d.appendChild(h);
    var fl = (u.reasons || []).concat(u.cautions || []);
    if (fl.length) { var ul = el('ul', { class: 'signals' }); fl.forEach(function (f) { ul.appendChild(el('li', null, LFLAG[f] || f)); }); d.appendChild(ul); }
    d.appendChild(stageList(u.stages));
    return d;
  }
  function renderLinks(facts, lg) {
    if (!lg.url_count) return;
    facts.appendChild(el('dt', { class: 'sec' }, '링크 검사 (LinkGuard)'));
    var dd = el('dd', { class: 'sec' });
    lg.urls.forEach(function (u) { dd.appendChild(linkBlock(u)); });
    dd.appendChild(el('small', { class: 'fine' }, '링크는 열지 않았어요. 검사하지 않은 단계는 "미실행"으로 표시합니다. 위협이 발견되지 않았다는 것이 안전하다는 뜻은 아니에요.'));
    facts.appendChild(dd);
  }
  if ($('urlBtn')) $('urlBtn').addEventListener('click', function () {
    var out = $('urlOut'); out.textContent = '';
    if (!LG) { out.appendChild(el('p', { class: 'fine' }, 'LinkGuard 모듈을 불러오지 못했어요.')); return; }
    var t = $('urlText').value; if (!t.trim()) { toast('링크나 문장을 입력해 주세요.'); return; }
    var ir; try { ir = LG.intake(t.slice(0, 4000), { consent: consent() }); } catch (e) { out.appendChild(el('p', null, '입력을 처리하지 못했어요.')); return; }
    var a = LG.assessMessage(ir);
    if (!a.url_count) { out.appendChild(el('p', null, '문장에서 링크를 찾지 못했어요.')); return; }
    var s = LSTATE[a.overall] || [a.overall, false];
    out.appendChild(el('p', { class: 'state-mini' + (s[1] ? ' warn' : '') }, '종합: ' + s[0]));
    a.urls.forEach(function (u) { out.appendChild(linkBlock(u)); });
  });
  var APK_FIND = { FILE_TOO_LARGE: '파일이 너무 커요 (150MB 초과)', NOT_AN_APK_CONTAINER: 'APK 형식이 아니에요', NOT_AN_APK_CONTAINER_EXTENSION_MISMATCH: '확장자는 .apk지만 실제 내용은 APK가 아니에요',
    EXTENSION_MISMATCH: '확장자와 내용 형식이 달라요', PATH_TRAVERSAL: '압축 안에 폴더 밖으로 빠져나가는 경로가 있어요', NO_ANDROID_MANIFEST: '앱 정보 파일(매니페스트)이 없어요',
    MANIFEST_PARSE_FAILED: '앱 정보 파일을 읽지 못했어요', UNSIGNED: '서명이 없어요', DEBUGGABLE: '디버그용 빌드예요', OBFUSCATION_LIKELY: '코드 이름이 난독화돼 있어요 (그 자체로 악성 아님)',
    DEX_PARSE_FAILED: '코드 파일 일부를 읽지 못했어요', DUPLICATE_ENTRY: '같은 이름의 파일이 중복돼요', ENCRYPTED_ENTRY_FLAG: '암호화 표시가 된 항목이 있어요' };
  var APK_STATE = { SUSPICIOUS: ['위험한 권한 조합·구조 확인', true], NO_KNOWN_THREAT_FOUND: ['정적 검사에서 알려진 위험 조합 없음 (안전 보증 아님)', false],
    INCONCLUSIVE: ['결론 없음', false], SCAN_FAILED: ['검사 실패', true], NOT_SCANNED: ['검사하지 않음', false] };
  var GROUP_KO = { SMS: '문자', CALL_LOG: '통화 기록', PHONE: '전화', CONTACTS: '연락처', MICROPHONE: '마이크', CAMERA: '카메라', LOCATION: '위치', STORAGE: '저장공간' };
  var SPECIAL_KO = { OVERLAY: '다른 앱 위에 그리기', ACCESSIBILITY: '접근성 서비스', INSTALL_PACKAGES: '다른 앱 설치', DEVICE_ADMIN: '기기 관리자', NOTIFICATION_LISTENER: '알림 읽기',
    PACKAGE_VISIBILITY: '설치 앱 목록 조회', USAGE_STATS: '사용 기록', VPN: 'VPN', WRITE_SETTINGS: '시스템 설정 변경', FOREGROUND_SERVICE: '상시 실행', BOOT: '부팅 시 시작',
    FULL_SCREEN_INTENT: '전체 화면 알림', CALL_SCREENING: '통화 선별', INCALL: '통화 화면' };
  if ($('apkFile')) $('apkFile').addEventListener('change', function () {
    var f = this.files && this.files[0], out = $('apkOut'); out.textContent = '';
    if (!f) return;
    if (!AS) { out.appendChild(el('p', null, '앱 검사 모듈을 불러오지 못했어요.')); return; }
    if (f.size > AS.MAX_APK_BYTES) { out.appendChild(el('p', { class: 'state-mini warn' }, '파일이 너무 커서 검사하지 않았어요 (150MB 초과).')); return; }
    out.appendChild(el('p', { class: 'fine' }, '기기 안에서 읽는 중… (업로드 없음)'));
    f.arrayBuffer().then(function (buf) { return AS.inspect(new Uint8Array(buf), f.name); }).then(function (r) {
      out.textContent = '';
      var s = APK_STATE[r.state] || [r.state, false];
      out.appendChild(el('p', { class: 'state-mini' + (s[1] ? ' warn' : '') }, s[0]));
      var dl = el('dl', { class: 'facts' });
      function row(k, v) { dl.appendChild(el('dt', null, k)); dl.appendChild(el('dd', null, v)); }
      row('SHA-256', r.sha256 || '-');
      if (r.manifest) { row('패키지', (r.manifest.package || '?') + ' · 버전 ' + (r.manifest.version_name || '?')); }
      if (r.permission_groups) row('민감 권한', r.permission_groups.length ? r.permission_groups.map(function (g) { return GROUP_KO[g] || g; }).join(', ') : '없음');
      if (r.special_access) row('특수 접근', r.special_access.length ? r.special_access.map(function (g) { return SPECIAL_KO[g] || g; }).join(', ') : '없음');
      if (r.risk_combinations && r.risk_combinations.length) row('위험 조합', r.risk_combinations.join(', '));
      if (r.exported) row('외부 노출 구성요소', r.exported.length + '개');
      if (r.signing) row('서명 인증서', r.signing.length ? r.signing.map(function (x) { return x.scheme + ' · ' + (x.subject_cn || '') + ' · ' + (x.cert_sha256 || '').slice(0, 16) + '…'; }).join(' / ') : (r.signing_v1_files && r.signing_v1_files.length ? 'v1 서명 파일 있음' : '없음'));
      if (r.network_indicators) row('코드 속 주소', r.network_indicators.url_total + '개 · IP ' + r.network_indicators.ipv4.length + '개');
      if (r.findings.length) row('발견 사항', r.findings.map(function (x) { return APK_FIND[x] || x; }).join(' · '));
      row('검사하지 않은 것', '실행 중 동작 · 개발사 서버 코드 · 서명의 암호학적 유효성 · 네이티브 코드 내용 · 내려받는 추가 코드');
      out.appendChild(dl);
      out.appendChild(el('p', { class: 'fine' }, '권한이 있다는 것만으로 악성이 아니고, 위험 조합이 없다고 안전한 것도 아닙니다. 출처가 불분명한 APK는 설치하지 마세요.'));
    }).catch(function (e) { out.textContent = ''; out.appendChild(el('p', { class: 'state-mini warn' }, '검사 실패: ' + ((e && e.message) || '원인 미상'))); });
  });
  // v4.8: purely local due-diligence evidence inspection. Does not replace existing policy or claim verified facts.
  var DI = window.DmsgDomainIntel || null;
  function renderDomainReview(text) {
    var dst = $('domainResult'); if (!dst) return;
    dst.textContent = '';
    if (!DI) { dst.appendChild(el('p', {class:'state-mini warn'}, '로컬 검토 모듈이 준비되지 않았습니다.')); return; }
    var result;
    try { result = DI.assess(text); }
    catch (err) { dst.appendChild(el('p', {class:'state-mini warn'}, '입력 형식을 처리하지 못했습니다.')); return; }
    var TITLE = { PRIORITY_VERIFICATION:'우선 검증할 주장 발견', ADDITIONAL_DUE_DILIGENCE:'추가 실사·확인 항목 발견',
      REPORTED_RISK_TEXT:'위험 표현이 인용·경고 문맥에서 등장', NO_PATTERN_DETECTED:'정의된 패턴 미발견 (안전 판정 아님)' };
    dst.appendChild(el('p', { class:'state-mini'+(result.status==='PRIORITY_VERIFICATION'?' warn':'' ) }, TITLE[result.status] || '검토 완료'));
    var meta = el('p',{class:'fine'},'실행 모드: 오프라인 텍스트 규칙 · AI 모델 미사용 · 네트워크 요청 0 · 실체·등록·온체인 검증 미실행');dst.appendChild(meta);
    if (result.truncated) dst.appendChild(el('p', {class:'fine'}, '5000자를 초과한 부분은 검사하지 않았습니다.'));
    if (result.findings.length) {
      var h=el('h3',null,'관찰된 표현 ('+result.findings.length+'개)');dst.appendChild(h);
      var list=el('ul',{class:'domain-findings'});
      result.findings.forEach(function(f){var li=el('li');li.appendChild(el('strong',null,f.id));
        li.appendChild(el('span',{class:'domain-quote'},' “'+f.evidence+'”'));
        li.appendChild(el('div',{class:'fine'}, (f.context==='QUOTED_OR_WARNED'?'인용·경고 가능 · ':'실제 주장 여부 미확인 · ')+f.explanation));list.appendChild(li);});
      dst.appendChild(list);
    }
    dst.appendChild(el('h3',null,'검증해야 할 자료'));
    Object.keys(result.checklists).forEach(function(k){var c=result.checklists[k];
      dst.appendChild(el('p',{class:'domain-heading'},c.label));
      var ul=el('ul',{class:'domain-questions'});c.questions.forEach(function(q){ul.appendChild(el('li',null,q));});dst.appendChild(ul);});
    dst.appendChild(el('p',{class:'fine'},'결론: 실사 전 단계 · 검증된 회사 실체/계약/정산/체인 상태 없음 · 법적 판단 아님 · 사기 확률 미산출'));
  }
  if ($('domainAnalyzeBtn')) $('domainAnalyzeBtn').addEventListener('click', function(){
    var t=$('domainPitch').value; if(!t.trim()) {toast('사업·투자 문구를 입력해 주세요.');return;}renderDomainReview(t);
  });
  if ($('domainFromMessage')) $('domainFromMessage').addEventListener('click', function(){
    $('domainPitch').value=$('freeText').value; if ($('domainPitch').value.trim()) renderDomainReview($('domainPitch').value);
    else toast('분석 화면에서 메시지를 먼저 입력해 주세요.');
  });

  // arbiter switch
  document.querySelectorAll('#arbSeg .seg-btn').forEach(function (b, i) {
    b.addEventListener('click', function () {
      invalidateAnalysis();
      ARB.mode = b.dataset.arb; b.parentNode.dataset.pos = i;
      document.querySelectorAll('#arbSeg .seg-btn').forEach(function (x) { x.classList.toggle('on', x === b); x.setAttribute('aria-checked', x === b); });
      if (NLP.model) NLP.model.arbiter = ARB.mode;
      toast(ARB.mode === 'dra' ? 'DRA 비교 정책을 선택했어요. 성능 검증이 끝난 기본 정책은 아니에요.' : '아레나와 같은 기준 정책으로 판단해요.');
    });
  });
  // v4.7 share sheet: the Android shell opens index.html#share=<base64url(UTF-8)>; read once, then drop it from the URL
  (function () {
    var m = /^#share=([A-Za-z0-9_\-=]+)$/.exec(location.hash || '');
    if (!m) return;
    try { history.replaceState(history.state, '', location.pathname + location.search); } catch (e) { /* file:// */ }
    var t = '';
    try {
      var b = atob(m[1].replace(/-/g, '+').replace(/_/g, '/')), u = new Uint8Array(b.length);
      for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
      t = new TextDecoder('utf-8').decode(u);
    } catch (e) { toast('공유된 내용을 읽지 못했어요.'); return; }
    t = Array.from(t).slice(0, 2000).join('');
    $('freeText').value = t; $('count').textContent = E.cpLen(t);
    toast('공유된 문자를 불러왔어요. 이 기기 안에서만 분석합니다.');
    setTimeout(run, 50);
  })();

  // ---------- PAYLOCK ----------
  E.vendors.forEach(function (v) { $('pVendor').appendChild(el('option', { value: v.vendor_id }, v.name + ' (' + v.vendor_id + ')')); });
  $('pVendor').appendChild(el('option', { value: 'V-UNKNOWN' }, '미등록 거래처'));
  E.invoices.forEach(function (i) { $('pInvoice').appendChild(el('option', { value: i.invoice_id }, i.invoice_id + ' · ' + i.amount_krw.toLocaleString('ko-KR') + '원')); });
  E.data.paylock.banks.forEach(function (b) { $('pBank').appendChild(el('option', { value: b }, b)); });
  var payReq = null;
  E.examples.forEach(function (x, i) {
    var c = el('button', { class: 'chip', role: 'option', 'aria-selected': i === 0 ? 'true' : 'false' }, x.title);
    c.addEventListener('click', function () { document.querySelectorAll('#payChips .chip').forEach(function (y) { y.setAttribute('aria-selected', y === c); }); fillPay(x); });
    $('payChips').appendChild(c);
  });
  function fillPay(x) {
    payReq = x; $('pVendor').value = x.vendor_id; $('pInvoice').value = x.invoice_id; $('pEmail').value = x.sender_email; $('pBank').value = x.requested_bank;
    $('pAccount').value = x.requested_account; $('pAmount').value = x.amount_krw.toLocaleString('ko-KR'); $('pMessage').value = x.message; $('payResult').hidden = true;
  }
  fillPay(E.examples[0]);
  $('payBtn').addEventListener('click', function () {
    var amt = Number(String($('pAmount').value).replace(/[,\s원]/g, ''));
    var p = { request_id: (payReq && payReq.request_id) || 'REQ-UI', requester_id: (payReq && payReq.requester_id) || 'clerkUI', invoice_id: $('pInvoice').value,
      vendor_id: $('pVendor').value, sender_email: $('pEmail').value.trim(), requested_bank: $('pBank').value, requested_account: $('pAccount').value.trim(),
      amount_krw: amt, message: $('pMessage').value };
    var card = $('payResult'), ul = $('payReasons'); ul.textContent = ''; card.hidden = false;
    var r;
    try { r = E.assessRequest(p); }
    catch (e) {
      card.dataset.state = 'ASK_HUMAN'; $('payIcon').innerHTML = svg(STATE.ASK_HUMAN.icon); $('payLabel').textContent = '입력을 확인해 주세요'; $('payCode').textContent = e.code || 'INVALID';
      ul.appendChild(el('li', null, ({ INVALID_SENDER_CLAIM: '이메일 형식이 올바르지 않아요(소문자 주소).', INVALID_ACCOUNT: '계좌번호는 숫자·하이픈·공백만, 6–20자리예요.', INVALID_AMOUNT: '금액은 1원 이상 정수예요.' })[e.code] || '필수 항목 형식을 확인해 주세요.'));
      return;
    }
    var hold = r.disposition === 'HOLD_FOR_INDEPENDENT_VERIFICATION', s = hold ? 'HOLD' : 'READY';
    card.dataset.state = s; $('payIcon').innerHTML = svg(STATE[s].icon); $('payLabel').textContent = STATE[s].ko; $('payCode').textContent = r.disposition;
    r.reasons.forEach(function (code) { var li = el('li', null, reasonText(code)); li.appendChild(el('code', null, code)); ul.appendChild(li); });
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });

  // ---------- model tab ----------
  KO = { transfer: '송금', otp: '인증번호 제공', remote_install: '원격제어 설치', personal_data: '개인정보 제공', link: '링크 열기', secrecy: '비밀 유지',
    none: '요청 없음', unclear: '불분명', direct_request: '직접 요청', reported_or_quoted: '인용·전달', negated_or_warning: '경고·부정' };
  E.data.model.spec.q_action.options.forEach(function (o) { $('sAction').appendChild(el('option', { value: o }, (KO[o] || o) + ' · ' + o)); });
  E.data.model.spec.q_speech.options.forEach(function (o) { $('sSpeech').appendChild(el('option', { value: o }, (KO[o] || o) + ' · ' + o)); });
  $('sSpeech').value = 'direct_request';
  ['sP', 'sAux'].forEach(function (id) { $(id).addEventListener('input', function () { $(id + 'Out').textContent = Number(this.value).toFixed(2); }); });
  function synthetic(action, speech, p, aux) {
    function ch(opts, win) { var r = {}; opts.forEach(function (o) { r[o] = (1 - p) / (opts.length - 1); }); r[win] = p; return r; }
    var M = E.data.model;
    return { answers: { q_action: { type: 'choice', probabilities: ch(M.spec.q_action.options, action) }, q_speech: { type: 'choice', probabilities: ch(M.spec.q_speech.options, speech) },
      q_scam: { type: 'noul', noul: aux }, q_claim: { type: 'noul', noul: 0.1 }, q_pressure: { type: 'noul', noul: aux }, q_risk: { type: 'score', probabilities: ch(M.risk_levels, M.risk_levels[1]) } } };
  }
  $('simBtn').addEventListener('click', function () {
    var t = $('sText').value, out = $('simOut'); out.textContent = '';
    var r;
    try { r = E.advisory(t, synthetic($('sAction').value, $('sSpeech').value, Number($('sP').value), Number($('sAux').value)), { source: 'SIMULATED_RESPONSE' }); }
    catch (e) { r = E.modelUnavailable('ContractError:' + (e.code || 'INVALID')); }
    var m = el('div', { class: 'mini result', 'data-state': r.action }); m.style.animation = 'none';
    m.appendChild(el('b', null, STATE[r.action].ko)); m.appendChild(el('code', null, r.reason)); out.appendChild(m);
    out.appendChild(el('p', { class: 'fine' }, reasonText(r.reason)));
    out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
  var PROBES = [['합성 사례: 지금 바로 이 계좌로 300만원 송금하세요.', ['PAUSE_AND_VERIFY']], ['합성 사례: 누가 요구해도 송금하지 마세요.', ['NO_STRONG_SIGNAL', 'ASK_HUMAN']],
    ['합성 사례: 상대가 송금하라고 했다고 신고했습니다.', ['CAUTION', 'ASK_HUMAN']], ['합성 사례: [경고] 계좌가 동결됩니다. 지금 바로 안전계좌로 이체하세요. 가족에게 말하지 마세요.', ['PAUSE_AND_VERIFY', 'ASK_HUMAN']]];
  $('probeBtn').addEventListener('click', function () {
    var l = $('probeList'); l.textContent = '';
    PROBES.reduce(function (p, pr) {
      return p.then(function () { return callModel(pr[0]); }).then(function (r) {
        var ok = pr[1].indexOf(r.action) >= 0;
        l.appendChild(el('li', null, (ok ? '✓ ' : '✗ ') + r.action + ' · ' + r.reason + (r.latency_ms != null ? ' · ' + r.latency_ms + 'ms' : '')));
      });
    }, Promise.resolve()).then(function () { toast('계약 점검 완료 (진품·정확도 증거 아님)'); });
  });
  $('cfgSave').addEventListener('click', function () {
    invalidateAnalysis();
    var body = { endpoint: $('cEndpoint').value.trim(), model_id: $('cModel').value.trim(), timeout_s: Number($('cTimeout').value || 20) };
    fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); }).then(function (j) { toast(j.ok ? '저장했어요.' : '저장 실패: ' + j.code); refreshHost(); })
      .catch(function () { toast('데스크톱 앱에서만 설정할 수 있어요.'); });
  });
  function setHost(kind, text, dot) {
    $('hostPill').textContent = kind; $('hostText').textContent = text; $('hostDot').className = 'dot ' + dot;
  }
  function refreshHost() {
    if (!/^https?:$/.test(location.protocol)) return offline();
    fetch('/api/health', { cache: 'no-store' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (j) {
      if (j.app !== 'dmsg-desktop') throw 0;
      host = 'desktop'; modelReady = !!j.model.configured;
      setHost('데스크톱', modelReady ? '데스크톱 앱 · 모델 설정됨 (' + j.model.endpoint_host + ', 진품 미인증)' : '데스크톱 앱 · 모델 미설정', modelReady ? 'ok' : 'warn');
      $('cEndpoint').value = j.model.endpoint || ''; $('cModel').value = j.model.model_id || ''; $('cTimeout').value = j.model.timeout_s || 20;
      $('cfgBox').querySelectorAll('input,button').forEach(function (x) { x.disabled = false; }); $('probeBtn').disabled = !modelReady;
      $('useModel').disabled = false; $('useModelHint').textContent = modelReady ? '(로컬 조로 우선 사용 · 연결 실패 시 판단 보류)' : '(연결되지 않음 · 선택하면 판단 보류)';
    }).catch(offline);
  }
  function offline() {
    host = 'browser'; modelReady = false; setHost(location.href.indexOf('file:///android_asset/') === 0 ? 'Android 앱' : (navigator.standalone || matchMedia('(display-mode: standalone)').matches) ? '설치된 앱' : '브라우저',
      '단독 실행 중 · 온디바이스 분석을 선택할 수 있어요. 조로 선택 시에는 연결되지 않았음을 표시하고 판단을 보류해요.', 'warn');
    $('cfgBox').querySelectorAll('input,button').forEach(function (x) { x.disabled = true; }); $('useModel').disabled = false; $('useModelHint').textContent = '(연결되지 않음 · 선택하면 판단 보류)';
  }
  refreshHost();

  // ---------- info ----------
  var VERIFY = [
    ['판단 엔진: Python 정본과 JS 이식본 일치 (합성 벡터)', B.conformance ? B.conformance.pass + '/' + B.conformance.total : '빌드 정보 없음', !!(B.conformance && B.conformance.pass === B.conformance.total)],
    ['합성 시나리오·지급 예시 정책 동작', '확인', true],
    ['온디바이스 NLP: JS ↔ Python 일치 (토큰·특징·라벨·판단)', B.nlp_parity ? B.nlp_parity.action_match + '/' + B.nlp_parity.n : '빌드 정보 없음', !!(B.nlp_parity && B.nlp_parity.status === 'PASS')],
    ['온디바이스 NLP: 고정 49문장 회귀 (작성자 데이터)', B.nlp_golden && B.nlp_golden.status === 'PASS' ? B.nlp_golden.n + '/' + B.nlp_golden.n : '검증 기록 없음', !!(B.nlp_golden && B.nlp_golden.status === 'PASS')],
    ['이 빌드의 실제 Zoro-1 모델 호출', B.typed_validation === 'SEE_SEPARATE_RUNTIME_EVIDENCE' ? '별도 실제 실행 보고서 참조' : (B.typed_validation || '검증 기록 없음'), B.typed_validation === 'LOCAL_TYPED_VERIFIED'],
    ['한국어 사기 문장 정확도 (독립·실사용 평가)', '미측정', false],
    ['NPU 실행', '미실행', false],
    ['Windows·macOS 실제 기기 실행', '미검증', false],
    ['Android·iOS 실제 기기 설치', '미검증', false]
  ];
  VERIFY.forEach(function (v) { var tr = el('tr'); tr.appendChild(el('td', null, v[0])); tr.appendChild(el('td', { class: v[2] ? 'ok' : 'no' }, v[1])); $('verifyTable').appendChild(tr); });
  $('buildInfo').textContent = '제품 ' + (B.version || '5.1 개발 후보') + ' · 기준 엔진 ' + E.version +
    (B.release_stage ? ' · ' + B.release_stage : '') + (B.built ? ' · 빌드 ' + B.built : '') + (B.source ? ' · 정본 ' + B.source : '');

  // HTTPS only: the desktop host uses a new loopback port per launch, so caching there would only pile up stale origins.
  // ---------- splash: hide as soon as the shell is ready (≥0.5 s only so the mark is legible; never waits on the model) ----------
  (function () {
    var sp = $('splash'); if (!sp) return;
    var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var now = (window.performance && performance.now) ? performance.now() : 500, wait = reduce ? 0 : Math.max(0, Math.min(500, 500 - now));
    setTimeout(function () { sp.classList.add('done'); setTimeout(function () { if (sp.parentNode) sp.parentNode.removeChild(sp); }, 320); }, wait);
  })();
  // Load the model after first paint; analysis waits for it only if the user runs before it is ready.
  (window.requestIdleCallback || function (f) { return setTimeout(f, 300); })(function () { if ($('useNLP').checked && !$('useModel').checked) loadNLP(); }, { timeout: 1200 });
  $('useNLP').addEventListener('change', function () { if (this.checked) loadNLP(); });
  $('nlpRetry').addEventListener('click', function () {
    document.querySelectorAll('script[src^="nlp/"]').forEach(function (n) { n.parentNode.removeChild(n); });
    NLP.promise = null; NLP.state = 'idle'; NLP.error = null; loadNLP();
  });
  nlpHint();

  if ('serviceWorker' in navigator && location.protocol === 'https:')
    navigator.serviceWorker.register('sw.js').catch(function () {});
})();
