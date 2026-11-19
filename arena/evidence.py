"""Local evidence export. Exported metadata is not independent model attestation."""
from datetime import datetime,timezone
from copy import deepcopy
import hashlib,json,math

def digest(value):
 return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def export_session(arena,sid):
 state=arena.read(sid)
 if len(state['events']) > 500:raise ValueError('EXPORT_EVENT_LIMIT')
 events=[]
 for event in state['events']:
  fields=('event_type','request_id','version','current_turn_action','current_turn_reason','action','reason',
          'prior_pause','model_status','mode','latency_ms','provenance','task_disposition','observed_task_id',
          'resolved_retry_task_ids')
  row={k:deepcopy(event[k]) for k in fields if k in event}
  for key in ('next_task','related_task'):
   if key in event:row[key]={k:event[key][k] for k in ('id','type','status','observation')}
  events.append(row)
 report={'schema':'iteraguard-evidence/1','package_version':arena.manifest()['version'],
         'created_utc':datetime.now(timezone.utc).isoformat(),'session_id':sid,
         'context_scope':'CURRENT_TEXT_ONLY','raw_input_included':False,'model_identity_verified':False,
         'state_version':state['version'],'lifecycle':state['lifecycle'],'prior_pause':bool(state['prior_pause']),
         'tasks':[{k:t[k] for k in ('id','type','status','observation')} for t in state['tasks']],
         'events':events,'integrity_scope':'UNSIGNED_LOCAL_DIGEST_NOT_AUTHENTICATION'}
 report['sha256']=digest(report)
 return report

def validate_report(report):
 if type(report) is not dict:raise ValueError('REPORT_OBJECT_REQUIRED')
 unsigned={k:v for k,v in report.items() if k!='sha256'}
 if report.get('sha256')!=digest(unsigned):raise ValueError('EVIDENCE_DIGEST_MISMATCH')
 if report.get('schema')!='iteraguard-evidence/1':raise ValueError('UNKNOWN_SCHEMA')
 if report.get('model_identity_verified') is not False or report.get('raw_input_included') is not False:
  raise ValueError('UNSUPPORTED_ATTESTATION_OR_RAW_INPUT')
 events=report.get('events')
 if type(events) is not list or len(events)>500:raise ValueError('INVALID_EVENTS')
 versions=[];requests=set()
 for e in events:
  if type(e) is not dict or type(e.get('version')) is not int:raise ValueError('INVALID_EVENT_VERSION')
  versions.append(e['version'])
  rid=e.get('request_id')
  if type(rid) is not str or rid in requests:raise ValueError('DUPLICATE_OR_INVALID_REQUEST')
  requests.add(rid)
  if e.get('event_type')=='EVALUATE':
   p=e.get('provenance',{})
   if p.get('execution_source') not in {'CONTROLLED_CLIENT','LOCAL_HTTP_MODEL_UNATTESTED'}:raise ValueError('UNKNOWN_EXECUTION_SOURCE')
   if p.get('model_identity_verified') is not False or p.get('npu_execution_verified') is not False:raise ValueError('UNSUPPORTED_ATTESTATION')
   n=p.get('pipeline_ms')
   if type(n) not in (int,float) or not math.isfinite(n) or n<0:raise ValueError('INVALID_TIMING')
 if versions!=list(range(1,report.get('state_version',-1)+1)):raise ValueError('EVENT_SEQUENCE_MISMATCH')
 return True

def latency_summary(reports):
 groups={};excluded=0
 for r in reports:
  for e in r.get('events',[]):
   p=e.get('provenance',{});value=p.get('pipeline_ms');source=p.get('execution_source')
   if e.get('model_status')!='VALID' or source not in {'CONTROLLED_CLIENT','LOCAL_HTTP_MODEL_UNATTESTED'} or type(value) not in (int,float) or not math.isfinite(value) or value<0:
    excluded+=1;continue
   groups.setdefault(source,[]).append(value)
 output={}
 for source,values in groups.items():
  values.sort()
  output[source]={'n':len(values),'p50':values[math.ceil(.5*len(values))-1],'p95':values[math.ceil(.95*len(values))-1]}
 return {'metric':'server_pipeline_ms','groups':output,'excluded_events':excluded,
         'method':'nearest_rank','scope':'includes policy and task construction; excludes HTTP serialization/browser render/commit completion',
         'independent_benchmark':False}

def readiness(reports):
 errors=[]
 for i,r in enumerate(reports):
  try:validate_report(r)
  except (ValueError,TypeError,KeyError,OverflowError):errors.append({'report_index':i,'status':'INVALID_LOCAL_EVIDENCE'})
 return {'status':'NOT_SUBMISSION_READY','model_identity_verified':False,
         'evidence_validation_errors':errors,
         'model_events':sum(e.get('model_status')=='VALID' for r in reports for e in r['events']),
         'unresolved':['live_model_attestation','three_live_scenarios','slides_access','repository_access','license_review','public_demo_access'],
         'note':'Local evidence and a model name do not prove submission readiness or model identity.'}
