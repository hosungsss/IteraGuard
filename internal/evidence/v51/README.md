# v5.1 로컬 구현·실험 증거

기준일 2026-11-04. 실제 모델 요청 557회: 등록 실험544회 + 브라우저/API/서버 재시작13회. 모델 가중치·HF 토큰·서명 개인키·SQLite 원문 기록은 포함하지 않는다. 실험의 raw는 파싱된 JSON 응답이며 인증된 원격 원본이나 정확한 HTTP wire 기록이 아니다.

- experiments/stage1_legacy_evidence~stage7_locked_validation24: 단계별 사전 동결, 모델 응답, 결과, 지표, 실행 원본 사본. stage5 정책/3의 실패 결과도 보존한다. 마지막 후보는 정책/4이다.
- full_pipeline_validation: 보관 응답314개, 현재 턴 정책/로컬 레이어 Python·JS 대조628회와 표시 품질. 새 추론은0이다.
- consolidated_checks: Python179 PASS/선택적2 SKIP, Node UI·전송·세션59 PASS, 근거18 PASS. 최초 실패와 수정 뒤 결과를 모두 보존한다.
- browser: 실제 브라우저 화면/접근성 기록과 API 검증. 실제 Zoro8회 + 별도 DRA7문항1회. 기본 browser-client 권한 오류 뒤 CUA 대체 연결로 검사했다.
- runtime_restart: 별도 프로세스4개/재시작3회/모델4회. 이전 위험과 확인 작업 유지, 중복 요청은 추가추론0.
- distribution_build.json: PWA/APK/desktop 자산32개와 Android version51/5.1 일치. 서명 검증·기기 실행과는 구분한다.
- actual_call_accounting.json: provider counter792→1349, 자체 집계557과 일치.

개발 데이터와 잠금24 모두 AI 합성이다. 인간 독립 성능, 의미 구간 독립 판정, Android/iOS 실기기는 NOT_RUN이다. 모든 절대 경로는 당시 실행 출처이고, 패키지의 상대 경로가 현재 보존 위치다. FULL 자체의 해시는 순환 포함을 피하기 위해 ZIP 옆의 외부 배포 영수증에 둔다.
