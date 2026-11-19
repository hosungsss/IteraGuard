"""v5.1 profile-bound current-turn execution; no hidden inference or risk release."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from integration import v50,v51_profiles as P
from integration.v48 import bridge
from integration.v51_policy import advisory as semantic_advisory
ROOT=Path(__file__).resolve().parents[1]
ContractError=bridge.ContractError

def _hash(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def _selection():return json.loads((ROOT/'configs/v51_release_selection.json').read_text())
def selected_profile(policy_id='legacy'):
 if policy_id not in ('legacy','dra'):raise ContractError('UNSUPPORTED_POLICY_ID')
 value=_selection()['default_profile_by_policy'][policy_id];P.profile(value,policy_id);return value

def execution_manifest():
 manifest=json.loads((ROOT/'configs/v51_contract.json').read_text());fingerprint=manifest.pop('manifest_fingerprint')
 if _hash(manifest)!=fingerprint:raise ContractError('V51_MANIFEST_FINGERPRINT_MISMATCH')
 base=v50.execution_manifest();reg=P.registry()
 if base['manifest_fingerprint']!=manifest['base_execution_manifest_fingerprint'] or reg['registry_fingerprint']!=manifest['profile_registry_fingerprint']:raise ContractError('V51_BASE_PROFILE_DRIFT')
 for rel,expected in manifest['source_hashes'].items():
  if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=expected:raise ContractError('V51_EXECUTION_SOURCE_DRIFT')
 if _selection()!=manifest['release_selection']:raise ContractError('V51_RELEASE_SELECTION_DRIFT')
 manifest['manifest_fingerprint']=fingerprint;return manifest

def request_binding(profile_id=None,policy_id='legacy'):
 ident=profile_id or selected_profile(policy_id);execution_manifest();return P.binding(ident,policy_id)

def question_payload(text,profile_id=None,policy_id='legacy'):
 return P.questions(text,profile_id or selected_profile(policy_id),policy_id)

def evaluate_current(text,raw,policy_id='legacy',*,profile_id=None,binding=None,source='MODEL_RESPONSE_UNATTESTED'):
 ident=profile_id or selected_profile(policy_id);manifest=execution_manifest();p=P.profile(ident,policy_id)
 if binding is None:raise ContractError('V51_REQUEST_BINDING_REQUIRED')
 P.validate_binding(binding,ident,policy_id)
 normalized=P.normalize_response(raw,ident,policy_id)
 original=deepcopy(raw);original['answers']={k:v for k,v in raw['answers'].items() if k in bridge.SPEC}
 base=v50.evaluate_current(text,original,policy_id,source=source)
 if 'q_request_scope' in p['response_schema']:
  out=semantic_advisory(text,raw,{'spec':p['response_schema'],'optional':p['optional_questions']});out['source']=source
 else:out=deepcopy(base)
 out.update(policy_id=policy_id,question_profile_id=ident,question_binding=deepcopy(binding),manifest_fingerprint=manifest['manifest_fingerprint'],product_version='5.1')
 preds=deepcopy(base['execution_trace']['predicates']);applied=list(base['execution_trace']['applied_rule_ids'])
 semantic=out.get('semantic_trace')
 if semantic:
  eligible=semantic['baseline_action']!='PAUSE_AND_VERIFY'
  for pred in semantic['predicates']:
   preds.append(dict(pred,eligible=eligible,layer='SEMANTIC_EXTENSION'))
   if eligible and pred['condition_met']:eligible=False
  if semantic['rule_id'] not in ['BASELINE_FALLBACK','PRESERVE_EXISTING_PAUSE']:applied.append('V51_'+semantic['rule_id'])
 trace=v50._trace(manifest,policy_id,source,'VALID',out,normalized,preds,applied,raw)
 trace.update(question_profile_id=ident,question_contract_sha256=binding['question_contract_sha256'],question_binding=deepcopy(binding),
   base_policy_action=base['action'],base_policy_rule=base['reason'],semantic_policy_id=out.get('semantic_policy_id','NONE_BASELINE_COMPARISON'))
 trace['predicate_semantics']='CONDITION_TRUE_IS_NOT_RULE_APPLIED; eligibility is layer-local and respects rule priority'
 if semantic:trace['semantic']=deepcopy(semantic)
 out['execution_trace']=trace
 return enrich_display(text,out)

def unavailable_current(code,policy_id='legacy',*,profile_id=None):
 ident=profile_id or selected_profile(policy_id);manifest=execution_manifest()
 out=v50.unavailable_current(code,policy_id);binding=P.binding(ident,policy_id)
 out.update(question_profile_id=ident,question_binding=binding,manifest_fingerprint=manifest['manifest_fingerprint'],product_version='5.1')
 trace=out['execution_trace'];trace.update(schema_version=manifest['trace_schema_version'],manifest_fingerprint=manifest['manifest_fingerprint'],question_contract_sha256=binding['question_contract_sha256'],question_profile_id=ident,question_binding=deepcopy(binding))
 return out

def enrich_display(text,out):
 from integration.v51_evidence import enrich_evidence
 return enrich_evidence(text,out)

def apply_local_layers(text,result,*,user_review=False,consent=None):
 out=v50.apply_local_layers(text,result,user_review=user_review,consent=consent)
 if 'evidence_display' not in out:out=enrich_display(text,out)
 trace=out.get('execution_trace')
 if trace is not None and 'evidence_display_trace' in out:trace['evidence_display']=deepcopy(out['evidence_display_trace'])
 return out
