"""External check wrapper: no product writes and no direct network/model calls."""
import datetime,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
W=Path('/home/ljmpc12/Documents/hackton/20261028수_해커톤 준비_IteraGuard-20261104T055702Z-1-002/20261028수_해커톤 준비_IteraGuard/[v5.1] IteraGuard_DoubtMeter')
name,command=sys.argv[1],sys.argv[2:]
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
for key in ('V51_SPECIFIED_DEV_PROTOCOL','V51_SEMANTIC_DEV_PROTOCOL'):env.pop(key,None)
def snapshot():
 roots=['tests_v49','tests_v50','tests_v51','integration','arena','tools','configs','apps/shared','apps/web','apps/desktop']
 out={}
 for base in roots:
  for p in sorted((W/base).rglob('*')):
   if p.is_file() and p.suffix in {'.py','.js','.json','.html','.webmanifest'} and '__pycache__' not in p.parts and p.name!='assets.gen.js' and '/nlp/' not in p.as_posix():
    out[p.relative_to(W).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
 return out
before=snapshot();started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
log=HERE/(name+'.log')
with log.open('wb') as f:
 try:
  result=subprocess.run(command,cwd=W,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  code=result.returncode
 except subprocess.TimeoutExpired:code=124
output=log.read_text(errors='replace');after=snapshot()
meta={'name':name,'command':command,'cwd':str(W),'started_utc':started,'elapsed_s':round(time.monotonic()-t,3),'exit_code':code,'status':'PASS' if code==0 else 'FAIL','log':str(log),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'source_before':before,'source_after':after,'concurrent_changes':[p for p in before if before.get(p)!=after.get(p)],'real_model_calls':0,'validation24_accessed':False,'optional_development_replay':'ENV_UNSET'}
match=re.search(r'Ran (\d+) tests?',output)
if match:meta['tests_run']=int(match.group(1))
for key in ('tests','pass','fail','skipped'):
 match=re.search(r'^# '+key+r' (\d+)$',output,re.M)
 if match:meta['tap_'+key]=int(match.group(1))
meta['skip_lines']=[s for s in output.splitlines() if 'skipped ' in s or s.startswith('OK (skipped')]
(HERE/(name+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in meta.items() if k not in ('source_before','source_after')},ensure_ascii=False,indent=2))
if code:print(output[-18000:])
sys.exit(code)
