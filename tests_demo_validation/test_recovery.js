const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../arena/web/main.js'),'utf8').split('function rememberSession')[0];
const payload={session_id:'s',request_id:'r',version:0,text:'synthetic',synthetic_only:true};
const ok=d=>({ok:true,status:200,json:async()=>d});
function setup(fetch){const ctx={document:{},fetch,TypeError,setTimeout:fn=>{fn();return 1;},clearTimeout(){}};vm.createContext(ctx);vm.runInContext(source,ctx);return ()=>vm.runInContext(`api('/api/evaluate',${JSON.stringify(payload)})`,ctx);}
test('lost committed response restores result without second inference',async()=>{
 let calls=0;const run=setup(async url=>{if(url==='/api/evaluate'){calls++;throw new TypeError('network');}return ok({version:1,events:[{session_id:'s',request_id:'r',version:1,action:'ASK_HUMAN',mode:'MODEL_UNAVAILABLE'}]});});
 assert.equal((await run()).mode,'MODEL_UNAVAILABLE');assert.equal(calls,1);
});
test('uncommitted failure retries exact same request',async()=>{
 const bodies=[];const run=setup(async(url,o)=>{if(url.startsWith('/api/state'))return ok({version:0,lifecycle:'OPEN',events:[]});bodies.push(o.body);if(bodies.length===1)throw new TypeError('network');return ok({action:'CAUTION'});});
 await run();assert.equal(bodies.length,2);assert.equal(bodies[0],bodies[1]);
});
test('session advance stops resend',async()=>{
 let calls=0;const run=setup(async url=>{if(url.startsWith('/api/state'))return ok({version:2,lifecycle:'OPEN',events:[]});calls++;throw new TypeError('network');});
 await assert.rejects(run(),/RECOVERY_STATE_CHANGED/);assert.equal(calls,1);
});
test('permanent network failure bounded at three attempts',async()=>{
 let calls=0;const run=setup(async url=>{if(url.startsWith('/api/state'))return ok({version:0,lifecycle:'OPEN',events:[]});calls++;throw new TypeError('network');});
 await assert.rejects(run(),/network/);assert.equal(calls,3);
});
test('auth failure never retried',async()=>{
 let calls=0;const run=setup(async()=>{calls++;return {status:401};});await assert.rejects(run(),/인증/);assert.equal(calls,1);
});
test('valid model abstention never retried or changed',async()=>{
 let calls=0;const run=setup(async()=>{calls++;return ok({action:'ASK_HUMAN',reason:'MODEL_NOT_CONFIGURED'});});assert.equal((await run()).reason,'MODEL_NOT_CONFIGURED');assert.equal(calls,1);
});
test('new session creation is never retried after lost response',async()=>{
 let calls=0;const ctx={document:{},TypeError,fetch:async()=>{calls++;throw new TypeError('network');}};vm.createContext(ctx);vm.runInContext(source,ctx);await assert.rejects(vm.runInContext("api('/api/start',{})",ctx));assert.equal(calls,1);
});
