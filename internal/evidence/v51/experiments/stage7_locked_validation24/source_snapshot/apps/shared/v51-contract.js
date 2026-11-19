/* v5.1 profile-bound execution. No I/O, attestation, or automatic session-risk release. */
(function(root,factory){
 function dep(name,path){if(root[name])return root[name];if(typeof require==='function'){var value=require(path);return root[name]||value;}return null;}
 var E=dep('DMSG_V51_BASE_ENGINE','./v51-base-engine.js'),B=dep('DMSG_V51_BASE_CONTRACT','./v51-base-contract.js');
 var R=dep('DMSG_V51_PROFILE_DATA','./v51-profile-data.js'),M=dep('DMSG_V51_MANIFEST','./v51-contract-data.js');
 var S=dep('DMSG_V51_SEMANTIC','./v51-semantic.js'),V=dep('DMSG_V51_EVIDENCE','./v51-evidence.js');
 var api=factory(root,E,B,R,M,S,V);if(typeof module==='object'&&module.exports)module.exports=api;root.DMSG_V51=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(root,E,B,R,M,S,V){
 'use strict';
 function clone(v){return JSON.parse(JSON.stringify(v));}
 function fail(code){var e=new Error(code);e.name='ContractError';e.code=code;throw e;}
 function same(a,b){if(a===b)return true;if(a===null||b===null||typeof a!=='object'||typeof b!=='object')return false;if(Array.isArray(a)!==Array.isArray(b))return false;var ak=Object.keys(a),bk=Object.keys(b);return ak.length===bk.length&&ak.every(function(k){return Object.prototype.hasOwnProperty.call(b,k)&&same(a[k],b[k]);});}
 function executionManifest(){
  if(!E||!B||!R||!M||!S||!V)fail('V51_EXECUTION_CONTRACT_NOT_AVAILABLE');
  if(R.registry_fingerprint!==M.profile_registry_fingerprint||B.executionManifest().manifest_fingerprint!==M.base_execution_manifest_fingerprint)fail('V51_BASE_PROFILE_DRIFT');
  if(!same(B.questionSignature(E.questions('').questions),R.profiles['v50-baseline'].question_signature))fail('QUESTION_CONTRACT_DRIFT');
  Object.keys(M.profiles).forEach(function(k){if(!R.profiles[k]||R.profiles[k].profile_fingerprint!==M.profiles[k].profile_fingerprint)fail('V51_PROFILE_MANIFEST_DRIFT');});
  return clone(M);
 }
 function profile(ident,policy){
  executionManifest();if(policy!=='legacy'&&policy!=='dra')fail('UNSUPPORTED_POLICY_ID');
  if(typeof ident!=='string'||!Object.prototype.hasOwnProperty.call(R.profiles,ident))fail('UNSUPPORTED_PROFILE_ID');
  var p=R.profiles[ident];if(p.allowed_policy_ids.indexOf(policy)<0)fail('PROFILE_POLICY_NOT_ALLOWED');return clone(p);
 }
 function selectedProfile(policy){policy=policy===undefined?'legacy':policy;var m=executionManifest();if(policy!=='legacy'&&policy!=='dra')fail('UNSUPPORTED_POLICY_ID');var ident=m.release_selection.default_profile_by_policy[policy];profile(ident,policy);return ident;}
 function requestBinding(ident,policy){policy=policy===undefined?'legacy':policy;ident=ident||selectedProfile(policy);var p=profile(ident,policy);return{profile_id:ident,policy_id:policy,question_contract_sha256:p.question_contract_sha256,questions_sha256:p.questions_sha256,profile_fingerprint:p.profile_fingerprint,registry_fingerprint:R.registry_fingerprint,base_execution_manifest_fingerprint:R.base_execution_manifest_fingerprint};}
 function validateBinding(binding,ident,policy){var expected=requestBinding(ident,policy);if(!same(binding,expected))fail('PROFILE_BINDING_MISMATCH');return expected;}
 function questionPayload(text,ident,policy){
  policy=policy===undefined?'legacy':policy;ident=ident||selectedProfile(policy);if(typeof text!=='string')fail('TEXT_REQUIRED');var p=profile(ident,policy),payload=E.questions(text);
  if(ident!=='v50-baseline')payload.questions.q_evidence.instructions=p.questions.q_evidence.instructions;
  Object.keys(p.questions).forEach(function(k){if(!Object.prototype.hasOwnProperty.call(payload.questions,k))payload.questions[k]=clone(p.questions[k]);});
  if(!same(B.questionSignature(payload.questions),p.question_signature))fail('PROFILE_PAYLOAD_MISMATCH');return payload;
 }
 function normalize(raw,p){return E.normalizeResponse(raw,p.response_schema,{optional:p.optional_questions,order:Object.keys(p.response_schema)});}
 function evaluateCurrent(text,raw,policy,options){
  policy=policy===undefined?'legacy':policy;options=options||{};var ident=options.profile_id||selectedProfile(policy),m=executionManifest(),p=profile(ident,policy),binding=validateBinding(options.binding,ident,policy);
  var n=normalize(raw,p),old=clone(raw);old.answers={};Object.keys(E.data.model.spec).forEach(function(k){if(raw.answers&&Object.prototype.hasOwnProperty.call(raw.answers,k))old.answers[k]=clone(raw.answers[k]);});
  var source=options.source===undefined?'MODEL_RESPONSE_UNATTESTED':options.source,base=B.evaluateCurrent(text,old,policy,{source:source});
  var out=p.response_schema.q_request_scope?S.advisory(text,raw,{spec:p.response_schema,optional:p.optional_questions}):clone(base);out.source=source;
  out.policy_id=policy;out.question_profile_id=ident;out.question_binding=clone(binding);out.manifest_fingerprint=m.manifest_fingerprint;out.product_version='5.1';
  var t=clone(base.execution_trace),sem=out.semantic_trace;
  t.schema_version=m.trace_schema_version;t.manifest_fingerprint=m.manifest_fingerprint;t.question_profile_id=ident;t.question_contract_sha256=binding.question_contract_sha256;t.question_binding=clone(binding);
  t.base_policy_action=base.action;t.base_policy_rule=base.reason;t.semantic_policy_id=out.semantic_policy_id||'NONE_BASELINE_COMPARISON';
  t.normalized_probabilities={};Object.keys(n).forEach(function(k){if(k[0]!=='_')t.normalized_probabilities[k]=n[k].probabilities;});t.dropped_optional_questions=n._dropped_optional||[];
  if(sem){var eligible=sem.baseline_action!=='PAUSE_AND_VERIFY';sem.predicates.forEach(function(v){t.predicates.push({id:v.id,condition_met:v.condition_met,eligible:eligible,layer:'SEMANTIC_EXTENSION'});if(eligible&&v.condition_met)eligible=false;});if(['BASELINE_FALLBACK','PRESERVE_EXISTING_PAUSE'].indexOf(sem.rule_id)<0)t.applied_rule_ids.push('V51_'+sem.rule_id);t.semantic=clone(sem);}
  t.predicate_semantics='CONDITION_TRUE_IS_NOT_RULE_APPLIED; eligibility is layer-local and respects rule priority';
  t.condition_ids=t.predicates.filter(function(v){return v.condition_met;}).map(function(v){return v.id;});t.final_action=out.action;t.final_rule=out.reason;
  t.evidence_spans=(out.evidence||[]).map(function(e){var z={};['start','end','kind','directness','origin'].forEach(function(k){if(k in e)z[k]=e[k];});return z;});
  out.execution_trace=t;return V.enrichEvidence(text,out);
 }
 function unavailableCurrent(code,policy,options){
  policy=policy===undefined?'legacy':policy;options=options||{};var ident=options.profile_id||selectedProfile(policy),m=executionManifest(),binding=requestBinding(ident,policy),out=B.unavailableCurrent(code,policy);
  out.question_profile_id=ident;out.question_binding=clone(binding);out.manifest_fingerprint=m.manifest_fingerprint;out.product_version='5.1';
  Object.assign(out.execution_trace,{schema_version:m.trace_schema_version,manifest_fingerprint:m.manifest_fingerprint,question_contract_sha256:binding.question_contract_sha256,question_profile_id:ident,question_binding:clone(binding)});return out;
 }
 function applyLocalLayers(text,result,options){var out=B.applyLocalLayers(text,result,options);if(!out.evidence_display)out=V.enrichEvidence(text,out);if(out.execution_trace&&out.evidence_display_trace)out.execution_trace.evidence_display=clone(out.evidence_display_trace);return out;}
 return{executionManifest:executionManifest,selectedProfile:selectedProfile,requestBinding:requestBinding,validateBinding:validateBinding,questionPayload:questionPayload,evaluateCurrent:evaluateCurrent,unavailableCurrent:unavailableCurrent,applyLocalLayers:applyLocalLayers};
});
