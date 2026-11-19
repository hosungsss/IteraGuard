# 의심계 PRD v5.4

## 제품 목적과 범위

Track 1 시연의 중심은 모델이 제안한 요청 해석을 비파괴 확인 행동으로 연결하는 Arena다. 현재 문장만 모델에 제공하고, 서버는 이전 위험과 업무 이력을 별도로 관리한다. 팀 리더는 최한길이다. 수상·실피해 예방·사기 분류 정확도는 보장하지 않는다.

## 요구사항과 추적

| ID | 요구사항 | 구현·검증 |
|---|---|---|
| R01 | Arena를 주 진입점으로 제공, 입력 출처와 판단 출처 구분 | run_hackathon.ps1, arena/web/index.html, manifest |
| R02 | 이전 업무 완료 보고와 새 모호 입력이 함께 오면 새 확인 업무 생성 | arena/store.py, tests_v54/test_workflow.py |
| R03 | 같은 입력·같은 사유의 반복 업무 억제, 사유 변경은 새 업무 허용 | test_same_input_reason_deduplicates_and_retry_is_identical, test_same_input_changed_reason_creates_task |
| R04 | 이전 위험만 상속된 ASK는 무한 업무 생성 금지 | test_inherited_risk_does_not_create_endless_tasks |
| R05 | 일회용 확인 코드 동의어에 모델 현재 요청·노출 근거와 절 단위 가드 함께 적용 | configs/v51_semantic_rules.json, tests_v54/test_lexical.py |
| R06 | 모델 연결 문제·정보 부족·위험 중지 안내 구분, 재조회에도 유지 | Arena._task_result, test_restart_preserves_guidance_and_private_fingerprints |
| R07 | 사용자 보고는 USER_REPORTED이며 위험 해제 권한 없음 | prior_pause, CLOSED_UNRESOLVED, 기존 세션 테스트 |
| R08 | 실행 소스와 JS 자산 계약 일치 | export_v51_semantic.py, export_v51_contract.py, tests_v51 |

## 상태와 제약

행동은 NO_STRONG_SIGNAL / CAUTION / PAUSE_AND_VERIFY / ASK_HUMAN 네 가지다. NO_STRONG_SIGNAL은 안전 인증이 아니다. 업무 상태 OPEN/REPORTED_COMPLETE와 세션 위험 상태는 별개다. 동시 열린 업무가 있으면 기존 열린 업무를 우선 제시한다. 다중 위험별 병렬 업무 큐는 이번 범위가 아니다.

저장소는 SQLite다. 입력 원문 대신 HMAC 지문을 사용하며 보고 결과와 판단 추적을 저장한다. 개인정보를 실제 입력하지 않는 합성 시연이 범위다. 위험 해제, 실기관 인증, 외부 송금·연락은 구현하지 않는다.

## 평가 수용 기준

워크플로 회귀, 어휘 반례, Python/JS 정합성, HTTP와 UI 상태 검사를 통과해야 한다. 저장 AI24 응답은 개발 재생 자료로 취급한다. 동일 자료를 보완에 사용했으므로 독립 성능 검증으로 재사용하지 않는다. 새로운 인간 검토 데이터와 모델 신원 확인을 별도 완료해야 실제 성능을 주장할 수 있다.
