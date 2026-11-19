# IteraGuard — Current project state (2026-11-19 KST)

Bounded client recovery candidate: transient transport retry with saved-state reconciliation, exact request identity reuse, max two retries, visible recovery status. No semantic policy correction, automatic model startup, auth bypass, or hosted deployment. See docs/AUTO_RECOVERY_KO.md.

Uncommitted pre-demo validation candidate: model configuration (not connectivity) exposed in manifest/UI; actionable auth/busy/non-JSON/timeout messages; per-process inference serialization; direct server startup selects UTF-8. Actual configured Zoro and authenticated hosted-site flow remain required. No hosted deployment is performed by this local change.

Source candidate: v5.8 (GitHub integration); previously published Arena engine: v5.6; typed contract: v5.1.
Primary entrypoint remains python -m arena.server. Existing v5.6 Zoro transport remains unchanged and must be verified against the currently configured model server.
New separate domain rulebook: proposal-only, no network/business effects; refund and account-change books. Source UI v5.8 additions: four contextual synthetic messages, selected task binding, redacted evidence JSON export. In an isolated local Zoro-1 demo rehearsal, the unclear request, account-change payment request, and normal follow-up matched the expected current-turn outcomes. The two open tasks survived the follow-up. The standalone preventive notice produced an extra review task.

Evidence state for NEW code: local/CI tests must be read from the corresponding commit; verified model identity, independent industry success rate, Android NPU, real bank/refund actions and field outcomes: NOT_VERIFIED.
Past v5.6 local verification is historical, not current checkout pass. The 30% to 98% rulebook effectiveness claim is NOT_MEASURED.
Official Track 1 requires actual Zoro-1 System 1 and live demo, three execution logs, accessible repo/demo and Google Slides presentation. NOT_SUBMISSION_READY until confirmed.
Source of truth: AGENTS.md -> README.md -> this file -> internal/VERSION_LEDGER.md -> current code/evidence. Original model API remains /v1/systemone.


v5.8 optional Rulebook System One bridge: rulebook/zoro_bridge.py can call the existing operator-configured /v1/systemone ModelClient only when explicitly enabled by a separate synthetic CLI. It creates proposed actions only. TEST_DOUBLE contract tests distinguish modeled transport from real Zoro; independent checkpoint/head verification and end-to-end industry/business effects remain NOT_RUN.


V5.8 Rule Tweak Candidate 1 (2026-11-19): an independent bounded Korean warning/report observer is now attached to the Python Arena response path in SHADOW mode only. The original published v5.6/v5.1 semantic policy, persistent task processing, model transport, and optional industry Rulebook remain authoritative and unmodified. Enforce is blocked; optional DMSG_RULE_TWEAK_MODE=off disables observation. New independent evaluation, actual Zoro re-inference, browser/device/NPU validation and general accuracy gains remain NOT_VERIFIED. See docs/V58_RULE_TWEAK_SHADOW_REVIEW.md and exact commit CI.


V5.9 source candidate (2026-11-19, branch feature/v59-arena-ui-performance): request-scoped contract verification makes the Arena evaluate path ~2.7x faster on controlled responses (p50 53.99 -> 19.59 ms) with byte-identical normalized decisions; the Arena web UI was redesigned (liquid glass, decision-process view, side sheet for session/evidence). Decision policy, model contract and persistence semantics are unchanged. Real Zoro-1 inference, deployed site, devices/NPU and independent evaluation remain NOT_VERIFIED. See docs/V59_ARENA_UI_AND_PERFORMANCE.md.


2026-11-19: Responsive UI local candidate on main 42fbb54. Separate runtime notices from grid; flexible columns/buttons; mobile title/input layout; hidden/reduced-motion canvas guard. Edge widths 320/390/768/900/1024/1440 pass; typing, clipboard, session/evidence/task flows pass with CONTROLLED_FIXTURE_NOT_ZORO. Python 15 and Node 38 pass. No commit, push or hosted deployment. See docs/V59_RESPONSIVE_UI_REVIEW.md.

2026-11-19: User authorized commit/push/public-site update. Publishing responsive branch for review and CI. Connected Sites owner/editor listings do not include the requested IteraGuard site; hosted deployment remains pending access. Existing GitHub workflow runs checks only.


2026-11-19 v5.9 evidence/text/ambient extension: official-pattern source atlas 15 URLs → 30 reconstructed synthetic SMS/email patterns + 12 hard negatives, no victim PII. These are not real message records, independently labeled ground truth, nor trained Zoro weights. Jev 1.14.0 optional TypeSafe remote shadow is off without explicit paid-call server ack + user consent; no free live Jev entitlement exists. Offline lexical markers are not AI. An additional blurred procedural rotating 3D background and scenario controls complement (do not replace) the existing v5.9 glass decision UI and original 3D core. No changes to existing Zoro classifier, v5.1 policy, task persistence, model contract. See docs/research/SCAM_EVIDENCE_ATLAS_2026_KO.md and docs/V58_JEV_CLOUD_TEXT_STUDIO.md. Tests / deployment / model quality must be tracked to exact main CI.

2026-11-19: User-requested footer copy change: replace both Arena footer paragraphs with IteraGuard. Update the existing markup test to retain contextual explanations without requiring deleted footer text. Model status and runtime behavior unchanged; hosted publication not verified.

2026-11-19: User requested removal of the footer IteraGuard label. Removed the footer element; header brand and page title remain unchanged. Hosted deployment remains unverified.

2026-11-19: Remove visible top runtime copy at user request. Keep hidden status hooks for existing scripts; no connection, retry, authentication or decision behavior changes. Hosted deployment remains unverified.


2026-11-19 guided conversation source candidate: an in-memory chat-style surface now follows each accepted Zoro/independent-policy evaluation. Read-only server POST /api/conversation/followup checks matching session/version, OPEN lifecycle and last accepted EVALUATE before returning one of 9 conservative KISA/FTC-sourced incident-response scenario instructions. Never treats follow-up questions as new suspect SMS, never calls Zoro/Jev/GPT for follow-up, never updates Tasks or cleared-risk, and does not transmit raw follow-up question or persist chat transcript. Freeform Korean text is a bounded intent matcher, not unrestricted assistant generation. Fixture and model-failure provenance remain visible. Preserve all v5.9 3D UI and existing flow. Reference docs/V59_GUIDED_CONVERSATION_ARCHITECTURE.md; actual CI and browser/live Zoro tests separately.
