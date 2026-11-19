import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from integration import v51,v50
from arena.store import Arena,Conflict
ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'tests_data/v51/execution_cases.json').read_text())
PROFILE='v51-specific-candidate'

class ExecutionTests(unittest.TestCase):
 def evaluate(self,row,review=False):
  out=v51.evaluate_current(row['text'],row['raw'],profile_id=PROFILE,binding=v51.request_binding(PROFILE))
  return v51.apply_local_layers(row['text'],out,user_review=review)
 def test_required_new_answers_cannot_use_old_raw(self):
  r=copy.deepcopy(CASES[0]);r['raw']['answers'].pop('q_request_specified')
  with self.assertRaises(v51.ContractError):self.evaluate(r)
 def test_mismatched_profile_response_binding_rejected(self):
  r=CASES[0]
  with self.assertRaises(v51.ContractError):v51.evaluate_current(r['text'],r['raw'],profile_id=PROFILE,binding=v51.request_binding('v50-baseline'))
 def test_missing_request_binding_rejected(self):
  r=CASES[0]
  with self.assertRaises(v51.ContractError):v51.evaluate_current(r['text'],r['raw'],profile_id=PROFILE)
 def test_policy_profile_pair_rejected(self):
  with self.assertRaises(v51.ContractError):v51.question_payload('문장',PROFILE,'dra')
 def test_redirect_request_is_not_ordinary_clearance(self):
  r=next(x for x in CASES if x['id']=='V13');out=self.evaluate(r)
  self.assertEqual(out['action'],'ASK_HUMAN');self.assertTrue(out['semantic_trace']['indirect_redirect_cue'])
 def test_harmless_request_vs_current_secret_demand(self):
  visit=self.evaluate(next(x for x in CASES if x['id']=='V50-AI-02'))
  secret=self.evaluate(next(x for x in CASES if x['id']=='V50-AI-22'))
  self.assertEqual(visit['action'],'NO_STRONG_SIGNAL');self.assertEqual(secret['action'],'PAUSE_AND_VERIFY')
 def test_semantic_trace_priority_matches_executed_rule(self):
  r=next(x for x in CASES if x['id']=='V50-AI-22');out=self.evaluate(r);seen=False
  for pred in out['execution_trace']['predicates']:
   if pred.get('layer')=='SEMANTIC_EXTENSION':
    if seen:self.assertFalse(pred['eligible'])
    if pred['eligible'] and pred['condition_met']:seen=True
  self.assertTrue(seen)
 def test_model_unavailable_never_fakes_success(self):
  out=v51.unavailable_current('MODEL_NOT_CONFIGURED',profile_id=PROFILE)
  self.assertEqual(out['action'],'ASK_HUMAN');self.assertEqual(out['question_profile_id'],PROFILE)
 def test_local_layers_cannot_run_twice(self):
  r=CASES[0];out=self.evaluate(r)
  with self.assertRaises(v51.ContractError):v51.apply_local_layers(r['text'],out)
 def test_original_policy_baseline_still_available(self):
  r=CASES[0];raw=copy.deepcopy(r['raw']);raw['answers']={k:v for k,v in raw['answers'].items() if k in v50.bridge.SPEC}
  old=v50.evaluate_current(r['text'],raw)
  new=v51.evaluate_current(r['text'],raw,profile_id='v50-baseline',binding=v51.request_binding('v50-baseline'))
  self.assertEqual((new['action'],new['reason']),(old['action'],old['reason']))
 def test_trace_contains_no_input_or_quote(self):
  out=self.evaluate(CASES[0])
  def walk(x):
   if isinstance(x,dict):
    for k,v in x.items():
     self.assertNotIn(k,{'text','quote','url','raw','original_evidence'});walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(out['execution_trace'])
 def test_python_js_whole_current_turn_pipeline(self):
  batch=[];expected=[]
  for r in CASES:
   for review in [False,True]:batch.append(dict(r,review=review));expected.append(self.evaluate(r,review))
  script="const C=require('./apps/shared/v51-contract.js');let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{const out=JSON.parse(s).map(r=>C.applyLocalLayers(r.text,C.evaluateCurrent(r.text,r.raw,'legacy',{profile_id:r.profile_id,binding:C.requestBinding(r.profile_id,'legacy')}),{user_review:r.review}));process.stdout.write(JSON.stringify(out));});"
  p=subprocess.run(['node','-e',script],input=json.dumps(batch,ensure_ascii=False),cwd=ROOT,text=True,capture_output=True,check=True)
  actual=json.loads(p.stdout)
  for row,a,b in zip(batch,expected,actual):self.assertEqual(a,b,(row['id'],row['review']))
 def test_arena_profile_bound_call_and_unresolved_risk_survives(self):
  secret=next(x for x in CASES if x['id']=='V50-AI-22');ordinary=next(x for x in CASES if x['id']=='V50-AI-02')
  class Client:
   def __init__(self):self.calls=[]
   def infer(self,text,*,question_payload=None):
    self.calls.append(question_payload);return copy.deepcopy(secret['raw'] if text==secret['text'] else ordinary['raw']),1.0
  with tempfile.TemporaryDirectory() as d:
   client=Client();a=Arena(Path(d)/'db.sqlite3',client=client,profile_id=PROFILE);s=a.start();sid=s['session_id']
   first=a.evaluate(session_id=sid,version=0,request_id='sensitive',text=secret['text'],synthetic_only=True)
   self.assertEqual(first['current_turn_action'],'PAUSE_AND_VERIFY');self.assertIn('q_request_specified',client.calls[0]['questions'])
   closed=a.close(session_id=sid,version=1,request_id='close',synthetic_only=True);self.assertTrue(closed['prior_pause'])
   reopened=a.reopen(session_id=sid,version=2,request_id='reopen',synthetic_only=True);self.assertTrue(reopened['prior_pause'])
   last=a.evaluate(session_id=sid,version=3,request_id='ordinary',text=ordinary['text'],synthetic_only=True)
   self.assertEqual(last['current_turn_action'],'NO_STRONG_SIGNAL');self.assertEqual(last['action'],'ASK_HUMAN')
   self.assertEqual(last['question_profile_id'],PROFILE)
   with a.connect() as db:
    stored=' '.join(r[0] for r in db.execute('SELECT result FROM events'))
   self.assertNotIn(secret['text'],stored);self.assertNotIn('original_evidence',stored);self.assertNotIn('"quote"',stored)
if __name__=='__main__':unittest.main()
