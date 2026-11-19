/* Port of integration/v51_policy.py. Offline candidate, never a safety proof. */
(function(root,factory){
  var E=root.DMSG_V51_BASE_ENGINE||(typeof require==='function'?require('./v51-base-engine.js'):null);
  var D=root.DMSG_V51_RULE_DATA||(typeof require==='function'?(require('./v51-semantic-data.js'),root.DMSG_V51_RULE_DATA):null);
  var api=factory(E,D);root.DMSG_V51_SEMANTIC=api;
  if(typeof module==='object'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(E,D){
  'use strict';
  if(!E||!D)throw new Error('V51_SEMANTIC_DATA_MISSING');
  var rules=D.rules, money=new RegExp(D.regex.payment_amount,'u'), url=new RegExp(D.regex.url,'iu');
  var exposureVerb=new RegExp(D.regex.direct_exposure,'iu'),paymentVerb=new RegExp(D.regex.payment_verb,'iu');
  var anomaly=new RegExp(D.regex.explicit_anomaly,'iu');
  var otherVerb=new RegExp(D.regex.other_request,'u');
  var redirect=new RegExp(D.regex.indirect_redirect,'iu');
  function fail(code){var e=new Error(code);e.name='ContractError';e.code=code;throw e;}
  function fold(text){return Array.from(text).map(function(c){return D.casefold_map[c]===undefined?c:D.casefold_map[c];}).join('');}
  function contains(text,terms){var lower=fold(text);return terms.some(function(x){return lower.indexOf(fold(x))>=0;});}
  function advisory(text,raw,profile){
    var threshold=rules.threshold;
    var n=E.normalizeResponse(raw,profile.spec,{optional:profile.optional||[],order:Object.keys(profile.spec)});
    if(rules.required_new_questions.some(function(q){return !(q in n);}))fail('V51_REQUIRED_SEMANTIC_FIELD_MISSING');
    var old=Object.assign({},raw), answers={};
    Object.keys(raw.answers).forEach(function(k){if(Object.prototype.hasOwnProperty.call(E.data.model.spec,k))answers[k]=raw.answers[k];});
    old.answers=answers;
    var out=E.advisory(text,old,{threshold:.70});
    var before={action:out.action,reason:out.reason};
    var scope=n.q_request_scope,ps=scope.probabilities,label=scope.choice;
    var exposure=n.q_current_exposure.probabilities,payment=n.q_payment_anomaly.probabilities;
    var current=ps.other_request+ps.sensitive_request;
    var flags=E.contextFlags(text),clauses=E.clauseProfile(text),cp=Array.from(text);
    var active=clauses.filter(function(c){return !c.flags.warning_cue&&!c.flags.report_cue;});
    var activeExposure=active.filter(function(c){return contains(cp.slice(c.start,c.end).join(''),rules.exposure_terms);});
    var paymentContext=contains(text,rules.payment_terms)||money.test(text);
    var exposureContext=contains(text,rules.exposure_terms);
    var sensitive=exposure.yes>=threshold&&current>=threshold&&activeExposure.length>0;
    var anomalousPayment=payment.yes>=threshold&&current>=threshold&&paymentContext;
    var directExposure=activeExposure.filter(function(c){return exposureVerb.test(cp.slice(c.start,c.end).join(''));});
    var scopedExposure=current>=threshold&&directExposure.length>0&&exposure.no<threshold;
    var payClauses=active.filter(function(c){var piece=cp.slice(c.start,c.end).join('');return contains(piece,rules.payment_terms)&&paymentVerb.test(piece);});
    var explicitAnomaly=payClauses.some(function(c){return anomaly.test(cp.slice(c.start,c.end).join(''));});
    var scopedPayment=ps.sensitive_request>=threshold&&payClauses.length>0&&payment.no<threshold
      &&n.q_scam.probabilities.yes>=threshold&&(explicitAnomaly||n.q_pressure.probabilities.yes>=threshold);
    var ev=n.q_evidence?n.q_evidence.probabilities:{};
    var sufficient=Object.keys(ev).length>0&&(ev.no===undefined?1:ev.no)<threshold;
    var noSensitive=exposure.no>=threshold&&payment.no>=threshold;
    var noAux=n.q_scam.probabilities.no>=threshold&&n.q_pressure.probabilities.no>=threshold;
    var otherGround=contains(text,rules.other_request_terms)||flags.request_cue||otherVerb.test(text);
    var specified=(n.q_request_specified?n.q_request_specified.probabilities.yes:0)>=threshold;
    var ordinaryScope=label==='other_request'&&ps.other_request>=threshold;
    var specifiedOther=specified&&label==='other_request'&&out.selected_action==='none'&&out.selected_speech==='direct_request'
      &&ps.sensitive_request<threshold&&ps.unclear<threshold;
    var redirectCue=redirect.test(text);
    var otherClear=(ordinaryScope||specifiedOther)&&otherGround&&!redirectCue&&noSensitive&&sufficient&&noAux
      &&!flags.action_mentioned&&!flags.pressure_cue&&!paymentContext&&!exposureContext&&!url.test(text);
    var imperative=clauses.some(function(c){return c.clean_imperative;});
    var infoClear=label==='no_request'&&ps.no_request>=threshold&&noSensitive&&sufficient&&noAux&&!flags.pressure_cue
      &&out.selected_speech==='informational'&&!imperative;
    var acts=clauses.filter(function(c){return c.flags.action_mentioned;});
    var warningClear=label==='no_request'&&ps.no_request>=threshold&&noSensitive&&sufficient
      &&out.selected_speech==='negated_or_warning'&&acts.length>0
      &&acts.every(function(c){return c.flags.warning_cue||c.flags.report_cue;})&&!imperative;
    var predicates=[['CURRENT_SENSITIVE_EXPOSURE',sensitive],['CURRENT_ANOMALOUS_PAYMENT',anomalousPayment],
      ['SCOPED_SENSITIVE_REQUEST',scopedExposure],['SCOPED_PAYMENT_CORROBORATION',scopedPayment],
      ['EXPLICIT_OTHER_REQUEST',otherClear],['EXPLICIT_INFORMATION_ONLY',infoClear],['EXPLICIT_PROTECTIVE_WARNING',warningClear]];
    var applied='BASELINE_FALLBACK';
    if(before.action==='PAUSE_AND_VERIFY')applied='PRESERVE_EXISTING_PAUSE';
    else for(var i=0;i<predicates.length;i++){
      var name=predicates[i][0];
      if(predicates[i][1]){
        out.action=['CURRENT_SENSITIVE_EXPOSURE','CURRENT_ANOMALOUS_PAYMENT','SCOPED_SENSITIVE_REQUEST','SCOPED_PAYMENT_CORROBORATION'].indexOf(name)>=0?'PAUSE_AND_VERIFY':'NO_STRONG_SIGNAL';
        out.reason='V51_'+name;out.message=E.messages[out.action];applied=name;break;
      }
    }
    var probabilities={};Object.keys(n).forEach(function(k){if(k.charAt(0)!=='_')probabilities[k]=n[k].probabilities;});
    Object.assign(out,{policy_id:'legacy',semantic_policy_id:rules.version,semantic_baseline:before,
      semantic_trace:{schema_version:'dmsg-v51-semantic/1',baseline_action:before.action,baseline_reason:before.reason,
        rule_id:applied,predicates:predicates.map(function(p){return{id:p[0],condition_met:!!p[1]};}),
        request_scope:label,specified_request:specified,indirect_redirect_cue:redirectCue,request_scope_probabilities:ps,current_exposure_probabilities:exposure,
        payment_anomaly_probabilities:payment,active_exposure_spans:activeExposure.map(function(c){return{start:c.start,end:c.end};}),
        raw_text_stored:false,is_semantic_proof:false},probs:probabilities});
    return out;
  }
  return{advisory:advisory};
});
