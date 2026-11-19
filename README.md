# 의심계 · IteraGuard v5.9 source candidate (Arena v5.6 engine)

> **v5.9 (2026-11-19):** 판단 결정은 그대로 두고 요청당 계약 재검증을 12회에서 3회 이하로 줄여, 통제 응답 기준 evaluate p50이 53.99ms에서 19.59ms로 빨라졌습니다. Arena 화면은 판단 과정 5단계가 보이는 단순한 구조로 다시 만들었습니다(세션·기록은 오른쪽 시트). 실제 Zoro-1 추론, 기기, 독립 평가는 미검증입니다. → [v5.9 문서](docs/V59_ARENA_UI_AND_PERFORMANCE.md)

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

검증 기준은 Python 3.12입니다. 저장소 최상위 폴더를 엽니다. 모델 실행 서버는 별도로 준비해야 합니다.

```powershell
python -X utf8 -m arena.server --port 8769
```

브라우저에서 <http://127.0.0.1:8769>에 접속합니다. Windows에서는 `./run_hackathon.ps1`도 사용할 수 있습니다. 합성 메시지로 시연하십시오.

화면 상단의 모델 설정 표시는 연결 성공을 의미하지 않습니다. 실제 요청 결과에서 모델 실패와 판단 보류를 구분하십시오. 단일 서버 프로세스에서 추론 요청은 한 번에 하나만 처리하며 혼잡 시 HTTP 429를 반환합니다. 응답 대기 초과 후에는 서버 처리가 완료됐을 수 있으므로 저장 상태를 먼저 재조회하십시오. 공개 시연 사이트의 인증과 배포는 별도 구성입니다.

화면 흐름: **현재 입력 → 모델 제안과 정책 판단 → 기존 위험 유지 → 확인 업무 선택 → 사용자 보고 → 저장 상태 재조회**. ‘현재 세션 증거 조회’에서 기록을 확인합니다.

메인 화면에서 합성·비식별 문자를 붙여넣고 **판단하기**를 누르면 **신호등 등급**과 **발신자가 지금 뭘 해달라고 하나요?**의 답이 표시됩니다. 원문과 행동 후보 20개가 있는 행동 질문, 피싱 의심 수준 질문을 한 번의 로컬 Zoro 요청으로 보냅니다. 위에 설명한 세션 기반 흐름은 기존 Arena API에서 사용합니다.

결과 카드에는 빨강·주황·초록·회색의 Zoro 선택 점수를 표시합니다. **성능검증**에서 한국어 테스트 551건의 저장 결과를 확인합니다. 원본 CSV와 로컬 Zoro를 연결한 Arena에서는 **재측정**으로 551건을 다시 판단하고 정확도와 피싱 탐지율을 갱신합니다. [재측정 실행 방법과 집계 기준](docs/SIGNAL_BENCHMARK_UI_20261120.md)

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


## v5.8 GitHub source integration (not a released APK)
- Rulebook/engine.py adds a *proposal-only* typed decision to configurable industry workflow; zero external side effects. Sample financial-operations account-change and customer-support refund books are in rulebook/presets/.
- Arena web UX includes four contextual synthetic messages covering a changed payment account, a preventive notice, an unclear request, and a routine follow-up, selected task observation target, and privacy-limited evidence JSON download. Existing v5.6 backend and v5.1 typed source contract are not replaced.
- Run local fixture preview: python -m tools.rulebook_preview_v58 --book refund_intake --answers tests_rulebook/refund_fixture.json
- Run rulebook contract checks: python -m unittest discover -s tests_rulebook -v
- Read AGENTS.md before AI edits, internal/VERSION_LEDGER.md for append-only detailed changes, and HANDOFF_CHANGELOG.md for cumulative resume instructions.
- See docs/V58_RULEBOOK_ARCHITECTURE.md and docs/V58_AGENT_EVIDENCE_GUIDE.md for business portability constraints and original source hashes.
- Neither this branch's existence nor a valid Zoro-looking JSON proves real checkpoint identity, independent accuracy, or field-level intervention. The hypothesized 30% to 98% business success gain is NOT MEASURED.
- Historic APKs, dmsg.skill/dmsg.zip, old manifests and full ZIP assets remain at their original release versions; their contents are not silently upgraded by source edits.


### Reconfigure another industry (local-only)
Duplicate one of the versioned rulebook/presets/*.json files, change question instructions/criteria and when/action rules, then save it as a local JSON file. No model retraining or business API credentials are needed for a synthetic preview:
python -m tools.rulebook_preview_v58 --book-file path/to/company_rules.json --answers tests_rulebook/refund_fixture.json
This command only evaluates an already supplied typed answer envelope. If the question set differs, supply a matching synthetic answers file. It never contacts Zoro or executes any business action.


### Optional real System One Rulebook preview (operator opt-in)
The existing configured Zoro /v1/systemone ModelClient may now be reused by rulebook/zoro_bridge.py with arbitrary versioned company question books. This does NOT modify the default Arena and does NOT execute the proposed business action.

Example for a local, synthetic scenario (requires the existing local model server and operator environment configuration):
DMSG_V58_RULEBOOK_LIVE_ENABLE=1 python -m tools.rulebook_live_v58 --book refund_intake --state-file tests_rulebook/refund_synthetic_message.txt --synthetic-only

A network response remains LOCAL_HTTP_MODEL_UNATTESTED unless the exact model/checkpoint/head is verified independently. If disabled, invalid, disconnected or unconfigured, no fixture is silently substituted. Use python -m unittest discover -s tests_rulebook -v for unit tests (test doubles are NOT a live model test).


### v5.8 Rule Tweak Candidate 1 — shadow-only integration
The team's historical v5.6 bounded Korean warning/report candidate has been adapted as a **read-only observer** next to the existing Arena v5.6/v5.8 source, NOT installed as a destructive v5.6 patch. By default, DMSG_RULE_TWEAK_MODE=shadow adds a strictly advisory trace to successful typed model judgments, including a proposed action but never changing the actual policy result, session risk or task. DMSG_RULE_TWEAK_MODE=off disables it. Enforce is intentionally blocked until independent safety evaluation and explicit new authorization.

- Source: integration/rule_tweak_shadow.py and configs/rule_tweak_shadow.json
- Review: docs/V58_RULE_TWEAK_SHADOW_REVIEW.md
- Checks: python -m unittest discover -s tests_rule_tweak_shadow -v
- Original 12-case replay was derived from past development data and does not measure improvement on this main or actual Zoro. Track 1 evidence and existing Rulebook are distinct.


## v5.9 공식 사기 유형·Jev Shadow·Ambient 3D 확장 (2026-11-19)
- 실제 공개기관 KISA·FTC·FBI IC3 등의 **사기 유형 자료 15건**에서 30종의 재구성 합성 메시지와 12종의 오탐 방지 반례를 수록했습니다. docs/research/SCAM_EVIDENCE_ATLAS_2026_KO.md. **실제 피해 문자 원문도, 정답 라벨도, fine-tuning 결과도 아닙니다.**
- TypeSafe Jev 1.14.0 선택형 보조 클라우드: 별도 과금 운영자 설정 + API 키 + 입력별 외부전송 동의가 필요합니다. 기본적으로 꺼져 있습니다. **무료 API가 아닙니다.** 로컬 무료 어휘 점검은 모델 추론이 아닙니다. docs/V58_JEV_CLOUD_TEXT_STUDIO.md.
- 기존 v5.9 유리 구체·5단계 판단 UI를 유지하면서 배경에 흐릿한 절차적 3D 토러스 매듭, 반례 샘플 버튼, 보조 관측 패널을 추가했습니다. 감소 모션·숨김 탭에서는 애니메이션을 줄이거나 정지합니다.
- 기존 Zoro-1·v5.1 정책·보류 업무·Rulebook은 그대로 유지합니다. Zoro 모델 가중치는 변경/재학습되지 않았습니다.
- 확인: python -m unittest discover -s tests_v59 -v && python -m unittest discover -s tests_secondary -v && node --test tests_v59/test_ambient_research_ui.js tests_secondary/test_secondary_ui.js.
- 실제 Jev/Zoro 신규 추론 성능 향상, 전체 독립 인간라벨 평가, 실기기 렌더링은 미검증입니다.

## 라이선스 / License

직접 작성한 IteraGuard 코드와 문서는 [Apache-2.0](LICENSE)으로 제공합니다. [적용 범위·예외](LICENSE_SCOPE.md), [외부 자료 고지](THIRD_PARTY_NOTICES.md)를 함께 확인하십시오. CC BY-SA 데이터·모델, 외부 자료 및 기존 APK/ZIP/스킬 패키지는 Apache-only로 변경하지 않습니다.

[정비 검증 보고서](docs/licensing/REVIEW_20261119.md)의 잔여 과제를 확인하십시오. `python tools/check_licensing.py`는 고지·분류·해시의 정적 검증이며 권리 전수 인증이 아닙니다.


## 2026-11-19 · v5.9 소비자 화면 단순화 / Rulebook 개선계획 검수
일반 화면은 **비식별 합성 메시지 붙여넣기 → 판단하기 → 이해하기 쉬운 위험 안내 → 상황별 후속 대화** 순서로 단순화했습니다. 엔진 자체의 Zoro/정책/SQLite Task 처리는 변경하지 않았습니다.
- 공식 사례 프리셋, 실험용 Jev 클라우드 패널, 내부 확인업무 선택·보고 UI는 기본 화면에서 숨겨져 사용자에게 표시되지 않습니다. 그렇다고 Jev가 자동 호출되거나 기관 확인이 자동으로 실행되는 것은 아닙니다.
- 판단 과정 패널은 기본적으로 숨기고 **실제 평가 HTTP 요청이 진행될 때만** 화면 상단에 표시합니다. 내부 서버 단계별 실시간 이벤트가 없으므로 임의의 퍼센트·가상 진행 시각을 제공하지 않습니다.
- 빈 입력은 요청하지 않습니다. 기존 미해결 위험·인간 확인 필요는 결과에 계속 표시합니다. 기존 보류를 안전으로 자동 해제하지 않습니다.
- 지금은 합성·비식별 테스트 전용이며 실제 SMS 개인정보, 원본 계좌정보, OTP, 비밀번호 전송을 허용하는 제품이라고 주장하지 않습니다. Zoro 실모델/정확도/실브라우저 반응형 완성은 별도 검증해야 합니다.
- 검수: `docs/reviews/RULEBOOK_ZORO_REMEDIATION_REVIEW_CURRENT_20261119.md`; 동봉 원본 `docs/reviews/RULEBOOK_ZORO_REMEDIATION_PLAN_KO_20261119_SOURCE.md`. RB-1~9/ZP-1~10의 위험 검토를 수록하되 실제 정책 변경/가중치 학습은 수행하지 않았습니다.
- 테스트: `python -m unittest discover -s tests_consumer -v` 및 `tests_remediation`, 기존 전 회귀검사. '진단 테스트 PASS'는 결함 해결이 아니라 **현행 결함을 재현했다는 뜻**입니다.

한국어 신호등 개선 후보와 실제 모델 실행 명령은 [신호등 질문 비교 및 성능검증](docs/SIGNAL_PAIRED_EVALUATION_KO.md)에 정리했습니다.
