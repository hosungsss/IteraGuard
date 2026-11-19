# IteraGuard / 의심계 cumulative handoff (append-only)

## 2026-11-10 / v5.2 experimental source candidate

**Purpose:** incorporate reasoned Decision Agents methodology and team-proposed 5-feature posterior sandbox without modifying protected Zoro-1 or production v5.1 policy.
**Originals:** uploaded v5.1 ZIP, Drive folder listing (read-only), provided 4-line upgrade prompt and Decision Agents v3.1 book (NOT distributed).
**Changed:** added `integration/v52_decision_sandbox.py`, `tools/v52_exploratory_train.py`, `tests_v52/test_decision_sandbox.py`, docs/V52*, dmsg reference, current README and skill intro, registered skill path additions. Existing `internal/VERSION_LEDGER.md` appended. Old v5.1 ZIP remains intact.
**Design:** input evidence -> strict typed validation -> exploratory logistic -> distinct cost/uncertainty gates -> existing independent policy (unchanged).
**Evidence:** new unit tests plus exploratory AI-authored 61-case group-fold results; strict non-promotion.
**Constraints:** no real Zoro-1 calls, no NPU, no Android device, no independent labels, no user-facing risk-probability validation. Python 3.13 Unicode version mismatch for an existing v5.1 JS regeneration check remains visible.
**Restore:** discard v5.2 candidate; re-unpack original v5.1 ZIP with SHA-256 `b7aa499b2306203710e94bd77a367de922f1ac5e5b44aec112c5d2d39703bbb1`.
**Follow-up:** source attestation, true family-locked human evaluation, direct/reasoned paired utility in consistent units, Android pilot and official event constraints, approved version promotion.


## 2026-11-19 / v5.8 GitHub integration candidate — append-only record
Purpose: portable typed decision -> business policy proposal with independent action authorization; adapt v5.8 UX into the existing GitHub Arena rather than overwriting its Zoro-linked v5.6 source.
Source of truth: GitHub main base 880468eb45988edbda8745c124fe62c67f15bb91; uploaded local v5.8 ZIP and three user reference docs (SHA-256 listed in docs/V58_AGENT_EVIDENCE_GUIDE.md).
Changed: rulebook/engine.py; two industry example books; tests_rulebook; tools/rulebook_preview_v58.py; Arena HTML/JS/CSS UX; AGENTS.md; docs/V58_*; source version pointer and README; workflow. No live Zoro endpoint, inference server, Android binary or external account was modified.
Guardrails: proposal-only, no real API actions, no hidden fixture fallback; probabilities only typed-choice confidence; model head/checkpoint identity UNVERIFIED. Uploaded full SUPER_PERSONA.md not published; selected methodology summarized.
Validation: new tests and CI should be read from the feature branch/merged commit. Do NOT treat creation of code or GitHub commits as run-time correctness. Independent labels/business success 30%-98%, GPU/NPU latency, production deployment NOT_VERIFIED.
Next: read PR checks and actual merge SHA; connect actual Zoro transport contract in a separate audited change; compare independent locked test families; acquire authorization prior to real action adapters. Use previous main commit for code rollback; back up SQLite separately.


## 2026-11-19 / v5.8 custom domain CLI follow-up
Purpose: make question+rulebook reconfiguration possible from a bounded external local JSON file rather than requiring Python edits or a hard-coded preset name.
Changed tools/rulebook_preview_v58.py; tests_rulebook/test_cli.py; README, architecture notes, canonical ledger.
Security: max 64 KiB local JSON; duplicate keys/nonfinite inputs refused; no Zoro/live network/side effects.
Verification: CI contract checks for custom preview, duplicate JSON and large payload; actual main SHA and statuses must be read back after merge. End-to-end live domain model validation NOT_RUN.
Rollback: revert follow-up PR; existing profiles and Arena remain present.


## 2026-11-19 / v5.8 optional local System One Rulebook bridge
Purpose: connect industry question books to existing installed Arena ModelClient without replacing active Arena v5.6 policy.
Added: rulebook/zoro_bridge.py, tools/rulebook_live_v58.py, synthetic text fixture, mock-only tests and source guide. Explicit opt-in is required; no external business side effects.
Source: locally configured /v1/systemone only; response modes distinguish test double, unavailable and unverified model. Real model/checkpoint validation NOT_RUN here.
Read-back: check corresponding PR/CI/main SHA and an independently authorized real synthetic Zoro probe before claiming live success. Rollback by stopping opt-in CLI; existing Arena unaffected.


## 2026-11-19 / v5.8 Rule Tweak Candidate 1 shadow-only integration (append-only)
**Purpose:** adopt measurable bounded Korean warning/report hypotheses without destroying v5.8 Arena v5.6 retry/task state and without treating past replay as a new model improvement.
**Provenance:** user-uploaded IteraGuard_v56_RuleTweak_Candidate1.zip SHA-256 c82708fc31ca6825991099e53a1ccf9c71dfd6cd9b4ee514c0159d7fc115dc9d, derived from historical 17e3bf5b1dbf7288254c7950bce991e81419fb42; GitHub integration base main 7e43d6afbc5fa720d83fa72921c7c09520e27cd8. Separate setup guide matched ZIP README.
**Change:** integration/rule_tweak_shadow.py, configs/rule_tweak_shadow.json, tests_rule_tweak_shadow, minimal hook in arena/store.py, test CI additions, .gitignore, docs, README, AGENTS and state updates. Did NOT overwrite old store.py, contract generator, application builds, or model/head.
**Safety:** default SHADOW, off supported, enforce blocked. Preserve decision/task/retry, no external calls or raw messages in added trace. Trace includes candidate/baseline, local source/config hashes and explicit evidence caveat.
**Verification:** source/CI tests are attributable to exact PR and commit only; historic 12-case replay is development-derived, not independently replicated here. Actual Zoro inference, desktop/mobile browser, independent locked labels, NPU and production rollout NOT_RUN.
**Rollback:** revert PR or set DMSG_RULE_TWEAK_MODE=off and restart; no SQLite migration. Do not import historical installer/backups to public Git. Full detail docs/V58_RULE_TWEAK_SHADOW_REVIEW.md; canonical version history internal/VERSION_LEDGER.md.

**Validation correction/addendum for CR-20261119-04:** fixed expanded GitHub Actions YAML command-block serialization; aligned Python 3.12 to generated semantic Unicode version; made optional querySelectorAll usage compatible with minimal DOM test harness. All prior failed logs remain in GitHub Actions and are not erased. Await definitive green CI/read-back.


## 2026-11-19 / Arena 웹 합성 예시
계좌 변경을 첫 입력으로 표시하고 상황 중심 예시 네 개를 제공한다. 방법이 빠진 요청을 먼저 판단한 다음, 같은 기록에서 계좌 변경과 정산 진행 보고를 판단하면 확인 업무 두 건을 보존하는 흐름을 재현할 수 있다.
실제 조로에서 이 세 판단은 사전 기대와 일치했다. 별도 보안 공지는 사람 검토와 추가 확인 업무를 만들었다. 브라우저 스크립트 회귀에서 예시 선택과 명시적 판단의 요청 수를 확인한다.


## 2026-11-19 pre-demo validation, uncommitted
Base 046feef; branch fix/pre-demo-validation. Added model configuration-only status, UI auth/busy/non-JSON/timeout errors, reset new-session source label, per-process inference slot, UTF-8 server re-exec. Policy fingerprints unchanged. Original UI new regressions: 1 pass/4 fail; modified selected suites total 168 pass/2 skipped including added timeout test. Actual model attempt MODEL_NOT_CONFIGURED. Hosted site PowerShell root 200/API401; Python403; authenticated flow/model identity/mobile NOT_RUN. No commit/push/deploy; temporary server stopped. Full report outputs/demo_fix_20261119/IteraGuard_Latest_Validation_and_Fixes.md outside source root. Rollback local changes only; no migration.


## 2026-11-19 bounded automatic recovery, uncommitted
User requested self-recovery during execution. Added browser transport recovery, max two retries, exact frozen request identity, stored-state reconciliation before inference resend, stop on auth/state/contract ambiguity. Existing policy and model status unchanged. UI reports recovery. Mock-network/minimal-DOM tests total 37 pass; live Zoro/hosted authenticated/mobile NOT_RUN. No commit/push/deploy. See docs/AUTO_RECOVERY_KO.md.


## 2026-11-19 PR publication authorized
User authorized commit/push and PR/Actions. Rebased recovery changes onto main 05103c7; preserved both append-only ledgers and contextual demo UI. Local Node 38 passed and runtime tests 2 passed after integration. GitHub Actions result must be checked on PR HEAD. Actual Zoro and hosted authenticated demo remain unverified. No main merge or site deployment included.
