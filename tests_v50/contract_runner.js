/* JSON stdin/stdout test adapter. No HTTP or model invocation. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const C=require('../apps/shared/v50-contract.js');
const E=require('../apps/shared/dmsg-engine.js');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
if(input.operation==='drift'){
  E.data.model.spec.q_action.options.reverse();
  assert.throws(()=>C.executionManifest(),/QUESTION_CONTRACT_DRIFT/);
  process.stdout.write(JSON.stringify({rejected:true}));
}else if(input.operation==='missing_linkguard'){
  const sandbox={DMSG:E,DMSG_V50_CONTRACT_DATA:C.executionManifest()};
  vm.runInNewContext(fs.readFileSync(require.resolve('../apps/shared/v50-contract.js'),'utf8'),sandbox);
  const r=sandbox.DMSG_V50.applyLocalLayers('일정 안내',input.result,{});
  process.stdout.write(JSON.stringify(r));
}else{
  const results=input.cases.map(x=>{
    try{
      let r=x.failure?C.unavailableCurrent(x.failure,x.policy):C.evaluateCurrent(x.text,x.raw,x.policy,{source:'FIXTURE'});
      if(x.local)r=C.applyLocalLayers(x.text,r,x.local);
      return{ok:r};
    }catch(e){return{error:e.message};}
  });
  process.stdout.write(JSON.stringify({manifest:C.executionManifest(),results}));
}
