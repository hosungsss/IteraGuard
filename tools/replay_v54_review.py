"""Replay previously inspected AI24 responses; development evidence, no new inference."""
import sys,json,hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from integration import v51,v51_policy as P
def main():
 data=ROOT/'data/v51_validation24.jsonl';saved=ROOT/'internal/evidence/v51/experiments/stage7_locked_validation24/specified_raw.jsonl'
 cases={r['id']:r for r in map(json.loads,data.read_text(encoding='utf-8').splitlines())}
 raws=list(map(json.loads,saved.read_text(encoding='utf-8').splitlines()))
 rules=P._rules();old=dict(rules,version='v51-semantic/4',exposure_terms=[x for x in rules['exposure_terms'] if x not in ['일회용 확인 코드','일회용 확인코드','일회용 인증 코드']])
 binding=v51.request_binding('v51-specific-candidate');results=[]
 for row in raws:
  case=cases[row['id']]
  with patch.object(P,'_rules',return_value=old):before=v51.evaluate_current(case['text'],row['raw'],profile_id='v51-specific-candidate',binding=binding)
  after=v51.evaluate_current(case['text'],row['raw'],profile_id='v51-specific-candidate',binding=binding)
  results.append(dict(id=row['id'],before_action=before['action'],before_reason=before['reason'],after_action=after['action'],after_reason=after['reason'],ai_proposed_expected=case['expect'],changed=before['action']!=after['action']))
 report=dict(mode='SAVED_RESPONSE_DEVELOPMENT_REPLAY',actual_model_calls=0,independent_evaluation=False,model_identity_verified=False,n=len(results),results=results,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (data,saved)})
 out=ROOT/'internal/evidence/v54/saved_response_replay.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'n':len(results),'changed':[r for r in results if r['changed']]},ensure_ascii=False))
if __name__=='__main__':main()
