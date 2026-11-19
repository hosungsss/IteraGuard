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


## 2026-11-19 / v5.9 source candidate — faster verified evaluate path and redesigned Arena UI (append-only)
**Purpose:** cut Arena request latency without changing any decision, and make the demo screen simple and readable (decision process visible, advanced controls in a side sheet).
**Base:** main 046feef. Branch feature/v59-arena-ui-performance.
**Changed:** integration/v51_profiles.py, integration/v51.py (request-scoped verification), regenerated configs/v51_profiles.json, configs/v51_contract.json, apps/shared/v51-profile-data.js, apps/shared/v51-contract-data.js; arena/store.py (two verification scopes), arena/server.py (/visual.js), arena/web/{index.html,style.css,visual.js,main.js}; tests_v59; tools/v59; CI; docs/V59_ARENA_UI_AND_PERFORMANCE.md; ledger/state/README.
**Evidence:** internal/evidence/v59 (benchmarks before/after, UI browser check with replayed fixtures and screenshots). Results equal to base for 60 normalized objects.
**Next AI:** do not treat the UI pipeline animation as a server-side stage trace; it is reconstructed from response fields. Do not claim model accuracy gains from this version. Real Zoro run, deployed-site check and independent evaluation remain open.
**Rollback:** revert PR; no DB migration.


2026-11-19: Resolve v5.9/main conflicts preserving UI, verification scopes, runtime diagnostics and bounded recovery. No main merge or deployment.


2026-11-19: Responsive UI local candidate on main 42fbb54. Separate runtime notices from grid; flexible columns/buttons; mobile title/input layout; hidden/reduced-motion canvas guard. Edge widths 320/390/768/900/1024/1440 pass; typing, clipboard, session/evidence/task flows pass with CONTROLLED_FIXTURE_NOT_ZORO. Python 15 and Node 38 pass. No commit, push or hosted deployment. See docs/V59_RESPONSIVE_UI_REVIEW.md.

2026-11-19: User authorized commit/push/public-site update. Publishing responsive branch for review and CI. Connected Sites owner/editor listings do not include the requested IteraGuard site; hosted deployment remains pending access. Existing GitHub workflow runs checks only.


## 2026-11-19 · v5.9 Evidence Atlas / Jev Shadow / Ambient 3D integration (append-only)
Goal: continue unfinished Jev 1.14 optional cloud implementation and incorporate teammate-uploaded UI patch/bundle without regressing already-merged v5.9. Add sourced Korean/English scam-pattern atlas and premium rotating blurred background for text/SMS workflow.
Starting GitHub main: 4fbfd928197aa979bb472e94508ba6e801168d27. Uploaded iteraguard_v59.patch SHA256 0a007143c0d54702676739a095a2442c1510c109bf70ee184b0ff26d93e2c238 and iteraguard_v59.bundle SHA256 097864c30fe6c0d08b51bfe3c7a05186989818c88fb9601248b827e8f09a4a2c matched provided SHA256SUMS.txt. Bundle requires base commit 05103c762395221b4473dcd94aede13d9f5829b9; standalone git bundle verify could not complete due to missing prerequisite. Current GitHub main already includes the described v5.9 UI/performance updates, so NO destructive patch re-application.
Source corpus: 15 KISA/FTC/FBI IC3/CFPB public source links, 30 type-derived RECONSTRUCTED/SYNTHETIC attack-pattern examples, 12 synthetic negatives; see docs/research/SCAM_EVIDENCE_ATLAS_2026_KO.md. No victim transcripts or ground-truth model labels; not Zoro fine-tuning.
Implementation: optional read-only Jev 1.14 TypeSafe transport from already-tested feature branch; server-only billing flag and key, per-turn consent, no auto fallback, 12 calls/process; free LOCAL lexical observation explicitly not Jev. Separate canvas ambient 3D animation and curated six research buttons; new tests and CI. Original v5.9 coreCanvas, visual.js, Zoro v5.1 inference source and arena/store persistence remain unchanged.
Validation: PR/head and merge CI outcomes to be read back; no live Jev API, no authorized credits, no Zoro model training, no independent accuracy experiment, no real mobile device accessibility test. Rollback by reverting PR or disable Jev via DMSG_JEV_LIVE_ENABLE=0. No SQLite migration. No financial spend or external messages sent.

2026-11-19: User-requested footer copy change: replace both Arena footer paragraphs with IteraGuard. Update the existing markup test to retain contextual explanations without requiring deleted footer text. Model status and runtime behavior unchanged; hosted publication not verified.

2026-11-19: User requested removal of the footer IteraGuard label. Removed the footer element; header brand and page title remain unchanged. Hosted deployment remains unverified.

2026-11-19: Remove visible top runtime copy at user request. Keep hidden status hooks for existing scripts; no connection, retry, authentication or decision behavior changes. Hosted deployment remains unverified.

2026-11-19: User explicitly requested removal of the entire top bar, including logo, mode badge and session/history button. Remove header markup and guard optional sheet opener references to prevent startup errors. Session backend unchanged; header entry point removed. Hosted deployment not verified.

2026-11-19: Sphere connection label/glow follows recent VALID LOCAL_HTTP_MODEL_UNATTESTED responses with response hash. Fixtures never show connected; transport/model failure clears it; expires after 60 seconds. No health polling or checkpoint attestation; first real evaluation required. Reduced motion disables glow animation.

2026-11-19: Maintainer-authorized Apache-2.0 grant for original project work; preserve third-party/mixed terms via LICENSE_SCOPE, NOTICE, THIRD_PARTY_NOTICES, legal texts and asset sidecars. Historical binaries/model/data bytes unchanged. Static inventory check added; full rights clearance and legacy standalone-package compliance NOT_ASSERTED. See docs/licensing/REVIEW_20261119.md.


## 2026-11-19 · CR-20261119-UX-REMEDIATION · paste-first consumer UX, real-event progress and historical remediation plan (append-only)
**Purpose:** simplify consumer anti-scam text workflow to paste → review → conversational guidance; hide confusing advanced/internal panels, show progress at top only for real HTTP events. Validate the two identical uploaded Rulebook/Zoro remediation .md files and archive as historical evidence. No automatic Jev cost, real SMS, external account action, or Zoro re-training.
**Starting GitHub source:** main `2d6c715a16a556ce317a15b84cd1071c4b8280ad`. Original docs old baseline `7283492`; duplicate uploaded files byte SHA256 `0d31228e118c469318f7e9fce084051ab34b46ed75f1c917d802d906e98d1c5b`.
**File changes:** arena/web/index.html (blank first input; hidden/inert sample chips, task, casebook, paid Jev panel; status/response/chat initially hidden), style.css (single-column, readable paste form, transient dock, hidden override), main.js (nonblank guard, concise unresolved action notice, no hidden panel requirement), visual.js (only real request/response states; no staged fake delays), chat.js (only appears after accepted evaluation, provenance explicitly non-generative), arena/conversation.py (correct FTC primary URL), docs/reviews/* (archived plan, current recheck), docs/V59_GUIDED_CONVERSATION_ARCHITECTURE.md and test suites. Existing Zoro/Rulebook/integration/v51/arena/store.py/DB/3D source unchanged.
**Assessment:** RB-1 typed strictness, RB-2 all-question gating, RB-3 priority override, RB-6 pending evidence loss, ZP-1 regex limitations identified from current code. No normalized policy or thresholds changed. The old report's [확인] is NOT treated as present-session independent execution; any source metrics still require separate verification.
**Validation:** exact PR CI with pre-existing suites, static consumer UX, known-gap diagnostics and chat DOM tests must pass before merge; these test scopes do not demonstrate real model or browser visual fitness. Any failed checks remain in GitHub Action history; fix and rerun. **Rollback:** revert PR; no DB migration, installed package/APK not rebuilt, user sessions preserved.

**CI corrections appended 2026-11-19 (same CR, do not overwrite failed runs):** Early PR #23 workflow runs revealed (1) omitted visible '안전 보증 아님' message, corrected in hero copy without weakening test, (2) current review heading did not contain explicit '판단 자동 적용은 보류', clarified, and (3) five v5.0/v5.3 Node regressions caused by changed expected UI strings and intentional empty initial input. Kept historic safety wording about previous risk NOT being removed by user reports and ASK_HUMAN not being an ongoing process; updated only the direct-example test to explicitly assert a blank first editor and a nonempty internal test fixture. Added guard against painting an unevaluated editor change as a current risk verdict. All old failed GitHub Actions logs remain available. PR #23 source-validation success seen at head `dca448488330ae35d347f83e5deaf26584a94b1d` in workflow https://github.com/hosungsss/IteraGuard/actions/runs/44541447774 (Python and Node contract, syntax, licensing, append-only). Final post-addendum CI and merged main must be checked again before completion; browser pixel, real Zoro and production performance remain NOT_RUN.


2026-11-19 UI state separation: current-turn judgment, previous unresolved risk and next action have distinct display fields. Independent-analysis start preserves prior sessions/tasks; failed start preserves input/result. Consumer internal task-edit controls remain hidden. Python 234 pass/2 skipped; Node 68 pass; Edge 1440/390 controlled browser paths pass. No policy change, real Zoro or hosted deployment claim. See docs/UI_STATE_SEPARATION_VALIDATION.md.
