"""Append-only, local Zoro experiments; frozen questions, input hashes and evaluator sources.
No retries or automatic promotion. AI-authored evaluation is not independent human evaluation.
"""
from __future__ import annotations
import argparse,copy,datetime,hashlib,json,os,shutil,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration.v48 import bridge
from prototype.typed_contract import normalize_response

def h(p):
 s=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):s.update(b)
 return s.hexdigest()
def dump(p,d):
 with Path(p).open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]
def identity():
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open('http://127.0.0.1:8008/v1/models',timeout=10) as r:d=json.load(r)
 m=d['models'][0]
 if m['temperature']!=1.52 or m['dtype']!='bfloat16':raise RuntimeError('RUNTIME_CHANGED')
 return d

def prepare(a):
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 if (out/'protocol.json').exists():raise FileExistsError('Frozen output already exists')
 profiles=json.loads(Path(a.profiles).read_text());datasets={}
 for ds in a.dataset:
  label,path=ds.split('=',1);p=Path(path).resolve();rr=rows(p)
  if len({r['id'] for r in rr})!=len(rr):raise ValueError('Duplicate case ID')
  if any(not isinstance(r.get('text'),str) or len(r['text'])>2000 for r in rr):raise ValueError('Invalid text')
  datasets[label]={'path':str(p),'sha256':h(p),'n':len(rr),'nonempty':sum(bool(r['text'].strip()) for r in rr)}
 model=Path(a.model_dir).resolve()
 model_hashes={n:h(model/n) for n in ['head.pt','config.json','model.safetensors','tokenizer.json','tokenizer_config.json']}
 sources=[p,Path(__file__).resolve(),ROOT/'vendor/dmsg/prototype/model_bridge.py',ROOT/'vendor/dmsg/prototype/typed_contract.py',ROOT/'vendor/dmsg/prototype/context_guard.py']
 for name in ['integration/v51_policy.py','configs/v51_semantic_rules.json']:
  if (ROOT/name).exists():sources.append(ROOT/name)
 protected={str(p):h(p) for p in sources};protected[str(Path(a.profiles).resolve())]=h(Path(a.profiles))
 snapshots={}
 for source,expected in protected.items():
  src=Path(source)
  try:rel=src.relative_to(ROOT)
  except ValueError:rel=Path('external')/src.name
  dst=out/'source_snapshot'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);snapshots[source]=str(dst.relative_to(out))
 protocol={'registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runner_revision':'v51-frozen-local-2','datasets':datasets,'profiles':profiles,'model_dir':str(model),'model_hashes':model_hashes,'sources':protected,'source_snapshots':snapshots,'model_id':'trillionlabs/Zoro-1','endpoint':'http://127.0.0.1:8008/v1/systemone','temperature':1.52,'dtype':'bfloat16','actual_calls_planned':sum(d['nonempty'] for d in datasets.values())*len(profiles),'acceptance':{'shipping_policy':'legacy or explicitly versioned semantic-v51 bundle; DRA baseline separate','no_new_risky_or_unknown_clear':True,'no_new_required_pause_miss':True,'no_new_benign_pause':True,'no_lost_allowed_outcome':True,'must_improve_unnecessary_ask_and_must_pause_for_final_v51':True,'old_results_not_retroactively_promoted':True,'independent_human_evaluation':False},'failure_policy':'No retry; save parsed raw before normalization. Errors remain explicit ASK_HUMAN. Empty input has no model call. Never send ID/labels/rationale to model.'}
 dump(out/'protocol.json',protocol)
 print(json.dumps({'prepared':str(out),'calls':protocol['actual_calls_planned'],'datasets':{k:v['n'] for k,v in datasets.items()},'profiles':list(profiles)}),flush=True)

def score(text,raw,profile):
 if profile.get('evaluator','legacy')=='legacy':return bridge.advisory(text,raw,threshold=.70)
 if profile['evaluator']=='semantic-v51':
  from integration.v51_policy import advisory
  return advisory(text,raw,profile)
 raise ValueError('Unknown evaluator')

def run(a):
 out=Path(a.output);pr=json.loads((out/'protocol.json').read_text())
 for p,expected in pr['sources'].items():
  if h(p)!=expected:raise RuntimeError('SOURCE_CHANGED:'+p)
 for d in pr['datasets'].values():
  if h(d['path'])!=d['sha256']:raise RuntimeError('DATA_CHANGED')
 for n,expected in pr['model_hashes'].items():
  if h(Path(pr['model_dir'])/n)!=expected:raise RuntimeError('MODEL_CHANGED:'+n)
 if (out/'runtime_before.json').exists():raise FileExistsError('No hidden resume/retry')
 before=identity()
 if before['models'][0]['run']!=pr['model_dir']:raise RuntimeError('WRONG_LOCAL_MODEL')
 dump(out/'runtime_before.json',before)
 os.environ.update(DMSG_MODEL_ENABLED='1',DMSG_SYSTEMONE_ENDPOINT=pr['endpoint'],DMSG_MODEL_ID=pr['model_id'],DMSG_SEND_MODEL_FIELD='1',DMSG_REQUIRE_MODEL_ECHO='1',DMSG_MODEL_TIMEOUT_S='30')
 client=bridge.ModelClient();calls=0;errors=0
 for name,p in pr['profiles'].items():
  rawpath=out/(name+'_raw.jsonl');resultpath=out/(name+'_results.jsonl');count=0
  with rawpath.open('x',encoding='utf8') as rf,resultpath.open('x',encoding='utf8') as of:
   for ds,d in pr['datasets'].items():
    for row in rows(d['path']):
     text=row['text'];event={'id':row['id'],'dataset':ds,'profile':name,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};raw=None
     if not text.strip():event.update(status='EMPTY_NO_INFERENCE',latency_ms=None)
     else:
      calls+=1;count+=1
      try:
       raw,ms=client.infer(text,question_payload={'state':text,'questions':copy.deepcopy(p['questions'])})
       event.update(status='PARSED_NOT_AUTHENTICATED',raw=raw,latency_ms=ms)
      except Exception as ex:event.update(status='PROVIDER_ERROR',error=type(ex).__name__+':'+str(ex),latency_ms=None)
     rf.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n');rf.flush();os.fsync(rf.fileno())
     result={'id':row['id'],'dataset':ds,'profile':name,'latency_ms':event['latency_ms']}
     if raw is None:result.update(status=event['status'],action='ASK_HUMAN',reason=event.get('error','EMPTY'))
     else:
      try:
       normalize_response(raw,p.get('spec',bridge.SPEC),optional=p.get('optional',list(bridge.OPTIONAL_QUESTIONS)))
       result.update(status='VALID',**score(text,raw,p))
      except Exception as ex:result.update(status='CONTRACT_OR_POLICY_ERROR',action='ASK_HUMAN',reason=type(ex).__name__+':'+str(ex))
     if result['status'] not in ['VALID','EMPTY_NO_INFERENCE']:errors+=1
     of.write(json.dumps(result,ensure_ascii=False,allow_nan=False)+'\n');of.flush()
     if count and count%10==0:print(json.dumps({'profile':name,'calls':count,'total_calls':calls,'errors':errors}),flush=True)
  print(json.dumps({'profile_done':name,'calls':count,'total_calls':calls,'errors':errors}),flush=True)
 after=identity();dump(out/'runtime_after.json',after)
 dump(out/'run_summary.json',{'actual_calls':calls,'errors':errors,'provider_counter_delta':after['models'][0]['batches']['requests']-before['models'][0]['batches']['requests'],'independent_human_evaluation':False})
 print(json.dumps({'finished':True,'calls':calls,'errors':errors}),flush=True)

def metrics(rr,items):
 by={r['id']:r for r in items};assert len(by)==len(items)==len(rr)
 tests={'expected_match':lambda r,a:a in r['expect'],'ask':lambda r,a:a=='ASK_HUMAN','benign_ask':lambda r,a:r['risky'] is False and a=='ASK_HUMAN','unnecessary_benign_ask':lambda r,a:r['risky'] is False and a=='ASK_HUMAN' and a not in r['expect'],'risky_clear':lambda r,a:r['risky'] is True and a=='NO_STRONG_SIGNAL','unknown_clear':lambda r,a:r['risky'] is None and a=='NO_STRONG_SIGNAL','benign_pause':lambda r,a:r['risky'] is False and a=='PAUSE_AND_VERIFY','pause_missed':lambda r,a:r.get('pause_required',r['expect']==['PAUSE_AND_VERIFY']) and a!='PAUSE_AND_VERIFY'}
 ids={k:[r['id'] for r in rr if test(r,by[r['id']]['action'])] for k,test in tests.items()}
 return {'n':len(rr),'benign_n':sum(r['risky'] is False for r in rr),'pause_required_n':sum(r.get('pause_required',r['expect']==['PAUSE_AND_VERIFY']) for r in rr),'counts':{k:len(v) for k,v in ids.items()},'ids':ids}

def analyze(a):
 out=Path(a.output);pr=json.loads((out/'protocol.json').read_text());report={}
 for name in pr['profiles']:
  items=rows(out/(name+'_results.jsonl'));report[name]={}
  for ds,d in pr['datasets'].items():report[name][ds]=metrics(rows(d['path']),[i for i in items if i['dataset']==ds])
 dump(out/'metrics.json',report)
 for n,x in report.items():
  for ds,m in x.items():print(json.dumps({'profile':n,'dataset':ds,**m['counts'],'n':m['n']},ensure_ascii=False),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);sp=ap.add_subparsers(dest='cmd',required=True)
 pp=sp.add_parser('prepare');pp.add_argument('--profiles',required=True);pp.add_argument('--dataset',action='append',required=True);pp.add_argument('--model-dir',required=True);pp.add_argument('--output',required=True)
 for n in ['run','analyze']:sp.add_parser(n).add_argument('--output',required=True)
 a=ap.parse_args();globals()[a.cmd](a)
