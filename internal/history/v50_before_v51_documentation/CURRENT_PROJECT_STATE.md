# 현재 상태 — v5.0 개발 후보

기준일: 2026-11-04 KST. 현재 판정: **실행·상태관리·배포 기반 수정 및 검증 완료 / 핵심 판단 성능 개선 미완료**.

| 영역 | 현재 상태 |
|---|---|
| 소스 기준 | 사용자 지정 모음의 `[v5.0] IteraGuard_DoubtMeter`; 기존 검증 v5에서 문서만 정리 |
| 실제 모델 | 승인 Zoro-1 Typed, 로컬 kev/RTX5080 BF16/T=1.52. 제품 인증 false, 도메인 보정 NOT_ESTABLISHED |
| 판단 계약 | 원본7문항·순서·0.70 유지, legacy 기본/DRA 비교 |
| 성능 문제 | 정상 과보류·일부 필수중단 누락 미해결. 질문 후보3개 모두 회귀로 미채택 |
| 상태관리 | 아레나 종료·재개, 과거위험 보존, 자기보고/현재턴 분리, 반복 과제 완화 |
| 단문 앱 | 현재 문장만 분석. 아레나의 위험 이력을 이어받지 않음 |
| 개발 평가 | 실제 질문388회 및 AI 개발25개. 인간 독립 평가 아님 |
| 검증 | 최초 독립 추출 v5 42/v49 64 PASS, Python/JS24488, NLP221, 고정49, APK 정적서명 PASS |
| 미실행 | 독립 인간 평가, Android 실기기/iOS, 실제 기관 확인/평판 조회/은행 제어 |
| 이번 정리 | Markdown/문서 진입점·원장·색인·manifest/FULL만 정리. 알고리즘 변경·새 추론 없음 |

다음 성능 작업은 docs/V50_OPEN_ISSUES.md를 따른다. 현재 v5 이름이나 테스트 PASS를 정확도 향상/최종 제출 완료로 해석하지 않는다. L2본문/GOLDEN-V33-G7/기관질문/L1 구체 승인 항목은 현행 유지한다.

현재 명세: docs/PRD_v50.md, docs/SYSTEM_PROMPTING_v50.md, configs/v50_contract.json. 상세 이력: internal/VERSION_LEDGER.md. 역사 문서는 docs/00_DOCUMENT_MAP.md에서 구분한다.
