# v5.1 문서 안내와 읽는 기준

현재 상태는 CURRENT_PROJECT_STATE.md, 다음 과제는 V51_OPEN_ISSUES.md, 잔여 실패는 V51_FAILURE_ANALYSIS.md가 정본이다. README/STATE/HANDOFF/all은 현행 사실이며 상세 변경 이력은 internal/VERSION_LEDGER.md 한 곳에 기록한다.

1. [현재 상태](../CURRENT_PROJECT_STATE.md)와 [미해결 과제](V51_OPEN_ISSUES.md), [실패 분석](V51_FAILURE_ANALYSIS.md)
2. [전체 이해](../all.md), [PRD](PRD_v51.md), [실행 지침](SYSTEM_PROMPTING_v51.md)
3. [구현 보고](V51_IMPLEMENTATION_REPORT.md), [요구사항 추적](V51_TRACEABILITY.json), [원장](../internal/VERSION_LEDGER.md)

v50 PRD/보고/실험과 기존 후보 HOLD는 당시 기준선 증거로 보존한다. v51 개발·잠금 AI 결과와 인간 독립 평가 NOT_RUN을 구분한다. 넓은 기존 rubric/작은 합성 표본의 기대 안내 일치를 일반 정확도로 표시하지 않는다. DRA는 원본 profile 비교이며 registry compatibility default와 제품 release_selection도 구분한다.

`dmsg/references/PRD_v51.md`와 SYSTEM_PROMPTING_v51.md는 docs 정본의 동일 사본이다. 같은 내용을 독립 증거로 중복 집계하지 않는다. 기존01~26/vendor/team 문서는 새로운 팀 승인이 아니다. L2/G7/기관 질문/L1은 현행 유지한다.

`internal/evidence/v51/`는 이번 실행·실험·브라우저·정적검사 증거, evidence/v50은 기준선 증거다. 보관 원문의 출처/hash는 internal/history/PROVENANCE.json에 있다. FULL/독립추출 검증 영수증은 [배포 ZIP 옆 상위 기록](<../../Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json>)을 따른다. source manifest에 FULL 자체를 포함하지 않는다.

아래는 작성 시점 소스의 Markdown 경로 인벤토리다. 모든 역사 문서를 다시 정독·실행하거나 내용을 인증했다는 뜻이 아니다.

## 현행 진입점·명세 (18개)

| 문서 경로 | 용도 |
|---|---|
| [CHANGELOG.md](<../CHANGELOG.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [CURRENT_PROJECT_STATE.md](<../CURRENT_PROJECT_STATE.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [MASTER_HANDOFF_PROMPT.md](<../MASTER_HANDOFF_PROMPT.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [README.md](<../README.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [all.md](<../all.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [apps/README.md](<../apps/README.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [apps/mobile/BUILD_ANDROID.md](<../apps/mobile/BUILD_ANDROID.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [apps/mobile/BUILD_IOS.md](<../apps/mobile/BUILD_IOS.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [dmsg/SKILL.md](<../dmsg/SKILL.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [dmsg/references/PRD_v51.md](<../dmsg/references/PRD_v51.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [dmsg/references/SYSTEM_PROMPTING_v51.md](<../dmsg/references/SYSTEM_PROMPTING_v51.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [docs/00_DOCUMENT_MAP.md](<../docs/00_DOCUMENT_MAP.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [docs/PRD_v51.md](<../docs/PRD_v51.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [docs/SYSTEM_PROMPTING_v51.md](<../docs/SYSTEM_PROMPTING_v51.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [docs/V51_IMPLEMENTATION_REPORT.md](<../docs/V51_IMPLEMENTATION_REPORT.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [docs/V51_OPEN_ISSUES.md](<../docs/V51_OPEN_ISSUES.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [internal/VERSION_LEDGER.md](<../internal/VERSION_LEDGER.md>) | 현재 제품 사실/계약/미완료/운영 안내 |
| [docs/V51_FAILURE_ANALYSIS.md](<../docs/V51_FAILURE_ANALYSIS.md>) | 잔여 실패·근거 품질·미들웨어 필요성; 별도 담당자가 작성한 현행 분석 |

## 기존 기능·운영 참고 (41개)

| 문서 경로 | 용도 |
|---|---|
| [dmsg/README.md](<../dmsg/README.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/assets/TEAM_WORKPLAN.md](<../dmsg/assets/TEAM_WORKPLAN.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/ELENCHUS_SNM_4D.md](<../dmsg/references/ELENCHUS_SNM_4D.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/EVALUATION.md](<../dmsg/references/EVALUATION.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/MODEL_CONTRACT.md](<../dmsg/references/MODEL_CONTRACT.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/PLATFORM_INSTALL.md](<../dmsg/references/PLATFORM_INSTALL.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/PRD.md](<../dmsg/references/PRD.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/PROMPTS.md](<../dmsg/references/PROMPTS.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/SYSTEM_PROMPT.md](<../dmsg/references/SYSTEM_PROMPT.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [dmsg/references/TRACEABILITY.md](<../dmsg/references/TRACEABILITY.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/01_PRODUCT_REQUIREMENTS_PRD_KO.md](<../docs/01_PRODUCT_REQUIREMENTS_PRD_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/02_SYSTEM_PROMPT_AGENT_KO.md](<../docs/02_SYSTEM_PROMPT_AGENT_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/03_TRACEABILITY_MATRIX_KO.md](<../docs/03_TRACEABILITY_MATRIX_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/04_DEPLOYMENT_AND_VERIFICATION_KO.md](<../docs/04_DEPLOYMENT_AND_VERIFICATION_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/05_ARCHITECTURE_SNM_4D_KO.md](<../docs/05_ARCHITECTURE_SNM_4D_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/06_SOURCE_INTEGRITY_AND_BARRIERS_KO.md](<../docs/06_SOURCE_INTEGRITY_AND_BARRIERS_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/07_DEMO_AND_PITCH_KO.md](<../docs/07_DEMO_AND_PITCH_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/08_RELEASE_AND_DRIVE_WORKFLOW_KO.md](<../docs/08_RELEASE_AND_DRIVE_WORKFLOW_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/09_MODEL_ADVISORY_CONTRACT_KO.md](<../docs/09_MODEL_ADVISORY_CONTRACT_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/10_SNM_4D_REDTEAM_KO.md](<../docs/10_SNM_4D_REDTEAM_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/11_MODEL_OPERATOR_GUIDE_KO.md](<../docs/11_MODEL_OPERATOR_GUIDE_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/12_SNM_4D_THREAT_AND_ACCEPTANCE_KO.md](<../docs/12_SNM_4D_THREAT_AND_ACCEPTANCE_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/13_MODEL_QUALITY_EXPERIMENT_KO.md](<../docs/13_MODEL_QUALITY_EXPERIMENT_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/14_SECURITY_EVIDENCE_NPU_KO.md](<../docs/14_SECURITY_EVIDENCE_NPU_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/15_CANDIDATE_DECISION_GATES_KO.md](<../docs/15_CANDIDATE_DECISION_GATES_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/16_ANNOTATED_EVALUATION_PROTOCOL_KO.md](<../docs/16_ANNOTATED_EVALUATION_PROTOCOL_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/17_CURRENT_TECHNICAL_AUDIT_KO.md](<../docs/17_CURRENT_TECHNICAL_AUDIT_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/18_PAYLOCK_PILOT_AND_VALIDATION_KO.md](<../docs/18_PAYLOCK_PILOT_AND_VALIDATION_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/19_V45_ON_DEVICE_NLP_KO.md](<../docs/19_V45_ON_DEVICE_NLP_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/20_ZORO_RUNBOOK_AND_ENGINE_COMPARISON_KO.md](<../docs/20_ZORO_RUNBOOK_AND_ENGINE_COMPARISON_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/21_TEAM_V33_ALIGNMENT_KO.md](<../docs/21_TEAM_V33_ALIGNMENT_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/22_V46_MULTITASK_LABELING_KO.md](<../docs/22_V46_MULTITASK_LABELING_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/23_V46_MODEL_REPORT_KO.md](<../docs/23_V46_MODEL_REPORT_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/24_V47_ABSTENTION_ANALYSIS_KO.md](<../docs/24_V47_ABSTENTION_ANALYSIS_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/25_V47_LINKGUARD_SECURITY_KO.md](<../docs/25_V47_LINKGUARD_SECURITY_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/26_V48_DOMAIN_RISK_INTELLIGENCE_AND_ZORO_GATES_KO.md](<../docs/26_V48_DOMAIN_RISK_INTELLIGENCE_AND_ZORO_GATES_KO.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/team_v3_3/DMSG_PRD_v3_3.md](<../docs/team_v3_3/DMSG_PRD_v3_3.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [docs/team_v3_3/DMSG_SYSTEM_PROMPTING_v3_3.md](<../docs/team_v3_3/DMSG_SYSTEM_PROMPTING_v3_3.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [internal/evidence/v51/README.md](<../internal/evidence/v51/README.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [internal/evidence/v51/data_preparation/ANNOTATION_RUBRIC.md](<../internal/evidence/v51/data_preparation/ANNOTATION_RUBRIC.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |
| [models/v46/MODEL_CARD.md](<../models/v46/MODEL_CARD.md>) | 보존 기능/주석 참고; 현재 v51 계약·시점과 대조 |

## 역사 원문·기준선 보고 (36개)

| 문서 경로 | 용도 |
|---|---|
| [IteraGuard_v4_9_Technical_Audit.md](<../IteraGuard_v4_9_Technical_Audit.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [dmsg/references/CHANGELOG.md](<../dmsg/references/CHANGELOG.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [dmsg/references/PRD_v49.md](<../dmsg/references/PRD_v49.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [dmsg/references/PRD_v50.md](<../dmsg/references/PRD_v50.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [dmsg/references/SYSTEM_PROMPTING_v49.md](<../dmsg/references/SYSTEM_PROMPTING_v49.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [dmsg/references/SYSTEM_PROMPTING_v50.md](<../dmsg/references/SYSTEM_PROMPTING_v50.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/FORMAT_ALIGNMENT_REPORT.md](<../docs/FORMAT_ALIGNMENT_REPORT.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/PRD_v4_9.md](<../docs/PRD_v4_9.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/PRD_v50.md](<../docs/PRD_v50.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/PREVIOUS_RC1_UPGRADE_REPORT.md](<../docs/PREVIOUS_RC1_UPGRADE_REPORT.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/PREVIOUS_V49_UPGRADE_REPORT.md](<../docs/PREVIOUS_V49_UPGRADE_REPORT.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/SYSTEM_PROMPTING_v4_9.md](<../docs/SYSTEM_PROMPTING_v4_9.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/SYSTEM_PROMPTING_v50.md](<../docs/SYSTEM_PROMPTING_v50.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/V49_UPGRADE_REPORT.md](<../docs/V49_UPGRADE_REPORT.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/V50_IMPLEMENTATION_REPORT.md](<../docs/V50_IMPLEMENTATION_REPORT.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [docs/V50_OPEN_ISSUES.md](<../docs/V50_OPEN_ISSUES.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/CHANGELOG_v49_original.md](<../internal/history/CHANGELOG_v49_original.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/README.md](<../internal/history/README.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/VERSION_LEDGER_through_v47_original.md](<../internal/history/VERSION_LEDGER_through_v47_original.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_organization_CHANGELOG.md](<../internal/history/v50_before_organization_CHANGELOG.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_organization_CURRENT_PROJECT_STATE.md](<../internal/history/v50_before_organization_CURRENT_PROJECT_STATE.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_organization_MASTER_HANDOFF_PROMPT.md](<../internal/history/v50_before_organization_MASTER_HANDOFF_PROMPT.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_organization_README.md](<../internal/history/v50_before_organization_README.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_organization_VERSION_LEDGER.md](<../internal/history/v50_before_organization_VERSION_LEDGER.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_organization_all.md](<../internal/history/v50_before_organization_all.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/CHANGELOG.md](<../internal/history/v50_before_v51_documentation/CHANGELOG.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/CURRENT_PROJECT_STATE.md](<../internal/history/v50_before_v51_documentation/CURRENT_PROJECT_STATE.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/MASTER_HANDOFF_PROMPT.md](<../internal/history/v50_before_v51_documentation/MASTER_HANDOFF_PROMPT.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/README.md](<../internal/history/v50_before_v51_documentation/README.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/all.md](<../internal/history/v50_before_v51_documentation/all.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/apps/README.md](<../internal/history/v50_before_v51_documentation/apps/README.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/apps/mobile/BUILD_ANDROID.md](<../internal/history/v50_before_v51_documentation/apps/mobile/BUILD_ANDROID.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/dmsg/SKILL.md](<../internal/history/v50_before_v51_documentation/dmsg/SKILL.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/docs/00_DOCUMENT_MAP.md](<../internal/history/v50_before_v51_documentation/docs/00_DOCUMENT_MAP.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/internal/VERSION_LEDGER.md](<../internal/history/v50_before_v51_documentation/internal/VERSION_LEDGER.md>) | 해당 시점 증거; 현재 상태와 구분 |
| [internal/history/v50_before_v51_documentation/internal/history/README.md](<../internal/history/v50_before_v51_documentation/internal/history/README.md>) | 해당 시점 증거; 현재 상태와 구분 |

## vendor 원본 (11개)

| 문서 경로 | 용도 |
|---|---|
| [vendor/dmsg/README.md](<../vendor/dmsg/README.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/SKILL.md](<../vendor/dmsg/SKILL.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/assets/TEAM_WORKPLAN.md](<../vendor/dmsg/assets/TEAM_WORKPLAN.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/ELENCHUS_SNM_4D.md](<../vendor/dmsg/references/ELENCHUS_SNM_4D.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/EVALUATION.md](<../vendor/dmsg/references/EVALUATION.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/MODEL_CONTRACT.md](<../vendor/dmsg/references/MODEL_CONTRACT.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/PLATFORM_INSTALL.md](<../vendor/dmsg/references/PLATFORM_INSTALL.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/PRD.md](<../vendor/dmsg/references/PRD.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/PROMPTS.md](<../vendor/dmsg/references/PROMPTS.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/SYSTEM_PROMPT.md](<../vendor/dmsg/references/SYSTEM_PROMPT.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
| [vendor/dmsg/references/TRACEABILITY.md](<../vendor/dmsg/references/TRACEABILITY.md>) | 원본 계보; 현재 승인/성능으로 승격하지 않음 |
