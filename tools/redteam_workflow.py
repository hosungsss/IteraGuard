"""Bounded adversarial probes; fixed responses, no real model calls."""
from pathlib import Path
import sys,json,tempfile,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.store import Arena
from arena.evidence import latency_summary
from tests_v54.test_workflow import Client,CASES,PROFILE

def probe():
 results=[]
 with tempfile.TemporaryDirectory() as d:
  c=Client();a=Arena(Path(d)/'x.db',client=c,profile_id=PROFILE);sid=a.start()['session_id']
  one=a.evaluate(session_id=sid,version=0,request_id='first',text='그 자료를 보내 주세요.',synthetic_only=True)
  secret=next(x for x in CASES if x['id']=='V50-AI-22');c.raw=secret['raw']
  two=a.evaluate(session_id=sid,version=1,request_id='second',text=secret['text'],synthetic_only=True)
  state=a.read(sid)
  results.append({'id':'OPEN_ASK_THEN_NEW_PAUSE','expected_open_tasks':2,'observed_open_tasks':sum(t['status']=='OPEN' for t in state['tasks']),
                  'new_risk_has_distinct_task':one['next_task']['id']!=two['next_task']['id'],'current_action':two['current_turn_action']})
  c.raw={'answers':{'bad':float('nan')}}
  try:
   bad=a.evaluate(session_id=sid,version=2,request_id='invalid',text='합성 입력',synthetic_only=True)
   results.append({'id':'NONFINITE_MODEL_RESPONSE','handled':bad['action']=='ASK_HUMAN','reason':bad['reason']})
  except Exception as e:results.append({'id':'NONFINITE_MODEL_RESPONSE','handled':False,'exception':type(e).__name__})
 rows=[{'events':[{'model_status':'VALID','provenance':{'pipeline_ms':1,'execution_source':'CONTROLLED_CLIENT'}}]},
       {'events':[{'model_status':'VALID','provenance':{'pipeline_ms':1000,'execution_source':'LOCAL_HTTP_MODEL_UNATTESTED'}}]}]
 results.append({'id':'LATENCY_SOURCE_MIXING','result':latency_summary(rows)})
 return {'mode':'CONTROLLED_ADVERSARIAL_PROBES','actual_model_calls':0,'findings':results}
if __name__=='__main__':
 result=probe();p=ROOT/'internal/evidence/current/redteam.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
