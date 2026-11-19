"""Candidate semantic policy; original response probabilities are never recalibrated.
New typed questions are required; old raw cannot be silently upgraded. Scope/evidence
are model proposals with local corroboration, not identity/safety certification.
"""
from __future__ import annotations
from copy import deepcopy
import json,re
from pathlib import Path
from integration.v48 import bridge
from prototype.typed_contract import normalize_response,ContractError
ROOT=Path(__file__).resolve().parents[1]

def _rules():return json.loads((ROOT/'configs/v51_semantic_rules.json').read_text())
def _contains(text,terms):
 lower=text.casefold();return any(x.casefold() in lower for x in terms)
def _active_clauses(text):
 return [c for c in bridge.clause_profile(text) if not c.flags.warning_cue and not c.flags.report_cue]

def advisory(text,raw,profile):
 rules=_rules();threshold=rules['threshold']
 normalized=normalize_response(raw,profile['spec'],optional=profile.get('optional',[]))
 required=rules['required_new_questions']
 if any(q not in normalized for q in required):raise ContractError('V51_REQUIRED_SEMANTIC_FIELD_MISSING')
 old=deepcopy(raw);old['answers']={k:v for k,v in raw['answers'].items() if k in bridge.SPEC}
 out=bridge.advisory(text,old,threshold=.70)
 before={'action':out['action'],'reason':out['reason']}
 scope=normalized['q_request_scope'];ps=scope['probabilities'];scope_label=scope['choice']
 exposure=normalized['q_current_exposure']['probabilities'];payment=normalized['q_payment_anomaly']['probabilities']
 current=ps['other_request']+ps['sensitive_request']
 flags=bridge.context_flags(text);clauses=bridge.clause_profile(text);active=_active_clauses(text)
 active_exposure=[c for c in active if _contains(text[c.start:c.end],rules['exposure_terms'])]
 # A payment sentence can use a noun absent from the legacy action vocabulary.
 # Currentness still requires the new typed scope AND anomaly question.
 payment_context=_contains(text,rules['payment_terms']) or bool(re.search(r'\d[\d,.]*\s*(?:만|천|억)?\s*원',text))
 exposure_context=_contains(text,rules['exposure_terms'])
 current_sensitive=exposure['yes']>=threshold and current>=threshold and bool(active_exposure)
 current_payment=payment['yes']>=threshold and current>=threshold and payment_context
 direct_exposure=[c for c in active_exposure if re.search(r'알려|입력|적어|보내|전송|제출|회신|읽어|넘겨|불러|올리|전달|촬영|설치|허용|권한|접속\s*코드|disclose|send|enter|install|grant|allow',text[c.start:c.end],re.I)]
 scoped_exposure=(current>=threshold and bool(direct_exposure) and exposure['no']<threshold)
 pay_clauses=[c for c in active if _contains(text[c.start:c.end],rules['payment_terms']) and re.search(r'송금|이체|입금|보내|내야|지불|결제|transfer|wire|pay',text[c.start:c.end],re.I)]
 explicit_anomaly=any(re.search(r'임시|보호용|안전\s*계좌|새(?:로)?|바뀌|변경|먼저|비밀|알리지|묻지',text[c.start:c.end],re.I) for c in pay_clauses)
 scoped_payment=(ps['sensitive_request']>=threshold and bool(pay_clauses) and payment['no']<threshold
                 and normalized['q_scam']['probabilities']['yes']>=threshold
                 and (explicit_anomaly or normalized['q_pressure']['probabilities']['yes']>=threshold))
 ev=normalized.get('q_evidence',{}).get('probabilities',{})
 ev_sufficient=bool(ev) and ev.get('no',1)<threshold
 no_current_sensitive=exposure['no']>=threshold and payment['no']>=threshold
 no_aux_coercion=normalized['q_scam']['probabilities']['no']>=threshold and normalized['q_pressure']['probabilities']['no']>=threshold
 other_ground=(_contains(text,rules['other_request_terms']) or flags.request_cue or bool(re.search(r'주세요|주십시오|주실|해\s*줘|알려|놓아|들어|적어|골라|답해',text)))
 specified=normalized.get('q_request_specified',{}).get('probabilities',{}).get('yes',0)>=threshold
 ordinary_scope=(scope_label=='other_request' and ps['other_request']>=threshold)
 specified_other=(specified and scope_label=='other_request' and out.get('selected_action')=='none' and out.get('selected_speech')=='direct_request'
                  and ps['sensitive_request']<threshold and ps['unclear']<threshold)
 redirect_cue=bool(re.search(r'(?:아래|첨부|해당|다음|안내한|보내드린)\s*(?:주소|페이지|사이트|링크)|접속|QR|큐알|오픈채팅|텔레그램',text,re.I))
 other_clear=((ordinary_scope or specified_other) and other_ground and not redirect_cue
              and no_current_sensitive and ev_sufficient and no_aux_coercion
              and not flags.action_mentioned and not flags.pressure_cue and not payment_context and not exposure_context
              and not re.search(r'https?://|www\.|[A-Za-z0-9.-]+\.(?:com|net|org|kr)(?:/|\b)',text,re.I))
 info_clear=(scope_label=='no_request' and ps['no_request']>=threshold and no_current_sensitive
             and ev_sufficient and no_aux_coercion and not flags.pressure_cue
             and out.get('selected_speech')=='informational' and not any(c.clean_imperative for c in clauses))
 acts=[c for c in clauses if c.flags.action_mentioned]
 warning_clear=(scope_label=='no_request' and ps['no_request']>=threshold and no_current_sensitive
                and ev_sufficient and out.get('selected_speech')=='negated_or_warning'
                and bool(acts) and all(c.flags.warning_cue or c.flags.report_cue for c in acts)
                and not any(c.clean_imperative for c in clauses))
 # Use whole-text forms so a quoted or negated segment cannot hide a new request
 # in the same sentence. These added branches only refine baseline abstention.
 text_form=text.casefold()
 bounded=rules.get('bounded_credential_context',{})
 contextual=(before['action']=='ASK_HUMAN' and no_current_sensitive and ev_sufficient
             and scope_label=='no_request' and current<threshold and not flags.pressure_cue
             and normalized['q_pressure']['probabilities']['yes']<threshold)
 credential_warning=bool(contextual and bounded.get('warning')
     and normalized['q_speech']['probabilities']['negated_or_warning']>=threshold
     and normalized['q_scam']['probabilities']['yes']<threshold
     and re.fullmatch(bounded['warning'],text_form))
 past_report=bool(contextual and bounded.get('report') and ps['no_request']>=threshold
     and out.get('selected_speech')=='reported_or_quoted'
     and re.fullmatch(bounded['report'],text_form))
 predicates=[('CURRENT_SENSITIVE_EXPOSURE',current_sensitive),('CURRENT_ANOMALOUS_PAYMENT',current_payment),
             ('SCOPED_SENSITIVE_REQUEST',scoped_exposure),('SCOPED_PAYMENT_CORROBORATION',scoped_payment),
             ('EXPLICIT_OTHER_REQUEST',other_clear),('EXPLICIT_INFORMATION_ONLY',info_clear),('EXPLICIT_PROTECTIVE_WARNING',warning_clear),
             ('EXPLICIT_CREDENTIAL_WARNING',credential_warning),('EXPLICIT_PAST_CREDENTIAL_REPORT',past_report)]
 applied='BASELINE_FALLBACK'
 if before['action']=='PAUSE_AND_VERIFY':applied='PRESERVE_EXISTING_PAUSE'
 else:
  for name,condition in predicates:
   if condition:
    action='PAUSE_AND_VERIFY' if name in ['CURRENT_SENSITIVE_EXPOSURE','CURRENT_ANOMALOUS_PAYMENT','SCOPED_SENSITIVE_REQUEST','SCOPED_PAYMENT_CORROBORATION'] else 'NO_STRONG_SIGNAL'
    if name=='EXPLICIT_PAST_CREDENTIAL_REPORT':action='CAUTION'
    out.update(action=action,reason='V51_'+name,message=bridge.MESSAGES[bridge.Action(action)]);applied=name;break
 out.update(policy_id='legacy',semantic_policy_id=rules['version'],semantic_baseline=before,
   semantic_trace={'schema_version':'dmsg-v51-semantic/1','baseline_action':before['action'],'baseline_reason':before['reason'],
     'rule_id':applied,'predicates':[{'id':k,'condition_met':bool(v)} for k,v in predicates],
     'request_scope':scope_label,'specified_request':specified,'indirect_redirect_cue':redirect_cue,'request_scope_probabilities':ps,'current_exposure_probabilities':exposure,
     'payment_anomaly_probabilities':payment,'active_exposure_spans':[{'start':c.start,'end':c.end} for c in active_exposure],
     'raw_text_stored':False,'is_semantic_proof':False},probs={k:v['probabilities'] for k,v in normalized.items() if not k.startswith('_')})
 return out
