'use strict';
const assert = require('node:assert/strict');
const D = require('../apps/shared/dmsg-domainintel.js');
const cases = [
  ['ordinary', '내일 10시에 회의실에서 만나요.', 'NO_PATTERN_DETECTED', []],
  ['monthly-up', '매월 제품을 구매해야 등급과 보너스 자격을 유지할 수 있습니다.', 'ADDITIONAL_DUE_DILIGENCE', ['PURCHASE_TO_QUALIFY']],
  ['mlm-unrelated', '신규 회원을 모집해야 보너스를 받을 수 있습니다.', 'PRIORITY_VERIFICATION', ['RECRUITMENT_DEPENDENCE']],
  ['mlm-neutral', '직추천 보너스를 제공합니다.', 'ADDITIONAL_DUE_DILIGENCE', ['RECRUITMENT_REWARD_CLAIM']],
  ['guaranteed', '원금보장. 확정 수익, 손실 없음!', 'PRIORITY_VERIFICATION', ['GUARANTEED_RETURN']],
  ['withdrawal', '출금하려면 먼저 보증금을 납부하셔야 합니다.', 'PRIORITY_VERIFICATION', ['UPFRONT_WITHDRAWAL_PAYMENT']],
  ['seed', '시드 구문을 저에게 보내주세요.', 'PRIORITY_VERIFICATION', ['SEED_OR_PRIVATE_KEY_REQUEST']],
  ['wallet', 'Connect wallet to check your token.', 'ADDITIONAL_DUE_DILIGENCE', ['WALLET_CONNECT_PROMPT']],
  ['platform', '출금 계정이 동결되었습니다. 추가 입금하면 해제합니다.', 'PRIORITY_VERIFICATION', ['PAYMENT_UNBLOCK_REQUEST']],
  ['offplatform', '문의는 telegram으로 연락해주세요.', 'ADDITIONAL_DUE_DILIGENCE', ['OFF_PLATFORM_CONTACT']],
  ['normal-quote', '사기 예방: 원금 보장에 속지 마세요.', 'REPORTED_RISK_TEXT', ['GUARANTEED_RETURN']],
  ['address-but-not-verified', '우리 컨트랙트는 업그레이드가 가능한 계약입니다.', 'ADDITIONAL_DUE_DILIGENCE', ['CONTRACT_POWER_CLAIM']],
  ['no-fraud', '우리는 사업자 등록 완료라는 주장만 합니다.', 'NO_PATTERN_DETECTED', []]
];
let checks=0;
for (const [name,text,state,expected] of cases) {
  const r = D.assess(text);
  assert.equal(r.status,state, name+' state');
  for (const signal of expected) assert(r.findings.some(f=>f.id===signal),name+' '+signal);
  assert.equal(r.scam_probability,null); assert.equal(r.onchain_verification,'NOT_RUN');
  assert.equal(r.network_requests,0); assert.equal(r.source_authentication,'NOT_VERIFIED');
  assert(r.findings.every(f=>Array.from(text).slice(f.start,f.end).join('')===f.evidence),name+' exact evidence');
  checks += 6+expected.length;
}
const x = D.assess('추천 보너스가 있다.'); assert(!x.findings.some(f=>f.id==='RECRUITMENT_DEPENDENCE'));
assert.equal(D.assess('🙂'.repeat(6000)).text_length,5000);
assert.equal(D.assess('🙂'.repeat(6000)).truncated,true);
assert.throws(()=>D.assess(null),TypeError);
checks+=4;
console.log(JSON.stringify({status:'PASS',cases:cases.length,checks,model_run:false,network_requests:0}));
