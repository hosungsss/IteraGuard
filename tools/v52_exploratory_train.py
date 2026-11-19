"""EXPLORATORY ONLY: train a five-feature logistic model on existing AI-authored
synthetic development labels. These are neither independent gold nor a future
fraud event probability; never promote the artifact or copy it into Android.
"""
from __future__ import annotations
import argparse,json,random
from collections import Counter,defaultdict
from pathlib import Path
from integration.v52_decision_sandbox import FitRow, SandboxError, extract_features,fit_exploratory_logistic
ROOT=Path(__file__).resolve().parents[1]
SOURCE=[("AI36_development","data/v51_development36.jsonl"),("AI25_new","data/v50_ai_development25.jsonl")]
RAW=ROOT/'internal/evidence/v51/experiments/stage5_specified_candidate/specified_raw.jsonl'

def run():
 annotated={}
 for dataset,path in SOURCE:
  for line in (ROOT/path).read_text(encoding='utf-8').splitlines():
   x=json.loads(line)
   if x.get('split') != 'development' or x.get('independent_eval') is not False or x.get('authorship') != 'AI_GENERATED':
    raise SandboxError('UNEXPECTED_SOURCE_LABEL_PROVENANCE')
   annotated[(dataset,x['id'])]=x
 rows=[];unavailable=[]
 for line in RAW.read_text(encoding='utf-8').splitlines():
  x=json.loads(line);key=(x['dataset'],x['id'])
  if key not in annotated:continue
  a=annotated[key]
  if type(a.get('pause_required')) is not bool:raise SandboxError('UNKNOWN_LABEL')
  try:f=extract_features(x['raw'])
  except SandboxError as e:unavailable.append({'id':x['id'],'reason':str(e)});continue
  rows.append(FitRow(x['id'],x['dataset']+':'+a['family_id'],'development','AI_AUTHORED_SYNTHETIC',f,int(a['pause_required'])))
 if len(rows)<10:raise SandboxError('TOO_FEW_DEVELOPMENT_CASES')
 fam=defaultdict(list)
 for r in rows:fam[r.family_id].append(r)
 if len(fam)<5:raise SandboxError('INSUFFICIENT_FAMILIES')
 random.Random(51).shuffle(groups:=list(fam))
 fold={g:i%5 for i,g in enumerate(groups)}
 out=[]
 for i in range(5):
  test=[r for r in rows if fold[r.family_id]==i]
  train=[r for r in rows if fold[r.family_id]!=i]
  model=fit_exploratory_logistic(train)
  for r in test:out.append({'case_id':r.case_id,'family_id':r.family_id,'fold':i,'label':r.label,
          'logistic_oof':model.score(r.features),'q_scam_noul':r.features[0]})
 if len(out)!=len(rows):raise SandboxError('GROUP_FOLD_MISMATCH')
 def brier(key):return sum((o[key]-o['label'])**2 for o in out)/len(out)
 result={'schema_version':'iteraguard-v52-exploratory/1','data_status':'AI_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',
         'independent_human_labels':'NOT_RUN','target_label':'PAUSE_REQUIRED_AS_ANNOTATED_BY_AI_NOT_REAL_FRAUD',
         'model_mode':'EXPLORATORY_GROUP_FOLD','n':len(rows),'families':len(fam),
         'class_counts':dict(Counter(r.label for r in rows)),
         'cross_family_5fold':{'logistic_oof_brier':brier('logistic_oof'),'raw_q_scam_brier_ILL_DEFINED_AS_EVENT':brier('q_scam_noul'),
            'note':'Q_SCAM is not a fraud probability; comparison is illustrative only'},
         'unavailable_raw':unavailable,'training_data_leakage_notice':'Previous releases used these cases; not untouched holdout',
         'status':'EXPLORATORY_ONLY_NO_PRODUCTION_PROMOTION','android_model_retrained':False,
         'domain_calibrated':False,'model_identity_attested':False,
         'case_id_only_oof':[{'id':o['case_id'],'fold':o['fold']} for o in out]}
 return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--acknowledge-ai-synthetic',action='store_true');ap.add_argument('--output')
 args=ap.parse_args()
 if not args.acknowledge_ai_synthetic:raise SystemExit('DENIED: explicit --acknowledge-ai-synthetic required')
 result=run();s=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 if args.output:Path(args.output).write_text(s,encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('case_id_only_oof','unavailable_raw')},ensure_ascii=False,indent=2))
