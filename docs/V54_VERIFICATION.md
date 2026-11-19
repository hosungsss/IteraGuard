# 의심계 v5.4 검증 보고서

검증일: 2026-11-19. 범위: 첨부 비판 검토문과 증거 묶음 기반의 로컬 전체 패키지 수정·검증.

## 결론

Arena를 주 실행 경로로 정리한 v5.4 로컬 검증 후보 패키지다. 새 모호 입력의 후속 업무, 중복 억제, 이전 위험 보존, 제한된 민감정보 동의어 처리에 대한 검사를 통과했다. 이번 작업은 신규 Zoro 추론·모델 신원 인증·독립 정확도 검증을 수행하지 않았다.

## 출발 자료와 범위

첨부 IteraGuard_v53_Review_Evidence_20261119.zip은 전체 앱이 아닌 검토 증거 묶음이다. 기존 로컬 전체 `[v5.3] IteraGuard_DoubtMeter.zip`을 기반으로 사용했고 원본은 보존했다. 첨부 원문은 internal/review_v53에 있다. 전체 패키지 기반 ZIP SHA256은 `6eeafd244beba5e214aba62078376695e8d84b305c19b777f8656a926e297bac`이다.

## 이번 검증 결과

| 검사 | 실행 결과 | 증거 |
|---|---|---|
| v5.4 신규 회귀 | 9 통과 | internal/evidence/v54/v54.log |
| 기존 프로필·정책·Python/JS·배포 검사 | 75 중 73 통과, 2 선택 검사 제외 | internal/evidence/v54/v51.log |
| 기존 실험 미들웨어 | 21 통과 | internal/evidence/v54/v52.log |
| 세션 생명주기 | 17 통과 | internal/evidence/v54/lifecycle.log |
| 로컬 HTTP API | 4 통과 | internal/evidence/v54/http_local_verified.log |
| 선택 표시 UI | 16 통과 | internal/evidence/v54/v53_ui.log |
| 세션 UI | 6 통과 | internal/evidence/v54/session_ui.log |

합계 **146 통과, 2 선택 검사 제외**다. Node UI 검사는 모의 DOM/동작 검사이며 브라우저 시각 검증이 아니다. v51 선택 검사 2건은 별도 dev98/dev133 입력 경로를 제공하지 않아 제외됐다. 별도로 AI24 저장 응답 24건을 재생했다. 전체 과거 테스트 557건을 이번에 모두 다시 실행했다고 주장하지 않는다.

HTTP 최초 검사는 실행 환경의 로컬 연결 제한(WinError10013)으로 실패했다. 로컬 통신 허용 후 패키지 버전을 5.1로 기대하던 검사 1건을 5.4 및 contract_version 5.1 확인으로 수정하고 4건 모두 통과했다. Windows 임시 DB 테스트는 연결을 명시적으로 닫도록 수정했다. 실패 기록을 숨기지 않고 함께 보존했다.

## 저장 응답 재생

동일한 기존 AI24 응답 24건에 정책만 다시 적용했다. `V51-F13_ARCHIVE_READING_ACCESS-03` 1건은 ASK_HUMAN/NO_GROUNDED_ACTION_ANCHOR에서 PAUSE_AND_VERIFY/V51_CURRENT_SENSITIVE_EXPOSURE가 됐다. 나머지 23건은 행동이 유지됐다. 원래 모델 확률과 0.70 임계값을 바꾸지 않았다. 근거: internal/evidence/v54/saved_response_replay.json, tools/replay_v54_review.py.

신규 합성 반례에는 직접 요청·동의어·부정 경고·간접 보고·정보 설명·경고와 직접 요청의 복합 문장을 포함했다. 이는 제한된 반례이며 모든 한국어 인용·부정 표현에 대한 보증이 아니다. AI24는 이미 검토·개선에 사용한 개발 재생 자료이므로 독립 validation 성능으로 승격하지 않는다.

## 검토문 항목별 현재 상태

| 항목 | 현재 상태 | 남은 조건 |
|---|---|---|
| F01 주 실행 경로 | Arena 실행 도구·현재 문서·출처 설명 제공 | 발표 장비에서 실모델과 실제 브라우저 연결 점검 |
| F02 새 불확실성의 후속 업무 | 통제 응답으로 기존 결함 재현 후 회귀 검사 통과 | 현재 열린 업무가 있으면 기존 업무를 우선함; 다중 업무 큐는 별도 |
| F03 동의어 근거 | 제한된 용어 보완, 반례·저장 응답·Python/JS 일치 검사 통과 | 신규 독립 데이터와 인간 라벨 필요 |
| F04 서버 계약 | 기존 /v1/systemone 유지, /v1/decide 자동 전환 없음 | 새 서버 어댑터·실제 호환성 검증 미구현 |
| F05 다음 행동 | 정보 부족·모델 실패·위험 중지 안내 구분, 재조회 유지 | 기관별 확인·계좌 대조의 세분화는 추가 설계 |
| F06 위험 해제 경계 | 자기 보고와 위험 해제 분리, 이전 위험 유지 검사 통과 | 실제 기관 검증·권한 있는 해제 기능 없음 |
| F07 증거 표현 | 정확도·모델 확률·구간 일치·개발 재생을 구분 | 독립 실세계 성능 미검증 |

## 우선 준비

1. 현장과 동일한 모델 서버에서 /v1/systemone 계약, 모델 이름·리비전·오류 응답을 기록한다. /v1/decide 전용 서버라면 호환된다고 가정하지 않는다.
2. Arena에서 정상·모호·직접 민감정보 요청·연결 실패의 실제 화면 흐름을 리허설하고 새 추론 원본과 환경 정보를 별도 보존한다.
3. 개발에 쓰지 않은 문장을 인간이 독립 검토한 뒤 오탐·미탐·보류·지연을 구분한다. 저장 응답 재생 결과를 수상 근거나 실제 예방률로 제시하지 않는다.

## 배포 경계

패키지와 Arena는 5.4, 질문 계약과 보조 앱 내부 버전은 5.1이다. 재생성된 보조 PWA/APK는 현재 소스 일치 검사를 통과했으나 실기기 실행은 NOT_RUN이다. model weights, real inference, identity attestation, independent human evaluation, browser visual check: NOT_RUN/NOT_VERIFIED.

변경 이력은 internal/VERSION_LEDGER.md, 현행 명세는 docs/PRD_v54.md와 docs/SYSTEM_PROMPTING_v54.md를 따른다. 현재 전체 파일 무결성의 기준은 MANIFEST_V54_SHA256.json이다. 기존 이름의 manifest와 과거 보고서는 해당 과거 스냅샷의 기록이다.
