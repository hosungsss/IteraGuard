# 의심계 PRD v5.6

주 사용자 여정은 의심 메시지 수신 후 실제 행동 전에 확인하는 합성 시연이다. Zoro 현재 판단과 서버의 기존 위험 기억을 분리한다.

| 요구사항 | 구현 | 수용 검사 |
|---|---|---|
| 현재 위험마다 확인업무 보존 | 입력 HMAC·행동·사유 키, OPEN 최대 64 | second_risk, distinct_asks, completed_duplicate |
| 위험 업무 우선·선택 가능 | PAUSE 우선 정렬, UI taskQueue | queue selection DOM, HTTP/state |
| 오류 시 상태 보존 | 계약 검사 후 해시, 비정상 값 FAILED | nonfinite_response, capacity atomic |
| 검증 가능한 기록 | UTC·요청·소스 지문·응답 해시·단계 | evidence_queue tests |
| 실행 출처 구분 | CONTROLLED_CLIENT/LOCAL_HTTP_MODEL_UNATTESTED + status | latency source groups |
| 안전 해제 권한 제한 | USER_REPORTED와 prior_pause 독립 | existing lifecycle tests |

세션당 열린 업무 한도는 실험 설정 64다. 한도 초과는 TASK_CAPACITY_REACHED로 현재 트랜잭션을 취소하며 저장된 위험·업무를 유지한다. 종결 보고만으로 안전을 인증하지 않는다. 신규 typed model 계약·외부 송금·기관 확인·모바일 NPU는 구현 범위가 아니다.

검증 결과와 제한은 CRITIQUE_AND_EXPERIMENT.md를 따른다. 요구사항의 통과는 독립 실제 사기 예방이나 수상을 증명하지 않는다.
