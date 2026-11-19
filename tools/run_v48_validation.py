"""Local v4.8 release gates with explicit NOT_RUN external capability statuses."""
from pathlib import Path
import subprocess,sys,json,re,datetime,hashlib
root=Path(__file__).resolve().parents[1]
outdir=root/'internal/evidence/v48';outdir.mkdir(parents=True,exist_ok=True)
steps={
 'python_unittest':[sys.executable,'-m','unittest','discover','-s','dmsg/tests','-p','test*.py','-q'],
 'zoro_trace_synthetic':[sys.executable,'-m','unittest','tools/test_trace_v48.py','-q'],
 'js_domain_synthetic':['node','tools/test_domain_v48.js'],
 'python_js_conformance':['node','apps/conformance/run_conformance.js',str(outdir/'conformance.json')],
 'apk_signature_content':[sys.executable,'tools/verify_apk_v48.py','apps/dist/IteraGuard_DoubtMeter_v4_8_android_debug.apk'],
 'js_syntax_app':['node','--check','apps/web/app.js'],
 'js_syntax_domain':['node','--check','apps/shared/dmsg-domainintel.js'],
}
r={'version':'4.8','run_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'CURRENT_SOURCE_REAL_EXECUTION',
 'checks':{},'not_run':['REAL_ZORO_INFERENCE','MODEL_CHECKPOINT_ATTESTATION','ONCHAIN_RPC','COMPANY_REGISTRY','INDEPENDENT_SCAM_ACCURACY','ANDROID_DEVICE_INSTALL','NPU_ACCELERATION','DESKTOP_WINDOWS_MACOS_IOS_V48','THREE_PLATFORM_SKILL_INSTALL','FULL_BROWSER_HTTP_RUNTIME']}
for name,cmd in steps.items():
 try:
  proc=subprocess.run(cmd,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=140)
  (outdir/(name+'.log')).write_text(proc.stdout,'utf8')
  r['checks'][name]={'status':'PASS' if proc.returncode==0 else 'FAIL','exit_code':proc.returncode,'stdout_tail':proc.stdout[-500:]}
  m=re.search(r'Ran\s+(\d+)\s+tests',proc.stdout)
  if m:r['checks'][name]['tests']=int(m.group(1))
 except Exception as e:r['checks'][name]={'status':'BLOCKED','error':str(e)[:300]}
 r['checks'][name]['command']=cmd
r['overall']='PASS_LOCAL_GATES' if all(x['status']=='PASS' for x in r['checks'].values()) else 'BLOCKED_OR_FAIL'
(outdir/'VERIFICATION.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps({k:{'status':v['status'],'tests':v.get('tests')} for k,v in r['checks'].items()},ensure_ascii=False))
print('OVERALL',r['overall'])
sys.exit(0 if r['overall']=='PASS_LOCAL_GATES' else 1)
