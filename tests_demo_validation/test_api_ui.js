const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const root=process.env.DMSG_TEST_ROOT || path.join(__dirname,'..');
const source=fs.readFileSync(path.join(root,'arena/web/main.js'),'utf8').split('function rememberSession')[0];
function run(response) {
  const context={document:{},fetch:async()=>response};vm.createContext(context);vm.runInContext(source,context);
  return vm.runInContext("api('/api/evaluate', {})",context);
}
test('expired website authentication is actionable even for HTML',async()=>{
  await assert.rejects(run({status:401,ok:false,json:async()=>{throw Error('html')}}),/다시 인증/);
});
test('busy model does not masquerade as a decision',async()=>{
  await assert.rejects(run({status:429,ok:false}),/다른 요청/);
});
test('login redirect HTML is not parsed as a decision',async()=>{
  await assert.rejects(run({status:200,ok:true,headers:{get:()=> 'text/html'}}),/JSON 대신/);
});
test('malformed JSON and arrays rejected',async()=>{
  await assert.rejects(run({ok:true,json:async()=>{throw Error('bad')}}),/응답 형식/);
  await assert.rejects(run({ok:true,json:async()=>[]}),/INVALID_API_RESPONSE/);
});
test('valid unavailable response remains unavailable',async()=>{
  const d=await run({ok:true,json:async()=>({mode:'MODEL_UNAVAILABLE'})});assert.equal(d.mode,'MODEL_UNAVAILABLE');
});
test('timeout warns to read saved state before retrying',async()=>{
  let expire,cleared=false;
  const context={document:{},AbortController,setTimeout:fn=>{expire=fn;return 1;},clearTimeout:()=>{cleared=true;},
    fetch:async(_,options)=>{expire();assert.ok(options.signal.aborted);throw {name:'AbortError'};}};
  vm.createContext(context);vm.runInContext(source,context);
  await assert.rejects(vm.runInContext("api('/api/evaluate', {})",context),/저장 상태를 먼저/);
  assert.ok(cleared);
});

function bootSignalHome(fetch) {
  const elements = Object.fromEntries([
    'signalForm', 'text', 'run', 'inlineSignal', 'inlineSignalGrade', 'inlineRequestedAction',
    'signalStatus', 'charCount', 'sampleNotice', 'signalExplanation'
  ].map(id => {
    const listeners = {};
    return [id, {
      textContent: '', value: '', hidden: id === 'inlineSignal', disabled: false, dataset: {},
      addEventListener(type, callback) { listeners[type] = callback; },
      setAttribute() {}, removeAttribute() {}, focus() {},
      trigger(type) { return (listeners[type] || this['on' + type])?.({preventDefault() {}}); }
    }];
  }));
  const document = {
    body: {dataset: {}},
    getElementById: id => elements[id]
  };
  const context = vm.createContext({document, fetch, AbortController, setTimeout, clearTimeout});
  const code = fs.readFileSync(path.join(root, 'arena/web/signal.js'), 'utf8');
  vm.runInContext(code, context);
  return elements;
}

function signalReply(status, body) {
  return {
    ok: status === 200, status,
    headers: {get: () => 'application/json'},
    json: async () => body
  };
}

test('the home form sends one request and shows its grade and requested action', async () => {
  const requests = [];
  const ui = bootSignalHome(async (url, config) => {
    requests.push([url, config.method, JSON.parse(config.body)]);
    return signalReply(200, {
      grade: 'red',
      requested_action: {id: 'share_auth_secret', label: '비밀번호·인증번호 알려주기'}
    });
  });
  assert.deepEqual(requests, []);
  const original = ' 가상 문자\n인증번호를 알려주세요. ';
  ui.text.value = original;
  ui.text.trigger('input');
  await ui.signalForm.trigger('submit');
  assert.deepEqual(requests, [['/api/signal', 'POST', {text: original, synthetic_only: true}]]);
  assert.equal(ui.inlineSignal.hidden, false);
  assert.equal(ui.inlineSignal.dataset.grade, 'red');
  assert.match(ui.inlineSignalGrade.textContent, /빨강/);
  assert.equal(ui.inlineRequestedAction.textContent, '비밀번호·인증번호 알려주기');
  ui.text.value = '다음 가상 문자';
  ui.text.trigger('input');
  assert.equal(ui.inlineSignal.hidden, true);
});

test('a failed signal request cannot leave the previous result visible', async () => {
  let response = signalReply(200, {
    grade: 'green',
    requested_action: {id: 'none', label: '요청 없음'}
  });
  const ui = bootSignalHome(async () => response);
  ui.text.value = '가상 일반 안내';
  await ui.signalForm.trigger('submit');
  assert.match(ui.inlineSignalGrade.textContent, /초록/);
  response = signalReply(503, {error: 'SIGNAL_MODEL_UNAVAILABLE'});
  await ui.signalForm.trigger('submit');
  assert.ok(ui.inlineSignal.hidden || !ui.inlineSignalGrade.textContent.includes('초록'));
  assert.equal(ui.run.disabled, false);
});

test('green grade does not endorse a credential request', async () => {
  const ui = bootSignalHome(async () => signalReply(200, {
    grade: 'green', requested_action: {id: 'share_auth_secret', label: '비밀번호·인증번호 알려주기'}
  }));
  ui.text.value = '합성 예시'; await ui.signalForm.trigger('submit');
  assert.match(ui.signalStatus.textContent, /두 답이 엇갈립니다/);
  assert.match(ui.inlineRequestedAction.textContent, /인증번호/);
});
test('busy and unavailable have distinguishable messages', async () => {
  for (const [code, label, expected] of [[429,'MODEL_BUSY_RETRY_LATER',/다른 요청/],
                                          [503,'SIGNAL_MODEL_UNAVAILABLE',/로컬 모델/]]) {
    const ui = bootSignalHome(async () => signalReply(code, {error: label}));
    ui.text.value = '합성 예시'; await ui.signalForm.trigger('submit');
    assert.match(ui.signalStatus.textContent, expected);
    assert.equal(ui.inlineSignal.hidden, true);
  }
});

test('rounded near tie carries a caution without changing the observed grade', async () => {
  const ui = bootSignalHome(async () => signalReply(200, {grade:'green', scores:{green:.251,gray:.250,red:.250,orange:.249},
    requested_action:{id:'unknown',label:'불명확'}}));
  ui.text.value='합성'; await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineSignal.dataset.grade,'green');
  assert.match(ui.signalStatus.textContent,/상위 두 선택 점수/);
});

test('link evidence control never submits on navigation or displays an obsolete reply', async () => {
  const listeners = {}, ids = {}, requests = [];
  const document = {getElementById: id => ids[id] ||= {value:'', checked:false,
    addEventListener: (event, fn) => {listeners[event] = fn;}}};
  let reply;
  const fetch = async (url, req) => { requests.push([url,JSON.parse(req.body)]);
    return new Promise(resolve => {reply = resolve;}); };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'arena/web/link-review.js'), 'utf8'), {document,fetch});
  document.getElementById('message').value='합성 https://example.org/sample';
  document.getElementById('host').value=''; document.getElementById('second').checked=true;
  assert.equal(requests.length,0);
  const run=listeners.submit({preventDefault(){}});
  assert.equal(requests[0][0],'/api/link-review'); assert.equal(requests[0][1].share_host,'');
  listeners.input(); reply(signalReply(200,{observation:{status:'LISTED_EXACT',checked:1,matched:1},shadow_model:{status:'NOT_RUN'}}));
  await run;assert.equal(ids.output.textContent,'');assert.equal(ids.submitReview.disabled,false);
});


test('a reconciled grade keeps its explanation and does not reinterpret original scores', async () => {
  const explanation = '요청 행동이 불명확해 정상으로 확정하지 않습니다.';
  const ui = bootSignalHome(async () => signalReply(200, {
    grade: 'gray', requested_action: {id: 'unknown', label: '불명확'}, explanation,
    scores: {green: .251, gray: .250, red: .250, orange: .249},
    context_review: {adjusted: true}
  }));
  ui.text.value = '그 일 좀 해줘요.';
  await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineSignal.dataset.grade, 'gray');
  assert.equal(ui.signalExplanation.textContent, explanation);
  assert.equal(ui.signalStatus.textContent, '');
});
