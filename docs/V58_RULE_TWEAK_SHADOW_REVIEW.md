# v5.8 Rule Tweak Candidate 1 — safe read-only integration

Status: SHADOW_ONLY_SOURCE_CANDIDATE. No independent human evaluation, production model recheck, browser/NPU validation, or real-world improvement claims.

## Source and reconciliation
Original team handoff: IteraGuard_v56_RuleTweak_Candidate1.zip, SHA-256 c82708fc31ca6825991099e53a1ccf9c71dfd6cd9b4ee514c0159d7fc115dc9d (19 entries, CRC clean). ZIP's original integration/rule_tweak.py SHA-256 fa394bbd2ea1834ca75984add0d4112ef0da6e5dbb745a468bd276cb37adbc32. README and separate 설치법.md provide installation instructions. Historic baseline commit 17e3bf5b1dbf7288254c7950bce991e81419fb42; actual current main base for integration 7e43d6afbc5fa720d83fa72921c7c09520e27cd8.

Original installer/payload/arena/store.py and the v5.1 contract generation files are NOT merged: overwriting them would regress the newer v5.6 task retry and v5.8 source. Instead a dedicated observer was adapted from bounded grammar and thresholds and inserted after the existing v5.1 semantic/local layers, before persistent Arena session transition.

## Actual design
- integration/rule_tweak_shadow.py: bounded Korean protective-warning and past-quote *candidate* recognizer, with existing model question probability gates; only examines existing typed response and current message. It makes NO new model calls.
- configs/rule_tweak_shadow.json: candidate's pre-declared, **not independently calibrated** thresholds. Loaded once per process; SHA recorded in trace.
- Arena output: execution_trace.rule_tweak_shadow reports status, candidate rule, baseline action, proposed action, source-module and config SHA; never stores raw text. No change to actual action/reason, probability, prior risk, task creation, model retry resolution, or user-report authority.
- Mode: DMSG_RULE_TWEAK_MODE=shadow (default) or off. Setting enforce is explicitly BLOCKED and produces a non-mutating diagnostic; never silently escalates the candidate to authority. Restart to change process mode, and use separate sessions for controlled measurement.
- Errors in the observer cannot veto the primary model decision: a sanitized SHADOW_OBSERVATION_ERROR is recorded, not an exception message.
- Uses the canonical Python Arena path only. PWA/APK/Rulebook engines are unchanged and therefore do not claim shadow coverage.

## Why no enforce yet
Existing v51_semantic_rules.json already includes EXPLICIT_CREDENTIAL_WARNING and EXPLICIT_PAST_CREDENTIAL_REPORT. Some apparent gains may duplicate the current policy; comparing to an older v5.6 baseline cannot prove improvements over this main.
The candidate's old M03 CAUTION may create an extra OPEN task if its reason is not excluded from the current task logic. Blind enforcement could increase workload or accidentally relax safety in another context. Shadow does not take that risk.

The 12 historic replay cases (off/shadow 10/12, enforce 12/12 expectations) are development-derived and **not** an independent accuracy or business-performance measurement.

## SNM test gates
1. Protective warning vs direct "send code" request; quoted past request vs active instruction; mixed warning plus new transfer/install/URL.
2. Model omitted/malformed answers, invalid probabilities, model unavailability, retry, repeat event and out-of-order session version.
3. Existing previous PAUSE and unresolved task must persist after a normal message.
4. Ask-human tasks after new current uncertainty; deduplicated tasks and no false safe completion on user report.
5. Comparison B0=existing policy versus B1=shadow hypothetical proposals on identical locked typed responses; newly collected human-labeled adversarial set, grouped by source/template, report denominators, false safety relaxation, over-review, abstention, p50/p95 overhead.
6. Only a separately reviewed future PR may propose enforce; it must explicitly track task semantics, idempotency keys, source hashes, rollback and business permission.

## 4D and NPU
4D: model raw/digest, policy, tweak trace, session version, user/third-party perspective, task and evidence read-back. Maintain both input->action and output->source trace. Shadow proposals are never authoritative facts.
NPU: no device inference; this is CPU/Python bounded grammar only. No acceleration claims.

## Rollback and provenance
Revert this PR. Original archived ZIP remains outside public Git; only the tailored logic and SHA reference are published. The old baseline manifest is preserved. Since the observer is side-effect-free, no DB migration is necessary; active sessions must not be deleted. Disable immediately with DMSG_RULE_TWEAK_MODE=off if instrumentation causes unexpected overhead. Protect private logs, tokens, backups and raw personal messages.

## CI/environment compatibility note
Baseline v51 semantic JS-data source was generated under Unicode 15.0; the historic full regression expects that exact version. CI uses Python 3.12. Initial Python 3.11 verification failed with STALE_V51_SEMANTIC_DATA and was not counted as a new product failure. Expanded Node UI verification also required graceful handling of absent querySelectorAll in the minimal DOM test harness; normal browser functionality remains available. Do not mistake either test-environment repair for a change in model accuracy.
