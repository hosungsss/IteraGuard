# IteraGuard Text Decision Studio — Jev 1.14 cloud option (2026-11-19)

**Status:** v5.8 source-level integration candidate. The new arena/secondary.py is an independent text-only observer. Zoro-1 remains the authoritative model proposal into the existing Arena v5.1/v5.6 policy and task state. No existing artifact package, PWA, APK or dmsg.skill has been rebuilt or independently validated.

## What is actually free?

- **Free and locally runnable:** POST /api/secondary/check with fields text, synthetic_only:true, mode:offline. Uses only a small group of Korean/English lexical patterns. No Jev, no AI model inference, no bill, no safety verdict. Never label this Jev.
- **Official Jev 1.14 API:** TypeSafe provides the pinned model ID jev-1.14.0 via POST https://api.typesafe.ai/v1/systemone, with per-input-token billing. On 2026-11-19 TypeSafe says it does not offer startup, research or trial credits. Vercel's monthly AI Gateway free credits do not cover Jev. Never label it free or attempt unauthorized billing bypass.
- **Real live Jev:** NOT_RUN in this change; the development user provided no real credential or credits. CI uses controlled test doubles, not real model inference.

Official evidence:
- https://docs.typesafe.ai/models
- https://docs.typesafe.ai/api/system-one
- https://help.typesafe.ai/articles/1592415054-do-you-offer-startup-research-or-trial-credits-or-redeem-codes
- https://vercel.com/docs/ai-gateway/pricing
- https://community.vercel.com/t/ai-gateway-jev-returns-403-no-providers-available-on-hobby-team/49885

## Zero-cost local quick start

1. Keep existing Zoro loopback /v1/systemone settings. Never replace the Zoro endpoint with Jev.
2. Run: python -X utf8 -m arena.server --port 8769 --db runs/arena.sqlite3
3. Open http://127.0.0.1:8769. Select synthetic sample text. Click the free local text-pattern observation. Jev cloud stays disabled without authorization.

## Optional paid Jev: enable only under separately approved financial limits

Configure on the server ONLY (never the browser, repository, client-side JS or log screenshots):

~~~powershell
$env:TYPESAFE_API_KEY = "<your TypeSafe API key>"
$env:DMSG_JEV_LIVE_ENABLE = "1"
$env:DMSG_JEV_SPEND_ACK = "I_ACKNOWLEDGE_CHARGES"
python -X utf8 -m arena.server --port 8769
~~~

All three settings are required, plus a browser checkbox and confirmation for EACH request. Key is never included in browser responses. The server reserves a maximum of 12 calls per process, makes no automatic retry, uses a fixed 8-second timeout and 2,000-character limit. **The process limit is NOT a real monetary budget and resets on restart.** Configure provider limits and disable auto-recharge to prevent unintended costs.

The application remains for synthetic input only. Do not enter personal messages, phone numbers, account identifiers, customer information or secrets. The synthetic_only flag is a user assertion, NOT independently verified anonymization.

## Trust boundaries and API

- GET /api/secondary/capabilities: readiness, model identifier, price-warning and consent status without credentials.
- POST /api/secondary/check mode offline: text / synthetic_only:true / mode:offline. Returns indicators and action:null, safety_verdict:null, external_call:false.
- POST /api/secondary/check mode jev: additionally consent_external:true. Requires all three operator-side permissions. HTTPS endpoint and exact version jev-1.14.0 are fixed. No redirect, environment proxy, arbitrary host or automatic retry.
- Sent question profile has choice speech-act scope and noul current sensitive action. Strict validation requires exact question keys, model version echo, finite probabilities and a valid distribution/argmax, usage, bounded JSON.
- Provider 402, authentication failures, 429, network outages or malformed results produce a sanitized error. They are NEVER converted into fake Jev results.
- There is NO shared Jev cache, no SQLite write, no task creation, no action execution and no model arbitration. The UI invalidates an old observation when text changes.
- Jev's two question prompts are thematically related to, but NOT identical to, the main Zoro typed profile. Do not average model probabilities or report like-for-like accuracy without independent ground truth.

## Scenario Network and counterexamples

| Situation | Acceptance |
| --- | --- |
| Ordinary synthetic SMS | Zero-cost indicators may be empty; never declare safe |
| OTP demand, account-switch request | Lexical terms do not become a scam probability |
| Protective warning / quotation | No automatic safety clearing |
| Mixed negation plus direct risk | Jev cannot override Zoro PAUSE or session risk |
| Missing API key, billing approval, or per-turn consent | No remote request |
| Wrong Origin, extra JSON keys | Reject before doing work |
| Provider 402/403/429/timeout/invalid JSON | No fake success or retry |
| Text edited while Jev is in flight | UI discards stale shadow result |
| Over-limit input, repeated attempts | Validate size and process call reservation |

## Quality and 4D evidence

Record exact Jev model/endpoint and the shared input revision; model raw result, action policy, task, provenance and independent human label must not be conflated. Model disagreement by itself does not tell which model is right.

Before claiming quality improvements: run independently human-labelled locked Korean SMS cases with Zoro baseline, Jev and candidate review escalation. Measure false negatives, false positives, abstention, calibration (if justified), disagreement, p50/p95 latency, provider errors and cost with denominators. Do not reuse edited development cases as a held-out test.

## UI / accessibility

Reworked dependency-free responsive dark studio, focused on text entry, current Zoro guidance, optional secondary checks, session state and task history. Includes native focusable controls, status regions, visible focus, mobile reflow and reduced-motion support. These design decisions are not a substitute for actual browser screenshots, accessibility/contrast auditing or mobile device testing; such checks remain NOT_RUN.

## Requirements traceability

- JEV58-01 truthful zero-cost local observation — arena/secondary.py, tests_secondary.
- JEV58-02 exact pinned Jev remote contract and fail-closed no-billing default — arena/secondary.py.
- JEV58-03 explicit per-request user consent, no auto calls — arena/web/secondary.js and tests.
- JEV58-04 loopback/origin checks, fixed TLS endpoint, redaction, bounded read, error/limit handling — server/backend and HTTP tests.
- JEV58-05 preserve Zoro, Rulebook and Task logic — existing tests_v51/v54/v56/tests_rulebook.
- JEV58-06 text-first responsive/a11y UI — HTML/CSS/JS + static checks. Real browser verification pending.
- JEV58-07 append-only ledger and read-back — CI and docs.

## Rollback

Revert this PR or set DMSG_JEV_LIVE_ENABLE=0. No SQLite migration needed and do not delete active sessions.

**Not verified:** actual Jev endpoint call, provider eligibility, true checkpoint identity, actual live cost, commercial free tier, independent accuracy improvement, automatic PII redaction, browser screenshot, Android, NPU, package rebuild. Public repo does not contain secrets or live messages.
