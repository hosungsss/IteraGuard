# v5.0 폴더·Markdown 정리 보고

정리일: 2026-11-04 KST. 사용자 지정 버전 모음에 **[v5 현재 폴더](../../%5Bv5.0%5D%20IteraGuard_DoubtMeter/README.md)** 를 추가하고, 현재 상태·미완료 과제·구버전 기록을 구분했다. 이 보고는 이번 문서 정리 결과이며, 최초 구현/실험 결과는 v5의 docs/V50_IMPLEMENTATION_REPORT.md를 참고한다.

## 결론과 현재 범위

**폴더 정리·기록·패키지 정합성 검증은 완료했다. 조로의 핵심 판단 성능 개선은 미완료다.** 정상 문장 과보류, 일부 위험 요청의 필수중단 누락, 근거 표시의 의미 품질 문제를 해결 완료로 표시하지 않았다. 별도 추론 LLM 미들웨어가 필수라고 결론 내리지 않았다.

| 항목 | 이번 결과 |
|---|---|
| 최신 작업 폴더 | 모음 루트의 `[v5.0] IteraGuard_DoubtMeter` |
| 시작 문서 | 모음 README → v5 CURRENT_PROJECT_STATE → V50_OPEN_ISSUES → all/문서 안내 |
| 상세 이력 | v5 internal/VERSION_LEDGER.md 단일 원장 |
| 과거 원본 | 기존 Markdown 360개, 보조 파일 31개 재해시 일치; 변경·삭제 없음 |
| v5 문서 지도 | 현재 Markdown 86개 전부 분류 |
| 실행 코드·모델·정책·질문 | 최초 검증 v5와 동일; 이번 작업에서 변경 없음 |
| APK/PWA | 최초 v5 바이트 유지, 소스→PWA→APK 자산 일치 재검증 |
| 새 모델 호출/서버 재시작 | 0회/0회 |
| 배포 정합성 | 새 FULL 486파일, 원본 소스와 새 추출본 모두 PASS |

## 문서 확인 범위

정리 전 Markdown 360개, 서로 다른 내용 159개를 전수 목록화하고 SHA-256을 남겼다. 구버전 243개, 최근 버전 112개, 최상위/보조 Markdown 5개를 빠짐없이 인벤토리에 넣었다. 중복 사본을 제외한 핵심 원장·PRD·현재 상태·실험/승인 자료를 중심으로 검토했다. 모든 파일을 전문 정독했다고 주장하지 않으며, 전문·부분·동일 사본·구조/해시 확인 범위는 각 감사 JSON에 기록했다.

- [전체 원본 목록](existing_markdown_inventory.json)
- [v3.1.0~v4.6 감사](older_versions_audit.json): 버전 계보·기록 규칙·보존 항목
- [v4.7~v4.9 감사](recent_versions_audit.json): 누락/사본·시점 충돌·기본 정책 구분
- [보조 자료 감사](supporting_docs_audit.json): 가이드·Package·Back Data·교재·별도 프로토타입

과거 소프트웨어를 새로 실행하지 않았고 외부 행사/서비스 조건을 다시 조회하지 않았다. 오래된 테스트 수치·기능/승인 주장은 해당 시점의 문서 기록으로 보존했다.

## 발견한 누락과 혼동, 처리

1. 펼친 v4.9 폴더에는 FULL ZIP의 Markdown 30개가 빠져 있었다. v5는 검증된 최초 v5 전체 패키지를 기준으로 만들었다. v4.9 FULL의 Markdown 69개 경로가 현재 v5에 모두 있다.
2. v4.9 FULL에도 상세 VERSION_LEDGER가 없다. v4.7까지의 원장과 v4.9 CHANGELOG 원문을 internal/history에 출처·해시와 함께 보관했다. 없는 v4.8 원장을 추정해 쓰지 않았다.
3. 오래된 all.md에는 이전 버전 헤더·모델 미연결·기본 정책 설명이 누적돼 있었다. 새 all.md는 현재 제품 흐름·실제 실험·제한·다음 과제를 설명하며, 정리 전 all.md는 역사 원문으로 남겼다.
4. Package v1.x는 별도 실험 키트 버전이다. 의심계 제품 v5와 혼동하지 않게 루트 안내에 표시했다. 루트의 오래된 dmsg.skill도 보존하고, 최신 스킬 경로를 v5 폴더로 안내했다.
5. 교재 영수증의 PDF/HTML/START_HERE/ZIP과 Package의 v1.1 ZIP은 지정 로컬 위치에 없다. 별도 iteraguard 프로토타입은 가이드 경로와 로컬 import 대상 9개가 누락돼 완전 실행본으로 기록하지 않았다. 누락은 이번 지정 폴더와 검사한 지원 ZIP 범위다.
6. 옛 Typed NOT_RUN과 현재 로컬 Typed 실행을 구분했다. 현재 388회 질문 비교, 재시작 4요청, 브라우저 7요청은 총 399요청/398수용이다. 세 질문 변경 후보는 HOLD이며 원본 질문을 유지한다. 실행 성공이나 AI 초안 25개를 독립 정확도 개선으로 기록하지 않았다.
7. 근거 offset 일치와 의미 있는 근거 선택, 자기보고와 기관 인증, 종료/재개와 위험 해제, APK 정적 검사와 실기기 실행을 각각 구분했다.

## 저장 구조와 기록 규칙

현재 진입 문서는 README/CURRENT_PROJECT_STATE/MASTER_HANDOFF/all이며, CHANGELOG는 원장 링크만 안내한다. 문서 지도 docs/00_DOCUMENT_MAP.md와 미완료 목록 docs/V50_OPEN_ISSUES.md를 추가했다. 이전 문서 원문은 internal/history, 파일별 감사와 과거 배포 근거는 internal/organization에 보관했다. 과거 배포 근거는 prior_release/SCOPE.json으로 적용 범위를 표시했다.

이번 정리에서는 기존 v5 파일 중 안내/원장 Markdown 6개를 수정하고, 스킬 ZIP 별칭 4개와 manifest를 재생성했다. 스킬 내부 내용은 동일하다. 새 문서·감사 근거 21개를 추가했다. 실제 변경 목록은 [소스 보존 비교](source_preservation.json)에 있다.

FULL은 소스 폴더 바깥 모음 루트에 뒀다. 최초 ZIP과 이전 workspace는 보존했고, LATEST_VERSION.json은 새 소스/패키지/보고서 위치를 가리킨다. 실행 중인 브라우저 서버를 새 경로로 재시작하지 않았다.

## 검증과 배포

- [현재 소스·ZIP 검증](source_release_verification.json): manifest·스킬 별칭·배포 해시·소스/앱 자산 PASS
- [새 추출본·ZIP 검증](clean_release_verification.json): 동일 검사 PASS, 오류 0
- [기존 파일 보존](historical_preservation.json): MD 360개·보조 31개 일치; 구 v4.9 FULL·루트 스킬 보존
- [기계 판독 영수증](ORGANIZATION_RECEIPT.json)

새 FULL: `IteraGuard_DoubtMeter_v5_0_FULL_CANDIDATE.zip`  
크기: 87,700,266 bytes / 486 files  
SHA-256: `6f13ae0ecfdab0801a4d2e242f744bbdeb9335c4abf3478a01f324d5daff99d2`

최초 검증 v5 FULL SHA-256 `b2ab13478290502fac9e088c17f159fc7ad2902d5ab2507edecf4acc03eb73ae`는 그대로 보존했다. 새 해시는 문서/근거 파일 정리와 재패키징에 따른 것이며, 모델이나 앱 성능 개선을 의미하지 않는다.

## 다음 작업

정상 과보류와 필수중단 누락을 줄일 schema/rubric 및 evidence 범위 후보를 사전 등록하고, 원본과 회귀를 함께 비교해야 한다. 사람 독립 평가·실기기·구체 팀 합의는 별도 미완료다. 사용자의 '승인 전까지 현행 유지'에 따라 L2 본문/G7/기관 질문/L1 상태를 유지했다. 행사 GPU/API·외부 API 허용·참가/제출 조건의 현재 공식 확인도 이번 로컬 정리의 완료 범위에 넣지 않았다.
