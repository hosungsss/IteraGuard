"""Four process cycles, at most four actual local model calls; no automatic retry."""
import datetime,hashlib,json,os,socket,sqlite3,subprocess,sys,time,urllib.error,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
W=Path('/home/ljmpc12/Documents/hackton/20261028수_해커톤 준비_IteraGuard-20261104T055702Z-1-002/20261028수_해커톤 준비_IteraGuard/[v5.1] IteraGuard_DoubtMeter')
BASE='http://127.0.0.1:8783';DB=HERE/'restart.sqlite3';AUDIT=HERE/'provider_calls.jsonl'
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}));proc=None;handles=[];calls=[];cycles=[];assertions=[]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
 p=HERE/name
 with p.open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def req(path,body=None):
 data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
 request=urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json','Origin':BASE})
 t=time.monotonic()
 try:
  with OP.open(request,timeout=40) as r:code,out=r.status,json.load(r)
 except urllib.error.HTTPError as r:code,out=r.code,json.load(r)
 item={'path':path,'request':body,'http_status':code,'response':out,'elapsed_s':round(time.monotonic()-t,4)}
 calls.append(item)
 with (HERE/'http_exchange.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(item,ensure_ascii=False,allow_nan=False)+'\n')
 return code,out
def must(condition,label):
 assertions.append({'check':label,'pass':bool(condition)})
 if not condition:raise AssertionError(label)
def audit():return [json.loads(l) for l in AUDIT.read_text().splitlines()] if AUDIT.exists() else []
def count():return sum(r['event']=='INFER_START' for r in audit())
def identity():
 with OP.open('http://127.0.0.1:8008/v1/models',timeout=10) as r:return json.load(r)
def stop():
 global proc
 if proc is not None:
  pid=proc.pid
  if proc.poll() is None:
   proc.terminate()
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
  cycles[-1]['exit_code_after_owned_stop']=proc.returncode;cycles[-1]['stopped_owned_pid']=pid
  proc=None
 for f in handles:f.close()
 handles.clear()
def start(cycle):
 global proc
 with socket.socket() as s:
  s.settimeout(.3)
  must(s.connect_ex(('127.0.0.1',8783))!=0,'port_8783_free_before_cycle_'+str(cycle))
 env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',DMSG_MODEL_ENABLED='1',DMSG_SYSTEMONE_ENDPOINT='http://127.0.0.1:8008/v1/systemone',DMSG_MODEL_ID='trillionlabs/Zoro-1',DMSG_SEND_MODEL_FIELD='1',DMSG_REQUIRE_MODEL_ECHO='1',DMSG_MODEL_TIMEOUT_S='30',RESTART_SOURCE_ROOT=str(W),RESTART_CALL_AUDIT=str(AUDIT),RESTART_CYCLE=str(cycle),RESTART_DB=str(DB))
 # The local model has no API credential requirement. Never inherit a token into evidence.
 env.pop('DMSG_MODEL_API_KEY',None)
 log=HERE/('server_cycle_'+str(cycle)+'.log');f=log.open('wb');handles.append(f)
 proc=subprocess.Popen([sys.executable,'-u',str(HERE/'server_probe.py')],cwd=W,env=env,stdout=f,stderr=subprocess.STDOUT)
 cycles.append({'cycle':cycle,'pid':proc.pid,'server_log':log.name,'db':DB.name})
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  if proc.poll() is not None:raise RuntimeError('OWN_SERVER_EXITED:'+str(proc.returncode))
  try:
   code,m=req('/api/manifest');must(code==200,'manifest_http_'+str(cycle));break
  except (urllib.error.URLError,ConnectionError,OSError):time.sleep(.15)
 else:raise RuntimeError('SERVER_START_TIMEOUT')
 profile=m['active_question_profile'];p=m['execution_manifest']['profiles'][profile]
 must(profile=='v51-specific-candidate' and len(p['required_questions'])+len(p['optional_questions'])==11,'selected_eleven_questions_cycle_'+str(cycle))
 cycles[-1]['manifest']=m
 return m
def control(sid,v,request):return {'session_id':sid,'version':v,'request_id':request,'synthetic_only':True}
def no_infer(path,body,status,expected=None,label='no_infer'):
 before=count();code,result=req(path,body);must(code==status,label+'_http');must(count()==before,label+'_no_extra_model_call')
 if expected is not None:must(result==expected,label+'_same_recorded_result')
 return result
started=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt={'status':'STARTED','started_utc':started,'source_root':str(W),'planned_real_calls_max':4,'process_cycles_planned':4,'provider_counter_is_exclusive':False,'provider_counter_note':'Root browser work may call the same provider concurrently; only this probe INFER_START records count own calls.','validation24_accessed':False,'product_source_modified':False,'inputs_are_ai_synthetic':True}
try:
 if DB.exists() or AUDIT.exists() or (HERE/'protocol.json').exists():raise FileExistsError('Append-only probe already exists; no hidden resume')
 rows=json.loads((W/'tests_data/v51/execution_cases.json').read_text());selected={r['id']:r for r in rows if r['id'] in ('V50-AI-02','V50-AI-22')}
 normal=selected['V50-AI-02']['text'];risk=selected['V50-AI-22']['text']
 files=['arena/store.py','arena/server.py','integration/v51.py','integration/v51_profiles.py','integration/v51_policy.py','integration/v51_evidence.py','configs/v51_contract.json','configs/v51_release_selection.json','tests_data/v51/execution_cases.json','vendor/dmsg/prototype/model_bridge.py']
 source_hashes={rel:h(W/rel) for rel in files}
 save('protocol.json',{'registered_utc':started,'own_actual_calls_planned':4,'restarts_planned':3,'process_cycles_planned':4,'port':8783,'fixture_ids':list(selected),'synthetic_inputs':{'risk':risk,'ordinary':normal},'source_hashes':source_hashes,'operations':'risk→close; restart/reopen→ordinary→retry→close repeated three times; closed new evaluation must409 without inference','model_endpoint':'http://127.0.0.1:8008/v1/systemone','model_id':'trillionlabs/Zoro-1','timeout_s':30,'send_model':True,'require_model_echo':True,'provider_delta_exclusive':False,'no_model_performance_tuning':True})
 before=identity();save('runtime_before.json',before)
 must(before['models'][0]['temperature']==1.52,'provider_temperature_1_52')
 sid=None;version=0;task_id=None;original_eval=None;first=None
 for cycle in range(4):
  print(json.dumps({'cycle':cycle,'state':'starting','own_calls':count()}),flush=True)
  start(cycle)
  if cycle==0:
   code,s=req('/api/start',{});must(code==200,'start_new_session');sid=s['session_id']
   original_eval=dict(control(sid,0,'initial-sensitive'),text=risk)
   n=count();code,first=req('/api/evaluate',original_eval)
   must(code==200 and count()==n+1,'one_actual_sensitive_call')
   must(first['current_turn_action']=='PAUSE_AND_VERIFY' and first['action']=='PAUSE_AND_VERIFY','sensitive_current_and_session_pause')
   must(first['question_profile_id']=='v51-specific-candidate','sensitive_profile_binding')
   task_id=first['next_task']['id'];version=first['version']
  else:
   code,s=req('/api/state?session_id='+sid);must(code==200 and s['version']==version and s['lifecycle']=='CLOSED_UNRESOLVED' and bool(s['prior_pause']),'persist_closed_risk_cycle_'+str(cycle))
   must(len(s['tasks'])==1 and s['tasks'][0]['id']==task_id,'persist_same_task_cycle_'+str(cycle))
   no_infer('/api/evaluate',original_eval,200,first,'cross_restart_original_retry_'+str(cycle))
   reopened=no_infer('/api/reopen',control(sid,version,'reopen-'+str(cycle)),200,label='reopen_'+str(cycle));version=reopened['version']
   must(reopened['prior_pause'] and reopened['risk_cleared'] is False,'reopen_does_not_clear_'+str(cycle))
   args=dict(control(sid,version,'ordinary-'+str(cycle)),text=normal)
   if cycle==1:args.update(task_id=task_id,observation='USER_REPORTS_CONFIRMED')
   n=count();code,out=req('/api/evaluate',args)
   must(code==200 and count()==n+1,'one_actual_ordinary_call_'+str(cycle))
   must(out['current_turn_action']=='NO_STRONG_SIGNAL' and out['action']=='ASK_HUMAN' and out['reason']=='PRIOR_RISK_UNRESOLVED','current_nss_session_hold_'+str(cycle))
   must(out['prior_pause'] and out['execution_trace']['session']['risk_cleared'] is False,'risk_retained_'+str(cycle))
   must(out['related_task']['id']==task_id and 'next_task' not in out,'reported_task_retained_without_duplicate_'+str(cycle))
   no_infer('/api/evaluate',args,200,out,'same_response_retry_'+str(cycle));version=out['version']
  closed=no_infer('/api/close',control(sid,version,'close-'+str(cycle)),200,label='close_'+str(cycle));version=closed['version']
  must(closed['lifecycle']=='CLOSED_UNRESOLVED' and closed['prior_pause'],'closed_risk_'+str(cycle))
  err=no_infer('/api/evaluate',dict(control(sid,version,'blocked-'+str(cycle)),text=normal),409,label='closed_evaluation_'+str(cycle))
  must(err['error']=='SESSION_CLOSED_UNRESOLVED','closed_error_'+str(cycle))
  if cycle==0:no_infer('/api/evaluate',original_eval,200,first,'initial_retry_while_closed')
  stop();print(json.dumps({'cycle':cycle,'state':'stopped','own_calls':count(),'version':version}),flush=True)
 must(count()==4,'exact_four_own_actual_model_calls')
 events=audit();returns=[x for x in events if x['event']=='INFER_RETURN']
 must(len(returns)==4 and not any(x['event']=='INFER_ERROR' for x in events),'four_successful_typed_returns')
 must(all(x['question_count']==11 for x in events if x['event']=='INFER_START'),'every_actual_call_used_eleven_question_payload')
 must(all(x['raw'].get('model')=='trillionlabs/Zoro-1' and x['model_echo']=='MATCH_UNAUTHENTICATED' for x in returns),'model_echo_matches_not_attestation')
 with sqlite3.connect(DB) as c:
  session=c.execute('SELECT version,prior_pause,lifecycle FROM sessions WHERE id=?',(sid,)).fetchone()
  event_rows=[json.loads(x[0]) for x in c.execute('SELECT result FROM events ORDER BY rowid')]
  task_rows=c.execute('SELECT id,status,observation FROM tasks').fetchall()
 encoded=json.dumps(event_rows,ensure_ascii=False)
 must(risk not in encoded and normal not in encoded,'db_events_no_synthetic_input_text')
 forbidden={'text','raw','quote','original_evidence','question_payload'};bad=[]
 def scan(x,p=''):
  if isinstance(x,dict):
   for k,v in x.items():
    if k in forbidden:bad.append(p+'/'+k)
    scan(v,p+'/'+k)
  elif isinstance(x,list):
   for i,v in enumerate(x):scan(v,p+'/'+str(i))
 scan(event_rows);must(not bad,'db_events_no_raw_or_quote_keys')
 dbbytes=DB.read_bytes();must(risk.encode() not in dbbytes and normal.encode() not in dbbytes,'sqlite_bytes_do_not_contain_inputs')
 must(session==(11,1,'CLOSED_UNRESOLVED'),'final_session_version_risk_lifecycle')
 must(len(event_rows)==11 and len(task_rows)==1,'duplicate_retries_create_no_events_or_tasks')
 must(task_rows[0][1:]==('REPORTED_COMPLETE','USER_REPORTS_CONFIRMED'),'reported_observation_persists_across_three_restarts')
 after=identity();save('runtime_after.json',after)
 receipt.update(status='PASS',session_id=sid,final_session={'version':session[0],'prior_pause':bool(session[1]),'lifecycle':session[2]},stored_event_count=len(event_rows),stored_task_count=len(task_rows),provider_counter_before=before['models'][0]['batches']['requests'],provider_counter_after=after['models'][0]['batches']['requests'],provider_counter_delta=after['models'][0]['batches']['requests']-before['models'][0]['batches']['requests'],source_hashes_unchanged=all(h(W/k)==v for k,v in source_hashes.items()),db_privacy_forbidden_keys=bad)
except BaseException as exc:
 receipt.update(status='FAIL',error_type=type(exc).__name__,error=str(exc));print(json.dumps({'status':'FAIL','error':str(exc)}),flush=True)
finally:
 stop();receipt.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),own_real_model_calls=count(),cycles=cycles,assertions=assertions,stopped_only_owned_popen=True,port=8783)
 with socket.socket() as s:s.settimeout(.3);receipt['final_port_closed']=s.connect_ex(('127.0.0.1',8783))!=0
 receipt['artifacts']={p.name:{'sha256':h(p),'bytes':p.stat().st_size} for p in HERE.iterdir() if p.is_file() and p.name!='receipt.json'}
 save('receipt.json',receipt)
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('cycles','assertions','artifacts')},ensure_ascii=False,indent=2),flush=True)
sys.exit(0 if receipt['status']=='PASS' else 1)
