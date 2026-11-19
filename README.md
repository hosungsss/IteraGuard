# 의심계 · IteraGuard v5.6

의심스러운 메시지를 받았을 때 **어떤 확인 행동을 해야 하는지 제안하고, 해결하지 못한 위험을 다음 대화에서도 유지하는** 로컬 실행 프로토타입입니다. Track 1을 위한 Zoro-1 Typed Decision 연동 경로, 결정론적 정책, 확인 업무 큐, SQLite 기록과 웹 화면을 포함합니다.

**현재 상태: 로컬 시연 검증 후보.** Arena 보완판은 로컬 Zoro-1로 합성 사례 12건과 세션·복구 흐름을 재검증했습니다. [Arena 시연 보완과 검증 범위](docs/V56_ARENA_DEMO_UPDATE.md)를 참고하세요. 기존 동봉 160건은 이전 소스의 기능 테스트 기록입니다.

## v5.6 핵심 개선

| 주안점 | 구현 |
| --- | --- |
| 미해결 위험 유지 | 다음 입력이 평범해도 이전 위험을 유지하고 사용자 확인 보고만으로 안전을 확정하지 않습니다. |
| 확인 업무 누락 방지 | 기존 업무가 열려 있어도 새로운 위험을 추가합니다. 입력 HMAC·행동·이유가 같은 업무는 중복 생성하지 않습니다. |
| 행동 우선순위 | PAUSE_AND_VERIFY 업무를 우선 표시하고 화면에서 처리할 업무를 선택합니다. |
| 응답 오류 처리 | 응답 검증 후 해시를 계산합니다. 형식 오류와 모델 실패는 ASK_HUMAN 및 실패 상태로 표시합니다. |
| 증거 조회 | 요청 ID, UTC 시각, 응답 해시, 정책·프로필·소스 정보를 기록하고 세션 증거를 재조회합니다. |
| 측정 분리 | 통제 응답과 로컬 모델 응답의 서버 처리 시간을 분리합니다. GPU 성능이나 브라우저 전체 지연 측정이 아닙니다. |

열린 업무는 최대 64개이며 초과 시 `TASK_CAPACITY_REACHED`로 거절하고 기존 상태를 보존합니다. `CLOSED_UNRESOLVED`는 안전 판정이 아닙니다.

## 빠른 시작

Python 3.11 이상에서 저장소 최상위 폴더를 엽니다. 모델 실행 서버는 별도로 준비해야 합니다.

```powershell
python -X utf8 -m arena.server --port 8769
```

브라우저에서 <http://127.0.0.1:8769>에 접속합니다. Windows에서는 `./run_hackathon.ps1`도 사용할 수 있습니다. 합성 메시지로 시연하십시오.

화면 흐름: **현재 입력 → 모델 제안과 정책 판단 → 기존 위험 유지 → 확인 업무 선택 → 사용자 보고 → 저장 상태 재조회**. ‘현재 세션 증거 조회’에서 기록을 확인합니다.

## Zoro-1 연결과 mock 구분

가중치와 모델 실행 서버는 포함되지 않습니다. `.env.example`은 예제이며 자동 로드되지 않습니다. 프로젝트의 로컬 `/v1/systemone` 계약을 지원하는 서버를 준비한 다음 설정합니다.

```powershell
$env:DMSG_MODEL_ENABLED = "1"
$env:DMSG_SYSTEMONE_ENDPOINT = "http://127.0.0.1:8008/v1/systemone"
$env:DMSG_MODEL_ID = "trillionlabs/Zoro-1"
$env:DMSG_SEND_MODEL_FIELD = "1"
$env:DMSG_REQUIRE_MODEL_ECHO = "1"
$env:DMSG_MODEL_TIMEOUT_S = "20"
python -X utf8 -m arena.server --port 8769
```

이 주소는 프로젝트 연동 계약이며 공식 공개 API 주소가 아닙니다. `/v1/decide`는 미지원입니다. 공개 Zoro 생성 모델 비교는 Arena 시연 화면에서 제외했습니다. 연구용 비교 API는 별도의 경로입니다.

- `controlled`: 고정된 통제 응답을 이용한 기능 검증으로 실제 추론이 아닙니다.
- `live`: 설정된 서버만 호출하고 실패를 통제 응답으로 대체하지 않습니다.
- `LOCAL_HTTP_MODEL_UNATTESTED`: 로컬 HTTP 응답을 받았다는 표시이며 실제 모델 정체의 외부 인증이 아닙니다.

## 판단과 실행 범위

판단은 `NO_STRONG_SIGNAL`, `CAUTION`, `PAUSE_AND_VERIFY`, `ASK_HUMAN`입니다. NO_STRONG_SIGNAL은 안전 보증이 아닙니다. 정책과 기존 상태로 모델 제안을 검증한 뒤 확인 업무로 연결합니다. 실제 송금·계좌 동결·문자 발송은 수행하지 않습니다.

패키지/Arena **5.6**, typed 계약 **5.1**, 의미 정책 **v54-semantic/2**은 서로 다른 구성요소 버전입니다.

## 재현과 테스트

```powershell
python -X utf8 -m unittest discover -s tests_v56 -v
python -X utf8 -m unittest discover -s tests_v54 -v
node --test tests_v50/test_session_ui.js tests_v53/test_choice_ui.js
python -X utf8 tools/run_judge_scenarios.py --mode controlled --out runs/controlled
python -X utf8 tools/run_judge_scenarios.py --mode live --out runs/live
python -X utf8 tools/redteam_workflow.py
```

시나리오는 직접 위험, 위험 이후 평범한 입력, 실패 이후 회복을 다룹니다. timeout 주입은 controlled에서만 수행합니다. 전체 기존 결과는 [test_summary.json](internal/evidence/v56/test_summary.json)을 참고하십시오. 위 테스트 명령은 핵심 기능 재현용 부분 집합입니다.

`GET /api/evidence?session_id=...`에서 세션 기록을 조회합니다. 공개 증거 출력에서 입력·응답 원문을 제외합니다. 로컬 무서명 해시는 구조·변경 검사를 돕지만 외부 인증이나 변조 불가능성을 보장하지 않습니다.

## 구성과 문서

| 경로 | 내용 |
| --- | --- |
| arena/ | 현재 서버, 웹 화면, 업무 큐, 저장·증거 처리 |
| integration/, vendor/ | 기존 계약·프로토타입 연결 및 포함 소스 |
| tests_v56/, tests_v54/ | 현재 개선 및 정책 회귀 테스트 |
| tools/ | 시나리오 실행과 반례 검증 |
| apps/ | 기존 앱과 과거 배포 자산 |
| internal/evidence/v56/ | 동봉 테스트·통제 및 live 시도 기록 |

- [PRD v5.6](docs/PRD_v56.md)
- [System Prompting v5.6](docs/SYSTEM_PROMPTING_v56.md)
- [반례·실험·잔여 문제 분석](docs/CRITIQUE_AND_EXPERIMENT.md)
- [심사 질문과 증거 안내](docs/JUDGE_EVIDENCE_GUIDE.md)
- [GitHub 반영 기록](GITHUB_UPLOAD.md)

## 남은 검증 과제

보완판의 로컬 Zoro-1 연결과 Arena HTTP 경로를 합성 입력으로 검증했습니다. 독립 모델 인증, 보완판의 브라우저 렌더링, Android/NPU 및 독립 사용자 평가는 미검증입니다. 제출 준비 상태는 `NOT_SUBMISSION_READY`입니다. 심사위원 페르소나는 기획 검토용 가설이며 실제 선호·수상 확률의 증거가 아닙니다.

동봉 APK/PWA 5.0·5.1은 과거 보조 자산이며 v5.6 Arena의 업무 큐·증거 기능을 포함한 Android 앱이 아닙니다. 현재 핵심 시연 대상은 Arena 웹 화면입니다. 기존 모델·외부 소스의 권리는 각 원본 조건을 따르며 이 README는 전체 파일에 새 일괄 라이선스를 부여하지 않습니다.
