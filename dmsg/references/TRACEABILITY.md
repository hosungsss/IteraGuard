# IteraGuard — PRD ↔ System Prompt ↔ Architecture ↔ Test 추적표

문서 범위: **현행 제품 요구사항과 검증 증거의 연결**. 해당 구현의 존재 여부를 현재 코드 기준으로 판단한다. 통과한 합성 시연 테스트는 실제 Zoro 추론이나 피해 예방 효과를 의미하지 않는다.

| PRD ID | 관련 System Prompt 규칙 | 구현/증거 경로 | 관련 테스트 또는 검증 조치 | 상태 |
|---|---|---|---|---|
| PRD-01 | GUARD-03 | `prototype/session.py`, `server.py` | `test_only_one_input`, `test_text_limit` | IMPLEMENTED_FIXTURE |
| PRD-02 | GUARD-02, GUARD-06 | `prototype/core.py`, `fixtures.py` | `test_reported_scam_is_not_direct_request` | PARTIAL |
| PRD-03 | GUARD-05 | `prototype/core.py` | `test_positive_fixtures` | IMPLEMENTED_FIXTURE |
| PRD-04 | GUARD-06 | `prototype/core.py`, `ontology.py`, `fixtures.py` | `test_negated_training_is_not_flagged`, `test_negation_not_direct` | IMPLEMENTED_FIXTURE |
| PRD-05 | GUARD-08 | `prototype/core.py`, `ontology.py` | `test_wrong_quote_offsets`, `test_conflict_in_overlapping_evidence_abstains` | IMPLEMENTED_FIXTURE (문자 무결성) |
| PRD-06 | GUARD-07 | `scripts/policy.py`, 문서 명세 | `test_authority_claim_only`; 출처 독립 검증 필요 | PARTIAL |
| PRD-07 | GUARD-10, GUARD-11 | `prototype/typed_contract.py`, `scripts/smoke_zoro.py` | `test_choice_and_noul_valid`, `test_score_supported`, 실서버 통합 시험 필요 | PARTIAL / REAL NOT_VERIFIED |
| PRD-08 | GUARD-10 | `prototype/core.py`, `session.py` | `test_model_down_without_trusted_evidence_abstains` | IMPLEMENTED_FIXTURE |
| PRD-09 | GUARD-12, GUARD-13 | `prototype/core.py` | `test_no_external_side_effects` | IMPLEMENTED_FIXTURE |
| PRD-10 | GUARD-14 | `web/main.js`, `server.py` | 정적 표시/HTTP 점검; 수동 렌더링 확인 필요 | IMPLEMENTED_FIXTURE |
| PRD-11 | GUARD-15 | `prototype/session.py` | `test_stale_version_rejected`, `test_idempotent_retry`, `test_chain_turn_ack_turn`, `test_return_mutations_do_not_change_store_or_cached_response` | IMPLEMENTED_FIXTURE |
| PRD-12 | GUARD-14 | `prototype/session.py` | `test_acknowledgment_is_intent_not_external_verification` | IMPLEMENTED_FIXTURE |
| PRD-13 | GUARD-04, GUARD-17 | `prototype/session.py`, `server.py` | 로컬 이력 필드 감사, 배포 로그 별도 검증 | PARTIAL |
| PRD-14 | GUARD-02, GUARD-12 | `prototype/core.py` | `test_injection_cannot_override_policy` | IMPLEMENTED_FIXTURE |
| PRD-15 | GUARD-06, GUARD-18 | `prototype/fixtures.py`, `web/` | 14개 fixture 반복/HTTP 점검 | IMPLEMENTED_FIXTURE |
| PRD-16 | GUARD-17 | `references/EVALUATION.md` | family-disjoint 블라인드 검증셋 필요 | NOT_VERIFIED |
| PRD-17 | GUARD-14, GUARD-17 | `scripts/smoke_zoro.py` | 실제 checkpoint·지연·표본 필요 | NOT_VERIFIED |
| PRD-18 | GUARD-01, GUARD-12 | `assets/TEAM_WORKPLAN.md` | 팀원 3인 합의 및 참가 증빙 확인 필요 | PROPOSED |
| PRD-19 | GUARD-16 | `prototype/session.py`, `web/main.js` | `test_next_turn`, `test_acknowledgment_is_intent_not_external_verification` | PARTIAL |
| PRD-20 | GUARD-09, GUARD-14 | `prototype/core.py`, `typed_contract.py` | `test_untrusted_model_label_abstains`, `test_proposal_never_authorizes_high_risk`; 실모델 출처 증빙 필요 | PARTIAL |

## 역방향 점검

1. **사용자 화면의 정책 결과** → `result.action` → `prototype/core.py:decide` → `reason` → `Evidence(kind, directness, origin, start, end)` → `text[start:end]`를 추적한다.
2. **사전 주석 데이터의 기대 결과** → `prototype/fixtures.py` → 단위 테스트 → 해당 PRD 수용 기준을 찾는다.
3. **모델 결과를 수치로 주장할 경우** → endpoint 원본 응답 캡처 → 모델/revision → 스키마 검사 → 실제 실행 모드 → 분리된 평가 데이터/표본을 요구한다.
4. **실제 사용자에게 행동을 권고할 경우** → 정책 코드의 네 가지 허용 행동인지 → 외부 실동작이 없는지 → 모드가 정확히 표시되는지 확인한다.

## 명세 모순 처리 규칙

- PRD와 실제 코드가 충돌하면 **코드의 관찰 가능한 동작**을 현재 구현 사실로 기록하고 PRD 기능을 `PARTIAL` 또는 `NOT_VERIFIED`로 판정한다.
- System Prompt는 구현 지시이며 실행 증거가 아니다. 프롬프트 내부의 보안 선언을 단위 테스트 결과로 대체하지 않는다.
- 스모크 테스트가 성공하더라도 실세계의 사기 여부 정답·피해 예방 효과는 별도 실험으로만 주장할 수 있다.
- 출처와 상태에 관한 버전간 변경 기록은 `internal/VERSION_LEDGER.md`만 관리한다.

## 현행 독립 근거 가드의 역방향 추적

- `ontology.assess_evidence` → `ontology.py` → `Evidence` 출처·오프셋 → `core.decide`의 중첩 상충 근거 보류 → `test_conflict_in_overlapping_evidence_abstains`.
- `Store.verify_audit` → 서명 없는 해시 체인 내부 일관성 → `test_chain_turn_ack_turn`, `test_internal_modification_detected`, `test_return_mutations_do_not_change_store_or_cached_response`.
- `decision_oracle.inspect_response` → Typed Decision 파싱 → `MODEL_PROPOSED` 근거 생성 → `ASK_HUMAN` 정책 → `test_proposal_never_authorizes_high_risk`.
- `scripts/evaluate_fixtures.py`는 작성자 지정 기대 레이블과 코드 출력의 일치만 검사하고, 독립 성능 평가로 승격하지 않는다.

## 추가 런타임 수용조건 (현행)

- `PRD-11 / GUARD-15`: 확인 계획은 반드시 세션의 가장 최근 판단 `turn_id`에 연결되어야 한다 (`test_ack_requires_matching_turn`, `test_ack_stale_prior_turn_rejected`).
- `PRD-13 / GUARD-04`: 내부 감사 체인 변조가 검출되면 새 턴과 계획 기록을 거절해야 한다 (`test_mutated_audit_prevents_turn`, `test_mutated_audit_prevents_ack`). 해시 체인은 외부 증거 인증이 아니다.
- `PRD-14 / GUARD-02`: 로컬 POST의 교차 출처·교차 사이트·중복 Content-Length·chunked 프레이밍을 제한한다 (`HTTPContext` 테스트). 인증·방화벽 등 프로덕션 대책을 대체하지 않는다.
- `PRD-15 / GUARD-17`: `scripts/metamorphic_audit.py`는 주석 원문 손상·모델 제안의 출처변환에 대한 합성 불변조건을 확인한다. 이는 탐지 정확도나 외부 데이터 일반화 평가가 아니다.


## 현행 모델 권고 경로의 요구사항 추적

- PRD-06 → GUARD-05 → `prototype/model_bridge.py:questions` → `test_provisional_question_contract` (6개 폐쇄 질문)
- PRD-07 → GUARD-02, GUARD-06 → `prototype/model_bridge.py:advisory` → `test_direct_grounded_advisory`, `test_obvious_warning_conflict_abstains`, `test_report_conflict_abstains`
- PRD-10 → GUARD-07 → `prototype/session.py:process_model` → `test_session_proposed_result_without_claiming_real`, `test_session_bad_source_abstains`
- PRD-14 → GUARD-14 → `prototype/model_bridge.py:ModelClient` → `test_no_external_endpoint_default`, `test_http_public_forbidden`, `test_endpoint_must_match`
- PRD-16 → GUARD-17 → `web/main.js`, `/api/model-status` → 실제 브라우저 접근성·모델 체크포인트별 성능은 NOT_VERIFIED
- PRD-20 → GUARD-09 → `prototype/model_bridge.py:advisory` → `test_nonfinite_rejected`, `test_score_fractional_not_fraud_probability`, `test_no_action_high_scam_conflict_abstains`

## 현행 안전 게이트의 추적성 확장

| 요구사항 | 프롬프트 규칙 | 구현 경로 | 검증/반례 | 증거 한계 |
|---|---|---|---|---|
| PRD-21 | GUARD-20 | `prototype/context_guard.py`, `model_bridge.py:advisory` | `test_v36_context_and_transport.py:ContextRegressions`, `scripts/run_adversarial_suite.py` | 어휘 충돌 검사, 의미 정답 아님 |
| PRD-22 | GUARD-19 | `prototype/model_bridge.py:ModelClient._check_target` | `test_remote_text_has_explicit_opt_in`, `test_remote_host_requires_allowlist` | 원격 서비스 인증·실운영 인증 미검증 |
| PRD-23 | GUARD-21 | `prototype/model_bridge.py:ModelClient.infer` | `test_duplicate_json_denied`, `test_wrong_response_content_type_denied`, `test_response_body_bounded` | 합성 로컬 HTTP |
| PRD-24 | GUARD-22 | `prototype/session.py:process_model` | `test_delayed_high_confidence_does_not_override_new_turn`, `test_duplicated_result_mutation_does_not_corrupt_audit` | 단일 프로세스·메모리 내 |
| PRD-25 | GUARD-23 | `web/main.js` | `node --check`, Playwright가 허용될 때 `tools/browser_smoke.py` | 실 브라우저 수동·접근성 검증 별도 |
| PRD-26 | GUARD-24 | `docs/08_RELEASE_AND_DRIVE_WORKFLOW_KO.md`, `tools/verify_release.py` | ZIP CRC·SHA256·다운로드 파일 존재 검사 | 원격 업로드는 사용자의 별도 요청 사항 |


## 현행 개인정보·원격 연결·모델 평가·NPU 요구사항 추적

| 요구사항 | 프롬프트 | 코드·기능 | 실제 실행 가능한 검증 | 증거 수준 및 한계 |
|---|---|---|---|---|
| PRD-27 | GUARD-25 | `prototype/session.py:Store._private_digest` | `test_v37_privacy_security.py:PrivacyTests` | 난수 키 HMAC 합성 테스트, 키 영속화·외부 인증 없음 |
| PRD-28 | GUARD-26 | `prototype/context_guard.py:context_flags`, `model_bridge.py:advisory` | `test_v37_privacy_security.py:AuxiliarySignalTests` | 어휘 기반 긴급 단서, 외부 의미 정확도 미측정 |
| PRD-29 | GUARD-27 | `prototype/model_bridge.py:_PinnedHTTPSConnection`, `ModelClient._check_target/infer` | `test_v37_privacy_security.py:RemoteTransportTests` | 핀 고정 요청 흐름은 모의 검증, 실제 원격 TLS/서버 증명 미실행 |
| PRD-30 | GUARD-28 | `prototype/evaluation_gate.py`, `scripts/evaluate_annotations.py` | `test_v37_evaluation_npu.py:EvaluationTests` | 합성 데이터 유출·수치 단위 테스트, 독립 정답 라벨 없음 |
| PRD-31 | GUARD-29 | `scripts/npu_readiness.py` | `test_v37_evaluation_npu.py:NPUReadinessTests` | 공급자/모델 파일의 존재가 실제 NPU 동작을 증명하지 않음 |


## 현행 PAYLOCK 도메인 전용 역방향 추적성

| PRD ID | System Prompt 규칙 | 코드·계약 | 테스트·검증 | 상태 |
|---|---|---|---|---|
| PRD-32 | GUARD-30 | `web/index.html`, `web/paylock.html`, `prototype/server.py` | `test_get_ui_and_fixtures`, `test_legacy_api_still_present` | IMPLEMENTED_SYNTHETIC |
| PRD-33 | GUARD-31 | `prototype/paylock.py:assess_request`, `VENDORS`, `INVOICES` | `test_changed_account_same_bank_hold`, `test_invoice_amount_hold`, `test_unchanged_never_payment` | IMPLEMENTED_SYNTHETIC |
| PRD-34 | GUARD-32 | `prototype/paylock.py`, `web/paylock.js` | `test_sender_spoof_hold`, `test_no_injection_escalation` | CLAIM_ONLY |
| PRD-35 | GUARD-33 | `prototype/paylock_model.py`, `prototype/model_bridge.py` | `test_model_malformed_goes_to_hold`, `test_model_positive_adds_hold` | MODEL_NOT_ATTESTED |
| PRD-36 | GUARD-34 | `prototype/paylock.py:record_verification` | `test_second_actor_can_report_not_verify`, `test_wrong_method_rejected` | OPERATOR_REPORT_ONLY |
| PRD-37 | GUARD-35 | `prototype/paylock.py:PaylockStore` | `test_no_raw_private_values_in_history`, `test_no_secret_raw_sha256` | EPHEMERAL |
| PRD-38 | GUARD-36 | `prototype/paylock.py:PaylockStore` | `test_parallel_idempotent_submission`, `test_audit_detects_tamper`, `test_stale_version_blocked` | SINGLE_PROCESS |
| PRD-39 | GUARD-37 | `prototype/server.py`, `web/paylock.html`, `web/paylock.js` | `test_real_api_end_to_end_hold_to_review`, `test_no_unknown_paths` | SIMULATED_ONLY |
| PRD-40 | GUARD-38 | `docs/18_PAYLOCK_PILOT_AND_VALIDATION_KO.md`, `scripts/npu_readiness.py` | `test_model_no_positive_does_not_clear_structural_hold`; independent field eval required | PROTOCOL_READY_NOT_MEASURED |

역검증 경로: 지급 검토 결과 → `reason_codes` → `assess_request()` → 등록 거래처·청구서 필드와 요청의 불일치 → 비신뢰 발신 주소/본문 → 원래 입력/동작의 실제 증거 수준. 확인 보고 결과 → `case.version` → `event_id` → 모의 연락 방식 → 실제 신원·계좌 진위는 검증하지 않았음을 표시. `model_attested=false`, `actual_payment_executed=false`는 항상 유지되어야 한다.

## 메모리 쓰기·지급 검토 시간 재평가·하네스 신뢰 경계

| Requirement | Guard | Production code path | Test evidence | Evidence status |
|---|---|---|---|---|
| PRD-41 | GUARD-39 | `prototype/context_guard.py:preview_memory_prewrite` | `PrewriteTrustBoundaryTests.test_external_role_spoof_quarantined_even_with_metadata`, `test_user_preference_review_ready_never_written`, `test_model_flags_can_only_add_review` | CODE_SYNTHETIC_ONLY, NO MEMORY WRITE |
| PRD-42 | GUARD-40 | `prototype/paylock.py:PaylockStore.evaluate` | `test_delayed_model_signal_escalates_idempotent_request`, `test_delayed_model_signal_cannot_rewrite_closed_case` | CODE_SYNTHETIC_ONLY, SINGLE PROCESS |
| PRD-43 | GUARD-41 | `prototype/context_guard.py:external_directive_flags`, `prototype/paylock.py:assess_request` | `test_paylock_matching_fields_but_role_override_goes_hold`, `test_paylock_innocent_quote_baseline_still_ready` | LEXICAL_ONLY |
| PRD-44 | GUARD-42 | `scripts/validate_skill.py`, `tools/verify_release.py`, `tools/build_release.py` | legacy regression, archive read-back, R01-R09 gate, separate real-model/NPU NOT_RUN | STATIC_VALIDATED_ONLY |

의심계 원래 `/api/start`, `/api/turn`, `/api/model-turn` 및 PAYLOCK `/api/paylock/evaluate`, `/api/paylock/verify` 경로를 보존한다. 기억 쓰기 API는 존재하지 않는다. 합성 시연이 실사용 기록·금융기관 인증을 의미하지 않는다.


## 현행 감사 무결성·브라우저 검사 추적

| PRD | Guard | Source | Test/Evidence | Status |
|---|---|---|---|---|
| PRD-45 | GUARD-43 | `prototype/paylock.py:PaylockStore._audit_hash` | `test_unkeyed_rehash_attack_cannot_forge_hmac_chain`; 정상 이벤트 회귀 | LOCAL_PASS_NO_EXTERNAL_ATTESTATION |
| PRD-46 | GUARD-44 | `prototype/paylock.py:PaylockStore._integrity_ok` | `test_state_tampering_is_detected_not_just_event_changes`, `test_hmac_audit_verifies_valid_review_transition` | LOCAL_PASS_EPHEMERAL |
| PRD-47 | GUARD-45 | `tools/browser_smoke.py` (project-level) | `internal/evidence/v40_browser_smoke.json`, 데스크톱·모바일 스크린샷 | CHROMIUM_INPAGE_REAL_BACKEND_BRIDGE |


## 현재 v4.1 계약-코드-검증 추적

| PRD | Guard | Source | Test/Evidence | Status |
|---|---|---|---|---|
| PRD-48 | GUARD-46 | `prototype/paylock.py:PaylockStore.record_verification` | `test_replay_same_event_id_with_modified_expected_version_rejected` | LOCAL_PASS_REQUIRED |
| PRD-49 | GUARD-47 | `prototype/paylock.py:PaylockStore._integrity_ok` | `test_created_time_tamper_fails_integrity_not_just_event_hash` | LOCAL_PASS_REQUIRED |
| PRD-50 | GUARD-48 | `tools/delivery_gate.py`, `tools/build_release.py` | `internal/evidence/v41_delivery_verification.json`; 다운로드 링크 사용자측 실제 성공은 미확인 | LOCAL_DELIVERY_VERIFIED_HOST_UNVERIFIED |
| PRD-51 | GUARD-49 | `prototype/server.py:Handler` | `test_duplicate_host_header_rejected`, `test_duplicate_origin_header_rejected` | LOCAL_HTTP_PASS_REQUIRED |
| PRD-52 | GUARD-50 | `prototype/typed_contract.py:normalize_response,_score_probabilities`, `prototype/model_bridge.py:SPEC,RISK_LEVELS,OPTIONAL_QUESTIONS` | `V42KevContract.*` (8개) | KEV_SHAPE_LOCAL_PASS_REAL_SERVER_NOT_RUN |
| PRD-53 | GUARD-51 | `prototype/model_bridge.py:ModelClient.infer,timeout`, `prototype/session.py:_failure_reason` | `V42KevTransport.*` (5개), `internal/evidence/v42_v41_counterexamples.json` C9 | KEV_STUB_PASS_REAL_SERVER_NOT_RUN |
| PRD-54 | GUARD-52 | `prototype/context_guard.py:clause_profile,_warning_cue,context_conflict`, `prototype/model_bridge.py:advisory` | `V42ClauseScopedGuard.*` (8개, 서브테스트 포함 메타모픽 60조합) | AUTHOR_SYNTHETIC_PASS_INDEPENDENT_NOT_RUN |
| PRD-55 | GUARD-53 | `prototype/session.py:process,process_model,acknowledge,_audit_digest` | `V42SessionBinding.*` (4개) | LOCAL_UNIT_PASS |
| PRD-56 | GUARD-54 | `scripts/smoke_zoro.py`, `scripts/npu_readiness.py:weight_memory_gib,prefill_budget` | `V42NpuFeasibility.*` (3개) | ARITHMETIC_ONLY_NPU_NOT_RUN |
| PRD-57 | GUARD-55 | `tools/export_engine_data.py`, `apps/shared/engine-data.js` (생성물) | `run_conformance.js` source_drift 7/7 | GENERATED_FROM_REFERENCE |
| PRD-58 | GUARD-56 | `apps/shared/dmsg-engine.js`, `tools/make_conformance_vectors.py`, `apps/conformance/run_conformance.js` | `internal/evidence/v43_conformance.json`, `test_v36_context_and_transport.V43Portability` | IMPLEMENTATION_EQUALITY_ON_SYNTHETIC_VECTORS |
| PRD-59 | GUARD-57 | `apps/desktop/server.js` | `internal/evidence/v43_app_smoke.json` http 13항목 (Linux 실행) | LINUX_RUNTIME_PASS_WINDOWS_MACOS_NOT_RUN |
| PRD-60 | GUARD-58 | `tools/verify_macho_signature.py`, `tools/build_apps.py` | `internal/evidence/v43_build.json` macho_signature | PAGE_HASHES_VALID_GATEKEEPER_NOT_EVALUATED |
| PRD-61 | GUARD-59 | `apps/web/index.html`, `apps/web/styles.css`, `apps/web/app.js`, `tools/check_contrast.py` | `v43_app_smoke.json` ui 5개 구성, 대비 검사 | CHROMIUM_PASS_REAL_DEVICES_NOT_RUN |
| PRD-62 | GUARD-60 | `tools/build_apk.py`, `tools/verify_apk.py` | `internal/evidence/v44_apk.json` | STRUCTURE_AND_SIGNATURE_PASS_DEVICE_NOT_RUN |

## v4.7 추적

| 요구사항 | 규칙 | 코드 | 테스트·증거 |
|---|---|---|---|
| PRD-47-01~03 | 47-1~47-3 | `dmsg/prototype/model_bridge.py::decision_relevant_advisory`, `apps/shared/dmsg-engine.js::decisionRelevantAdvisory` | `dmsg/tests` V47*, `tests_linkguard/test_arbiter.py`, 적합성 `dra` 468 |
| PRD-47-04 | 47-1 | `abstention_cause`, `tools/zoro/abstention_audit.py` | `Audit.*` 테스트 |
| PRD-47-05,06,08 | 47-4, 47-5 | `linkguard/intake.py`, `linkguard/policy.py`, `apps/shared/dmsg-linkguard.js` | `tests_linkguard/test_linkguard.py`, `run_linkguard.js`, `v47_validation_matrix.md` |
| PRD-47-07 | 47-6 | `linkguard/apk.py`, `apps/shared/dmsg-apkscan.js` | `tools/linkguard/apk_parity.py`, A01–A06 |
| PRD-47-09 | 47-4 | `tools/build_apk.py`, `apps/web/app.js` (#share=) | `verify_apk.py`, 앱 스모크 `share_*` |

## v4.8 현행 기능 추적

`PRD-48-01 ↔ GUARD-48-01 ↔ apps/shared/dmsg-domainintel.js ↔ apps/web/app.js #domainCard ↔ tools/test_domain_v48.js ↔ docs/26_V48_DOMAIN_RISK_INTELLIGENCE_AND_ZORO_GATES_KO.md`; 모델 자체의 실세계 성능과 범죄 판단은 NOT_RUN.
