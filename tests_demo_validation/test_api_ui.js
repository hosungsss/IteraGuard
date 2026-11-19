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
