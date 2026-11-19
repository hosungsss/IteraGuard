# v5.0 개발 후보 인수인계

먼저 README.md, CURRENT_PROJECT_STATE.md, docs/V50_IMPLEMENTATION_REPORT.md, docs/V50_TRACEABILITY.json, configs/v50_contract.json을 읽는다. 기존 all.md의 v4 기록은 역사이며 최신 실행 사실을 대신하지 않는다.

원본 7문항/선택지 순서/0.70을 보존한다. 기본 legacy·비교 dra이며 두 정책의 안전성은 독립 검증 전이다. 388회 새 개발 실험에서 단독 질문 후보 세 개 모두 회귀가 있어 미채택이다. AI 25개를 독립 인간 평가로 부르지 않는다.

Python/JS 공통 evaluate_current/evaluateCurrent 다음 apply_local_layers/applyLocalLayers를 정확히 한 번 적용한다. 세션 위험을 현재 모델 출력으로 표시하지 않는다. CLOSED_UNRESOLVED는 안전 해제가 아니다. DB에는 원문/인용/URL을 저장하지 않는다. trace는 분포/offset 등 파생정보를 보존하므로 익명 원문 재생 자료가 아니다.

현행 빌더/검사는 tools/*_v50.py 및 tools/verify_release.py다. 모델 가중치/환경/토큰은 패키지 밖에 있다. 새 소스 수정 후 과거 빌드 PASS를 재사용하지 말고 자산/manifest 지문을 다시 확인한다. 독립 평가와 실기기 NOT_RUN을 성공으로 바꾸지 않는다. 사용자 지시를 우선하며 구현 허가를 다시 묻지 않는다. L2/G7/기관질문/L1의 기존 구체 결정은 그대로다.
