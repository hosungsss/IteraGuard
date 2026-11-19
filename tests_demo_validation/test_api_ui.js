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
    'signalStatus', 'charCount', 'sampleNotice'
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
