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
