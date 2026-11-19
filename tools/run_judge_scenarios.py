"""Three local scenarios; --mode live never falls back to a fixture."""
from pathlib import Path
import argparse,json,sys,tempfile,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from arena.store import Arena
from arena.evidence import export_session,latency_summary,readiness
from integration import v51
from integration.v48 import bridge

class Controlled:
 def __init__(self,rows):self.rows=list(rows)
 def infer(self,text,*,question_payload=None):
  item=self.rows.pop(0)
  if item is None:raise bridge.ModelUnavailable('MODEL_TRANSPORT_ERROR_TimeoutError')
  return copy.deepcopy(item['raw']),0.

def run(mode,out):
 cases=json.loads((ROOT/'tests_data/v51/execution_cases.json').read_text(encoding='utf-8'))
 secret=next(x for x in cases if x['id']=='V50-AI-22');ordinary=next(x for x in cases if x['id']=='V50-AI-02')
 plans={'A_request':[secret],'B_retained_risk':[secret,ordinary],'C_failure_recovery':[None,secret]}
 reports=[];out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as d:
  for name,rows in plans.items():
   client=Controlled(rows) if mode=='controlled' else bridge.ModelClient()
   a=Arena(Path(d)/(name+'.db'),client=client,profile_id=v51.selected_profile());sid=a.start()['session_id']
   for i,row in enumerate(rows):
    # Live C does not manufacture a timeout. Injecting failures is a separate controlled experiment.
    a.evaluate(session_id=sid,version=i,request_id=name+'_'+str(i),text=(row or secret)['text'],synthetic_only=True)
   report=export_session(a,sid);report['scenario']=name;report['requested_mode']=mode
   from arena.evidence import digest
   report.pop('sha256');report['sha256']=digest(report)
   (out/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');reports.append(report)
  summary={'requested_mode':mode,'actual_live_identity_attested':False,'latency':latency_summary(reports),'readiness':readiness(reports),
           'failure_injection':'CONTROLLED_ONLY' if mode=='controlled' else 'NOT_INJECTED_OBSERVE_ACTUAL_RESPONSE'}
  (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps(summary,ensure_ascii=False))
 return reports
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['controlled','live'],required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.mode,Path(a.out))
