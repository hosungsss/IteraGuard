"""Offline captured-response/fixture replay. No live model or performance claims."""
import copy,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration import v51,v50
from arena.store import Arena
rows=json.loads((ROOT/'tests_data/v51/execution_cases.json').read_text(encoding='utf8'))
records=[]
for row in rows:
 out=v51.evaluate_current(row['text'],row['raw'],profile_id='v51-specific-candidate',binding=v51.request_binding('v51-specific-candidate'))
 records.append(dict(case_id=row['id'],source='PACKAGED_TEST_RESPONSE_REPLAY',action=out['action'],reason=out['reason'],selected_action=out.get('selected_action'),selected_speech=out.get('selected_speech'),action_probability=out.get('action_probability'),speech_probability=out.get('speech_probability'),trace=out['execution_trace']))
# Controlled seven-question fixtures isolate the legacy gate, not the default 11-question policy.
r=copy.deepcopy(next(x for x in rows if x['id']=='V50-AI-22')['raw'])
r['answers']={k:v for k,v in r['answers'].items() if k in v50.bridge.SPEC}
for q,key,top in [('q_action','otp',.75),('q_speech','direct_request',2/3)]:
 opts=v50.bridge.SPEC[q]['options'];r['answers'][q]={'type':'choice','choice':key,'probabilities':{k:top if k==key else (1-top)/(len(opts)-1) for k in opts}}
for prob in [2/3,.71]:
 opts=list(r['answers']['q_speech']['probabilities']);r['answers']['q_speech']['probabilities']={k:prob if k=='direct_request' else (1-prob)/(len(opts)-1) for k in opts}
 out=v51.evaluate_current('인증번호를 알려주세요.',r,profile_id='v50-baseline',binding=v51.request_binding('v50-baseline'))
 records.append(dict(case_id='CONTROLLED_SPEECH_'+str(prob),source='SYNTHETIC_FIXTURE_NOT_MODEL',action=out['action'],reason=out['reason'],speech_probability=prob))
assert records[-2]['action']=='ASK_HUMAN'
assert records[-1]['action']=='PAUSE_AND_VERIFY'
secret=next(x for x in rows if x['id']=='V50-AI-22');ordinary=next(x for x in rows if x['id']=='V50-AI-02')
class Client:
 def infer(self,text,**kwargs):return copy.deepcopy(secret['raw'] if text==secret['text'] else ordinary['raw']),0.0
with tempfile.TemporaryDirectory() as d:
 a=Arena(Path(d)/'replay.sqlite3',client=Client(),profile_id='v51-specific-candidate');sid=a.start()['session_id']
 for i,row in enumerate([secret,ordinary]):
  out=a.evaluate(session_id=sid,version=i,request_id='replay-'+str(i),text=row['text'],synthetic_only=True)
  # Arena transport labels are overridden in evidence because this is an injected replay client.
  out['mode']='OFFLINE_RESPONSE_REPLAY_NOT_LIVE_MODEL';out['latency_ms']=None
  records.append(dict(case_id='SESSION_'+str(i),source='PACKAGED_TEST_RESPONSE_REPLAY',result=out))
 assert out['current_turn_action']=='NO_STRONG_SIGNAL' and out['action']=='ASK_HUMAN'
path=ROOT/'internal/evidence/v53/path_replay.json'
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps({'live_model_calls':0,'user_incident_reproduced':False,'records':records},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'cases':len(rows),'controlled_gate_cases':2,'session_turns':2,'live_model_calls':0,'status':'PASS'}))
