'use strict';
/* Chat UI runs inside a synthetic DOM: no real model, browser or network. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Node {
  constructor() {
    this.value='';this.disabled=false;this.dataset={};this.className='';
    this.children=[];this.events={};this._text='';this.scrollHeight=500;this.scrollTop=0;
  }
  set textContent(s) {this._text=String(s);this.children=[];}
  get textContent() {return this._text+this.children.map(x=>x.textContent).join('');}
  appendChild(node) {this.children.push(node);return node;}
  removeChild(node) {this.children=this.children.filter(x=>x!==node);}
  get firstChild() {return this.children[0]||null;}
  addEventListener(name,fn) {(this.events[name] ||= []).push(fn);}
  fire(name, event={}) {for (const fn of this.events[name]||[]) fn(event);}
  click() {this.fire('click');}
}
const settle=async()=>{await new Promise(setImmediate);await new Promise(setImmediate);};
const SID='a'.repeat(32);
function app({defer=false,fail=false}={}) {
  const nodes={},handlers={},calls=[],pending=[];
  const get=id=>nodes[id] ||= new Node();
  const names=['link_only','clicked','downloaded','installed','entered_secret','paid','verify','not_clicked'];
  const buttons=names.map(k=>{const n=new Node();n.dataset.followup=k;return n;});
  function response(payload){
    return {schema:'iteraguard-guided-conversation/1',mode:'RULE_BASED_FOLLOWUP_NOT_GENERATIVE',
      session_id:payload.session_id,version:payload.version,scenario:payload.scenario,
      title:'공식 확인',introduction:'안전 보증이 아닙니다.',risk_notice:'이전 위험 미해결.',
      steps:['공식 경로 확인'],sources:[{name:'KISA',url:'https://www.boho.or.kr/example'}],
      action_taken:false,task_updated:false,decision_changed:false,risk_cleared:false};
  }
  async function fetch(url,options) {
    const payload=JSON.parse(options.body);
    calls.push({url,payload});
    if(defer){
      return new Promise(resolve=>pending.push(()=>{
        resolve({ok:!fail,json:async()=>fail?{error:'STALE_SESSION_VERSION'}:response(payload)});
      }));
    }
    return {ok:!fail,json:async()=>fail?{error:'STALE_SESSION_VERSION'}:response(payload)};
  }
  const document={
    getElementById:get,createElement:()=>new Node(),
    querySelectorAll:(s)=>s==='[data-followup]'?buttons:[],
    addEventListener(name,fn){(handlers[name] ||= []).push(fn);}
  };
  const context={document,fetch,console};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../arena/web/chat.js'),'utf8'),context);
  const emit=(name,detail)=>{for(const fn of handlers['iteraguard:'+name]||[])fn({detail});};
  const decision=(overrides={})=>emit('decision',{
    session_id:SID,version:1,text:'[합성] 비밀번호를 알려주세요.',
    action:'PAUSE_AND_VERIFY',model_status:'VALID',
    message:'독립 확인을 진행하세요.',prior_pause:true,
    provenance:'CONTROLLED_CLIENT',task_count:1,...overrides
  });
  return {get,calls,pending,emit,decision,buttons};
}

test('no follow-up before actual accepted evaluation',async()=>{
  const a=app();assert.equal(a.get('sendFollowup').disabled,true);
  assert.equal(a.buttons[0].disabled,true);
  a.buttons[0].click();await settle();
  assert.equal(a.calls.length,0);
});

test('controlled fake response provenance never called real Zoro',()=>{
  const a=app();a.decision();
  const text=a.get('conversationFeed').textContent;
  assert.match(text,/합성/);
  assert.match(text,/통제 응답/);
  assert.match(text,/실제 Zoro 추론 아님/);
  assert.equal(a.buttons[0].disabled,false);
  assert.equal(a.calls.length,0);
});

test('model failure appears as failure not model answer attestation',()=>{
  const a=app();a.decision({model_status:'FAILED'});
  assert.match(a.get('conversationFeed').textContent,/실제 추론 결과 없음/);
});

test('choice sends structured scenario only, never user text',async()=>{
  const a=app();a.decision();a.buttons[1].click();await settle();
  assert.equal(a.calls.length,1);
  assert.equal(a.calls[0].url,'/api/conversation/followup');
  assert.deepEqual(a.calls[0].payload,{
    session_id:SID,version:1,scenario:'clicked',synthetic_only:true
  });
  assert.doesNotMatch(JSON.stringify(a.calls[0]),/비밀번호를 알려/);
  assert.match(a.get('conversationFeed').textContent,/규칙 기반/);
});

test('user screenshot phrase link-only is classified without re-evaluating Zoro',async()=>{
  const a=app();a.decision();
  const field=a.get('followupText');field.value='그럼 링크만 누르고 인증번호를 안 넣으면 괜찮아?';
  field.fire('input');a.get('sendFollowup').click();await settle();
  assert.equal(a.calls.length,1);
  assert.equal(a.calls[0].payload.scenario,'link_only');
  assert.doesNotMatch(JSON.stringify(a.calls[0]),/괜찮아/);
});

test('user screenshot phrase clicked selects clicked, not link-only',async()=>{
  const a=app();a.decision();
  const field=a.get('followupText');field.value='근데 나 이미 링크를 눌렀어. 이제 어떻게 해?';
  field.fire('input');a.get('sendFollowup').click();await settle();
  assert.equal(a.calls[0].payload.scenario,'clicked');
});

test('unknown freeform question is not falsely interpreted as model guidance',async()=>{
  const a=app();a.decision();
  const f=a.get('followupText');f.value='지금 기분이 어때?';f.fire('input');
  a.get('sendFollowup').click();await settle();
  assert.equal(a.calls.length,0);
  assert.match(a.get('conversationNotice').textContent,/상황을 확정할 수 없습니다/);
});

test('text revision invalidates stale response before it can be displayed',async()=>{
  const a=app({defer:true});a.decision();a.buttons[1].click();await settle();
  assert.equal(a.pending.length,1);
  const count=a.get('conversationFeed').children.length;
  a.emit('invalidate',{reason:'input_changed'});
  a.pending.shift()();await settle();
  assert.equal(a.get('conversationFeed').children.length,count);
  assert.equal(a.buttons[0].disabled,true);
});

test('new session clears ephemeral conversation, no storage',()=>{
  const a=app();a.decision();assert.ok(a.get('conversationFeed').children.length);
  a.emit('reset',{session_id:'b'.repeat(32)});
  assert.equal(a.get('conversationFeed').children.length,0);
  assert.equal(a.buttons[0].disabled,true);
});

test('server version conflict is not presented as successful guidance',async()=>{
  const a=app({fail:true});a.decision();a.buttons[1].click();await settle();
  assert.match(a.get('conversationFeed').textContent,/확인 보류/);
  assert.equal(a.buttons[0].disabled,true);
  assert.match(a.get('conversationNotice').textContent,/자동 재시도하지 않음/);
});

test('question text is rendered via textContent without HTML interpretation',()=>{
  const a=app();
  a.decision({text:'<img src=x onerror=alert(1)>',message:'확인'});
  const feed=a.get('conversationFeed');
  assert.match(feed.textContent,/<img/);
  assert.equal(feed.children[0].children[1].children.length,0);
});


test('new pause is not mislabeled as a previous unresolved risk',()=>{
  const a=app();a.decision({prior_pause:true,prior_risk_unresolved:false});
  assert.doesNotMatch(a.get('conversationFeed').textContent,/기존 위험 보류 이력/);
  a.decision({action:'ASK_HUMAN',current_turn_action:'NO_STRONG_SIGNAL',prior_risk_unresolved:true});
  assert.match(a.get('conversationFeed').textContent,/기존 위험 보류 이력/);
});
test('failed inference is not displayed as a completed current judgment',()=>{
  const a=app();a.decision({model_status:'FAILED',action:'ASK_HUMAN'});
  assert.match(a.get('conversationFeed').textContent,/분석 실패 · 판단 불가/);
});

for (const [question, expected] of [
  ['인증번호를 안 보냈어요.', null], ['인증번호를 보냈어요.', 'entered_secret'],
  ['아직 송금했는지 모르겠어요.', null], ['제가 아니라 친구가 송금했어요.', null],
  ['앱을 설치했을 때는 어떻게 하나요?', null], ['제가 방금 송금했어요.', 'paid'],
  ['앱을 설치했어요.', 'installed'], ['제가 파일을 내려받았습니다.', 'downloaded'],
  ['입금했어요? 제가 확인해야 하나요?', null],
]) {
  test('follow-up preserves actor, polarity and timing: ' + question, async () => {
    const a = app(); a.decision();
    a.get('followupText').value = question; a.get('sendFollowup').click(); await settle();
    assert.equal(a.calls.length, expected === null ? 0 : 1);
    if (expected) assert.equal(a.calls[0].payload.scenario, expected);
    else assert.match(a.get('conversationNotice').textContent, /상황을 확정할 수 없습니다/);
  });
}
