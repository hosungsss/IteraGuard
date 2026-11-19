# v5 문서 안내와 읽는 기준

기준일: 2026-11-04. **판단 성능 개선은 미완료**이며 현재 상태는 CURRENT_PROJECT_STATE.md, 다음 과제는 V50_OPEN_ISSUES.md를 기준으로 읽는다. 상세 변경 이력은 internal/VERSION_LEDGER.md 한 곳에 기록한다. all.md는 전체 이해 문서이고, CHANGELOG.md는 이력 색인이다.

## 우선 읽기

1. [현재 상태](../CURRENT_PROJECT_STATE.md)와 [미해결 과제](V50_OPEN_ISSUES.md)
2. [전체 이해](../all.md), [현재 PRD](PRD_v50.md), [현재 시스템 지침](SYSTEM_PROMPTING_v50.md)
3. [구현 보고](V50_IMPLEMENTATION_REPORT.md), [요구사항 추적](V50_TRACEABILITY.json), [변경 원장](../internal/VERSION_LEDGER.md)
4. 아래 기능별 참고 문서와 역사 원문

## 시점 충돌을 읽는 방법

옛 문서의 Typed NOT_RUN·메모리 세션·DRA 기본·원격 endpoint 허용을 현재 실행 상태로 옮겨 적지 않는다. 현재는 로컬 Typed 실행 근거, SQLite 세션, legacy 기본, loopback 전송이다. 모델 실행 성공과 판단 성능 개선은 별개다. 사용자의 관측 보고는 기관 인증이 아니며 종료/재개도 위험 해제가 아니다.

`dmsg/references/PRD_v50.md`와 `SYSTEM_PROMPTING_v50.md`는 docs의 대응 정본과 같은 내용이다. 이름이 다른 동일 사본은 별도 검증으로 세지 않는다. 번호 문서 01~26, v4.9 보고서, vendor 및 team_v3_3 원문은 출처·시점과 함께 보존하며 새 팀 승인으로 해석하지 않는다.

## 증거와 감사 범위

- `internal/evidence/v50/`: 최초 구현/실험 당시 증거. 이번 폴더 정리에서 모델을 다시 호출하지 않았다.
- `internal/organization/`: 기존 MD 360개 인벤토리(고유 내용 159개), 버전별/보조자료 감사와 검토 범위. 전수 경로·해시 확인과 전문 정독·부분 검토를 구분해 기록한다.
- `internal/history/PROVENANCE.json`: 보관 원문의 출처·SHA-256. v4.7까지 원장과 v4.9 변경 기록을 보존하며 없는 v4.8 상세 원장을 추정하지 않는다.
- 현재 FULL의 해시·문서 정리 검증 결과는 이 폴더 바깥의 `../LATEST_VERSION.json`과 `../Back Data/v5.0_정리기록_20261104/`에 둔다. 자기 자신을 해시 근거로 포함하는 순환을 피한다.

아래 목록은 이 소스에 있는 Markdown 전체를 분류한 것이다. 각 문서 내용의 정확성·과거 실행 결과를 새로 인증하는 목록은 아니다.

## 현행 진입점·명세 (17개)

| 문서 경로 | 용도 |
|---|---|
| [CHANGELOG.md](<../CHANGELOG.md>) | 상세 원장으로 연결하는 색인 |
| [CURRENT_PROJECT_STATE.md](<../CURRENT_PROJECT_STATE.md>) | 현재 완료/미완료 상태 정본 |
| [MASTER_HANDOFF_PROMPT.md](<../MASTER_HANDOFF_PROMPT.md>) | 다음 작업자 인계와 변경 경계 |
| [README.md](<../README.md>) | 현재 실행법·배포 범위와 진입점 |
| [all.md](<../all.md>) | 현재 제품 전체 이해/NotebookLM 진입점 |
| [apps/README.md](<../apps/README.md>) | 앱 실행/빌드 범위 |
| [apps/mobile/BUILD_ANDROID.md](<../apps/mobile/BUILD_ANDROID.md>) | Android 빌드 절차; 기기 실행 증명 아님 |
| [apps/mobile/BUILD_IOS.md](<../apps/mobile/BUILD_IOS.md>) | iOS 빌드 절차; 완료 증명 아님 |
| [dmsg/SKILL.md](<../dmsg/SKILL.md>) | 현재 스킬 진입점 |
| [dmsg/references/PRD_v50.md](<../dmsg/references/PRD_v50.md>) | 스킬용 현재 PRD 사본 |
| [dmsg/references/SYSTEM_PROMPTING_v50.md](<../dmsg/references/SYSTEM_PROMPTING_v50.md>) | 스킬용 현재 시스템 지침 사본 |
| [docs/00_DOCUMENT_MAP.md](<../docs/00_DOCUMENT_MAP.md>) | 전체 Markdown 경로와 읽는 순서 |
| [docs/PRD_v50.md](<../docs/PRD_v50.md>) | 현재 제품 요구사항 |
| [docs/SYSTEM_PROMPTING_v50.md](<../docs/SYSTEM_PROMPTING_v50.md>) | 현재 실행/판단 지침 |
| [docs/V50_IMPLEMENTATION_REPORT.md](<../docs/V50_IMPLEMENTATION_REPORT.md>) | 최초 v5 구현 및 실험 보고; 당시 증거 |
| [docs/V50_OPEN_ISSUES.md](<../docs/V50_OPEN_ISSUES.md>) | 미해결 과제·근거·완료 조건 |
| [internal/VERSION_LEDGER.md](<../internal/VERSION_LEDGER.md>) | 현재 상세 변경 이력 정본 |

## 기존 기능 명세·운영 참고 (39개)

| 문서 경로 | 용도 |
|---|---|
| [dmsg/README.md](<../dmsg/README.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/assets/TEAM_WORKPLAN.md](<../dmsg/assets/TEAM_WORKPLAN.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/ELENCHUS_SNM_4D.md](<../dmsg/references/ELENCHUS_SNM_4D.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/EVALUATION.md](<../dmsg/references/EVALUATION.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/MODEL_CONTRACT.md](<../dmsg/references/MODEL_CONTRACT.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/PLATFORM_INSTALL.md](<../dmsg/references/PLATFORM_INSTALL.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/PRD.md](<../dmsg/references/PRD.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/PROMPTS.md](<../dmsg/references/PROMPTS.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/SYSTEM_PROMPT.md](<../dmsg/references/SYSTEM_PROMPT.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [dmsg/references/TRACEABILITY.md](<../dmsg/references/TRACEABILITY.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/01_PRODUCT_REQUIREMENTS_PRD_KO.md](<../docs/01_PRODUCT_REQUIREMENTS_PRD_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/02_SYSTEM_PROMPT_AGENT_KO.md](<../docs/02_SYSTEM_PROMPT_AGENT_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/03_TRACEABILITY_MATRIX_KO.md](<../docs/03_TRACEABILITY_MATRIX_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/04_DEPLOYMENT_AND_VERIFICATION_KO.md](<../docs/04_DEPLOYMENT_AND_VERIFICATION_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/05_ARCHITECTURE_SNM_4D_KO.md](<../docs/05_ARCHITECTURE_SNM_4D_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/06_SOURCE_INTEGRITY_AND_BARRIERS_KO.md](<../docs/06_SOURCE_INTEGRITY_AND_BARRIERS_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/07_DEMO_AND_PITCH_KO.md](<../docs/07_DEMO_AND_PITCH_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/08_RELEASE_AND_DRIVE_WORKFLOW_KO.md](<../docs/08_RELEASE_AND_DRIVE_WORKFLOW_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/09_MODEL_ADVISORY_CONTRACT_KO.md](<../docs/09_MODEL_ADVISORY_CONTRACT_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/10_SNM_4D_REDTEAM_KO.md](<../docs/10_SNM_4D_REDTEAM_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/11_MODEL_OPERATOR_GUIDE_KO.md](<../docs/11_MODEL_OPERATOR_GUIDE_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/12_SNM_4D_THREAT_AND_ACCEPTANCE_KO.md](<../docs/12_SNM_4D_THREAT_AND_ACCEPTANCE_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/13_MODEL_QUALITY_EXPERIMENT_KO.md](<../docs/13_MODEL_QUALITY_EXPERIMENT_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/14_SECURITY_EVIDENCE_NPU_KO.md](<../docs/14_SECURITY_EVIDENCE_NPU_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/15_CANDIDATE_DECISION_GATES_KO.md](<../docs/15_CANDIDATE_DECISION_GATES_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/16_ANNOTATED_EVALUATION_PROTOCOL_KO.md](<../docs/16_ANNOTATED_EVALUATION_PROTOCOL_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/17_CURRENT_TECHNICAL_AUDIT_KO.md](<../docs/17_CURRENT_TECHNICAL_AUDIT_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/18_PAYLOCK_PILOT_AND_VALIDATION_KO.md](<../docs/18_PAYLOCK_PILOT_AND_VALIDATION_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/19_V45_ON_DEVICE_NLP_KO.md](<../docs/19_V45_ON_DEVICE_NLP_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/20_ZORO_RUNBOOK_AND_ENGINE_COMPARISON_KO.md](<../docs/20_ZORO_RUNBOOK_AND_ENGINE_COMPARISON_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/21_TEAM_V33_ALIGNMENT_KO.md](<../docs/21_TEAM_V33_ALIGNMENT_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/22_V46_MULTITASK_LABELING_KO.md](<../docs/22_V46_MULTITASK_LABELING_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/23_V46_MODEL_REPORT_KO.md](<../docs/23_V46_MODEL_REPORT_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/24_V47_ABSTENTION_ANALYSIS_KO.md](<../docs/24_V47_ABSTENTION_ANALYSIS_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/25_V47_LINKGUARD_SECURITY_KO.md](<../docs/25_V47_LINKGUARD_SECURITY_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/26_V48_DOMAIN_RISK_INTELLIGENCE_AND_ZORO_GATES_KO.md](<../docs/26_V48_DOMAIN_RISK_INTELLIGENCE_AND_ZORO_GATES_KO.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/team_v3_3/DMSG_PRD_v3_3.md](<../docs/team_v3_3/DMSG_PRD_v3_3.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [docs/team_v3_3/DMSG_SYSTEM_PROMPTING_v3_3.md](<../docs/team_v3_3/DMSG_SYSTEM_PROMPTING_v3_3.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |
| [models/v46/MODEL_CARD.md](<../models/v46/MODEL_CARD.md>) | 유지 기능/기존 계약 참고; v5 현행 문서와 상태·기본값을 대조 |

## 역사 원문·과거 보고 (19개)

| 문서 경로 | 용도 |
|---|---|
| [IteraGuard_v4_9_Technical_Audit.md](<../IteraGuard_v4_9_Technical_Audit.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [dmsg/references/CHANGELOG.md](<../dmsg/references/CHANGELOG.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [dmsg/references/PRD_v49.md](<../dmsg/references/PRD_v49.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [dmsg/references/SYSTEM_PROMPTING_v49.md](<../dmsg/references/SYSTEM_PROMPTING_v49.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [docs/FORMAT_ALIGNMENT_REPORT.md](<../docs/FORMAT_ALIGNMENT_REPORT.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [docs/PRD_v4_9.md](<../docs/PRD_v4_9.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [docs/PREVIOUS_RC1_UPGRADE_REPORT.md](<../docs/PREVIOUS_RC1_UPGRADE_REPORT.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [docs/PREVIOUS_V49_UPGRADE_REPORT.md](<../docs/PREVIOUS_V49_UPGRADE_REPORT.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [docs/SYSTEM_PROMPTING_v4_9.md](<../docs/SYSTEM_PROMPTING_v4_9.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [docs/V49_UPGRADE_REPORT.md](<../docs/V49_UPGRADE_REPORT.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/CHANGELOG_v49_original.md](<../internal/history/CHANGELOG_v49_original.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/README.md](<../internal/history/README.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/VERSION_LEDGER_through_v47_original.md](<../internal/history/VERSION_LEDGER_through_v47_original.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/v50_before_organization_CHANGELOG.md](<../internal/history/v50_before_organization_CHANGELOG.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/v50_before_organization_CURRENT_PROJECT_STATE.md](<../internal/history/v50_before_organization_CURRENT_PROJECT_STATE.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/v50_before_organization_MASTER_HANDOFF_PROMPT.md](<../internal/history/v50_before_organization_MASTER_HANDOFF_PROMPT.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/v50_before_organization_README.md](<../internal/history/v50_before_organization_README.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/v50_before_organization_VERSION_LEDGER.md](<../internal/history/v50_before_organization_VERSION_LEDGER.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |
| [internal/history/v50_before_organization_all.md](<../internal/history/v50_before_organization_all.md>) | 해당 시점 기록; 현재 상태로 읽지 않음 |

## vendor 원본 (11개)

| 문서 경로 | 용도 |
|---|---|
| [vendor/dmsg/README.md](<../vendor/dmsg/README.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/SKILL.md](<../vendor/dmsg/SKILL.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/assets/TEAM_WORKPLAN.md](<../vendor/dmsg/assets/TEAM_WORKPLAN.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/ELENCHUS_SNM_4D.md](<../vendor/dmsg/references/ELENCHUS_SNM_4D.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/EVALUATION.md](<../vendor/dmsg/references/EVALUATION.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/MODEL_CONTRACT.md](<../vendor/dmsg/references/MODEL_CONTRACT.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/PLATFORM_INSTALL.md](<../vendor/dmsg/references/PLATFORM_INSTALL.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/PRD.md](<../vendor/dmsg/references/PRD.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/PROMPTS.md](<../vendor/dmsg/references/PROMPTS.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/SYSTEM_PROMPT.md](<../vendor/dmsg/references/SYSTEM_PROMPT.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
| [vendor/dmsg/references/TRACEABILITY.md](<../vendor/dmsg/references/TRACEABILITY.md>) | 수정하지 않은 기존 스킬 계보; 현재 실행 상태 정본 아님 |
