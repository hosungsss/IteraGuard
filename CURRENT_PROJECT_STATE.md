# IteraGuard — Current project state (2026-11-19 KST)

Source candidate: v5.8 (GitHub integration); previously published Arena engine: v5.6; typed contract: v5.1.
Primary entrypoint remains python -m arena.server. Existing v5.6 Zoro transport remains unchanged and must be verified against the currently configured model server.
New separate domain rulebook: proposal-only, no network/business effects; refund and account-change books. Source UI v5.8 additions: synthetic examples, selected task binding, redacted evidence JSON export.

Evidence state for NEW code: local/CI tests must be read from the corresponding commit; verified model identity, independent industry success rate, Android NPU, real bank/refund actions and field outcomes: NOT_VERIFIED.
Past v5.6 local verification is historical, not current checkout pass. The 30% to 98% rulebook effectiveness claim is NOT_MEASURED.
Official Track 1 requires actual Zoro-1 System 1 and live demo, three execution logs, accessible repo/demo and Google Slides presentation. NOT_SUBMISSION_READY until confirmed.
Source of truth: AGENTS.md -> README.md -> this file -> internal/VERSION_LEDGER.md -> current code/evidence. Original model API remains /v1/systemone.


v5.8 optional Rulebook System One bridge: rulebook/zoro_bridge.py can call the existing operator-configured /v1/systemone ModelClient only when explicitly enabled by a separate synthetic CLI. It creates proposed actions only. TEST_DOUBLE contract tests distinguish modeled transport from real Zoro; independent checkpoint/head verification and end-to-end industry/business effects remain NOT_RUN.
