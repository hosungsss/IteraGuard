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


## 2026-11-19 · 문자 신호등 웹 미리보기
기준 main 41461f98deee145200a9ac230ab553341d56a80d. Arena 홈에서 /signal로 연결합니다. POST /api/signal은 합성·비식별 텍스트에 q_signal 선택형 질문 한 개만 로컬 Zoro로 전송하고 공용 응답 계약으로 검증합니다. 기존 Arena 판단, 이전 위험, 확인 업무는 기존 경로에서 처리합니다.
검증: HTTP·업무 회귀 테스트 17건 통과. 실제 로컬 Zoro의 합성 6건 중 5건은 설정한 기대와 같았고, 과거 인용 신고 1건은 빨강으로 분류됐습니다. 화면은 등급 기준과 대응 안내를 표시합니다. 독립 정확도 평가는 미실행입니다.
복구: PR을 되돌린 뒤 신호등 웹 경로 연결을 제거합니다. DB 마이그레이션은 없습니다.


2026-11-19: Integrated origin/main 636f56b by fast-forward, preserving 9ed5dac UI state separation. No conflicts or runtime code edits required. Python 237 passed / 2 skipped, Node 68 passed, Edge 1440/390 controlled session flows passed, licensing 608-file inventory passed. Signal preview HTTP checks included; live model and hosted deployment NOT_RUN in this integration. See docs/MAIN_INTEGRATION_VALIDATION_20261119.md.

## 2026-11-19 · 문자 신호등을 분석 결과에 표시
기준 main 636f56b. 기존 판단 결과 상단에 신호등을 추가했습니다. 기존 평가 응답을 반영한 뒤 같은 입력으로 /api/signal을 호출하며, 입력이 바뀌면 이전 색을 숨깁니다. 신호등 오류는 회색으로 표시하고 기존 판단 및 저장 기록을 유지합니다. /signal 경로는 메인 화면을 제공합니다.

## 2026-11-20 · 공개 메인 시연의 두 가지 조로 답변
기준 main 20652f0. 메인 입력과 실제 사례 불러오기 동작을 연결하는 폼은 /api/signal을 한 번 호출합니다. config의 사용자 제공 행동 후보 20개(q_action)와 신호등(q_signal)을 한 요청에 담습니다. 결과 카드에는 등급과 요청 행동 답변을 표시합니다. 이전 기록을 읽고 유지하는 Arena API는 호환 경로로 둡니다.


2026-11-20: Signal-only bounded context reconciliation preserves original model scores/grade/action and reports corrections. Full recognized warning/report clauses distinguish past/negated requests; unknown or sensitive-action + green conflicts defer to gray. Existing Arena policy and shadow remain unchanged. Python 244 pass/2 skipped; Node 71 pass; controlled Edge 390/1440 pass. New 8 actual public responses plus prior 12 replayed locally; not a deployed new-model test. Colloquial warning action and family-impersonation grade remain limitations. See docs/SIGNAL_CONTEXT_VALIDATION_20261120.md.


## 2026-11-20 KST · Zoro audit and optional link evidence candidate

Base 7f48096bbfca03e4d5ac1b16f112920771c68e6c. Local review candidate only.
The two-question home retains the original typed choices. The UI reports grade/action conflicts and rounded near ties, distinguishes busy/unavailable, and offers a separate /link-review screen. /arena serves the detailed session interface. Explicit self-reports gate high-impact follow-up guidance.
Read-only evidence options: operator-supplied, time-bounded PhishTank CSV for exact URL matching, or an explicitly shared hostname via the official ScamAdviser cache with a server key. Structured evidence can be passed to an optional local shadow choice. No case adjudication or authority follows from the result.
Python top-level suites: 417 passed, 2 skipped of 419. Node: 137 passed of 137. Saved model output replay: 48 case/profile pairs; 11-question guidance matched allowed labels in 18/24 under current policy, with 1/7 required pauses missed and 5/12 unnecessary benign holds. No independent human labels. This is not a score for the two-question home.
Actual provider credentials, actual Zoro checkpoint/head, hardware inference, production deployment, and pixel verification: not established. Chromium launch stopped by process socket permission. Rollback: reverse this isolated patch; no DB migration. Reproduce: python -m tools.zoro.replay_locked_audit; python -m unittest discover -s tests_v56; node --test tests*/test_*.js.


2026-11-20 KST | Integrated audit candidate from 7f48096 with main 695afc8 (PR #29). Two typed questions now use four internal review perspectives. Existing response keys, choice IDs, context reconciliation and score provenance retained. Separate optional link observations and explicit follow-up self-reports. Requirements, counterexamples, settings and rollback: docs/SIGNAL_REVIEW_PERSPECTIVES_KO.md. Live checkpoint effect, comprehension and provider quality unmeasured.
Local integration verification: Python 424 passed, 2 skipped / 426; Node 138/138; exact controlled response equality 240/240 vs 695afc8 (4 grades x 20 actions x 3 contexts). License inventory 608. Local model not configured; new live inference and real provider lookup not verified.


## 2026-11-20 KST · 성능검증과 실시간 선택 점수
551건 저장 결과를 메인 성능검증에서 조회할 수 있다. 원본 링크와 브라우저 내 파일 지문 비교를 제공한다. 기존 신호등 결과 카드에 실제 조로 응답의 네 색 점수와 최종 등급을 표시한다. 로컬 실제 모델 브라우저 확인, Python·Node·라이선스 검증 결과는 docs/SIGNAL_BENCHMARK_UI_20261120.md에 기록했다.


2026-11-20 KST | Signal prompt comparison on 1af8d50. Server-selected baseline, short and verify profiles, identical two-question output contract. New paired local evaluator checks pinned valid/test CSVs and authored counterexamples; validation-only score threshold is offline. Local Python 431/431 across default and supplemental runs, Node 143/143, 2538 controlled HTTP calls. Baseline is still the default. Real candidate inference NOT_RUN (no configured model here). Reproduction and rollback: docs/SIGNAL_PAIRED_EVALUATION_KO.md.


## 2026-11-20 KST · 로컬 조로 551건 재측정
성능검증에서 고정 CSV 551건을 다시 실행해 피싱 탐지율과 정확도를 갱신한다. 로컬 Arena 실행 옵션, 집계 기준, 실측 결과는 docs/SIGNAL_BENCHMARK_UI_20261120.md에 기록했다. 운영용 투영에는 평가 CLI가 포함되지 않으므로 CLI 시험은 전체 소스 CI의 tests_v59에서 실행한다.


## 2026-11-20 KST · 결과 카드 원문 강조
`요청한 행동`과 기존 `조로 선택 점수` 사이에서 `확인이 필요한 부분`을 표시한다. 결과가 현재 입력과 일치하고 `/api/signal`에서 확인 구절 위치를 반환했을 때 원문 한 구절을 강조한다. 로컬 Zoro 구절 단독 점수는 표시 후보 선택에만 사용한다. 구절 표시 정확도의 독립 검증은 `NOT_RUN`이다. 되돌릴 경우 관련 커밋을 되돌리면 된다. DB 마이그레이션은 없다.


## 2026-11-20 KST · 신호등 고감도 교차 확인

`/api/signal`과 `/api/signal/benchmark`의 기본으로 `high-recall`을 선택한다. 기존 문맥 보정 뒤 초록·회색에서만 고위험 행동과 빨강·주황 합을 확인한다. 정상 탐지율은 정상 라벨 중 경보가 없는 초록·회색의 비율로 표시한다. 앞선 고정 CSV의 실제 조로 실행과 집계 기준은 [성능검증 기록](docs/SIGNAL_BENCHMARK_UI_20261120.md)에 있다. 이전 질문을 비교할 때는 `--signal-profile baseline`으로 실행한다. 변경을 되돌릴 때는 해당 커밋을 되돌린다.


## 2026-11-20 KST · README 현행화

`main` `d283fad` 기준으로 첫 화면의 신호등·원문 강조, 상세 Arena 및 551건 재측정 흐름을 정리했다. 기존 질문·고감도 질문·교차 확인의 탐지율과 정상 경보의 변화를 [README](README.md)에 반영했다. 로컬 모델 설정과 CSV 재현 절차를 담았다.


## 2026-11-20 KST · 평가 데이터와 라이선스 안내

고려대학교 Autonomous AI Lab 평가 CSV의 고정 리비전, 라벨 분포, SHA-256과 확인 가능한 이용 조건을 README에 적었다. 피싱 탐지율과 전체 이진 정확도의 계산 범위를 설명했다. 프로젝트 원저작물, Zoro-1 가중치, 외부 데이터의 적용 조건은 [외부 자료 고지](THIRD_PARTY_NOTICES.md)에서 확인한다.


## 2026-11-20 KST · README에 연구모형 표시

README의 연구모형에 PPT용 수정본과 동일한 SVG를 표시한다. 신호등의 두 모델 응답, 교차 확인, 결과 표시 및 551건 피싱 탐지율을 담았다.


## 2026-11-20 KST · 문자 신호등 아래 회계 확인 절차

기존 `/api/signal` 응답에 회계 절차 필드를 선택적으로 추가했다. FIN-01은 승인 계좌 대조, FIN-02는 변경 지급 보류와 기존 연락처 확인 및 별도 승인 절차다. 브라우저에서 두 결과의 제목, 단계, 가상 계좌 표시를 실제 로컬 조로로 확인했다. 기존 판단의 결과 필드는 합성 대조 6건에서 변경 전과 일치했다.


## 2026-11-20 KST · PointerHead 검색 구상 기록

README에 Zoro-1 한 요청으로 신호등, 공개 사례, 사내 대응 매뉴얼을 함께 조회하는 구조를 추가했다. 로컬 합성 한 건에서 신호등 빨강·사례 AT01·절차 FIN-02에 해당하는 모델 응답을 확인했다. 세 질문 묶음은 확장 아이디어로 표기했다.


## 2026-11-20 KST · 트랙 1 실행 로그 새로 기록

소스 62c0acf에서 A·B·C를 실제 로컬 Zoro로 실행했다. B에서 송금 위험과 이전 확인 업무를 보존하고 FIN-02를 별도로 확인했다. C에서 실험용 연결을 닫았다가 복구하면서 실제 응답과 기술 재시도 해결을 확인했다. [실행 로그](docs/execution-logs/2026-11-20/README.md)

## 2026-11-20 KST · 연결 복구와 이전 요청 확인 상태 표시

Arena 결과가 같은 문장 분석의 복구를 알리고 이전 요청 확인 대기를 함께 표시한다. 장애 중에는 재시도 방법과 이전 요청 실행 보류를 안내한다. 실제 로컬 Zoro와 브라우저로 시나리오 C를 다시 검증했다. [브라우저와 서버 기록](docs/execution-logs/2026-11-20/C_transport_failure_recovery_ui.json)

## 2026-11-20 KST · 제출용 시나리오 C 로그 정리

제출용 목록에서 C는 브라우저 재실행 기록을 가리킨다. 이전 C JSON은 main에서 제거했다.

## 2026-11-20 KST · 업무 자료 검토 행동 선택지 수정

기존 행동 ID `check_content_or_link`의 설명에 확인 대상이 분명한 회의 자료와 검토 후 수정 의견 요청을 추가했다. 회의 자료 예시에서 같은 신호등 선택 점수로 ‘자료 확인’과 초록을 받았다. 확인용 15건의 현행 사이트 응답과 수정본 로컬 응답을 대조했다. [사례별 실행 기록](docs/SIGNAL_MATERIAL_REVIEW_20261120.json)

## 2026-11-20 KST · README 공개 시연 안내

README 제목 아래에 공개 시연 링크를 배치하고 신호등·원문 강조·회계 절차 조회를 설명했다. PointerHead가 피해 사례와 매뉴얼 ID를 고르는 구조는 현재 시연 기능과 로컬 실험 범위를 함께 적었다. 로컬 실행 방법은 환경변수와 터미널 출력 주소로 안내한다.
