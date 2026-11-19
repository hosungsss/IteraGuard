# v5.0 현행 인수인계

이 폴더가 사용자 지정 버전 모음의 최신 개발 기준이다. 먼저 CURRENT_PROJECT_STATE.md → all.md → docs/V50_OPEN_ISSUES.md → docs/00_DOCUMENT_MAP.md → internal/VERSION_LEDGER.md를 읽는다. 현재 계약은 configs/v50_contract.json 및 docs/*v50.md를 따른다. vendor/와 역사 문서를 현재 승인·성능으로 오해하지 않는다.

핵심 목표인 조로의 정상/위험 판단 개선은 미완료다. 완료한 것은 공통 실행 계약·trace·세션 업무·디버깅·개발 실험·배포 검증이다. 388회 비교에서 세 변경 후보는 새 회귀로 HOLD했고, 원본 7문항과 기준값 0.70은 유지했다. 'v5 완성', '안전성 검증 완료', '우승 준비 완료'로 기록하지 않는다.

현재 기준은 legacy, DRA는 비교다. 모델은 현재 문장만 입력받고 아레나가 과거 위험을 별도로 유지한다. CLOSED_UNRESOLVED/사용자 확인 보고는 위험 해제가 아니다. 단문 앱은 세션 위험을 결합하지 않는다. DB 원문/인용/URL 비저장과 파생 분포/offset/보고 보관을 구분한다. 모델 인증 false, T=1.52 제공자 설정, 도메인 보정 NOT_ESTABLISHED를 분리한다.

다음 작업의 P0는 요청 유무/민감 행동 schema 후보와 evidence 범위를 사전 등록 비교하고 정상 부담·필수중단 누락·회귀를 함께 줄이는 것이다. AI 개발 25개는 인간 독립 평가가 아니다. 독립 평가/실기기/구체 팀 합의는 미완료 상태를 유지한다. L2/G7/기관 질문/L1 현행 유지 지시를 임의 변경하지 않는다.

기존 버전 원본을 덮어쓰지 말고 상세 변경은 internal/VERSION_LEDGER.md에 남긴다. 소스 변경 후 tools/validate_v50.py 및 필요한 검사를 실행하고, apps 변경 시 build_distribution_v50.py를 사용한다. 문서만 변경한 경우 모델/앱을 불필요하게 다시 만들지 않는다. 최종 build_release_v50.py 출력은 이 소스 폴더 밖으로 두고 verify_release.py로 확인한다. 가중치·자격증명·실험 DB는 배포하지 않는다.
