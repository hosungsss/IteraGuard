# 의심계 IteraGuard v5.6

실행 중 통신 복구는 저장 상태 확인 후 동일 요청을 최대 두 번 재시도한다. 이미 저장된 결과는 재추론 없이 복원하고, 인증 오류·세션 변경·판단 보류는 자동으로 바꾸지 않는다. 구현과 검증 범위는 docs/AUTO_RECOVERY_KO.md에 기록했다.

현재 검증 작업본은 main 046feef 기반 소스 후보다. 모델 설정 상태와 실제 연결 성공을 구분하며, 인증 실패·혼잡·잘못된 응답·대기 초과를 안내한다. 추론은 프로세스당 하나로 제한한다. Windows 직접 서버 시작은 UTF-8 모드를 선택한다. 공개 사이트 로그인 이후와 실제 Zoro 추론 성공은 별도 검증이 필요하며, 이 작업은 공개 배포나 커밋을 수행하지 않는다.

최종 로컬 검증 후보. **제출 준비 완료 또는 수상 보장 상태가 아닙니다.** 새 실모델 성공 응답 0건이며 현재 live 시도는 MODEL_NOT_CONFIGURED로 기록됐습니다.

## 실행

Python 3.11 이상에서 `python -X utf8 -m arena.server --port 8769` 또는 `./run_hackathon.ps1` 실행 후 http://127.0.0.1:8769 를 엽니다. .env는 자동으로 읽지 않습니다. 별도 로컬 Zoro 서버와 환경변수는 .env.example을 참조하세요. /v1/systemone 루프백 계약을 유지하며 /v1/decide는 미지원입니다.

현재 입력→현재 판단→기존 위험 유지→우선순위 확인업무 큐→사용자 보고→저장 상태 재조회 순으로 시연합니다. 화면에서 여러 미해결 업무를 선택할 수 있고 ‘현재 세션 증거 조회’로 원문 없는 기록을 읽습니다.

```powershell
python -X utf8 tools/run_judge_scenarios.py --mode controlled --out runs/controlled
python -X utf8 tools/run_judge_scenarios.py --mode live --out runs/live
python -X utf8 -m unittest discover -s tests_v56 -v
python -X utf8 -m unittest discover -s tests_v54 -v
python -X utf8 tools/redteam_workflow.py
```

controlled는 실제 추론이 아닙니다. live는 설정된 모델만 사용하며 실패를 대체하지 않습니다. 시나리오 C의 timeout 주입은 controlled에서만 이뤄집니다. 증거 JSON은 로컬 구조 검사와 무서명 해시를 제공할 뿐 모델 진품 여부를 인증하지 않습니다.

## 문서와 증거

- docs/CRITIQUE_AND_EXPERIMENT.md: v5.5 반례와 v5.6 해결·잔여 한계
- docs/PRD_v56.md 및 docs/SYSTEM_PROMPTING_v56.md: 현재 명세
- docs/JUDGE_EVIDENCE_GUIDE.md: 전문 질문과 증거의 대응
- internal/evidence/v56/: 현재 검사·통제 시나리오·실모델 설정 실패 기록
- internal/inputs_20261119/: 사용자 참고 MD 원본
- MANIFEST_V56_SHA256.json: 현재 배포 파일 해시

패키지/Arena 5.6, 기존 모델 계약 5.1, 의미 정책 v54-semantic/1을 구분합니다. 기존 APK/PWA는 보조 역사 자산으로 Arena 5.6 큐·증거 기능을 포함하지 않습니다. 핵심 시연은 Arena입니다. 내부 참고자료와 과거 산출물을 포함하므로 ZIP 전체를 그대로 공개 GitHub에 올리지 마세요. 권리·비밀정보·불필요 자료 정제와 Apache-2.0 적용 범위 검토는 별도입니다.


# 의심계 v5.5 비판 검토와 v5.6 실험 분석

작성일 2026-11-19 · 대상 IteraGuard 팀 · 리더 최한길 · 분석 및 구현 보조 Codex

“판단을 설득하려는가, 판단의 근거를 검증하려는가?”
“반례 앞에서도 유지되는 주장만이 우리의 설계를 지탱할 수 있다.”
“모르는 것을 남겨 두는 정직함이, 완벽하다는 선언보다 강하다.”

위 세 문장은 이번 분석을 위한 창작이며 소크라테스의 실제 인용이 아니다.

## 1 결론과 사용 범위

v5.5는 심사 대응 증거·출처·시나리오 기록 기능을 추가한 중간 검토본이다. 기존 회귀 9건은 통과했지만 추가 반례에서 업무 누락, 비정상 숫자 응답의 예외, 출처 혼합 지연 집계가 재현됐다. v5.6은 이 세 문제를 수정하고 업무 큐와 증거 검사를 추가한 로컬 검증 후보다. 최종 사용 권장은 v5.6이며, v5.5는 비교·재현을 위해 보존한다.

**완벽한 제품 또는 제출 완료본이라는 판정은 아니다.** 실제 모델 경로도 실행했으나 현재 환경에서 모든 5개 평가 시도가 MODEL_NOT_CONFIGURED로 기록됐다. 성공한 신규 모델 추론은 0건이다. 통제 응답 성공과 이 실패 기록을 분리했다. 모델·head·revision 인증, 공식 제출 자료·저장소·데모 접근 확인은 미완료다.

## 2 근거의 우선순위와 충돌

이번에 실제 읽은 자료는 첨부 두 MD, 로컬 v5.4 전체 ZIP 및 현재 코드·검증 로그, 현재 대화에 제공된 과거 이력, 공식 공개 웹페이지다. 모든 과거 대화와 Drive 파일을 전수 재조회한 것은 아니다. 첨부 MD가 인용하는 현장 23쪽 PDF 원본은 이번 작업에서 직접 열지 못했다. 세부 배점 50/15/15/15/5, 11월 20일 09시 마감, Slides·저장소·실행 로그 3종 요구는 **첨부의 공식 문서 해석**으로 기록하며 독립 원문 재검증과 구분한다.

공개 해커톤 페이지는 Track 1의 판단→행동 에이전트와 창의성을 안내하고 상세 기준은 당일 안내한다고 명시한다. 이 페이지로 현장 배점 전체를 검증했다고 주장하지 않는다. 첨부의 ‘v5.4 미구현’ 상태는 현재 로컬 구현·로그와 충돌하므로 현재 소스가 우선한다. 심사위원 연구 경력은 첨부의 출처 있는 전문 페르소나 자료로 활용했으며 개인별 호불호·점수·심리를 새로 확정하지 않았다.

공식 자료 확인: [대회](https://hackathon.trillionlabs.co/), [Zoro-1 모델 카드](https://huggingface.co/trillionlabs/Zoro-1), [Trida Decision](https://trida.trillionlabs.co/decision/). Trida 페이지는 /v1/systemone 예시를 제공한다. 모델 카드와 웹 문서의 구성·온도 설명이 같다고 가정하지 않으며 현재 구현 계약과 임계값을 임의 변경하지 않았다. /v1/decide 어댑터는 이번 범위에 없다.

## 3 반복해서 깔고 있는 전제 하나와 엘렌코스

**지목할 전제:** “심사위원 페르소나에 맞춰 기능·문서·테스트를 더 많이 추가하고 버전을 높이면 실제 제출 경쟁력도 자동으로 높아진다.” 이는 이번 요청과 반복적인 ‘완벽한 고도화’ 요청에서 읽히는 작업 가정에 대한 비판이며, 손호성 박사님의 성격을 진단한 것이 아니다.

**반례 질문:** “기존 검사가 모두 통과하고 로그 화면도 추가됐지만, 열린 ASK 업무 때문에 새 OTP 위험 업무가 생기지 않고, 실제 Zoro는 한 번도 성공하지 않았다면 심사위원이 관찰하는 목표 달성과 라이브 완성도가 높아졌다고 말할 수 있는가?”

**답:** 아니다. 증거의 양은 새로운 상태 전이의 정확성과 실호출을 대신하지 못한다. v5.5에서 기존 9개 검사가 통과한 직후 실제로 새 위험 업무 누락을 재현했다. 버전 수·테스트 수는 보조 정보이고, 핵심 사용자 경로와 실패 복구의 증명이 수용 기준이어야 한다.

후속 심문:

1. “모델을 없애도 같은 화면이 나오면 모델의 기여는 무엇인가?” 모델 응답·정책·세션 행동을 분리하고 통제/실호출을 표시해야 한다. 이번 통제 실험은 모델 기여의 독립 효과를 증명하지 않는다.
2. “확인 버튼을 눌렀으니 위험이 사라졌는가?” 사용자 보고가 저장됐을 뿐이다. REPORTED_COMPLETE와 기관 검증 완료는 다르다.
3. “해시가 있으니 진짜 Zoro의 응답인가?” 아니다. 해시는 로컬 파일 변경 검출 수단이다. 동일 운영자가 내용과 해시를 함께 바꿀 수 있으므로 신원 인증이 아니다.
4. “응답이 빠르니 NPU 최적화에 성공했는가?” 아니다. 통제 응답의 서버 처리 시간이며 실제 모델/NPU 지연을 측정하지 않았다.
5. “심사위원의 공개 연구를 알면 취향을 안다고 할 수 있는가?” 아니다. 대비할 기술 질문의 가설만 만들 수 있다.

## 4 v5.5에서 재현한 세 결함

| ID | 재현 조건 | 관찰 | 원인과 영향 | v5.6 수용 결과 |
|---|---|---|---|---|
| C01 P0 | 모호한 요청 업무 OPEN → 다른 민감정보 요청 PAUSE | OPEN 업무 1개, 새 위험의 고유 업무 없음 | 전체 세션의 open_task 존재가 새 업무 생성을 막음. 위험 상태는 남지만 업무 안내가 이전 질문에 묶임 | OPEN 2개, 새 위험 업무 ID 분리·우선 표시 |
| C02 P0 | 응답 객체에 NaN 포함 | ValueError가 보류 처리 밖으로 빠짐 | 추가한 증거 해시 생성이 응답 정규화보다 먼저 수행됨 | 검사 후 해시, 오류를 FAILED/ASK로 기록하고 세션 유지 |
| C03 P1 | 통제 경로 1ms와 로컬 모델 경로 1000ms를 집계 | 단일 n=2, p50=1·p95=1000 | 실행 출처별 분모가 없음. 처리 속도 해석을 왜곡할 수 있음 | 출처별 n=1 통계로 분리, 비유한·음수·bool 제외 |

근거는 각 버전의 tools/redteam_workflow.py와 internal/evidence/current/redteam.json이다. C03 수치는 검사자가 넣은 합성 숫자이며 하드웨어 벤치마크가 아니다. C02의 최종 세션 사유가 PRIOR_RISK_UNRESOLVED인 경우에도 current_turn_reason/model_status에서 현재 모델 오류를 별도로 추적한다.

## 5 가설과 실험 방법

H1: 전역 ‘열린 업무 있음’ 조건을 입력 지문·현재 행동·현재 사유별 중복 판단으로 바꾸면 새 위험을 누락하지 않으면서 같은 요청은 중복 생성하지 않는다.

H2: 응답 검증 후 해시를 생성하고 숫자 입력을 제한하면 잘못된 응답이 예외로 끝나는 대신 실패·보류·다음 확인으로 이어진다.

H3: 실행 출처별 지연 집계는 통제/연결 경로의 혼합을 막지만 실제 모델 성능 개선을 뜻하지 않는다.

통제된 동일 응답과 입력을 v5.5/v5.6에 적용한 결정론적 회귀 실험이다. 무작위 배정·사람 표본·실사기 라벨·통계적 유의성 검정이 없다. p값과 신뢰구간은 해당 없음이다. 기능 여러 개를 바꿨으므로 전체 제품 성능에 관한 단일 인과효과를 추정하지 않는다. 각 반례별 작동 기전만 코드·로그로 확인한다.

## 6 v5.6 실행 결과

| 검사 | 결과 | 범위 |
|---|---|---|
| 새 업무 큐·증거 검사 | 12 통과 | 중복, 우선순위, 용량, 해시·순서·허위 인증, 숫자·출처 |
| v5.4 회귀 | 9 통과 | 확인 코드 동의어, 부정·간접 인용, 재시작, 이전 위험 |
| v5.1 계약·정책·배포 회귀 | 73 통과·2 선택 검사 제외 | Python/JS·프로필·계약 |
| v5.2 실험 모듈 | 21 통과 | 기존 탐색 미들웨어 |
| 세션 생명주기 | 17 통과 | 종료·재개·멱등·경합·DB |
| UI 모의 DOM | 23 통과 | 선택 큐와 기존 상태·늦은 응답 경로 |
| 로컬 HTTP | 5 통과 | 상태 API와 증거 조회 |

총 **160 통과, 2 선택 검사 제외**다. 제외된 검사는 dev98/dev133 선택 재생 경로 미제공으로 인한 것이다. 이 합계는 실제 브라우저·Android·새 Zoro 추론·독립 인간 검증을 포함하지 않는다. 패키지 CRC·파일 해시는 별도 배포 검증이며 테스트 합계에 중복 가산하지 않는다.

세 시나리오 A=직접 위험 요청, B=위험 후 평범한 요청에서 미해결 보존, C=통제 timeout 뒤 복구를 수행했다. 통제 평가 이벤트는 총 5개이며 4개 유효 응답과 1개 주입 실패다. ‘3개 실제 Zoro 로그 제출 요건을 충족했다’고 말할 수 없다. live 모드의 별도 5개 시도는 전부 MODEL_NOT_CONFIGURED였다.

## 7 SNM 시나리오 네트워크

SNM은 조건에 따른 경로와 대응을 구성하는 분석 도구로 사용했다. 아래 네트워크는 Dennis List의 방법을 참고한 실무 확장이며 미래 예측 정확도나 발생확률 계산이 아니다.

| 경로 | 과거·현재 출발 | 미래 조건부 전개 | 관찰 신호 | 대응 |
|---|---|---|---|---|
| S1 정상 | 현재 요청 판단 완료 | 추가 위험이 없으면 동일 업무 유지 | 입력·사유 지문과 업무 수 | 중복 생성 억제 |
| S2 새 위험 | 기존 ASK 업무 OPEN | 다른 민감 요청 발생 | current_turn PAUSE, 새 지문 | 새 업무 생성, 중단 우선 |
| S3 복구 | 모델 실패·보류 | 서버가 복구되면 실제 재평가 | FAILED→VALID와 별도 request_id | 이전 위험 유지, 자동 안전 해제 없음 |
| S4 경합 | 평가 중 세션 변경 | 늦은 응답 도착 | version 불일치 | 기존 충돌 검사로 반영 거부 |
| S5 과부하 | OPEN 업무 증가 | 65번째 새 업무 필요 | 64건 한도 | 상태를 잃지 않고 명시적 충돌 반환 |
| S6 제출 | 로컬 테스트 완료 | 실제 모델/링크 확인 실패 | 인증·제출 게이트 미충족 | NOT_SUBMISSION_READY 유지 |

S2와 S5는 상충한다. 업무 누락을 막으려고 무한 큐를 만들면 운영 부담이 커진다. 64건 한도는 이번 로컬 실험의 공학적 선택이지 현장 최적값이 아니다. 새 문장 변형으로 큐가 증가할 수 있으며 의미 기반 중복 판정은 아직 없다. 사업화 단계에서는 입력 제한·사건 묶음·인간 운영 기준을 별도 검증해야 한다.

## 8 4D Ontology

구조: Message, ModelResponse, Profile, PolicyDecision, Session, Task, UserObservation, EvidenceExport를 분리한다. 모델은 정책과 기관 인증의 권한을 갖지 않는다. UI는 DB에 저장된 상태를 재조회한다.

시간: received_utc, 요청 ID, 세션 버전, 현재 행동, 이전 위험, 완료 보고를 연결한다. 입력이 같아도 사유가 다르면 새 업무가 될 수 있다. 현재 문장만 모델에 전달하므로 ‘전체 대화 장기 추론’이라고 표현하지 않는다.

관점: 사용자는 실행 가능한 다음 안내를 원하고, 개발자는 원인을 재현해야 하며, 심사위원은 실제 모델·작동 범위·실패를 확인해야 한다. 정상 사용자의 불필요한 확인 부담과 위험 요청 누락은 다른 지표다.

방향·역검증: 화면 업무→task ID→request ID→current_turn_reason→프로필·정책·소스 해시→응답 해시를 따라간다. 반대 방향으로 동일 통제 응답을 재생한다. 원문·raw를 공개 export에 담지 않으므로 공개 로그만으로 모델 원응답 전체를 독립 재계산할 수는 없다. 권한 있는 별도 실험 저장소가 필요하다.

## 9 NPU 관점

NPU 관점의 장점은 지연·메모리·전력 예산과 실제 실행 장치를 명확히 묻는 데 있다. 이번에는 NPU 가속 구현·벤치마크를 하지 않았다. Windows 하드웨어 조회도 CIM 접근 제한으로 실패했다. 기록의 GPUs=null은 GPU가 없다는 증거가 아니다.

검증 단계: 모델 연산자/typed head 지원 확인 → 동일 입력·프로필의 CPU/GPU/NPU 출력 대조 → 실제 provider 배치·fallback 여부 프로파일링 → cold/warm 지연과 n·p50·p95·전력 측정 → 발열·긴 세션 반복. 장치 이름이나 NNAPI/ONNX 패키지 존재만으로 NPU 사용을 확정하지 않는다.

현장 우선순위는 이미 검증된 서버 경로의 안정성이다. NPU 이식은 조건부 후속 실험이며 제출 전 필수 고도화로 간주하지 않는다. 측정값 없는 ‘NPU 몇 배 가속’ 주장은 금지한다.

## 10 심사 전문 관점으로 준비할 증거

페르소나는 전문 질문을 준비하는 가설이다. 실제 개인의 선호·채점·성격으로 취급하지 않는다.

- 모델·데이터 관점: source와 model_status, 응답 해시, 프로필, 소스 지문을 제시한다. model_checkpoint/head/revision은 미확인이며 문자열 모델명으로 대체하지 않는다.
- 시스템·재현 관점: 실행 명령, 세 시나리오, 오류와 복구, 현재 테스트와 제외 항목을 제시한다. server_pipeline_ms는 브라우저 E2E 지연이 아니다.
- 행동·장기 상태 관점: 새 업무 큐와 중복 방지, 현재/과거 위험 분리, 자기보고의 권한 한계를 시연한다.

사업화는 현재 고객 검증 가설이다. 최초 사용자로 ‘의심 메시지를 받은 사람이 행동 직전에 확인할 수 있는 도구’를 제시할 수 있으나 구매 의향·피해 감소율은 측정되지 않았다. 고객 인터뷰, 사용성 실험, 정상 요청 부담을 다음 단계로 둔다. PAYLOCK은 확장 예시로 분리하고 본 시연의 필수 기능을 늘리지 않는다.

## 11 끝까지 남은 문제와 다음 행동

P0: 로컬 Zoro 설정과 실호출 성공, 정확한 checkpoint/head/revision 증거, 현장 제출 원문·Slides·저장소·데모 접근 확인. 이 작업은 자동으로 완료하지 않았고 초대·외부 메시지·업로드를 하지 않았다.

P1: /v1/decide 새 어댑터 미구현, 완전한 한국어 문맥 일반화 미검증, 실제 브라우저·기기 시각 검증 미수행, 로컬 로그를 동일 운영자가 수정하는 공격에 대한 독립 서명 부재, 64건 한도의 운영 적정성 미검증. 오래된 DB 이벤트는 provenance가 없어서 신규 엄격 검증에서 거부될 수 있다. 원본 DB 백업과 새 시연 세션 사용을 권장한다.

P2: 사용자 사건 묶음/의미 중복, UI 전체 지연 계측, cold/warm 반복, 권한 있는 독립 확인과 해제 절차, 라이선스 권리 목록·공개용 패키지 정제. 현재 ZIP은 내부 검토 자료를 포함한 팀 작업용이며 그대로 공개 저장소에 올리는 패키지가 아니다.

권장 순서: 새 기능 동결 → 실제 Zoro 세 시나리오 → 장비 재시작 후 재현 → 공식 Slides에서 5분 리허설 → 다른 계정에서 링크 확인. 이 순서가 충족되면 시연 준비의 신뢰도가 높아질 수 있지만 수상 여부는 미공개 판단과 경쟁작에도 의존하므로 확률을 산출하지 않는다.

## 12 기록과 재현

각 버전의 internal/evidence에 실행 로그와 반례 JSON이 있다. v5.6의 tools/run_judge_scenarios.py는 --mode controlled 또는 --mode live를 명시해야 한다. live 실패를 fixture로 채우지 않는다. arena/evidence.py의 검증은 로컬 구조·지문·순서 검사이며 제3자 인증이 아니다. 원본 v5.4 ZIP과 첨부 두 MD를 보존했고 최종 변경 이력은 internal/VERSION_LEDGER.md에 기록한다.


## Current GitHub v5.8 source candidate orientation
The current source integrates a proposal-only business Rulebook next to (not in place of) the existing v5.6 Arena / v5.1 typed Zoro contract. The core technical thesis is that typed proposals, domain policy, authorization, persistent execution and outcome verification are independently measurable layers; changing questions and if-else is not sufficient to guarantee broad industrial success. Two small example books show refund intake and beneficiary bank-change triage; neither triggers an external action.
A v5.8 web usability layer offers synthetic inputs, selected follow-up target and evidence JSON download. Existing model transport has not been replaced. A real Zoro checkpoint/head, cross-industry locked evaluation, NPU performance, actual refund/bank outcomes and presentation submission remain separate unverified tasks. Detailed diffs belong only to internal/VERSION_LEDGER.md. Future agents begin with AGENTS.md and the cumulative handoff file, then inspect the present repository HEAD and run relevant tests before proposing claims. See docs/V58_RULEBOOK_ARCHITECTURE.md for the threat model and testable follow-up plan.
