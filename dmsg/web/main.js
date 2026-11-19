'use strict';
let session=null, count=0, fixtures=[], last=null, selectedText='', busy=false;
const el=id=>document.getElementById(id);
const view=(id,text)=>{el(id).textContent=text;};
async function serialized(work){
 if(busy)return;busy=true;for(const id of ['run','modelrun','new','next'])el(id).disabled=true;
 try{await work();}finally{busy=false;for(const id of ['run','modelrun','new','next'])el(id).disabled=false;}
}
async function api(path,payload){
 const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const data=await r.json();if(!r.ok)throw Error(data.error||'REQUEST_FAILED');return data;
}
async function start(){session=await api('start',{});count=0;last=null;view('status','세션 시작 / FIXTURE · SIMULATED');view('action','평가 전');view('message','새 사례를 선택하세요.');view('evidence','근거 인용: 아직 없음');view('reason','정책 버전: 4.0 · 모델 인증 전');view('xray','아직 모델 응답 없음');el('history').replaceChildren();view('err','');}
async function load(){const r=await fetch('/api/fixtures');const data=await r.json();fixtures=data.fixtures;for(const f of fixtures){let op=document.createElement('option');op.value=f.id;op.textContent=f.title;el('scenario').append(op);}choose();await start();}
function choose(){const f=fixtures.find(x=>x.id===el('scenario').value);if(f){selectedText=f.text;el('text').value=f.text;}}
async function run(){try{view('err','');if(!session)await start();let f=fixtures.find(x=>x.id===el('scenario').value);let edited=el('text').value!==f.text;
 const payload={session_id:session.session_id,version:session.version,turn_id:'turn-'+(++count),simulate_failure:el('failure').checked};
 if(edited)payload.text=el('text').value;else payload.fixture_id=f.id;
 const out=await api('turn',payload);session.version=out.version;last=out;
 view('status',out.mode+(edited?' / MANUAL UNVERIFIED':' / ANNOTATED FIXTURE'));
 view('action',out.action);view('message',out.message);view('reason','reason_code: '+out.reason+' · session version '+out.version);
 view('xray','FIXTURE: 확률 없음 · 합성 작성자 주석 사용');
 view('evidence',out.evidence.length?'원문 근거: '+out.evidence.map(x=>'“'+x.quote+'” ['+x.kind+']').join(' · '):'인증된 직접 위험 요청 근거 없음 (안전 보증 아님)');
 const hist=el('history');hist.replaceChildren();for(let i=out.history.length-1;i>=0;i--){let li=document.createElement('li');li.textContent=out.history[i].turn_id+' / '+out.history[i].scenario_id+' → '+out.history[i].action+' · '+out.history[i].reason;hist.append(li);}
 }catch(e){last=null;view('xray','현재 요청 실패 · 이전 확률 표시 폐기');view('status','오류 · 새 판단 미확인 / SIMULATED');view('action','ASK_HUMAN');view('message','현재 판단을 확인할 수 없습니다. 중요한 행동을 실행하지 말고 독립적인 공식 경로에서 확인하세요.');view('evidence','현재 요청의 확인된 근거가 없습니다.');view('err','요청 실패: '+e.message+' · 이전 판단은 최신 판단이 아닙니다.');}}
 async function modelRun(){try{view('err','');if(!session)await start(); const payload={session_id:session.session_id,version:session.version,turn_id:'turn-'+(++count),text:el('text').value};const out=await api('model-turn',payload);session.version=out.version;last=out;view('status',out.mode);view('action',out.action);view('message',out.message);view('reason','model-origin: '+out.source+' · '+out.reason+' · '+out.latency_ms+'ms');view('evidence',out.evidence.length?out.evidence.map(x=>x.quote+' ['+x.kind+','+x.directness+']').join(' · '):'검증된 동작 근거 없음');if(out.probs&&Object.keys(out.probs).length){let lines=Object.entries(out.probs).map(([k,v])=>k+': '+Object.entries(v).map(([a,p])=>a+' '+(100*p).toFixed(1)+'%').join(' / '));view('xray',lines.join('\n')+'\n※ 미보정 모델 선택확률 · 범죄 발생 확률 아님')}else view('xray','모델 응답 없음 · 통계 미측정');const hist=el('history');hist.replaceChildren();for(let i=out.history.length-1;i>=0;i--){let li=document.createElement('li');li.textContent=(out.history[i].turn_id||'event')+' / '+out.history[i].action;hist.append(li);}}catch(e){last=null;view('status','모델 판정 실패 · 이전 결과 무효화');view('action','ASK_HUMAN');view('message','판단 보류. 독립적인 공식 경로로 확인하세요.');view('evidence','현재 요청의 검증된 근거 없음');view('reason','현재 모델 판단을 확정하지 못했습니다.');view('xray','모델 요청 실패 · 이전 확률 표시 폐기');view('err','모델 판정 실패: '+e.message);}}
 async function modelStatus(){try{const r=await fetch('/api/model-status');const d=await r.json();view('model-status',d.configured?'운영자 지정 엔드포인트 연결 설정 있음 · 실모델 인증 전':'모델 미연결 · 기본 실행은 합성 fixture');}catch(e){view('model-status','모델 상태 조회 불가');}}
 el('modelrun').addEventListener('click',()=>serialized(modelRun));modelStatus();
 el('scenario').addEventListener('change',choose);el('run').addEventListener('click',()=>serialized(run));el('new').addEventListener('click',()=>serialized(start));
 el('again').addEventListener('click',()=>{view('err','다른 합성 시나리오를 선택한 뒤 평가를 누르세요. 이전 결정은 유지됩니다.');});
 el('next').addEventListener('click',()=>serialized(async()=>{try{if(!last)return view('err','먼저 사례를 평가하세요.');const out=await api('ack',{session_id:session.session_id,event_id:last.turn_id,version:session.version,choice:'PLAN_INDEPENDENT_VERIFICATION'});session.version=out.version;last=null;view('err','SIMULATED: 공식 경로를 확인할 계획만 기록했습니다. 실제 확인은 수행되지 않았습니다. 다음 발화를 평가할 수 있습니다.');const hist=el('history');hist.replaceChildren();for(let i=out.history.length-1;i>=0;i--){const x=out.history[i];let li=document.createElement('li');li.textContent=x.event?x.event+' → '+x.choice:x.turn_id+' / '+x.scenario_id+' → '+x.action;hist.append(li);}}catch(e){view('err','계획 기록 실패: '+e.message);}}));
 load().catch(e=>view('err','초기화 실패: '+e.message));
