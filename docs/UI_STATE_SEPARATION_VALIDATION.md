# UI 상태 분리 구현·검증 보고서

2026-11-19 · 기반 main ba5d8f4 · 통제 응답 기반 검사

## 구현
- 현재 문장 판단은 current_turn_action/current_turn_reason에서 표시합니다. 최종 action/reason과 정책 판단은 변경하지 않습니다.
- 이전 위험은 prior_pause_before 또는 PRIOR_RISK_UNRESOLVED로 구분합니다. 이번 문장의 첫 위험 감지를 이전 위험으로 잘못 설명하지 않습니다.
- 이전 업무는 생성 버전(created_version)을 현재 버전과 비교합니다. 이 필드를 응답에 추가했으며 데이터베이스 구조와 업무 처리 정책은 그대로입니다.
- 결과 카드에서 설명, 다음 행동, 이전 미해결 상태를 나누고 겹치는 고정 경고를 제거했습니다. 모델 실패는 판단 완료처럼 표시하지 않습니다.
- 별개의 메시지 분석 시작: 새 세션 성공 후에만 입력과 화면을 초기화합니다. 이전 사건을 종료·해결·삭제하지 않습니다. 실패하면 입력과 결과를 보존합니다.
- 이전 기록 보기와 기록 전환을 복원했습니다. 분석 중에는 전환을 막습니다. 같은 사건의 후속 문장은 기존 분석을 이어가도록 안내합니다.
- 채팅 요약에도 동일한 현재 문장 설명을 사용합니다. 휴대폰에서 입력과 결과가 후속 채팅보다 먼저 배치됩니다.
- 소비자 화면의 내부 업무 수정·유료 Jev 기능은 계속 숨깁니다. 기술 상세와 저장 기록에서 상태를 조회할 수 있습니다.

## 검증 결과
- Python 11개 회귀 모음: 236건 실행, 234건 통과, 기존 2건 건너뜀. 정책·계약·저장·UI·대화·알려진 한계 검사 포함. 알려진 한계 특성화 검사의 성공은 그 한계의 해결을 뜻하지 않습니다.
- Node UI 검사: 68건 통과(기존 66건 및 추가 채팅 상태 회귀 2건).
- Edge 실제 브라우저: 1440px/390px에서 입력·붙여넣기, 새 분석 실패 보존, 성공 후 초기화, 이전 기록 재선택, 기존 세션 상태 완전 일치, 가로 넘침 없음, JavaScript 오류 없음.
- 정책 코드 수정 없음. store.py 변경은 응답에 기존 created_version 필드 노출 1줄뿐입니다.
- 라이선스 예외 608개 파일의 무결성 검사 통과. 전체 권리 확인을 주장하지 않습니다.
- 최초 제한 환경에서는 로컬 HTTP 접속이 차단됐습니다. 로컬 접속 허용 환경에서 해당 검사를 다시 실행해 통과했습니다.

## 한계
실제 Zoro 추론·신원 인증, 공개 사이트 배포 및 인증 이후 경로는 이번 검사에 포함되지 않았습니다. 브라우저 검사는 CONTROLLED_FIXTURE_NOT_ZORO입니다. 이전 위험은 사용자 완료 보고만으로 해제되지 않습니다. 이 수정은 표현과 세션 선택을 개선하며 모델 정확도 향상이나 사기 여부 확정을 주장하지 않습니다.

## 재현
Python: 각 tests_rulebook, tests_rule_tweak_shadow, tests_v59, tests_secondary, tests_conversation, tests_consumer, tests_remediation, tests_v56, tests_v54, tests_v51, tests_demo_validation에 unittest discover 실행.
Node: tests_v50/test_session_ui.js, tests_v53/test_choice_ui.js, tests_secondary/test_secondary_ui.js, tests_v59/test_ambient_research_ui.js, tests_conversation/test_guided_chat_ui.js 및 tests_demo_validation의 API/recovery 검사.
브라우저 작업 기록: 로컬 outputs/responsive_qa/check_state_separation.py 및 state-separated-1440.png, state-separated-390.png. 별도 통제 서버 18893 사용. 로컬 실행 도구는 배포 산출물이 아닙니다.
