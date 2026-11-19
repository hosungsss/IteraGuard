# 의심계 IteraGuard 현재 작업 상태

패키지·Arena 5.6, UI 소스 후보 5.9, 모델 계약 5.1을 구분합니다. 현재 기준은 저장소 소스와 CURRENT_PROJECT_STATE.md, LATEST_VERSION.json이며 상세 이력은 internal/VERSION_LEDGER.md입니다.

현재 UI는 문장 판단과 이전 미해결 상태를 분리합니다. 별개의 메시지 분석 시작은 새 기록을 만들고 이전 업무를 보존합니다. 실패 시 기존 입력·결과를 유지하며, 이전 기록 보기에서 기록을 전환할 수 있습니다. 소비자 화면의 내부 업무 편집은 숨겨져 있습니다. 판단 정책과 모델 계약은 변경하지 않았습니다.

실행은 Python 3.11 이상에서 python -X utf8 -m arena.server --port 8769입니다. 별도 Zoro 서버와 환경변수 설정은 .env.example을 참조하십시오. .env는 자동 로드되지 않습니다. 모델 API는 /v1/systemone입니다.

이번 검증은 통제 응답을 사용한 회귀·브라우저 검사입니다. 실제 Zoro 연결·체크포인트 신원과 공개 사이트 배포는 확인하지 않았습니다. 제출 준비 완료나 정확도 개선을 주장하지 않습니다. docs/UI_STATE_SEPARATION_SOLUTION.md와 docs/UI_STATE_SEPARATION_VALIDATION.md에 요구사항과 결과를 정리했습니다.

프로젝트 작성 코드의 Apache-2.0 적용 범위와 외부 자료 예외는 LICENSE_SCOPE.md 및 THIRD_PARTY_NOTICES.md를 참조하십시오. 상세 변경 이력을 이 파일에 중복 기록하지 않습니다.
