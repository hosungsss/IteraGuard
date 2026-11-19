/* Versioned, pure current-turn contract. No inference, network, or session clearance. */
(function(root,factory){
  var E=root.DMSG || (typeof require==='function'?require('./dmsg-engine.js'):null);
  var D=root.DMSG_V50_CONTRACT_DATA || (typeof require==='function'?(require('./v50-contract-data.js'),root.DMSG_V50_CONTRACT_DATA):null);
  var api=factory(root,E,D);
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.DMSG_V50=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(root,E,D){
  'use strict';
  function fail(code){var e=new Error(code);e.name='ContractError';throw e;}
  function clone(v){return JSON.parse(JSON.stringify(v));}
  function signature(q){return Object.keys(q).map(function(k){var x=q[k],c=x.criteria,kind=Array.isArray(c)?'levels':c&&typeof c==='object'?'choice':'absent';return[k,x.type,x.instructions===undefined?null:x.instructions,kind,kind==='choice'?Object.keys(c).map(function(a){return[a,c[a]];}):c===undefined?null:c];});}
  function executionManifest(){
    if(!E||!D)fail('EXECUTION_CONTRACT_NOT_AVAILABLE');
    if(JSON.stringify(signature(E.questions('').questions))!==JSON.stringify(D.question_signature))fail('QUESTION_CONTRACT_DRIFT');
    return clone(D);
  }
  function policy(id){if(id!=='legacy'&&id!=='dra')fail('UNSUPPORTED_POLICY_ID');}
  function legacyPredicates(text,n,r){
    var a=n.q_action.choice,s=n.q_speech.choice,f=E.contextFlags(text),p=E.clauseProfile(text);
    var acts=p.filter(function(c){return c.flags.action_mentioned;}),clean=acts.filter(function(c){return c.clean_action;}),imp=acts.filter(function(c){return c.clean_imperative;});
    var values=[
      ['MODEL_NONE_BUT_ACTION_TERMS_PRESENT',a==='none'&&f.action_mentioned&&s!=='informational'],
      ['NONE_DIRECT_REQUEST_CONFLICT',a==='none'&&s==='direct_request'],
      ['DIRECT_REQUEST_CONTRADICTS_CONTEXT',s==='direct_request'&&acts.length>0&&!clean.length],
      ['WARNING_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE',s==='negated_or_warning'&&imp.length>0],
      ['UNSUPPORTED_WARNING_LABEL',s==='negated_or_warning'&&acts.length>0&&!acts.some(function(c){return c.flags.warning_cue;})],
      ['INFORMATIONAL_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE',s==='informational'&&imp.length>0],
      ['REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE',s==='reported_or_quoted'&&imp.length>0],
      ['UNSUPPORTED_QUOTATION_LABEL',s==='reported_or_quoted'&&acts.length>0&&!acts.some(function(c){return c.flags.report_cue;})]];
    var preds=[],context=null;
    values.forEach(function(v){preds.push({id:v[0],condition_met:!!v[1],eligible:context===null});if(v[1]&&context===null)context=v[0];});
    if(context!==(E.contextConflict(a,s,f,p)||null))fail('TRACE_CONTEXT_POLICY_DRIFT');
    var parts=[['LOW_ACTION_PROBABILITY',n.q_action.probabilities[a]<.70],['LOW_SPEECH_PROBABILITY',n.q_speech.probabilities[s]<.70],['UNCLEAR_ACTION_LABEL',a==='unclear'],['UNCLEAR_SPEECH_LABEL',s==='unclear']];
    var low=parts.some(function(v){return v[1];});
    parts.forEach(function(v){preds.push({id:v[0],condition_met:v[1],eligible:context===null});});
    preds.push({id:'MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS',condition_met:low,eligible:context===null});
    var scam=n.q_scam.probabilities.yes,press=n.q_pressure.probabilities.yes,aux=!!(f.pressure_cue&&(scam>=.70||press>=.70));
    var conflict=a==='none'&&(scam>=.70||(press>=.70&&f.pressure_cue)),eligible=context===null&&!low;
    preds.push({id:'CONFLICTING_MODEL_QUESTIONS',condition_met:!!conflict,eligible:eligible});
    var branch=eligible&&!conflict;
    var anchor=(E.data.model.anchors[a]||[]).some(function(x){return new RegExp(x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'iu').test(text);});
    var anchored=branch&&s!=='informational'&&a!=='none';
    var branches=[
      ['AUX_COERCION_BLOCKS_INFORMATIONAL_CLEARANCE',s==='informational'&&aux,branch],
      ['MODEL_INFORMATIONAL_NOT_REQUEST',s==='informational'&&!aux,branch],
      ['NO_ACTION_CANDIDATE_NOT_SAFETY_CLEARANCE',a==='none',branch&&s!=='informational'],
      ['NO_GROUNDED_ACTION_ANCHOR',!anchor,anchored],
      ['AUX_COERCION_BLOCKS_WARNING_CLEARANCE',s==='negated_or_warning'&&aux,anchored&&anchor],
      ['MODEL_WARNING_NOT_REQUEST',s==='negated_or_warning'&&!aux,anchored&&anchor],
      ['MODEL_REPORTED_REQUEST',s==='reported_or_quoted',anchored&&anchor],
      ['MODEL_DIRECT_ACTION_ADVISORY',['transfer','otp','remote_install','personal_data'].indexOf(a)>=0,anchored&&anchor&&s!=='negated_or_warning'&&s!=='reported_or_quoted'],
      ['MODEL_DIRECT_CAUTION_ADVISORY',['transfer','otp','remote_install','personal_data'].indexOf(a)<0,anchored&&anchor&&s!=='negated_or_warning'&&s!=='reported_or_quoted']];
    branches.forEach(function(v){preds.push({id:v[0],condition_met:!!v[1],eligible:!!v[2]});});
    var base=context||(low?'MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS':conflict?'CONFLICTING_MODEL_QUESTIONS':branches.filter(function(v){return v[1]&&v[2];})[0][0]);
    var clear=['MODEL_INFORMATIONAL_NOT_REQUEST','NO_ACTION_CANDIDATE_NOT_SAFETY_CLEARANCE','MODEL_WARNING_NOT_REQUEST','MODEL_REPORTED_REQUEST','MODEL_DIRECT_CAUTION_ADVISORY'].indexOf(base)>=0;
    var ev=!!(n.q_evidence&&n.q_evidence.probabilities.no>=.70);
    preds.push({id:'MODEL_EVIDENCE_INSUFFICIENT',condition_met:ev,eligible:clear});
    var applied=[base].concat(ev&&clear?['MODEL_EVIDENCE_INSUFFICIENT']:[]);
    if(applied[applied.length-1]!==r.reason)fail('TRACE_FINAL_POLICY_DRIFT');
    return[preds,applied];
  }
  function draPredicates(n,r){
    var catalog=E.data.model.dra.action_options.filter(function(a){return ['HIGH','MID'].indexOf(E.data.model.dra.action_class[a])>=0;}).map(function(a){return'UNGROUNDED_'+a.toUpperCase();});
    catalog=catalog.concat(['CLEAN_IMPERATIVE_ACTION_CLAUSE','ALL_ACTION_CLAUSES_WARNED_OR_REPORTED','AUX_COERCION_WITH_PRESSURE_CUE','MODEL_EVIDENCE_DOUBT','PAUSE_WITHOUT_ANCHOR_DEMOTED']);
    var preds=catalog.map(function(k){return{id:k,condition_met:r.trace.indexOf(k)>=0,eligible:true};});
    var transfer=!!(n.q_evidence&&n.q_evidence.probabilities.no>0);
    preds.push({id:'DRA_EVIDENCE_TRANSFER_FACTOR',condition_met:transfer,eligible:!!n.q_evidence});
    return[preds,r.trace.concat(transfer?['DRA_EVIDENCE_TRANSFER_FACTOR']:[]).concat([r.reason])];
  }
  function trace(m,id,source,status,r,n,preds,applied,raw){
    n=n||{};preds=preds||[];applied=applied||[];
    var echo=raw&&raw.model, probs={};Object.keys(n).forEach(function(k){if(k[0]!=='_')probs[k]=n[k].probabilities;});
    return{schema_version:m.trace_schema_version,manifest_fingerprint:m.manifest_fingerprint,question_contract_sha256:m.question_contract_sha256,policy_id:id,
      model_status:status,inference_source:source,runtime:{expected_temperature:m.runtime.expected_temperature,temperature_source:m.runtime.temperature_source,
        temperature_observed_by_this_evaluator:false,model_attested:false,domain_calibration:'NOT_ESTABLISHED',client_probability_recalibration:'NONE',
        model_echo_status:echo===undefined||echo===null?'ABSENT':echo===m.runtime.model_id?'MATCH_UNAUTHENTICATED':'MISMATCH_UNAUTHENTICATED'},
      predicates:preds,condition_ids:preds.filter(function(p){return p.condition_met;}).map(function(p){return p.id;}),applied_rule_ids:applied,final_rule:r.reason,final_action:r.action,
      normalized_probabilities:probs,dropped_optional_questions:n._dropped_optional||[],evidence_spans:(r.evidence||[]).map(function(e){var v={};['start','end','kind','directness','origin'].forEach(function(k){if(k in e)v[k]=e[k];});return v;}),
      predicate_semantics:'CONDITION_TRUE_IS_NOT_RULE_APPLIED; eligibility respects current-turn priority',trace_scope:'CURRENT_TURN_ONLY_NO_SESSION_DECISION',raw_text_stored:false};
  }
  function evaluateCurrent(text,raw,id,options){
    id=id===undefined?'legacy':id;options=options||{};policy(id);
    var source=options.source===undefined?'MODEL_RESPONSE_UNATTESTED':options.source;
    if(['MODEL_RESPONSE_UNATTESTED','FIXTURE','SURROGATE','ON_DEVICE_NLP'].indexOf(source)<0)fail('UNSUPPORTED_INFERENCE_SOURCE');
    var m=executionManifest(),n=E.normalizeResponse(raw,E.data.model.spec,{optional:E.data.model.optional,order:E.data.model.spec_order});
    var r=id==='legacy'?E.advisory(text,raw,{source:source,threshold:.70}):E.decisionRelevantAdvisory(text,raw,{source:source});
    var pp=id==='legacy'?legacyPredicates(text,n,r):draPredicates(n,r);
    if(!r.probs){r.probs={};Object.keys(n).forEach(function(k){if(k[0]!=='_')r.probs[k]=n[k].probabilities;});}
    r.policy_id=id;r.manifest_fingerprint=m.manifest_fingerprint;r.execution_trace=trace(m,id,source,'VALID',r,n,pp[0],pp[1],raw);return r;
  }
  function unavailableCurrent(code,id){
    id=id===undefined?'legacy':id;policy(id);
    var known=['MODEL_NOT_CONFIGURED','INVALID_TIMEOUT_CONFIG','INVALID_MODEL_ENDPOINT','HTTPS_REQUIRED','REMOTE_TEXT_TRANSFER_NOT_CONSENTED','REMOTE_HOST_NOT_ALLOWLISTED','NON_PUBLIC_ENDPOINT_IP','DNS_FAILURE','REQUEST_TOO_LARGE','HTTP_STATUS_NOT_OK','UNEXPECTED_MODEL_CONTENT_TYPE','RESPONSE_TOO_LARGE','INVALID_RESPONSE_JSON','MODEL_ID_MISMATCH','MODEL_ID_ECHO_REQUIRED','INVALID_TEXT','EMPTY','CONTRACT_INVALID','LOCAL_APP_UNREACHABLE','V50_LOOPBACK_ONLY','REMOTE_RELAY_DISABLED_V50'];
    var v=String(code).split(':').pop(),safe=known.indexOf(v)>=0||/^MODEL_TRANSPORT_ERROR_(OSError|TimeoutError|ConnectionRefusedError|ConnectionResetError|gaierror|SSLError|URLError)$/.test(v)?v:'MODEL_OR_CONTRACT_FAILURE';
    var m=executionManifest(),r={source:'MODEL_UNAVAILABLE_OR_INVALID',model_attested:false,calibration_status:'NOT_ESTABLISHED',action:'ASK_HUMAN',reason:safe,message:E.messages.ASK_HUMAN,
      mode:'MODEL_UNAVAILABLE_OR_INVALID / NOT_ATTESTED',probs:{},evidence:[],grounding:'NONE',policy_id:id,manifest_fingerprint:m.manifest_fingerprint};
    r.execution_trace=trace(m,id,'MODEL_UNAVAILABLE_OR_INVALID','UNAVAILABLE_OR_INVALID',r,null,null,[safe]);return r;
  }
  function applyLocalLayers(text,result,options){
    options=options||{};var review=options.user_review===undefined?false:options.user_review,consent=options.consent==null?{}:options.consent;
    if(typeof text!=='string'||typeof review!=='boolean')fail('INVALID_LOCAL_LAYER_INPUT');
    if(Object.prototype.toString.call(consent)!=='[object Object]'||Object.keys(consent).some(function(k){return ['external_reputation','web_analysis'].indexOf(k)<0||typeof consent[k]!=='boolean';}))fail('INVALID_LOCAL_LAYER_CONSENT');
    var out=clone(result);if(['NO_STRONG_SIGNAL','CAUTION','ASK_HUMAN','PAUSE_AND_VERIFY'].indexOf(out.action)<0)fail('INVALID_LOCAL_LAYER_ACTION');
    var t=out.execution_trace;
    if(!t){t=trace(executionManifest(),out.policy_id||'legacy','LOCAL_OR_NLP_UPSTREAM','NOT_EVALUATED_BY_THIS_CONTRACT',out);t.trace_scope='LOCAL_POSTPROCESS_ONLY';t.upstream_evaluation_trace_available=false;out.execution_trace=t;}
    if(t.local_layers)fail('LOCAL_LAYERS_ALREADY_APPLIED');
    var steps=[],before=out.action;
    if(review&&before==='NO_STRONG_SIGNAL')Object.assign(out,{base_action:before,base_reason:out.reason,action:'ASK_HUMAN',reason:'USER_REQUESTED_REVIEW',message:E.messages.ASK_HUMAN});
    steps.push({id:'USER_REQUESTED_REVIEW',status:'EVALUATED',condition_met:review,before_action:before,after_action:out.action,applied:before!==out.action});
    before=out.action;
    var LG=root.LinkGuard;
    if(!LG&&typeof require==='function'){try{LG=require('./dmsg-linkguard.js');}catch(e){LG=null;}}
    var link,fusion,status;
    if(LG&&typeof LG.intake==='function'&&typeof LG.assessMessage==='function'&&typeof LG.fuse==='function'){
      link=LG.assessMessage(LG.intake(text,{consent:consent}));fusion=LG.fuse({policy_action:before},link);status='EVALUATED_OFFLINE';
    }else{
      link={overall:'SCAN_FAILED',urls:[],url_count:0,network_used:false,status:'NOT_AVAILABLE'};
      fusion={policy_action:before==='NO_STRONG_SIGNAL'?'ASK_HUMAN':before,base_action:before,escalated:before==='NO_STRONG_SIGNAL',escalation_reasons:before==='NO_STRONG_SIGNAL'?['LOCAL_LINKGUARD_NOT_AVAILABLE']:[],downgraded:false};status='NOT_AVAILABLE';
    }
    out.linkguard=link;out.linkguard_fusion=fusion;
    if(fusion.escalated)Object.assign(out,{base_action:before,base_reason:out.reason,action:fusion.policy_action,reason:fusion.escalation_reasons[0],message:E.messages[fusion.policy_action]});
    var summary={status:status,overall:link.overall,url_count:link.url_count,network_used:false,escalated:fusion.escalated,escalation_reasons:fusion.escalation_reasons.slice()};
    out.link_summary=summary;steps.push({id:'OFFLINE_LINKGUARD',status:status,before_action:before,after_action:out.action,applied:fusion.escalated,summary:clone(summary)});
    t.local_layers=steps;t.current_turn_policy_action=t.final_action;t.current_turn_policy_rule=t.final_rule;t.final_action=out.action;t.final_rule=out.reason;
    steps.filter(function(s){return s.applied;}).forEach(function(s){t.applied_rule_ids.push(s.id==='USER_REQUESTED_REVIEW'?s.id:out.reason);});return out;
  }
  return{executionManifest:executionManifest,evaluateCurrent:evaluateCurrent,unavailableCurrent:unavailableCurrent,applyLocalLayers:applyLocalLayers,questionSignature:signature};
});
