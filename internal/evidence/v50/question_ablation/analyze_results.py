"""Read-only post-hoc analysis of the already frozen, completed ablation."""
import collections,hashlib,json,pathlib
O=pathlib.Path(__file__).resolve().parent
P=json.loads((O/'protocol.json').read_text())
D=json.loads((O/'comparison.json').read_text())
items={name:{(i['dataset'],i['id']):i for i in [json.loads(x) for x in (O/name/'results.jsonl').read_text().splitlines()]} for name in P['variant_order']}
rows={dataset:{r['id']:r for r in [json.loads(x) for x in pathlib.Path(info['path']).read_text().splitlines()]} for dataset,info in P['datasets'].items()}
head_metrics={}
for name,data in items.items():
 action=[];speech=[];both=[];confusions=[]
 for (dataset,c),i in data.items():
  if dataset!='AI25_new':continue
  r=rows[dataset][c];qa=i['normalized']['q_action']['choice'];qs=i['normalized']['q_speech']['choice'];la='none' if r['requested_action']=='outside_listed_categories' else r['requested_action'];ls=r['speech']
  if qa==la:action.append(c)
  if qs==ls:speech.append(c)
  if qa==la and qs==ls:both.append(c)
  if qa!=la or qs!=ls:confusions.append({'id':c,'requested_action_proposed':r['requested_action'],'mapped_action_label':la,'observed_action':qa,'speech_proposed':ls,'observed_speech':qs,'additional_actions':r['additional_requested_actions']})
 head_metrics[name]={'n':25,'action_label_match':len(action),'speech_label_match':len(speech),'joint_match':len(both),'confusions':confusions,'label_status':'AI_PROPOSED_NOT_INDEPENDENT_GROUND_TRUTH','warning':'Single main action score does not evaluate simultaneous secondary actions. Mapping outside_listed_categories to none is a development comparison, not silently adopted product ontology.'}
coupling={}
for name,target in [('action_only','q_action'),('speech_only','q_speech'),('evidence_only','q_evidence')]:
 coupling[name]={q:sum(i['status']=='VALID' and i['normalized'][q]['probabilities']!=items['baseline'][key]['normalized'][q]['probabilities'] for key,i in items[name].items()) for q in P['variants']['baseline'] if q!=target}
old=pathlib.Path(P['datasets']['V2_48']['path']).parent
oldreport=json.loads((old/'baseline_results.json').read_text())
previous={('AI25_previous' if ds=='AI25' else ds,i['id']):i for ds,s in oldreport['sets'].items() for i in s['items']}
same_probs=[];same_guidance=[]
for key,i in previous.items():
 fresh=items['baseline'][key]
 if i['status']=='VALID' and i['normalized']==fresh['normalized']:same_probs.append(key)
 if all(i[p]['action']==fresh[p]['action'] and i[p]['reason']==fresh[p]['reason'] for p in ('legacy','dra')):same_guidance.append(key)
# Blank reason labels differ by explicit harness status; only nonempty baseline reproduction matters.
oldprotocol=json.loads((old/'baseline_protocol.json').read_text())
modelmatches={pathlib.Path(p).name:h==oldprotocol['export_hashes'][pathlib.Path(p).name] for p,h in P['model_export_hashes'].items()}
status={'requests_planned':388,'actual_inference_requests':D['fresh_actual_model_calls'],'valid_responses':sum(s['valid'] for r in D['reports'].values() for s in r['sets'].values()),'failures':sum(s['failed'] for r in D['reports'].values() for s in r['sets'].values()),'blank_cases_without_inference':4,'provider_request_counter_delta':sum(r['server_request_count_delta'] for r in D['reports'].values()),'additional_combination_calls':0,'external_paid_api_calls':0,'independent_eval':False}
result={'status':status,'recommendation':'KEEP_BASELINE_QUESTIONS_NO_PROMOTION','screening_outcome':{n:c['development_screen'] for n,c in D['comparisons'].items()},'baseline_reproduction':{'old_nonempty':72,'identical_normalized_responses':len(same_probs),'same_policy_action_reason_nonempty':sum(previous[k]['status']=='VALID' for k in same_guidance),'model_export_hashes_match_prior':modelmatches},'new25_head_label_comparison':head_metrics,'untouched_question_probability_changes':coupling,'coupling_interpretation':'An input question-only ablation is not an isolated head perturbation. action/speech wording alters other heads; evidence-only left all six other heads identical in these97 calls. This observation is local, not a guarantee of model architecture.','recommendation_detail':[
 'action_only removes V47 DRA risky clearance but loses required pause on new V50-AI-22 (credential disclosure through link) and expected CAUTION on AI-JM-12; hold.',
 'speech_only gains11 policy-case expected matches but loses V33 original-policy PAUSE: direct_request probability0.712 to0.657 crosses unchanged0.70; hold.',
 'evidence_only gains14 policy-case expected matches and improves new25 DRA17to20, but turns V02 protective OTP warning ASK into unwanted CAUTION; hold under the predeclared both-policy no-loss screen.',
 'Do not run a combination selected after failures under a rewritten acceptance rule. No candidate passes this registered screen; product wording remains unchanged.',
 'This is not a finding that every partial change is unusable: evidence_only under original policy showed3 expected gains without observed lost matches. A policy-specific follow-up requires its own prospective criterion, not a retroactive promotion.'
 ],'persistent_problems':[
 {'id':'P01','case_ids':['V38','V50-AI-04','V50-AI-05'],'problem':'Legitimate transfers remain transfer actions. Action labels alone do not distinguish normal business from coercion. V38 DRA stays PAUSE in all variants; new normal transfers remain mostly ASK.'},
 {'id':'P02','case_ids':['V47','V50-AI-18'],'problem':'Indirect threat can predict none with uncertain speech. DRA can clear V47; action-only fixes that one case while introducing other regression.'},
 {'id':'P03','case_ids':['V50-AI-02','V50-AI-03','AI-JM-02'],'problem':'Harmless request is none plus direct_request; existing NONE_DIRECT_REQUEST_CONFLICT abstains even when model semantics are plausible. AI-JM-02 old INFORMATION annotation also conflates guidance and speech.'},
 {'id':'P04','case_ids':['V50-AI-19','V50-AI-20','V50-AI-21','V50-AI-22'],'problem':'Warnings/reports plus a new current demand and simultaneous actions spread mass or select quote/unclear. Single action pointer and fixed threshold retain gaps.'},
 {'id':'P05','case_ids':['V50-AI-11','V50-AI-12','AI-JM-16'],'problem':'Original evidence-sufficiency wording rejects complete no-action notices. Evidence-only reduces that failure but must be checked with the selected downstream policy.'}
 ],'limitations':[
 'All98 unique cases are authored synthetic development material; first use of new25 is not independent validation. Labels and harms need human review before release claims.',
 'Expected-match is rubric compatibility, not real-world fraud accuracy. V2 has many multi-allowed outcomes and blankV34; do not compare its fraction directly with stricter AI25.',
 'New25 unknown-risk cases3 are excluded from benign/risky denominators and reported separately. NO_STRONG_SIGNAL is not a safety verdict.',
 'Both policies consume each identical parsed response, without changing0.70 threshold, DRA cost matrix, tokenizer, orT1.52. Temperature is actual serving config, not established calibration.',
 'No whole arena/LinkGuard/session pipeline, mobile deployment, actual financial action, NPU or third-party attestation is established by this experiment.',
 'Raw files contain model-client parsed JSON before typed normalization, not byte-for-byte HTTP responses. Transport failures would retain error codes because the existing client does not expose rejected raw bytes.',
 'Sequential warm-server block timing is descriptive; no randomization, repeated-seed uncertainty or production latency claim.',
 'Replay inputs preserve frozen code/data/candidate files; actual rerun needs a separately configured local model and these inputs. Model weights are not packaged.'
 ],'source_inputs_verified_unchanged':all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in P['protected_hashes'].items())}
(O/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':status,'baseline_reproduction':result['baseline_reproduction'],'new25_head_label_matches':{n:{k:v[k] for k in ('action_label_match','speech_label_match','joint_match')} for n,v in head_metrics.items()}},ensure_ascii=False))
