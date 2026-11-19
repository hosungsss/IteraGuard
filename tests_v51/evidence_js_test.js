'use strict';
// Author-written development counterexamples. This file never reads data/ or
// any locked validation set. --stdin is used only for Python/JS result parity.
const assert = require('assert');
const fs = require('fs');
const {enrichEvidence} = require('../apps/shared/v51-evidence.js');
const make = (text,word) => {
  const e = [], chars=Array.from(text);
  if(word!==undefined){const start=Array.from(text.slice(0,text.indexOf(word))).length;e.push({start,end:start+Array.from(word).length,quote:word,kind:'otp'});}
  return {action:'ASK_HUMAN',reason:'ORIGINAL_REASON',message:'기존 안내',evidence:e,execution_trace:{final_action:'ASK_HUMAN'}};
};
if(process.argv.includes('--stdin')){
  const req=JSON.parse(fs.readFileSync(0,'utf8'));
  process.stdout.write(JSON.stringify(req.map(r=>enrichEvidence(r.text,r.result))));
}else{
  let checks=0;
  function check(name,fn){try{fn();checks++;}catch(e){e.message=name+': '+e.message;throw e;}}
  check('suffix includes object and action',()=>{
    const t='인증번호를 알려주세요.',r=make(t,'주세요'),before=JSON.stringify(r),o=enrichEvidence(t,r);
    assert.strictEqual(o.evidence[0].quote,'인증번호를 알려주세요');assert.strictEqual(JSON.stringify(r),before);
    assert.deepStrictEqual(o.original_evidence,r.evidence);assert.deepStrictEqual(o.execution_trace,r.execution_trace);
  });
  check('deictic request remains unavailable',()=>assert.strictEqual(enrichEvidence('그것을 보내주세요.',make('그것을 보내주세요.')).evidence.length,0));
  check('report word as action object',()=>{const t='교육 자료를 보내주세요.';assert.strictEqual(enrichEvidence(t,make(t)).evidence[0].clause_mode,'DIRECT_REQUEST_CUE');});
  check('ambiguous report phrase',()=>{const t='예시 OTP를 보내주세요.';assert.strictEqual(enrichEvidence(t,make(t)).evidence.length,0);});
  check('warning scope differs from following request',()=>{
    const t='인증번호를 알려주지 마세요. 하지만 지금 OTP를 보내주세요.';
    assert.deepStrictEqual(enrichEvidence(t,make(t)).evidence.map(e=>e.clause_mode),['NEGATED_OR_WARNING_CUE','DIRECT_REQUEST_CUE']);
  });
  check('quoted request not direct',()=>{
    const t='“OTP를 보내주세요”라고 했습니다.';
    assert.strictEqual(enrichEvidence(t,make(t)).evidence[0].clause_mode,'QUOTED_OR_REPORTED');
  });
  check('mixed quoted and current request abstains from display',()=>{
    const t='‘OTP를 보내세요’라는 문자를 보고 인증번호를 알려주세요.';
    assert.strictEqual(enrichEvidence(t,make(t)).evidence.length,0);
  });
  check('unclosed quote',()=>{const t='“OTP를 보내주세요.';assert.strictEqual(enrichEvidence(t,make(t)).evidence.length,0);});
  check('report heading does not invent direct context',()=>{const t='교육 예시:\nOTP를 보내주세요.';assert.strictEqual(enrichEvidence(t,make(t)).evidence.length,0);});
  check('emoji offsets are code points',()=>{
    const t='🧑🏽‍💻🙂 서류를 가져오세요.\r\n🔒 OTP를 보내지 마세요.',o=enrichEvidence(t,make(t,'서류'));
    for(const e of o.evidence)assert.strictEqual(Array.from(t).slice(e.start,e.end).join(''),e.quote);
    assert.strictEqual(o.original_evidence[0].start,6);
  });
  check('example scope continues after punctuation',()=>{
    for(const t of ['예시: 송금하세요. OTP를 보내주세요.','경고: 사기 메시지 예시입니다. OTP를 보내주세요.'])assert(!enrichEvidence(t,make(t)).evidence.some(e=>e.clause_mode==='DIRECT_REQUEST_CUE'));
  });
  check('explicit scope end allows new request display',()=>{const t='예시: 송금하세요. 예시 끝. OTP를 보내주세요.';assert.strictEqual(enrichEvidence(t,make(t)).evidence.slice(-1)[0].clause_mode,'DIRECT_REQUEST_CUE');});
  check('Unicode whitespace is explicit',()=>{
    for(const [prefix,start] of [['\u0085',1],['\ufeff',0],['\u001c',0],['\u2007',1]]){const t=prefix+'OTP를 보내주세요.';assert.strictEqual(enrichEvidence(t,make(t)).evidence[0].start,start);}
  });
  check('ordinary request and financial term do not change judgement',()=>{
    for(const t of ['서류를 가져오세요.','일상 비용 2만원을 보내주세요.']){
      const r=make(t);r.action='NO_STRONG_SIGNAL';const o=enrichEvidence(t,r);
      assert.strictEqual(o.action,r.action);assert.strictEqual(o.reason,r.reason);assert.strictEqual(o.evidence_display.risk_classification,'NOT_PERFORMED');
    }
  });
  check('safe trace excludes arbitrary original metadata',()=>{
    const t='SECRET_XYZ OTP를 보내주세요.',r=make(t,'주세요');r.evidence[0].kind='SECRET_METADATA';
    const o=enrichEvidence(t,r);assert(!JSON.stringify(o.evidence_display_trace).includes('SECRET'));
    assert(!JSON.stringify(o.evidence_display_trace).includes('quote'));
  });
  check('partial coverage remains visible',()=>{
    const t='OTP를 보내주세요. 그것을 보내주세요.',o=enrichEvidence(t,make(t));
    assert.strictEqual(o.evidence_display.candidate_clause_coverage,.5);assert.strictEqual(o.evidence_display.unavailable_clause_rate,.5);
  });
  check('idempotence',()=>{const t='OTP를 보내주세요.',o=enrichEvidence(t,make(t,'주세요'));assert.deepStrictEqual(enrichEvidence(t,o),o);});
  check('oversize rejected',()=>assert.throws(()=>enrichEvidence('x'.repeat(2001),{}),/INVALID_EVIDENCE_INPUT/));
  process.stdout.write(JSON.stringify({status:'PASS',checks,model_calls:0,locked_data_read:false})+'\n');
}
