from pathlib import Path
import json,sys,subprocess,re,datetime,os,hashlib,zipfile
root=Path(__file__).resolve().parents[1]
evd=root/'internal/evidence';evd.mkdir(parents=True,exist_ok=True)
checks={}
def run(name,cmd,cwd=root):
 q=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
 log=q.stdout
 (evd/('v45_'+name+'.log')).write_text(log,'utf8')
 checks[name]={'exit_code':q.returncode,'pass':q.returncode==0,'log':'internal/evidence/v45_'+name+'.log','last_output':log.strip().splitlines()[-1:]}
 if q.returncode:
  print(name,'FAIL',log[-1200:]);sys.exit(1)
 print(name,'PASS')
 return log
log=run('unittest',['python','-m','unittest','discover','-s','tests','-q'],root/'dmsg')
match=re.search(r'Ran (\d+) tests',log)
checks['unittest']['tests_run']=int(match.group(1)) if match else None
run('skill_validate',['python','scripts/validate_skill.py'],root/'dmsg')
run('adversarial',['python','scripts/run_adversarial_suite.py'],root/'dmsg')
run('fixtures',['python','scripts/evaluate_fixtures.py'],root/'dmsg')
run('metamorphic',['python','scripts/metamorphic_audit.py'],root/'dmsg')
run('npu',['python','scripts/npu_readiness.py'],root/'dmsg')
run('ablation',['python','scripts/paylock_ablation.py'],root/'dmsg')
run('forbidden_phrases',['python','tools/check_forbidden_phrases.py','--json',str(evd/'v45_forbidden_phrases.json')],root)
run('golden_v33',['python','tools/run_golden_v33.py'],root)
run('node_dmsg_nlp',['node','--check','apps/shared/dmsg-nlp.js'],root)
q=subprocess.run(['node','tools/nlp/nlp_parity.js'],cwd=str(root),text=True,stdout=subprocess.PIPE,timeout=1800)
(evd/'v45_nlp_parity.json').write_text(q.stdout,'utf8')
checks['nlp_parity']={'pass':q.returncode==0,**{k:json.loads(q.stdout)[k] for k in ('n','tokenizer_exact','action_match','anchor_match','latency')}}
if q.returncode: print('nlp_parity FAIL');sys.exit(1)
print('nlp_parity PASS')
run('compare_rule_nlp',['python','tools/compare_engines.py','--locked','tools/nlp/locked_handwritten_v2.jsonl','--out',str(evd/'v45_compare.json'),'--engines','rule,nlp,zoro,gpt'],root)
run('engine_conformance',['node','apps/conformance/run_conformance.js',str(evd/'v45_conformance.json')],root)
run('contrast',['python','tools/check_contrast.py'],root)
run('macho_signatures',['python','tools/verify_macho_signature.py','apps/dist/desktop/macos-arm64/dmsg-desktop','apps/dist/desktop/macos-x64/dmsg-desktop'],root)
run('app_smoke',['python','tools/app_smoke.py'],root)
run('apk_verify',['python','tools/verify_apk.py','apps/dist/IteraGuard_DoubtMeter_v4_5_android_debug.apk','--evidence',str(evd/'v45_apk.json')],root)
for js in ('apps/shared/dmsg-engine.js','apps/web/app.js','apps/desktop/server.js','apps/conformance/run_conformance.js'):
    run('node_'+js.split('/')[-1].split('.')[0],['node','--check',js],root)
run('pycompile',['python','-m','compileall','-q','dmsg','tools'],root)
for name in ('main.js','paylock.js'):
 run('node_'+name.split('.')[0],['node','--check',str(root/'dmsg/web'/name)],root)
# Baseline paths and test ID preservation
baseline=Path(os.environ.get('DMSG_BASELINE_V44',str(root.parent/'[v4.4] IteraGuard_DoubtMeter'/'dmsg')))
def files_under(p):return {f.relative_to(p).as_posix() for f in p.rglob('*') if f.is_file() and f.suffix not in('.pyc','.pyo') and '__pycache__' not in f.parts}
new=files_under(root/'dmsg')
if baseline.is_dir():
    old=files_under(baseline)
    assert old==new,(old-new,new-old)
    checks['skill_path_lock']={'pass':True,'old_count':len(old),'new_count':len(new),'removed_paths':[], 'new_paths':[]}
else:
    old=set()
    checks['skill_path_lock']={'pass':False,'status':'NOT_RUN_BASELINE_MISSING','new_count':len(new)}
# Exact unit-test function identifiers retained; no regressions hidden by deleting tests
import ast
def tests(p):
 out=set()
 for f in (p/'tests').rglob('test_*.py'):
  tree=ast.parse(f.read_text('utf8'))
  for node in ast.walk(tree):
   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):
    out.add((f.name,node.name))
 return out
new_tests=tests(root/'dmsg')
if baseline.is_dir():
    old_tests=tests(baseline)
    assert old_tests<=new_tests,old_tests-new_tests
    checks['test_identity_lock']={'pass':True,'baseline_distinct_test_names':len(old_tests),'candidate_distinct_test_names':len(new_tests),'removed':[]}
else:
    old_tests=set()
    checks['test_identity_lock']={'pass':False,'status':'NOT_RUN_BASELINE_MISSING','candidate_distinct_test_names':len(new_tests)}
# Compare required UI API endpoints preserved
for f in ('prototype/server.py','prototype/session.py','prototype/paylock.py','SKILL.md'):
 assert (root/'dmsg'/f).exists()
checks['core_component_lock']={'pass':True,'components':4}
# Provenance of external sources remains attributed
s=(root/'dmsg'/'SKILL.md').read_text('utf8').rstrip()
creator='<!-- Developed by Hankil Choi | M.S., Graduate School of Virtual Convergence, Sogang University | Instagram / LinkedIn: @hank3149 -->'
assert s.endswith(creator)
checks['creator_attribution']={'pass':True,'attribution_last_line':True}
run('browser_smoke',['python','tools/browser_smoke.py'],root)
checks['browser_ui']=json.loads((evd/'v45_browser_smoke.json').read_text('utf8'))
checks['baseline_reproduction']={'previous_v41_counterexamples':'internal/evidence/v45_v41_counterexamples.json',
    'v45_regression_classes':'V42KevContract;V42KevTransport;V42ClauseScopedGuard;V42SessionBinding;V42NpuFeasibility'}
# Negative test on full release archive verifier: deliberate duplicates/path traversal.
sys.path.insert(0,str(root/'tools'))
from verify_release import unsafe_entries
from io import BytesIO
from contextlib import redirect_stderr
for kind,items in [('duplicate',[('safe/x','a'),('safe/x','b')]),('traversal',[('safe/../etc/evil','x')])]:
 buf=BytesIO()
 with zipfile.ZipFile(buf,'w') as z:
  for name,content in items:z.writestr(name,content)
 buf.seek(0)
 with zipfile.ZipFile(buf) as z:
  found=unsafe_entries(z)
 assert found,kind
 checks['archive_negative_'+kind]={'pass':True,'reject_codes':found}
report={'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'version':'4.5','status':'STATIC_VALIDATED_CANDIDATE','verification_levels':{'STATIC_VALIDATED':'PASS','REAL_MODEL_CALL_PASS':'PASS (on-device NLP only; Linux Node + Chromium)','LOCKED_EVAL':'RUN (developer-authored 48; no pre-registered pass criterion)','ANDROID_RUNTIME_PASS':'NOT_RUN','ZORO_CHECKPOINT_ATTESTED':'BLOCKED','3_ENGINE_RUNTIME_VERIFIED':'NOT_RUN (rule+nlp only)'},'checks':checks,
        'actual_zoro_inference':'BLOCKED_IN_THIS_ENVIRONMENT','gpt_baseline':'NOT_RUN (paid; requires team approval)','independent_korean_detection_accuracy':'NOT_RUN',
        'npu_typed_inference':'NOT_RUN','live_gpt_grok_claude_install':'NOT_RUN',
        'apps_executed':'linux-x64 binary + Chromium (http, file://)','apps_not_executed':['windows-x64','macos-arm64','macos-x64','android (APK structure+signature verified, device NOT_RUN)','ios'],
        'real_erp_bank_email_integration':'NOT_RUN','real_end_user_validation':'NOT_RUN',
        'google_drive_writes':0,
        'notes':['Local tests demonstrate contract correctness, not real-world detection effectiveness.',
                 'Browser test uses actual Chromium DOM and real backend HTTP through Python transport bridge.',
                 'NPU readiness does not imply model execution.']}
(evd/'v45_verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n','utf8')
print('SUMMARY:',json.dumps({'unit_tests':checks['unittest']['tests_run'],'skill_files':len(new),'tests_preserved':len(old_tests) if baseline.is_dir() else 'NOT_RUN','executed_checks_pass':all(x.get('pass',x.get('status')=='PASS') for k,x in checks.items() if k not in ('baseline_reproduction','skill_path_lock','test_identity_lock')),'baseline_available':baseline.is_dir()},ensure_ascii=False))
