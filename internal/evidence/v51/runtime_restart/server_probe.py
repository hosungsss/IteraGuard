"""Launch the product module; count real bridge calls without changing its output."""
import datetime,json,os,runpy,sys,time
from pathlib import Path
W=Path(os.environ['RESTART_SOURCE_ROOT'])
sys.path.insert(0,str(W))
from integration.v48 import bridge
original=bridge.ModelClient.infer
AUDIT=Path(os.environ['RESTART_CALL_AUDIT'])
cycle=int(os.environ['RESTART_CYCLE'])
def append(value):
 with AUDIT.open('a',encoding='utf8') as f:
  f.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def instrumented(self,text,*,question_payload=None):
 ident=str(cycle)+'-'+str(time.time_ns())
 append({'event':'INFER_START','call_id':ident,'cycle':cycle,'pid':os.getpid(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'synthetic_only':True,'text':text,'question_payload':question_payload,'question_count':len(question_payload['questions']) if question_payload else None})
 try:
  raw,ms=original(self,text,question_payload=question_payload)
  append({'event':'INFER_RETURN','call_id':ident,'cycle':cycle,'pid':os.getpid(),'raw':raw,'latency_ms':ms,'model_echo':self.last_model_echo})
  return raw,ms
 except BaseException as e:
  append({'event':'INFER_ERROR','call_id':ident,'cycle':cycle,'pid':os.getpid(),'type':type(e).__name__})
  raise
bridge.ModelClient.infer=instrumented
sys.argv=['arena.server','--port','8783','--db',os.environ['RESTART_DB'],'--policy','legacy']
runpy.run_module('arena.server',run_name='__main__')
