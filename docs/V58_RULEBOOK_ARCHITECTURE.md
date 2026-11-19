# v5.8 Rulebook — typed decision to business proposal

Status: CODE_ADDED; LIVE_ZORO_AND_CROSS_INDUSTRY_ACCURACY_NOT_VERIFIED.

## Objective
Reconfigure a versioned question profile and deterministic policy per industry without assuming typed classification automatically makes downstream work safe.

Input -> Zoro System 1 typed answer (separate transport) -> schema validator -> rulebook proposal -> independent authorization (not built) -> idempotent business executor (not built) -> result read-back (not built).

Examples:
- rulebook/presets/account_change.json: bank details change signal -> OPEN_VERIFICATION_TASK, NOT actual account change.
- rulebook/presets/refund_intake.json: refund request and order reference -> OPEN_REVIEW_TASK or REQUEST_INFORMATION, NOT actual refund or SMS.

The rulebook engine is an isolated extension point, NOT wired to Arena's production policy. Existing Arena remains the submission demo and model execution entry point.
To preview a synthetic typed response without contacting Zoro:
python -m tools.rulebook_preview_v58 --book refund_intake --answers tests_rulebook/refund_fixture.json

## Contract
Rulebook schema includes schema_version, id, version, domain, questions, rules and minimum_confidence. Only bounded noul and choice question types are accepted; score is unsupported pending explicit semantics. Rules have id, when, action and priority; ambiguous same-priority matches require review. Inputs must contain complete typed answers with finite choice probabilities; uncertain, invalid or missing cases produce HOLD_FOR_REVIEW.

Output includes source book SHA-256, selected rule and confidence, tenant-scoped idempotency key, authorized=false, effects_executed=false, model_identity_verified=false. Idempotency key persistence and real authorization are explicitly NOT implemented. Decision thresholds 0.80 and 0.85 in samples are examples, not calibrated outcome probabilities.

## Two industry migration modes
A. Same classification meaning, new internal rule: retain question profile and alter only the rules, with new governance and tests.
B. New industry, such as customer support: change question profile plus rules; validate semantic accuracy, consent, ownership, business eligibility, data protection, real API permissions and independent user outcomes separately.

## Socratic counterexample
Unfounded assumption: changing questions and if-else yields 98% success in every industry. A correctly classified refund message can belong to a stolen account or previously refunded order. Answer classification can be correct while execution is illegal or duplicated. Hence model metric, policy metric and verified business outcome need different denominators. 30% versus 98% is a hypothesis, not a measured claim.

## SNM and 4D
Scenarios: normal, direct risk, negated quote, ambiguous instruction, missing identifier, model timeout, malformed typed response, duplicate or stale event, contradicting rules, tenant mixing, approval revoked, external API failure and operator recovery.
Structure: actor, statement, question version, proposal, policy, task, approval, evidence, real-world action.
Time: prompt and policy revision, request order, action retry, outcome read-back and retention.
Perspective: customer, legitimate counterparty, business owner, operator, independent reviewer.
Reverse validation: result -> executor authorization -> rule -> model choice -> source state.

NPU is hardware, not a strategy framework. On-device inference only qualifies after device/runtime/driver and actual p50/p95, energy and quality parity measurements. Existing remote Zoro HTTP does not demonstrate NPU utilization.

## Guardrails
No payment, refund, credential collection, SMS, banking change, account freeze or other external effects. No inference that no signal means safe. No conversion of arbitrary model output into authorization. Lock evaluation families before tuning or quoting accuracy, false positive/negative costs, abstention and throughput.

## Rollback
Rulebook can be unused or reverted without replacing existing Arena. Restore database snapshots separately; do not wipe open tasks.
