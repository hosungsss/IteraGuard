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

2026-11-19: User explicitly requested removal of the entire top bar, including logo, mode badge and session/history button. Remove header markup and guard optional sheet opener references to prevent startup errors. Session backend unchanged; header entry point removed. Hosted deployment not verified.

2026-11-19: Sphere connection label/glow follows recent VALID LOCAL_HTTP_MODEL_UNATTESTED responses with response hash. Fixtures never show connected; transport/model failure clears it; expires after 60 seconds. No health polling or checkpoint attestation; first real evaluation required. Reduced motion disables glow animation.

2026-11-19: Maintainer-authorized Apache-2.0 grant for original project work; preserve third-party/mixed terms via LICENSE_SCOPE, NOTICE, THIRD_PARTY_NOTICES, legal texts and asset sidecars. Historical binaries/model/data bytes unchanged. Static inventory check added; full rights clearance and legacy standalone-package compliance NOT_ASSERTED. See docs/licensing/REVIEW_20261119.md.


2026-11-19 · v5.9 consumer paste-first UI and remediations audit candidate: the existing Zoro-1 + v51 policy and persisted unresolved-risk semantics remain unchanged. Main screen has empty text editor, clear manual Review action, response / guided-chat, and a top progress dock shown only during actual /api/evaluate HTTP request. Internal casebook, Task edit and TypeSafe Jev opt-in panel are hidden/inert from consumers, not deleted; no external calls are auto-enabled. Mock stages are no longer delayed after response as if live model stages streamed. Synthetic-only contract and PII warning remain; **not** a real-world PII-safe deployed anti-fraud service. The teammate remediation document dated at old main 7283492 is archived with source SHA256 in docs/reviews/; a current-source review documents verified contract/priority hazards, defers all outcome-changing threshold/priority/regex adjustments until independent labels. Chat UI tests/documentation are carried forward from unmerged prior audit branch. Browser pixels/live Zoro/real messages remain NOT_RUN; see exact PR CI.


2026-11-19 UI state separation: current-turn judgment, previous unresolved risk and next action have distinct display fields. Independent-analysis start preserves prior sessions/tasks; failed start preserves input/result. Consumer internal task-edit controls remain hidden. Python 234 pass/2 skipped; Node 68 pass; Edge 1440/390 controlled browser paths pass. No policy change, real Zoro or hosted deployment claim. See docs/UI_STATE_SEPARATION_VALIDATION.md.


2026-11-19 · 문자 신호등 미리보기. Arena 홈에서 /signal을 열 수 있습니다. /api/signal은 합성·비식별 텍스트로 로컬 Zoro의 선택형 질문 한 개를 실행하며 기존 평가, 세션, 확인 업무와 분리됩니다. 실제 로컬 Zoro 호출 6건에서 네 등급을 모두 관찰했습니다. 예방 경고는 초록이었으며, 과거 피싱 인용 신고 한 건은 빨강으로 분류됐습니다. 이 관찰의 정확도 일반화와 독립 평가는 미검증입니다.


2026-11-19: Integrated origin/main 636f56b by fast-forward, preserving 9ed5dac UI state separation. No conflicts or runtime code edits required. Python 237 passed / 2 skipped, Node 68 passed, Edge 1440/390 controlled session flows passed, licensing 608-file inventory passed. Signal preview HTTP checks included; live model and hosted deployment NOT_RUN in this integration. See docs/MAIN_INTEGRATION_VALIDATION_20261119.md.

2026-11-19 · Arena 분석 결과 상단에 현재 문자 조로 신호등을 표시합니다. 합성·비식별 입력을 사용하며 별도 페이지 진입 없이 기존 판단 버튼으로 실행합니다. 조로의 단일 등급 질문과 기존 Arena 분석·세션·업무를 분리합니다. 과거 인용을 위험으로 분류할 수 있습니다.

2026-11-20 · 메인 시연은 신호등과 현재 요청 행동 두 항목을 표시합니다. 합성·비식별 원문과 두 선택형 질문을 한 번에 로컬 Zoro로 보냅니다. 기본 웹 판단은 세션과 확인 업무를 생성하지 않습니다.
