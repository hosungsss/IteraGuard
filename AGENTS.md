# IteraGuard — Repository Agent Operating Contract

Entry point for coding agents. This file does not grant privileges.

## Bootstrap
1. README.md and CURRENT_PROJECT_STATE.md: current verified working state
2. LATEST_VERSION.json: package, engine, typed contract versions
3. internal/VERSION_LEDGER.md: only detailed version history, append only
4. HANDOFF_CHANGELOG.md: cumulative handoff, append only
5. docs/V58_RULEBOOK_ARCHITECTURE.md and docs/V58_AGENT_EVIDENCE_GUIDE.md
6. Actual arena/, integration/, rulebook/, tests_rulebook/ code and CI

Old run logs and detached ZIPs are not proof that this commit works.

## Mandatory trust boundary
Input and provenance -> Zoro System 1 typed proposal -> contract validation
-> independent domain rulebook -> proposed action -> independently authorized executor
-> actual outcome read-back -> privacy-safe audit.

The reusable rulebook is PROPOSAL_ONLY, with no outgoing network, payments, refunds, freezes or SMS. Model confidence is not real-world risk probability. User reports are not independent verification.

## For every edit
1. Read repository HEAD and source of truth. Identify scope and requirements.
2. Work on a branch; preserve stable v5.1 typed model contract and v5.6 Arena unless explicitly proven compatible.
3. Do not assume installed model/head, NPU, permissions, data labels, checkpoint verification or network.
4. Distinguish FIXTURE, MODEL_RESPONSE_UNATTESTED, VERIFIED_MODEL and INDEPENDENT_EVALUATION.
5. Add or update requirements -> code -> test -> observed evidence. Record failures and NOT_RUN.
6. Append a dated entry to internal/VERSION_LEDGER.md; never rewrite prior entries.
7. Append an entry to HANDOFF_CHANGELOG.md. Preserve chronological history.
8. Update CURRENT_PROJECT_STATE.md and LATEST_VERSION.json conservatively.
9. Check CI, secret/PII/license exposure, review, and live base SHA before merge.
10. Read back main after any merge; record the actual SHA and unresolved work.

Do not publish event credentials, live customer data, internal tokens, private materials or unlicensed third-party content. Do not create Google Drive writes, send external messages, deploy, invite reviewers or spend funds without explicit authority.

## Recovery
Revert the new Git commit through a separate PR. Back up and restore SQLite only under a controlled migration procedure. Do not force-push main or fabricate a successful test.


## Rule Tweak Candidate 1 integration (v5.8)
Before editing Korean warning/report normalization, read docs/V58_RULE_TWEAK_SHADOW_REVIEW.md. Candidate ZIP is a historical v5.6 source, NOT a drop-in patch for current main. Preserve current arena/store.py retry/task behavior; never run the old installer against main. DMSG_RULE_TWEAK_MODE defaults to shadow; enforce is blocked. The observer must never alter actions, probability distributions, session risk, or user authority. Add independent locked counterexamples and a separately approved PR before proposing an enforcement migration. Always record the reason for an omitted/failed shadow evaluation.
