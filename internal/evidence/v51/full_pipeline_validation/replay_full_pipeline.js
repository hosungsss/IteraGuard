'use strict';
const C=require(process.argv[2]+'/apps/shared/v51-contract.js');
global.fetch=()=>{throw new Error('REPLAY_NETWORK_DISABLED');};
let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{
 const results=JSON.parse(s).map(r=>{
  const policy=C.evaluateCurrent(r.text,r.raw,'legacy',{profile_id:r.profile_id,binding:C.requestBinding(r.profile_id,'legacy')});
  const full=C.applyLocalLayers(r.text,policy,{user_review:false});
  return {dataset:r.dataset,arm:r.arm,id:r.id,policy,full};
 });process.stdout.write(JSON.stringify(results));
});
