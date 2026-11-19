# IteraGuard — Current project state (2026-11-19 KST)

Source candidate: v5.8 (GitHub integration); previously published Arena engine: v5.6; typed contract: v5.1.
Primary entrypoint remains python -m arena.server. Existing v5.6 Zoro transport remains unchanged and must be verified against the currently configured model server.
New separate domain rulebook: proposal-only, no network/business effects; refund and account-change books. Source UI v5.8 additions: four contextual synthetic messages, selected task binding, redacted evidence JSON export. In an isolated local Zoro-1 demo rehearsal, the unclear request, account-change payment request, and normal follow-up matched the expected current-turn outcomes. The two open tasks survived the follow-up. The standalone preventive notice produced an extra review task.

Evidence state for NEW code: local/CI tests must be read from the corresponding commit; verified model identity, independent industry success rate, Android NPU, real bank/refund actions and field outcomes: NOT_VERIFIED.
Past v5.6 local verification is historical, not current checkout pass. The 30% to 98% rulebook effectiveness claim is NOT_MEASURED.
Official Track 1 requires actual Zoro-1 System 1 and live demo, three execution logs, accessible repo/demo and Google Slides presentation. NOT_SUBMISSION_READY until confirmed.
Source of truth: AGENTS.md -> README.md -> this file -> internal/VERSION_LEDGER.md -> current code/evidence. Original model API remains /v1/systemone.


v5.8 optional Rulebook System One bridge: rulebook/zoro_bridge.py can call the existing operator-configured /v1/systemone ModelClient only when explicitly enabled by a separate synthetic CLI. It creates proposed actions only. TEST_DOUBLE contract tests distinguish modeled transport from real Zoro; independent checkpoint/head verification and end-to-end industry/business effects remain NOT_RUN.


V5.8 Rule Tweak Candidate 1 (2026-11-19): an independent bounded Korean warning/report observer is now attached to the Python Arena response path in SHADOW mode only. The original published v5.6/v5.1 semantic policy, persistent task processing, model transport, and optional industry Rulebook remain authoritative and unmodified. Enforce is blocked; optional DMSG_RULE_TWEAK_MODE=off disables observation. New independent evaluation, actual Zoro re-inference, browser/device/NPU validation and general accuracy gains remain NOT_VERIFIED. See docs/V58_RULE_TWEAK_SHADOW_REVIEW.md and exact commit CI.


## 2026-11-19 — v5.8 Text Decision Studio Jev Shadow source candidate
A text/SMS-first standalone Arena secondary workspace has been added to current main development work. Free mode is a local lexical indicator only. Jev 1.14 is pinned to the official TypeSafe API but is strictly off by default until separately configured billing authorization (server-side key + LIVE_ENABLE=1 + SPEND_ACK), plus per-message browser consent. No real Jev API invocation, no authorized cost, no commercial free route, no independent Jev-vs-Zoro accuracy evidence. No existing Zoro policy/task/risk semantics are intentionally changed. New high-contrast responsive UI and CI tests are source level; device/browser visual verification remains NOT_RUN. See docs/V58_JEV_CLOUD_TEXT_STUDIO.md.
