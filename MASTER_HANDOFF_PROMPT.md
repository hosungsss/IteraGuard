v5.2 handoff preflight: uploaded v5.1 source and hash are the frozen baseline. Read README, CURRENT_PROJECT_STATE, docs/V52_DECISION_MIDDLEWARE_ARCHITECTURE.md, docs/V52_ADVERSARIAL_AUDIT.md and internal/VERSION_LEDGER.md. Do not promote experimental logistic or treat raw q_scam as fraud risk. Preserve actual current decision policy. The named Decision Agents v3.1 PDF is not part of or to be copied into the package.

# v5.1 현행 인수인계

CURRENT_PROJECT_STATE.md → all.md → docs/V51_OPEN_ISSUES.md → docs/V51_IMPLEMENTATION_REPORT.md → docs/00_DOCUMENT_MAP.md → internal/VERSION_LEDGER.md 순으로 읽는다. v50 문서는 보존된 기준선이며 현행 계약은 configs/v51_contract.json, v51_profiles.json, v51_release_selection.json과 v51 명세다.

실제 모델 요청 전에 profile·policy·질문 순서/지문을 동결한다. legacy라는 policy ID만으로 원본 7문항 실행과 11문항 의미 확장 실행을 혼동하지 않는다. DRA는 v50-baseline과만 비교한다. 결과를 받은 뒤 다른 profile로 해석하거나 필수 head 누락을 정상 기본값으로 채우지 않는다.

semantic policy /3은 새 위험 정상처리 1건으로 실패했다. /4는 요청 구체성만으로 무해함을 인정하지 않고 scope=other_request와 간접 이동 차단을 요구한다. 수정 뒤 개발 replay는 개선 방향을 보였지만 필수중단 누락3건과 정상 false PAUSE1건이 남는다. 잠금24 집계에서도 필수중단 누락2/7과 불필요 정상 ASK5/12가 남는다. 개발 및 잠금 AI 결과를 인간 독립 검증·보정 확률·완전한 안전 판단으로 설명하지 않는다.

final24 이후 판단 코드 튜닝은 금지한다. 결함 때문에 판단 경로를 바꾸면 기존 잠금셋을 개발 자료로 전환하고 새 잠금셋으로 검증한다. 최종 UI/전체 후처리/회귀 및 배포 자산 검증 결과는 구현 보고를 따른다. FULL과 별도 추출 검증은 외부 배포 영수증에서 확인한다. 인간 독립 평가와 실기기는 NOT_RUN이다.

근거 표시 모듈은 정책과 원본 앵커를 보존한다. trace의 조건 충족·적용 가능성·최종 규칙, 현재 턴·세션 위험을 구분한다. 종료/재개와 자기보고는 위험 해제가 아니다. 원문/인용/URL 비저장 경계, loopback 전송, 모델 인증 false를 유지한다. L2/G7/기관 질문/L1은 승인 전 현행 유지다.

상세 이력은 internal/VERSION_LEDGER.md에 append하며 과거 보고를 덮어쓰지 않는다. 배포 도구는 build_distribution_v51.py/build_release_v51.py이고, FULL은 소스 밖에 둔다. 최종 source·source→PWA→APK/desktop·스킬·FULL·별도 추출 검증 후에만 상위 최신 포인터를 바꾼다. 모델 가중치·토큰·실험 DB·새 개인 서명키를 배포하지 않는다.
