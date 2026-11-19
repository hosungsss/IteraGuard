"""Capture genuine typed endpoint requests (synthetic only); no fixture fallback."""
import argparse,json,platform,subprocess,time,hashlib
from pathlib import Path
from integration.v48 import bridge

PROBES=[('normal','급여 입금 안내입니다.'),('warning','인증번호를 알려주지 마세요.'),
        ('direct','지금 인증번호를 알려주시겠어요?'),('mixed','인증번호를 알려주지 마세요. 하지만 지금 제게 인증번호를 보내주세요.')]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('Evidence output already exists')
    rows=[];client=bridge.ModelClient()
    for name,text in PROBES:
        t=time.monotonic();row={'case_id':name,'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'synthetic_only':True}
        try:
            raw,ms=client.infer(text)
            row.update(status='RESPONSE_RECEIVED_UNATTESTED',raw=raw,latency_ms=ms,
                       policy=bridge.advisory(text,raw,threshold=.70),diagnostic=bridge.abstention_cause(text,raw))
        except (bridge.ModelUnavailable,bridge.ContractError) as e:
            row.update(status='FAILED',error=type(e).__name__,error_code=str(e) if len(str(e))<100 else 'REDACTED',elapsed_ms=round(1000*(time.monotonic()-t),2))
        rows.append(row)
    result={'mode':'ACTUAL_ENDPOINT_ATTEMPT','platform':platform.platform(),'question_ids':sorted(bridge.SPEC),
            'fixture_fallback':False,'attempted_requests':len(rows),'valid_responses':sum(x['status']=='RESPONSE_RECEIVED_UNATTESTED' for x in rows),'rows':rows}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))
    return 0 if result['valid_responses']==len(rows) else 2
if __name__=='__main__':raise SystemExit(main())
