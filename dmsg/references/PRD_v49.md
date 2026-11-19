# 의심계 PRD v4.9

개정일: 2026-11-04. 제품 계보: v4.8 → v4.9 검증 아레나 확장. 실험 키트 계보: v1.1 → v1.2. 제품과 키트 버전을 구분한다. 본 개정은 우승 기획서의 P0를 구현하는 개발 후보이며, 실제 Zoro-1 실행과 효과 검증 완료를 뜻하지 않는다.

## 1. 제품 판단

의심계는 합성 대화에서 요청된 행동을 해석하고, 다음 확인 작업을 선택하며, 후속 관측을 받아 안내를 갱신하는 로컬 검증 아레나다. 우승 전략은 단일 사기 점수의 강조보다 **입력 변경 → 판단 → 작업 생성 → 관측 → 재판단**의 작동 증거를 보여주는 것이다. 이는 전략적 추론이며 공식 심사 배점이나 수상 예측이 아니다.

주력 사용자는 불확실한 요청을 받은 상황을 시험하는 시연 참가자다. 결과는 사용자 확인을 돕는 안내이며 금융·통신 실행 권한이 없다. 실제 개인정보 입력은 범위 밖이며 UI와 API는 합성 입력 확인을 요구한다.

## 2. 개체·관계와 상태

| 개체 | 속성·관계 | 상태·제약 |
|---|---|---|
| Session | id, version, prior_pause | version은 커밋마다 증가. 이전 중단 위험은 자기 보고로 해제하지 않음 |
| Turn | request_id, text, expected version | text는 요청 동안만 사용. 원문 SQLite 저장 금지 |
| Decision | 질문별 분포, 현재 발화 안내, 세션 안내, reason | 현재 발화와 과거 미해결 위험을 구분 |
| VerificationTask | id, session, created_version | OPEN → REPORTED_COMPLETE. 실제 기관 검증 완료 상태는 없음 |
| Observation | task_id, 범주, provenance | USER_REPORTED. 다른 세션·닫힌 작업은 거부 |
| AuditEvent | request_id, version, 정책·모드·분포·offset | 원문·인용 제외. 로컬 DB 수정 방지 인증은 아님 |
| ModelArtifact | 모델 id/revision/head/runtime | 모델 에코는 체크포인트 인증이 아님 |

시간 순서: 새 세션 v0 → 첫 판단 v1/작업 생성 → 관측과 새 대화 v2/새 모델 요청 → 작업 재조회. 입력이 늦게 돌아오면 커밋 시 version을 재검사한다. 같은 request_id와 같은 요청은 이전 결과를 반환하고, 내용이 다르면 충돌이다.

관점 차이: 참가자는 다음 행동과 한계를, 개발자는 raw 계약·원인·지연을, 심사위원은 실제 모델 기여와 실행 증거를 확인한다. 표시 문구와 평가 지표는 같은 원천 결과에서 나온다.

## 3. 필수 기능과 검증 연결

| ID | 요구 | 구현 | 수용·근거 |
|---|---|---|---|
| R01 | v4.8 계약 보존 | vendor/dmsg, integration/v48.py | 7문항·원본 0.70 유지. 원본 325 tests PASS |
| R02 | 실제 요청과 실패 구분 | arena/probe.py, ModelClient | 실제 endpoint 시도 4건/응답 0건. 연결 FAIL |
| R03 | 확인 작업 저장·재조회 | arena/store.py, SQLite | 키트 task/reopen/HTTP 테스트 PASS |
| R04 | 관측 후 새 판단 | Arena.evaluate | 새 infer 호출·새 version 테스트 PASS, 모델 STUB 사용 |
| R05 | stale/중복/세션 경계 | optimistic commit, request digest | 충돌·cross-session·late response 테스트 PASS |
| R06 | 실패 때 fixture 대체 금지 | 예외→MODEL_UNAVAILABLE/ASK_HUMAN | 실패·빈 확률 테스트 PASS |
| R07 | 원문 비저장 | offsets·범주만 DB 저장 | 원문 표식 비저장 테스트 PASS |
| R08 | 최소 UI | arena/web, server | 실제 HTTP 경로·보안 헤더 PASS. 시각적 UX 시험 별도 |
| R09 | 실제 Zoro-1 추론 | 승인된 checkpoint와 kev 필요 | 접근 401, NOT_RUN. 공개 Zoro 생성과 구분 |
| R10 | 대상 과제 효과 | 별도 미열람 평가 | NOT_RUN. 기존 회귀·STUB 통과는 정확도 증거 아님 |
| R11 | 공개 Zoro 생성 비교 | arena/generation_server.py, generation_client.py, UI | 실제 GPU·HTTP·화면 실행 PASS. Zoro-1 Typed Decision 대체 아님 |

## 4. 모델·정책 계약

정본은 `vendor/dmsg/prototype/model_bridge.py`의 SPEC과 questions(), `typed_contract.py`다. 7문항은 q_action, q_speech, q_scam, q_claim, q_pressure, q_risk, q_evidence다. q_claim/q_risk/q_evidence는 선택 보조 문항이다. 누락·오류 시 dropped_optional로 기록한다. 필수 q_action/q_speech/q_scam/q_pressure의 불량은 실패 경로다.

행동: transfer, otp, remote_install, personal_data, link, secrecy, none, unclear.
화행: direct_request, reported_or_quoted, negated_or_warning, unclear, informational.
주의 수준: none, low, moderate, high.

모든 분포는 유한한 [0,1], 합 허용오차 0.002 등 기존 정규화를 적용한다. 0.70은 검증된 최적 임계값이 아닌 기존 데모 정책이다. 보류를 줄이기 위해 임의로 낮추지 않는다. DRA/indicator 후보는 비교 실험용이며 기본 정책으로 승격하지 않는다.

출력은 NO_STRONG_SIGNAL, CAUTION, PAUSE_AND_VERIFY, ASK_HUMAN만 사용한다. NO_STRONG_SIGNAL은 안전 보증이 아니다. 문자열 근거 위치 검사는 한국어 의미 또는 발신자의 신원을 인증하지 않는다. q_scam의 수치는 실제 사기 발생 확률이 아니다.

세션 확장 정책: 과거 PAUSE_AND_VERIFY가 있으면 새 발화가 약한 안내더라도 세션은 ASK_HUMAN을 유지하고 `current_turn_action`을 따로 보여준다. 해제 절차는 미구현이다. 이 보수성으로 정상 보류가 지속될 수 있으므로 개선 성능으로 주장하지 않는다.

## 5. API와 로컬 실행

- POST /api/start `{}` → session_id/version.
- POST /api/evaluate `{session_id,version,request_id,text,synthetic_only:true,task_id?,observation?}`.
- GET /api/state?session_id=... → 저장된 version/tasks/events.
- POST /api/generation-compare `{text,synthetic_only:true}` → 공개 Zoro 생성 비교. 최대 300자, 고정 loopback:8010, 정책·세션 상태 변경 없음.
- observation: NOT_CHECKED, USER_REPORTS_CONFIRMED, USER_REPORTS_DENIED, UNRESOLVED.

관측 범주는 코드 상태 갱신에만 사용한다. 새 text에 관측을 반영한 문장을 제공하면 해당 텍스트를 새로 추론한다. 이 버전은 누적 대화 전체를 모델에 입력하거나 기관 조회를 수행하지 않는다. 독립적인 상태/관측을 LLM reasoning으로 둔갑시키지 않는다.

`python -m arena.server` → 127.0.0.1:8766. SQLite 기본 경로 runs/arena.sqlite3. 기존 `python -m prototype.server`(vendor/dmsg)는 보존된 기존 UI다. 새 UI는 웹·Android 전체 앱을 대체하거나 APK를 갱신한 것이 아니다.

## 6. 평가·발표

같은 입력·정책에서 규칙 기준선/실제 Typed Decision을 비교하고, 무조건 ASK_HUMAN 기준선도 보고한다. 정상 불필요 중단, 정상 보류, 위험 개입 누락, 비보류 coverage, 작업 완료·모델 실패·지연을 분자/분모와 함께 제시한다. 테스트 개수는 성능 표본 수와 합산하지 않는다.

이미 열람한 48/25 문장은 회귀용이다. 새 미열람 패밀리와 독립 주석이 없는 상태에서 정확도 향상·사고 예방을 주장하지 않는다. 생성 Zoro가 동작하더라도 Zoro-1 판단 헤드 실행을 대체하지 않는다.

시연 순서: 정상 경고 → 질문형 OTP 요구 → 경고 뒤 별도 요구 → 확인 작업 ID 재조회 → 사용자 관측/새 문장 → 새 version과 이전 위험 유지 → 모델 장애. 공식 발표 시간이 확정되면 3분 내부 연습안을 조정한다.

## 7. 비목표와 남은 게이트

실송금 차단, 계좌 동결, 실전화 종료, 연락처 접근, 실제 OTP 수집, 음성 딥페이크 탐지, 기관 신원 인증, NPU 개선, 새 APK 실기기 검증은 완료 범위가 아니다. 원문 비저장은 개인정보 자동 검출·익명화를 보증하지 않는다. DB 분포·offset도 민감한 파생정보가 될 수 있으므로 합성 실험만 한다.

최종 릴리스 승격 조건: 승인된 Zoro-1 체크포인트/헤드/kev revision·온도 기록 → 실제 7문항 응답 → 재시작 3회 재현 → 새 평가 split 고정 → 정상·위험·보류 지표 공개 → UI 사용자 검토. 현재 rc 표기를 유지한다.

## 8. 출처

- [우승 기획 기준](https://hackathon.trillionlabs.co/#top): Track 1 판단·행동, 구체 심사 당일 공지. 일정·규정은 최신 공식 공지 재확인.
- [Trida Decision](https://trida.trillionlabs.co/decision/): typed 질문과 옵션별 분포. 대상 사기 도메인 성능의 증거는 아님.
- [Zoro-1 모델 카드](https://huggingface.co/trillionlabs/Zoro-1): 판단 헤드·kev export·온도 1.52 설명, 접근 조건.
- [사용자 전달 Zoro](https://huggingface.co/trillionlabs/Zoro): 생성 모델, 별도 체크포인트. 공개 API revision e8b7dc33b6e30b01ba59c46364fced85342ff4ff 확인.
- `evidence/v49/`의 실제 테스트·접속 기록과 이전 `docs/PREVIOUS_RC1_UPGRADE_REPORT.md`. 문서 주장과 현재 실행을 구분한다.


## v4.9 전체 소스 배포 보완

최신 실행·수정·미완료 상태는 V49_UPGRADE_REPORT.md 및 evidence/v49/를 따른다. 공개 Zoro 생성 비교의 실제 재실행 4건과 코드 회귀 42/325개를 구분한다. Zoro-1 Typed 헤드 추론·Android 실기기 실행·독립 성능은 미검증이다. v4.9 디버그 APK/PWA는 별도 소스 빌드·정적 검증을 수행한다. 이전 실험 키트 v1.2의 구조를 전체 제품에 통합했다.


## v4.8 동일 형식 배포

배포는 펼쳐진 소스 폴더, 현재 버전 스킬 4개 별칭, 새 v4.9 디버그 APK/PWA, 통합 문서·인수인계·감사 보고서·해시로 구성한다. 최종 상태는 FORMAT_ALIGNMENT_REPORT.md를 따른다. APK는 PC GPU 모델을 내장하지 않고 오프라인 분석과 PC 검증 안내를 제공한다. 실모델 비교는 별도 arena/생성 서버를 사용한다.
