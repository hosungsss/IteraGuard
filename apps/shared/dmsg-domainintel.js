/* IteraGuard / Doubt Meter - offline research-assist module.
 * No remote fetch, financial transactions, blockchain RPC, or fraud conviction.
 * Human-readable evidence and due diligence only; no numerical scam probability.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.DmsgDomainIntel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var VERSION = '4.8.0';
  var CATALOG = {
    mlm: {label:'네트워크마케팅·판매 보상', questions:[
      '참가자 외 실제 소비자 매출과 반복 구매를 독립 자료로 확인할 수 있나요?',
      '신규 회원 모집 없이도 수익이 가능한가요? 수당이 실제 최종 소비자 판매에 연결되나요?',
      '전체 참여자의 비용 공제 후 순수익 분포와 탈퇴·환불 조건이 공개되어 있나요?',
      '국가별 등록·규제·소비자 보호 요건을 공식 기관에서 확인했나요?']},
    crypto: {label:'블록체인·가상자산', questions:[
      '정확한 체인 ID, 컨트랙트 주소, 토큰 코드 및 검증된 소스가 확인되나요?',
      '관리자 권한(민팅·동결·업그레이드), 유동성·거래 제한, 소유 집중도가 독립 분석되었나요?',
      '시드 구문·개인키를 제출하라고 요구하지 않나요? 토큰 승인 권한은 최소한인가요?',
      '온체인 거래와 홍보 문구가 일치하나요? 외부 사업과 수익 원천을 별도로 검증했나요?']},
    investing: {label:'금융·투자 권유', questions:[
      '수익 원천, 손실 가능성, 수수료, 출금 절차가 계약서에 명확히 적혀 있나요?',
      '투자 권유자와 운영 주체의 등록·인가를 관할 공식 기관에서 검증했나요?',
      '원금 보장이나 고정 수익 약속에 독립적인 지급능력 증거가 있나요?',
      '계약서·입출금 기록·실제 손실 사례를 교차 검증했나요?']},
    platform: {label:'온라인 플랫폼·구독·정산', questions:[
      '운영자 법적 실체, 고객 지원, 약관, 환불·해지·정산 조건이 명확한가요?',
      '정산을 받기 전에 추가 입금·세금·인증비를 요구하나요?',
      '실제 사용자의 독립적인 거래·환불 증거가 존재하나요?',
      '앱·사이트의 권한, 링크, 개인정보 처리·자동결제 조건을 확인했나요?']}
  };
  var SIGNALS = [
    ['GUARANTEED_RETURN', ['investing','crypto'], 3, /(?:원금\s*보장|손실\s*(?:없음|제로)|확정\s*수익|무위험\s*고수익|guaranteed\s*(?:returns?|profits?)|risk[- ]?free\s*(?:returns?|profits?))/giu,
      '손실이 없다는 주장 또는 확정 수익 약속은 검증이 필요한 고위험 표현입니다.'],
    ['FIXED_DAILY_YIELD', ['crypto','investing'], 2, /(?:매일|하루|daily)\s*(?:수익|이자|배당|yield|profit)?\s*(?:\d+(?:\.\d+)?\s*%|퍼센트)|(?:일\s*\d+(?:\.\d+)?\s*%\s*수익)/giu,
      '단기 고정 수익 구조의 원천과 지속가능성을 확인해야 합니다.'],
    ['UPFRONT_WITHDRAWAL_PAYMENT', ['investing','crypto','platform'], 3, /(?:출금|인출|정산|withdraw(?:al)?)[^\n.!?]{0,55}(?:먼저|선납|추가|별도)[^\n.!?]{0,28}(?:입금|납부|수수료|세금|보증금|fee|tax)|(?:해제비|출금세금|출금\s*보증금)/giu,
      '자금을 인출하기 위한 별도 선납 요구는 공식 계약·독립 확인이 필요합니다.'],
    ['SEED_OR_PRIVATE_KEY_REQUEST', ['crypto'], 3, /(?:시드\s*(?:구문|문구|단어)|복구\s*문구|니모닉|seed\s*phrase|private\s*key|개인키)[^\n.!?]{0,40}(?:보내|입력|제공|제출|공유|알려|verify|submit|send)/giu,
      '시드 구문 또는 개인키를 요구하는 메시지입니다. 제공하지 마세요.'],
    ['RECRUITMENT_DEPENDENCE', ['mlm'], 3, /(?:추천|모집|리크루팅|recruit|downline)[^\n.!?]{0,56}(?:해야|필수|조건|없이는|않으면|충족|유지)[^\n.!?]{0,25}(?:수당|보상|자격|등급|보너스|소득|income|bonus)|(?:수당|보너스)[^\n.!?]{0,28}(?:모집|추천)[^\n.!?]{0,20}(?:필수|조건)/giu,
      '수당 자격이 모집에 의존하는지 실거래 보상 구조를 검증해야 합니다.'],
    ['PURCHASE_TO_QUALIFY', ['mlm'], 2, /(?:매월|매달|월간|정기)[^\n.!?]{0,30}(?:구매|매입|제품|패키지)[^\n.!?]{0,40}(?:등급|유지|보너스|수당|자격|충족)|(?:등급|수당)[^\n.!?]{0,30}(?:유지|자격)[^\n.!?]{0,30}(?:의무\s*구매|월\s*구매)/giu,
      '참여자 구매가 실제 수요인지 보상 자격 유지 목적인지 확인해야 합니다.'],
    ['RECRUITMENT_REWARD_CLAIM', ['mlm'], 1, /(?:추천\s*(?:수당|보너스|인센티브)|직추천\s*보상|후원\s*수당|recruitment\s*bonus|referral\s*commission)/giu,
      '추천 수당의 존재 자체는 위법 증거가 아닙니다. 지급 조건·소매 판매 연계를 확인하세요.'],
    ['INCOME_TESTIMONIAL', ['mlm','investing','platform'], 1, /(?:월\s*(?:수익|수입|소득)\s*\d[\d,]*(?:만|억|원)|하루에\s*\d[\d,]*(?:만|억|원)\s*(?:벌|수익)|(?:월|매달)\s*\d+(?:\.\d+)?\s*(?:만|억)\s*(?:벌|수익))/giu,
      '성공담은 참여자 전체의 비용 차감 후 실적을 대신하지 못합니다.'],
    ['RECRUITMENT_EMPHASIS', ['mlm'], 1, /(?:사람만\s*데려오|회원만\s*모으|제품\s*판매\s*없이\s*수익|모집만\s*하면\s*돈|추천만\s*하면\s*수익)/giu,
      '최종 소비자 판매 없이 모집만으로 보상되는지 확인해야 합니다.'],
    ['URGENT_INVESTMENT_PRESSURE', ['investing','crypto','mlm','platform'], 1, /(?:지금\s*즉시\s*(?:입금|투자|가입)|오늘\s*안에\s*(?:투자|입금|결제)|선착순\s*투자|비밀\s*투자\s*기회|마감\s*임박)/giu,
      '시간 압박은 독립 검증을 어렵게 만들 수 있습니다.'],
    ['UNVERIFIED_REGULATORY_CLAIM', ['investing','crypto','mlm','platform'], 1, /(?:정부\s*공인|국가\s*보증|금융당국\s*인증|거래소\s*공식\s*인증|정부가\s*보장)/giu,
      '기관 인증이라는 문구는 주장일 뿐입니다. 공식 등록부에서 확인해야 합니다.'],
    ['WALLET_CONNECT_PROMPT', ['crypto'], 1, /(?:지갑\s*(?:연결|승인)|connect\s*(?:your\s*)?wallet|approve\s*token|무제한\s*승인)/giu,
      '지갑 연결·토큰 승인은 실제 권한 범위 확인이 필요합니다.'],
    ['OFF_PLATFORM_CONTACT', ['platform','mlm','investing','crypto'], 1, /(?:텔레그램|telegram|라인|line\s*(?:id|:)|카카오\s*오픈채팅|왓츠앱|whatsapp)[^\n.!?]{0,35}(?:연락|추가|문의|이동|join)|(?:연락|문의|이동)[^\n.!?]{0,35}(?:텔레그램|telegram|라인|line\s*(?:id|:)|왓츠앱|whatsapp)/giu,
      '공식 채널 밖에서의 소통은 발신자 확인과 개인정보 보호가 필요할 수 있습니다.'],
    ['SIDELOAD_INSTALL_PROMPT', ['platform','investing','crypto'], 2, /(?:apk|설치\s*파일|외부\s*앱)[^\n.!?]{0,35}(?:설치|다운|허용)|(?:출처\s*불명|알\s*수\s*없는\s*출처)[^\n.!?]{0,30}(?:설치|허용)/giu,
      '검증되지 않은 앱 설치는 권한·서명·배포 출처를 확인해야 합니다.'],
    ['PAYMENT_UNBLOCK_REQUEST', ['platform','crypto','investing'], 3, /(?:계정|정산|출금|withdrawal)[^\n]{0,55}(?:동결|잠금|제한)[^\n]{0,55}(?:추가\s*입금|충전|해제비|납부|결제)|(?:충전|추가\s*입금)[^\n.!?]{0,30}(?:출금|정산)[^\n.!?]{0,18}(?:가능|해제)/giu,
      '출금/정산을 위해 추가 금전을 요구하는지 계약과 실거래로 확인해야 합니다.'],
    ['CONTRACT_POWER_CLAIM', ['crypto'], 1, /(?:컨트랙트|smart\s*contract)[^\n.!?]{0,45}(?:민팅|업그레이드|소유자\s*권한|동결|블랙리스트|owner|mint|upgrade)/giu,
      '컨트랙트 권한에 관한 문구는 코드·체인 상태를 실제 조회해 검증해야 합니다.']
  ];
  var WARN = /(?:조심하세|속지\s*마세|주의하세|하지\s*마세|피하세|금지|사기\s*(?:주의|경고|예방|신고)|절대\s*(?:보내|입금|제출|입력)하지\s*마)/iu;
  function cap(value, max) { if (typeof value !== 'string') throw new TypeError('TEXT_REQUIRED'); return Array.from(value).slice(0, max).join(''); }
  function cpo(s, i) { return Array.from(s.slice(0, i)).length; }
  function perspective(s) { return WARN.test(s) ? 'POSSIBLE_WARNING_OR_REPORT' : 'UNVERIFIED_PROMOTIONAL_OR_OTHER_TEXT'; }
  function assess(input, opts) {
    opts = opts || {};
    var text = cap(input, 5000), perspectiveName = perspective(text), findings=[], seen=new Set();
    for (var x of SIGNALS) {
      var id=x[0], domains=x[1], weight=x[2], regex=x[3], reason=x[4]; regex.lastIndex = 0;
      var m;
      while ((m=regex.exec(text)) && findings.length < 30) {
        var key=id+':'+m.index; if (seen.has(key)) continue; seen.add(key);
        var before=text.slice(Math.max(0,m.index-24),m.index), after=text.slice(m.index+m[0].length,m.index+m[0].length+25);
        var warned = WARN.test(before + m[0] + after);
        findings.push({ id:id, domains:domains, severity: warned ? 0 : weight,
          context:warned?'QUOTED_OR_WARNED':'UNVERIFIED_CLAIM', evidence:m[0], start:cpo(text,m.index), end:cpo(text,m.index+m[0].length), explanation:reason });
        if (m[0].length === 0) regex.lastIndex++;
      }
    }
    findings.sort(function(a,b){return a.start-b.start;});
    var active=findings.filter(function(x){return x.severity>0;});
    var domains=[], total={};
    active.forEach(function(x){x.domains.forEach(function(k){total[k]=(total[k]||0)+x.severity;});});
    Object.keys(total).sort(function(a,b){return total[b]-total[a];}).forEach(function(k){domains.push({id:k,label:CATALOG[k].label, observed_weight:total[k]});});
    var max = active.reduce(function(v,x){return Math.max(v,x.severity);},0), status = max>=3?'PRIORITY_VERIFICATION':active.length?'ADDITIONAL_DUE_DILIGENCE':findings.length?'REPORTED_RISK_TEXT':'NO_PATTERN_DETECTED';
    var required = {}, domainIds=domains.map(function(x){return x.id;});
    if (!domainIds.length) domainIds=['platform','investing'];
    domainIds.forEach(function(id){required[id]={label:CATALOG[id].label, questions:CATALOG[id].questions};});
    return {version:VERSION, status:status, context:perspectiveName, text_length:Array.from(text).length, truncated:Array.from(input).length>5000,
      findings:findings, active_findings:active.length, domains:domains, checklists:required,
      provenance:'TEXT_OBSERVATION_ONLY', source_authentication:'NOT_VERIFIED', onchain_verification:'NOT_RUN', legal_classification:'NOT_DETERMINED',
      financial_audit:'NOT_RUN', nlp_model_used:false, scam_probability:null, network_requests:0,
      note:'입력 텍스트에서 표현을 찾는 로컬 예비 검토입니다. 실거래·계약·등록·온체인 데이터·법적 판단을 검증하지 않았습니다.'};
  }
  return {VERSION:VERSION, CATALOG:CATALOG, assess:assess};
});
