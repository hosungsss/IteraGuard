# 의심계 상세 변경 원장

상세 변경 이력은 이 파일에 기록한다. README/CURRENT_PROJECT_STATE/MASTER_HANDOFF_PROMPT는 현행 사실, all.md는 전체 이해 문서다. 과거 문서의 수치와 승인을 현재 완료로 승격하지 않는다.

## 2026-11-04 · v5.0 개발 후보 구현 (기록 정정 포함)

### 사용자 의도와 현재 미달 범위

사용자의 핵심 목표는 조로가 플랫폼에서 정상 문장과 위험 요청을 적절히 판단하도록 개선하는 것이다. 실제로 완료한 범위는 실행 계약·상태관리·디버깅·개발 실험·패키징이다. 정상 과보류와 일부 필수중단 누락은 해결하지 못했다. 따라서 이 단계를 '핵심 판단 성능 개선 완료', '최종 완성', '우승 준비 완료'라고 기록하지 않는다. 이전 대화의 '끝났다'는 완료 범위 설명은 이 구분으로 정정한다.

### 구현·디버깅한 항목

1. Python/JS 공통 판단 계약과 질문·선택지 순서를 포함한 manifest를 추가했다. 앱과 아레나 기본을 legacy로 일치시키고 DRA는 비교 경로로 유지했다. 원본 7문항·0.70·DRA 비용표를 보존했다.
2. 조건 충족/적용 가능성/최종 규칙을 분리해 보류 원인을 추적한다. 사용자 검토와 오프라인 LinkGuard 후처리를 공통화했다.
3. 아레나의 현재 턴·세션 과거 위험·사용자 보고를 분리했다. OPEN↔CLOSED_UNRESOLVED 종료·재개와 DB 마이그레이션을 추가하고, 보고 완료 뒤 같은 과제가 반복 생성되는 현상을 완화했다. 위험 자동 해제는 구현하지 않았다.
4. 단문 앱은 이전 문장의 위험을 결합하지 않는 도구임을 입력/결과/기록에 표시했다. 한글 긴 입력 body 제한, 비동기 요청 설정 결합, 배포 도구의 import 경로 충돌을 수정했다. v5 원격 relay는 제외하고 loopback만 허용한다.
5. PWA/APK/스킬/FULL을 현재 소스로 만들고 검증했다. 화면의 과거 버전/생성모델 설명을 현재 Typed 범위와 맞췄다.

### 실험과 검증

- 실제 질문 비교388회: 원본/action만/speech만/evidence만 ×97개. 세 후보 모두 비교 정책에서 새 회귀가 있어 HOLD. 성능 개선을 채택한 결과가 아니다.
- 새 AI 개발25개: 정상12·위험10·맥락부족3. 인간 독립 평가가 아니다. 기존 데이터/주석을 임의 교체하지 않았다.
- 실제 재시작3회(초기 포함4프로세스), Typed4호출. 브라우저7요청 중6유효·1모델 이름 설정 오류 거부. 총 실제399요청/수용398. 설정 오류는 모델명 전송/echo 확인 명령을 고쳐 해결했다.
- 최초 배포본 별도 추출 검사: v5 42/42, v49 64/64. dmsg325, Python/JS24,488, NLP221/221, 고정49/49, APK 독립 구조/서명/자산 검사 통과. 구현 일치와 독립 정확도는 다르다.
- 독립 사람 평가·Android 실기기·iOS·최적 정책/확률 보정은 미완료. L2본문/GOLDEN-V33-G7/기관질문/L1 구체 승인 상태는 현행 유지다.

### 근거와 산출물

- docs/V50_IMPLEMENTATION_REPORT.md, docs/V50_TRACEABILITY.json: 33요구·12충돌·8결정·13게이트를 보존한 보고/추적.
- internal/evidence/v50/question_ablation/: 원실험 프로토콜·raw·입력·실행 당시 runner.
- internal/evidence/v50/: source/APK/browser/restart 검증 요약. 최초 FULL SHA-256: b2ab13478290502fac9e088c17f159fc7ad2902d5ab2507edecf4acc03eb73ae.

## 2026-11-04 · 지정 버전 모음 폴더 정리

사용자 지정 폴더에 `[v5.0] IteraGuard_DoubtMeter`를 기존 버전 형식으로 추가했다. 최초 검증 FULL465파일을 바이트 검증 후 펼쳤다. 기존 버전·루트 스킬 사본·Package·Back Data 원본은 수정하지 않는다.

- 기존 Markdown360개/서로 다른 내용159개를 인벤토리화하고 구버전·최근버전·보조자료로 나눠 검토했다. 파일 확인은 구버전 소프트웨어 실행 재검증을 뜻하지 않는다.
- v4.9 펼친 폴더는 FULL의 MD30개가 빠지고 루트 사본2개가 더 있다. v5는 이 불완전한 펼친 트리를 복제하지 않고 검증 FULL을 사용했다. v4.9 FULL의 MD69경로가 v5에 모두 존재함을 확인했다.
- 상세 변경은 이 원장으로 모으고, 현행 README/STATE/HANDOFF/CHANGELOG/all 진입점은 현재 범위와 남은 일 중심으로 정리했다. 정리 전 v5 문서 및 v4.7 원장/v4.9 changelog는 internal/history에 원문 보존했다.
- docs/00_DOCUMENT_MAP.md와 docs/V50_OPEN_ISSUES.md를 추가해 최신 명세·과거 참고·미완료 과제를 구분했다. 모델·코드·질문·임계값·기존 APK/PWA는 이번 정리에서 바꾸지 않았다. 새 모델 호출0이다.
- 문서가 달라졌으므로 소스 manifest와 스킬/FULL 패키지를 다시 만들었다. APK/PWA 재빌드는 하지 않는다. 기존 b2ab 배포 근거는 보존하며 새 패키지 SHA는 모음 루트 LATEST_VERSION.json 및 외부 정리 영수증에서 확인한다.
- FULL ZIP은 버전 폴더 바깥의 모음 루트에 배치한다. 소스 manifest에 FULL 자체가 순환 포함되는 것을 막기 위한 배치다. Package의 실험 키트 v1.x와 제품 v5.0을 합치지 않는다.

## 과거 원장 연결

v3.1.0~v4.7 상세 원문은 history/VERSION_LEDGER_through_v47_original.md, v4.8→v4.9 기록은 history/CHANGELOG_v49_original.md에 있다. 보관 원문 출처/hash는 history/PROVENANCE.json이다. v4.9 내부에 없었던 상세 원장이나 누락된 구버전 문서를 추정해 채우지 않는다.

## 2026-11-04 · v5.1 의미 계약·근거 표시·실행 결합 개발

검증된 정리 v5.0 FULL(6f13ae0…99d2)을 기준으로 별도 `[v5.1] IteraGuard_DoubtMeter`를 만들었다. 기존 v5.0 원본·실험·배포물은 보존한다. 목표는 정상 과보류와 필수중단 누락을 함께 줄이고 근거 표시의 의미 품질을 개선하는 것이다. 최종 채택 판정은 로컬 개발·잠금 AI 게이트를 통과한 v5.1 개발 후보. 인간 독립·실기기 평가는 미완료이며 인간 독립·실기기 검증 완료를 뜻하지 않는다.

### 구현과 실패 수정

- 원본7/evidence7/semantic10/specific11문항 profile과 요청 binding을 추가했다. Python/JS가 요청 전에 질문 순서·profile·policy·지문을 고정한다. DRA는 원본 기준선과의 비교로 분리하며 기존 계약/임계값을 소급 변경하지 않는다.
- 현재 요청 범위·민감 노출·송금 이상·요청 구체성 문항과 원문 단서를 조합하는 의미 확장 정책을 구현했다. semantic policy /3은 V13 위험 NO_STRONG_SIGNAL 회귀로 HOLD했다. /4는 명시적 other_request scope와 간접 주소/페이지 이동 차단을 요구해 수정했다. 임계값 변경은 없었다.
- 근거 표시를 정책/원래 앵커에서 분리했다. 어미 단독·경고/인용 범위 오표시를 줄이는 계층과 Unicode 대응을 구현했다. 예시 제목 뒤 절에서 범위를 성급히 해제하던 문제, Python/JS 공백·casefold 차이, trace 우선순위 표시를 수정했다.
- 아레나·단문 앱·desktop Typed에 profile binding을 연결했다. 기존 세션 위험·종료/재개·자기보고·중복/버전 보호를 유지한다. 기기 내 NLP는 별도 기준선 경로다.
- v51 배포 도구에서 실제 release_selection을 메타에 반영하고, 비웹 계약 소스 변경도 읽기 전용으로 검증한다. 임시 APK 서명키가 소스에 생성되지 않도록 메모리 서명으로 바꿨다. v50 stamped 배포물은 보존한다.

### 실험·잔여 문제

stage1 원본/evidence194회, stage2 semantic97회, stage3 raw replay0회, stage4 새 개발36×2=72회, stage5 specified133회, stage6 /4 raw replay0회로 실제496호출을 수행했다. 단계별 실패·채택 사유는 V51_IMPLEMENTATION_REPORT와 동결 프로토콜/metrics에 있다.

개발134개 보조 합산은 기대 안내64→107, 불필요 정상 ASK42→21/정상64, 필수중단 누락25→3/필수39다. 정상 false PAUSE는 기준선·후보 모두1이다. 최종 개발 누락 V15/V18/V50-AI-21과 정상 false PAUSE V51-F03_THEATRE_RESERVATION_FEE-01을 해결한 것으로 기록하지 않는다. 넓은 기존48 rubric과 반복 AI 개발 자료의 합산을 일반 정확도로 홍보하지 않는다.

정책 /4·11문항 profile 동결 뒤 잠금 AI24에 기준선/후보 총48회 호출한 집계를 집계로 확인했다. 기대 안내7→17/24, 불필요 정상 ASK11→5/정상12, 필수중단 누락6→2/필수7. 위험/맥락부족 정상처리와 정상 PAUSE는 양쪽0. no-lost-allowed PASS — 잠금24를 포함한158개 기준선/후보 쌍에서 기존 허용 안내 손실·새 위험/맥락부족 NO_STRONG_SIGNAL·새 정상 PAUSE·새 필수중단 누락 모두0, 전체 경로 PASS — 비빈157개×2조건=314개 raw에 대해 Python/JS 정책 및 전체 처리 객체628개 일치. user-review/LinkGuard 경로의 action/reason 변경0. 세션 위험은 별도 UI 경로로 확인. 결과 뒤 판단 코드를 튜닝하지 않는다.

최종 코드/브라우저/배포 검증: Python 181건 중179 PASS·선택적 개발 replay2 SKIP, Node UI/desktop/session59 PASS·근거18 PASS. 원본 Python core26개 hash 동일. 최종 로그: internal/evidence/v51/consolidated_checks/summary.json / 실제 Typed 브라우저8요청 성공. 정상 NSS·OTP PAUSE와 근거, 아레나 현재NSS/세션ASK, 자기보고·종료·새로고침·재개 뒤 위험/작업 보존 확인. 일반 Node 브라우저 연결 실패 후 CUA 경로로 확인; 경고문 ASK 잔여 / PWA/APK/desktop 자산32 PASS 및 APK 독립 구조·서명·변조검출 PASS. FULL/독립추출은 배포 ZIP 옆 Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json 참고. 근거 의미 품질·coverage: PARTIAL — 비빈157문장 중48문장에52구간 표시; offset/quote52/52 일치와 표시 전후 정책/원본 앵커157/157 보존. 표시 coverage와 과도한 포함 문제가 남으며 인간 의미 평가는 NOT_RUN. 인간 독립 평가, Android 실기기/iOS는 NOT_RUN. 모델 인증false, 도메인 보정NOT_ESTABLISHED, L2/G7/기관 질문/L1 승인 전 현행 유지다.

### 문서와 계보

현행 진입점은 v51로 갱신하고 v50 PRD/시스템 지침/보고/실험은 당시 증거로 보존한다. 갱신 전 진입 문서와 출처/hash를 internal/history에 추가하며 원장의 기존 항목을 삭제하지 않는다. 상세 이력은 이 원장에 모으고 CHANGELOG는 링크 색인으로 유지한다. 새 FULL은 소스 밖에 두며 최종 검증 후에만 모음/상위 최신 포인터를 바꾼다. 최종 패키지 경로·해시: PWA/APK/desktop 자산32 PASS 및 APK 독립 구조·서명·변조검출 PASS. FULL/독립추출은 배포 ZIP 옆 Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json 참고.

잠금 뒤 manifest/profile binding 예외가 연결 종료로 이어지던 전송 경로를 정적503으로 수정하고 회귀검사했다. 판단 정책/계약 source 지문은 불변이며 잠금셋 결과에 맞춘 결정 튜닝은 하지 않았다. 기존 복사본의 debug 개인키 디렉터리는 새 FULL에서 제외했고 원래 v5.0은 보존했다. 독립 APK 검사에서 원본 바이트 불변·서명/변조검출/manifest/DEX/자산 일치를 확인했다. 최종 문서에는 source/PWA/APK/desktop, 개발/잠금 AI, 인간 독립, 실기기를 구분한다.

지연은 비빈157입력/조건의 warm GPU 관측으로 공개했다(원본 p50/p95 145.3/156.608ms, 11문항 후보275.9/289.008ms). cache 혼재·순서 비무작위로 인과 배율을 주장하지 않는다. 모델 cold start 및 부하/동시성은 NOT_RUN이며 앱 서버 재시작과 구분한다.

## 2026-11-10 · v5.2 experimental Decision Sandbox (NO CHANGE to active model/policy)

- Original uploaded v5.1 ZIP SHA-256 `b7aa499b2306203710e94bd77a367de922f1ac5e5b44aec112c5d2d39703bbb1` frozen; 876 original entries were preserved before adding files. Google Drive root and v5.1 folder inspected read-only at direct-child metadata level; prior versions were not forcibly merged.
- Added strict five-feature typed output extraction, logistic training on development-only data, family leakage guard, mathematical odds inverse with explicit independent-evidence disclaimer, reasoning threshold vs cost-derived p*, paired cluster bootstrap and fail-close tests. No provider model was invoked by this addition. Default v5.1 policy unchanged.
- Exploratory model fit: existing AI-authored synthetic development n=61, family n=37, 5-fold OOF logistic Brier 0.1120304591, raw q_scam diagnostic Brier 0.1102680449 (different probability semantics). No evidence of superior independent domain performance; no model promoted.
- Reconciled two v5.1 references omitted from `tests_data/release/skill_path_additions.json` and registered one v5.2 additive reference, preserving old baseline path/hash. v5.1 Unicode generator exact check on Python 3.13 Unicode 15.1 mismatches generated JS metadata originally created with 15.0: original artefact not silently regenerated.
- Historical v5.1 tests remain the source of truth for their own release criteria. Added v5.2 offline tests and separate distribution. Android real device, real Zoro-1 inference, NPU and independent human evaluation: NOT_RUN. Model attestation and production calibration: NOT_ESTABLISHED.
- `Decision_Agent_v3.1_표지포함.pdf` is intentionally excluded entirely; adopted only independently described methodological principles. No Google Drive writes. Rollback to untouched original ZIP; experimental module is opt-in only.

## 2026-11-12 v5.3 SOURCE_REVIEW_CANDIDATE
- 출발점: 로컬 v5.2. 원본 OneDrive 폴더와 첨부 MD 보존.
- 전략 MD v1.1: confidence/pmax 경쟁가설, 유효 확률 재배분, 독립 기여 비교, 그룹 정의, 제보 증상에 따른 우선순위 정정.
- app.js: 행동/화행 선택 확률 개별 표시, 단일 ‘확신’ 삭제, 보류 다음 단계 표시. Arena: 처리 완료 보류/이전 위험 유지 안내.
- Windows 빌더 생성 파일 LF/UTF-8/비삭제 staging/캐시지문 수정. 판정 계약 지문은 48b0bbd05a51de8d2612186f7420090e0ab4330071f42abdb856b195838afdb7 그대로다.
- 정책 변경/추가 추론/실모델 호출/사람 독립 평가/사용자 사건 원인 확정 없음. 상세 검사 결과 docs/V53_VALIDATION_REPORT.md 및 internal/evidence/v53/.

## 2026-11-19 v5.4 REVIEW_FIX_LOCAL_VERIFIED
- Base: untouched full v5.3 ZIP; supplied review evidence preserved under internal/review_v53. Original F02 reproduced with supplied controlled responses before editing.
- arena/store.py: additive trigger_reason migration; create task for changed current ASK input/reason, retain inherited-risk and dedup safeguards; persisted reason-specific guidance; package manifest 5.4 with contract_version 5.1.
- configs/v51_semantic_rules.json: three narrowly scoped one-time-code synonyms; threshold unchanged 0.70; semantic data/contract and auxiliary app assets regenerated. Saved AI24 same-response replay: one action changed as expected, 23 unchanged. Development replay only.
- Arena primary launcher and current README/PRD/System Prompting/demo/all.md; old root docs retained under internal/history/v53_documents; skill references v5.4 with dmsg identifier retained.
- Local validation: 146 passed, 2 optional replay tests skipped; source asset build check passed. HTTP initially environment-blocked, then old version assertion updated, finally 4 passed. Windows test-only SQLite cleanup fixed.
- No /v1/decide adapter, model-temperature change, new live model inference, model identity attestation, independent human evaluation, visual browser/device verification or Drive upload. Rollback: original full v5.3 ZIP; use a separate DB/backup before switching versions.

## 2026-11-19 v5.6
Added priority task queue with dedup/capacity rollback, guarded digest, source-separated metrics, strict local evidence validator and queue UI. 160 tests passed, 2 optional skipped. Live attempts failed MODEL_NOT_CONFIGURED; no authenticated inference.


## 2026-11-19 · v5.8 GitHub source integration candidate (2026-11-19 feature branch)
Change request: CR-20261119-01. Prior main base SHA 880468eb45988edbda8745c124fe62c67f15bb91. Feature branch feature/v58-rulebook-governance.
Scope: additive rulebook/engine.py, JSON refund and bank-change profiles, rulebook CLI fixture preview, strict contract tests; v5.8 Arena sample chooser, evidence JSON download and task selection target preservation; agent instructions, evidence guide and CI. Existing v5.6 Arena backend and original v5.1 typed policies remain untouched.
R58-G-01: strict typed profile + finite probability/allowed choice check -> rulebook/engine.py -> tests_rulebook/test_engine.py -> GitHub CI evidence pending.
R58-G-02: no model-to-authority escalation, tenant-scoped proposal keys -> same files; idempotency persistence/executor intentionally NOT_IMPLEMENTED.
R58-G-03: domain reconfiguration -> rulebook/presets/refund_intake.json and account_change.json -> test_account_change_industry_switch; no claim of business-wide generalization.
R58-G-04: task selection, synthetic examples and evidence export -> arena/web/index.html/main.js/style.css -> node syntax check; browser/device test NOT_RUN at authored time.
R58-G-05: third-party AI continuity -> AGENTS.md, append-only VERSION_LEDGER and HANDOFF_CHANGELOG + CI guard. Entries are append-only; no deletion of prior documented failures.
R58-G-06: official evaluation evidence separation -> docs/V58_AGENT_EVIDENCE_GUIDE.md and README/CURRENT_PROJECT_STATE/LATEST_VERSION. Score 30/98 and true checkpoint identity remain NOT_MEASURED/NOT_VERIFIED.
Safety/limits: NO payments, emails, SMS, bank freezes, auto refunds, unseen user data processing, remote Drive, or automatic public deployment. New rulebook is not wired to Arena live; Zoro adapter integration deferred. Separate release ZIP/APK/skill rebuild NOT_DONE, so published package remains v5.6.
Rollback: revert this PR in GitHub; stop isolated rulebook preview; do not reset or delete the SQLite sessions. Preserve base commit and source SHA.
Verification status: GitHub commit/write is not a real runtime test. Check actions/CI + actual main merge SHA, and later an actual authorized Zoro API and browser check before claiming VERIFIED.


## 2026-11-19 · v5.8 follow-up: generic company JSON override
CR-20261119-02. Add custom --book-file to tools/rulebook_preview_v58.py so a business owner or future AI can adjust question profile and deterministic rules through a local versioned schema. Strict duplicate-key, nonfinite, suffix and size validation; no network/side effects.
Requirements R58-G-07 source edit: CLI arbitrary JSON parsing; test_cli local custom, duplicate keys and >64KiB rejection; new docs and input limitations.
Risk: rulebook still not connected to live Zoro service or independent business authorization; sample confidence remains uncalibrated. Scope does not add actual transaction APIs, NPU or performance promises. CI log must be checked against HEAD after PR; developer-authored correctness cannot substitute for user or business validation.
Rollback: revert PR on top of merged v5.8 base; no DB migration.


## 2026-11-19 · v5.8 follow-up: opt-in real transport wiring, no side-effect authority
CR-20261119-03. Previous isolated rulebook had no live Zoro adapter. Added rulebook/zoro_bridge.py to reuse operator-configured bridge.ModelClient with a dynamic bounded System One question profile. Real endpoint restricted by existing loopback check; response passed to independent strict rulebook policy; live flag and --synthetic-only are both required by CLI.
Acceptance/test: tests_rulebook/test_zoro_bridge.py exercises disabled/no call, typed request payload with test double, model failure, malformed response and invalid model latency. All such tests are fixture/test-double evidence only; real Zoro checkpoint/head and public API authentication remain NOT_VERIFIED. Core Arena still defaults to v5.6; question probability != fraud/outcome probability; no customer order/refund/SMS API is invoked.
Impact: new extensibility path and operator script, but not an automatic transaction system or production-ready multitenant service. Risk and rollback: disable environment flag or do not invoke module; no SQLite migration, no model checkpoint mutation; preserve prior ledgers.


## 2026-11-19 · v5.8 Rule Tweak Candidate 1 shadow-only integration candidate (append-only)
CR-20261119-04. User authorized source upgrade/merge/push following prior code audit. Root cause: v5.6 Candidate 1 installer based on 17e3bf5b is incompatible with present 7e43d6a main and contains an older Arena store implementation that would remove newer retry/task behavior. Existing v51 semantic policy already handles similar warning and quote contexts.
**Architectural decision:** import only isolated observational grammar and thresholds, NOT original installer, old arena/store.py, contract generator, generated manifest, or broad enforce behavior. Python Arena successful response gets an additive rule_tweak_shadow trace after current local layers. Default shadow; off available; enforce remains unavailable pending independent safety evaluation. Existing policy remains single authority.
**Req trace:** RT58-01 candidate provenance -> docs/V58_RULE_TWEAK_SHADOW_REVIEW.md; RT58-02 bounded-only proposals -> integration/rule_tweak_shadow.py -> tests_rule_tweak_shadow/test_shadow.py; RT58-03 protected state/task/old risk -> minimal arena/store.py hook + existing tests_v56/v54/v51; RT58-04 no silent downgrade -> refusal of enforce and unchanged action/reason/probs; RT58-05 safe failures -> redacted observation error, no exception payload, no new raw source; RT58-06 audit/read-back -> existing ledger/CI and SHA; RT58-07 static source compatibility -> no generated v51 contract drift.
**Potential risks:** shadow trace may marginally increase CPU/size; model proposals are correlated, not independent evidence; historical 10/12 to 12/12 is development replay, not novel accuracy; no actual Zoro invocation/independent humans/browser/NPU. M03 CAUTION could create extraneous OPEN task if enforcement were added, hence blocked.
**Validation:** execute new and existing CI on feature HEAD; do not claim passing until read-back. Release package/APK/PWA/dmsg binaries are NOT regenerated. Rollback by reverting PR or off mode + restart, keeping SQLite sessions. New independent locked evaluation is mandatory for any future enforce request. Detailed implementation and source fingerprint in docs/V58_RULE_TWEAK_SHADOW_REVIEW.md.

**CI remediation, same CR:** Initial expanded workflow failed due to YAML scalar folding; replaced with multiline run block. Python 3.11 exposed preexisting v51-semantic-data Unicode 15.0 generator version mismatch; set CI Python 3.12 (Unicode 15.0) rather than silently regenerating historical assets. The expanded Node minimal-DOM test exposed an older v5.8 main UI assumption that querySelectorAll always exists; synthetic example registration now treats the optional DOM API as absent in minimal harness, retaining full behavior in real browsers. These are CI/environment compatibility repairs, not evidence of live model quality. Rerun all checks on HEAD.


## 2026-11-19 · Arena 웹 합성 예시 문맥 보강

첫 입력과 예시 버튼에 거래처 계좌 변경, 보안팀 예방 공지, 방법이 빠진 확인 요청, 정산 진행 보고를 담았다. 같은 기록에서 확인 요청, 계좌 변경, 진행 보고를 차례대로 판단해 업무 보존을 시연할 수 있다.
브라우저 스크립트 회귀는 각 예시가 편집기 값을 채우고, 사용자가 판단을 눌렀을 때만 해당 문장이 평가로 전달되는지 확인한다.
별도 SQLite에서 실제 로컬 Zoro-1의 응답 4건을 받았다. 사전 기대와 일치한 확인 요청, 계좌 변경, 진행 보고는 같은 기록에서 두 확인 업무를 보존했다. 새 기록에서 평가한 예방 공지는 `MODEL_NONE_BUT_ACTION_TERMS_PRESENT` 이유로 사람 검토와 추가 업무를 만들었다. 이 결과는 시연에 쓰는 합성 예시에 대한 점검이다.


## 2026-11-19 pre-demo validation, uncommitted
Base 046feef; branch fix/pre-demo-validation. Added model configuration-only status, UI auth/busy/non-JSON/timeout errors, reset new-session source label, per-process inference slot, UTF-8 server re-exec. Policy fingerprints unchanged. Original UI new regressions: 1 pass/4 fail; modified selected suites total 168 pass/2 skipped including added timeout test. Actual model attempt MODEL_NOT_CONFIGURED. Hosted site PowerShell root 200/API401; Python403; authenticated flow/model identity/mobile NOT_RUN. No commit/push/deploy; temporary server stopped. Full report outputs/demo_fix_20261119/IteraGuard_Latest_Validation_and_Fixes.md outside source root. Rollback local changes only; no migration.


## 2026-11-19 bounded automatic recovery, uncommitted
User requested self-recovery during execution. Added browser transport recovery, max two retries, exact frozen request identity, stored-state reconciliation before inference resend, stop on auth/state/contract ambiguity. Existing policy and model status unchanged. UI reports recovery. Mock-network/minimal-DOM tests total 37 pass; live Zoro/hosted authenticated/mobile NOT_RUN. No commit/push/deploy. See docs/AUTO_RECOVERY_KO.md.


## 2026-11-19 PR publication authorized
User authorized commit/push and PR/Actions. Rebased recovery changes onto main 05103c7; preserved both append-only ledgers and contextual demo UI. Local Node 38 passed and runtime tests 2 passed after integration. GitHub Actions result must be checked on PR HEAD. Actual Zoro and hosted authenticated demo remain unverified. No main merge or site deployment included.


## 2026-11-19 · v5.9 source candidate: request-scoped contract verification + Arena UI redesign
CR-20261119-05. User request: review current main (046feef), raise real performance and operability, redesign the Arena UI (simple, premium, liquid glass, subtle 3D, visible decision process), then merge and push.
**Root cause (performance):** cProfile showed one Arena evaluate rebuilt and re-verified the full v51 question-profile registry 12 times (build_registry ~78% of request time). **Change:** integration/v51_profiles.verification_scope()/scope_cached()/refresh_scope() and v51.execution_manifest() cached per thread-local scope; arena/store.py verifies once before and once after the model call. Outside a scope every call still verifies from scratch. Measured (controlled responses, 10 fixture cases x 300, Python 3.12, same machine): evaluate p50 53.99 -> 19.59 ms, p95 70.43 -> 28.85 ms; pipeline_ms p50 42.33 -> 16.63 ms. Normalized results for 10 single-turn and 10 multi-turn sequences (60 objects) are byte-identical to 046feef (sha256 2162b9d7...e9fb).
**Contract identity:** source hashes of integration/v51.py and v51_profiles.py changed, therefore profile_registry_fingerprint and v51 manifest_fingerprint (7a6df762... -> 86e02915...) were regenerated with the repository exporters; all four exporter --check pass. Model-facing question contract unchanged (question_contract_sha256 63c2ff24..., questions_sha256, response schema).
**UI:** arena/web/index.html, style.css rewritten; new visual.js (read-only observer of main.js requests; derives pipeline stage text from real response fields; never writes payloads, decisions, localStorage or inputs); server route /visual.js; main.js only shortens displayed task ids. Session/evidence/contract controls moved to a side sheet; task panel only when open tasks exist. CSP unchanged. Real Chromium check desktop/mobile with REPLAYED FIXTURE responses (CONTROLLED_CLIENT): 0 console errors, no horizontal overflow.
**Tests:** new tests_v59 (15) added to CI; existing suites pass on Python 3.12; Node 24/24. Python 3.13 still shows the pre-existing v51 Unicode-version check difference (also at base).
**Not done / NOT_RUN:** real Zoro-1 inference, deployed chatgpt.site check (robots-blocked), Safari/Firefox, devices, NPU, independent evaluation. Decision policy intentionally unchanged (AGENTS: no tuning without a new locked set). APK/PWA/desktop assets not rebuilt.
**Rollback:** revert the PR; no SQLite migration. Details docs/V59_ARENA_UI_AND_PERFORMANCE.md.


2026-11-19: Resolve v5.9/main conflicts preserving UI, verification scopes, runtime diagnostics and bounded recovery. No main merge or deployment.


2026-11-19: Responsive UI local candidate on main 42fbb54. Separate runtime notices from grid; flexible columns/buttons; mobile title/input layout; hidden/reduced-motion canvas guard. Edge widths 320/390/768/900/1024/1440 pass; typing, clipboard, session/evidence/task flows pass with CONTROLLED_FIXTURE_NOT_ZORO. Python 15 and Node 38 pass. No commit, push or hosted deployment. See docs/V59_RESPONSIVE_UI_REVIEW.md.

2026-11-19: User authorized commit/push/public-site update. Publishing responsive branch for review and CI. Connected Sites owner/editor listings do not include the requested IteraGuard site; hosted deployment remains pending access. Existing GitHub workflow runs checks only.


## 2026-11-19 · CR-20261119-06 · evidence-informed text studio + Jev 1.14 Shadow + ambient 3D (append-only)
Base: GitHub main 4fbfd928197aa979bb472e94508ba6e801168d27. Scope: non-authoritative optional Jev 1.14 observer, zero-cost lexical check, evidence-source atlas and display-only 3D ambiance. User's uploaded v5.9 patch SHA-256 0a007143c0d54702676739a095a2442c1510c109bf70ee184b0ff26d93e2c238 and bundle SHA-256 097864c30fe6c0d08b51bfe3c7a05186989818c88fb9601248b827e8f09a4a2c matched SHA256SUMS.txt; incremental bundle needs unavailable prerequisite commit 05103c762395221b4473dcd94aede13d9f5829b9 for standalone verification. V5.9 UI/performance changes already in main and intentionally preserved.
EVID59-01 sources → docs/research/SCAM_EVIDENCE_ATLAS_2026_KO.md → tests_v59/test_evidence_atlas_and_ambient.py (15 public sources, 30 synthetic patterns, 12 negatives; not independently labeled).
EVID59-02 retained Zoro source/typed contract/task → original arena/store.py, integration/v51* untouched; existing CI v59/v56/v54/v51/Rulebook suite.
JEV59-03 optional TypeSafe Jev 1.14.0 exact pinned model and consent → arena/secondary.py, arena/server.py, arena/web/secondary.js, tests_secondary. No free TypeSafe/Vercel Jev route; per-token charges require explicit operator authorization, key, and per-request user consent. Offline lexical mode is not AI and cannot give a safety verdict. No real calls performed.
DES59-04 accessible design → arena/web/index.html + style.css + ambient3d.js + research.js and static/Node tests; preserve sticky top bar, fixed sheet/scrim, reduce motion, hidden-tab pause; preserve v5.9 existing coreCanvas and visual.js. No claim of verified visual design quality on real devices.
AUDIT59-05 append-only ledger, documented provenance, source hash and CI; final result to be read back after merge. No user data, APK, PWA, weights or dmsg packages altered.
Risks: sample selection/source publication biases, no actual ground-truth, no Zoro fine-tune or demonstrable accuracy change, model mismatch/incomplete network support, provider spending when explicitly enabled, GPU/performance/visual accessibility unmeasured. Rollback PR or cloud-off; sessions unmodified. Input is synthetic-only and declaration alone is not a privacy guarantee.

2026-11-19: User-requested footer copy change: replace both Arena footer paragraphs with IteraGuard. Update the existing markup test to retain contextual explanations without requiring deleted footer text. Model status and runtime behavior unchanged; hosted publication not verified.

2026-11-19: User requested removal of the footer IteraGuard label. Removed the footer element; header brand and page title remain unchanged. Hosted deployment remains unverified.

2026-11-19: Remove visible top runtime copy at user request. Keep hidden status hooks for existing scripts; no connection, retry, authentication or decision behavior changes. Hosted deployment remains unverified.

2026-11-19: User explicitly requested removal of the entire top bar, including logo, mode badge and session/history button. Remove header markup and guard optional sheet opener references to prevent startup errors. Session backend unchanged; header entry point removed. Hosted deployment not verified.

2026-11-19: Sphere connection label/glow follows recent VALID LOCAL_HTTP_MODEL_UNATTESTED responses with response hash. Fixtures never show connected; transport/model failure clears it; expires after 60 seconds. No health polling or checkpoint attestation; first real evaluation required. Reduced motion disables glow animation.

2026-11-19: Maintainer-authorized Apache-2.0 grant for original project work; preserve third-party/mixed terms via LICENSE_SCOPE, NOTICE, THIRD_PARTY_NOTICES, legal texts and asset sidecars. Historical binaries/model/data bytes unchanged. Static inventory check added; full rights clearance and legacy standalone-package compliance NOT_ASSERTED. See docs/licensing/REVIEW_20261119.md.


## 2026-11-19 · UX59 / REMED59 · consumer paste-first and rulebook historical audit (append-only)
Baseline main 2d6c715a16a556ce317a15b84cd1071c4b8280ad. User requested simple pasted text anti-scam workflow, transient progress and hiding internal cases/tasks/experimental Jev panels. Source report uploaded twice identically (sha256 0d31228e118c469318f7e9fce084051ab34b46ed75f1c917d802d906e98d1c5b) was written against 7283492 and is archived as historical untrusted-by-default analysis.
UX59-01 minimal input: blank textarea + synthetic-only/PII warning + manual action, missing input fails without evaluation call. Files arena/web/index.html and main.js, tests_consumer.
UX59-02 internal-only panels: taskPanel/reference-panel/secondary-lab and fixture sample controls hidden+inert, existing code retained for compatibility; no paid Jev activation or claim of background AI. User-facing unresolved risk notice retained. Files index.html, style.css, main.js; tests_consumer.
UX59-03 running progress: top dock hidden by default; on /api/evaluate request show true request/wait status, on actual HTTP response show source-aware response and hide; remove imaginary model steps/cumulative percent. Files visual.js/style.css/index; tests_consumer + existing UI contract. No real streamed server-stage events, unlike fabricated progress.
UX59-04 guided chat: hidden until accepted decision, read-only follow-up stays scenario-coded, raw follow-up text not sent; fixture and failed-model provenance retained. chat.js and tests_conversation/test_guided_chat_ui.js. Correct FTC source URL in arena/conversation.py; no policy authority change.
REMED59-05 include historical source file + audited contemporary review, characterization tests illustrating known RB-1/RB-2/RB-3/RB-4 unresolved behavior. A green test indicates current issue reproduced, NOT improved accuracy. Source refs docs/reviews and tests_remediation. Threshold changes, static conflict rejection, Zoro fine-tuning and all outcome-changing proposals deferred for independent locked labels.
Security/rollback: preserve arena/store.py, rulebook/engine.py, integration/v51* untouched, Zoro remains sole primary. Synthetic-only input label doesn't reliably anonymize personal information; real messages restricted. No monetary charges or external actions, no database migration. Revert PR to restore UI; retain append-only historical ledger.
Verification evidence: CI and main read-back after merge, not guessed; full browser screenshot/real Zoro/real Jev, labeled detection metrics NOT_RUN.

**CR-20261119-UX-REMEDIATION verification correction (append-only):** Earlier feature-branch/PR workflow runs failed and were retained in Actions history. Investigations: test_consumer first checked a visible non-guarantee warning absent from HTML → added explicit hero warning. Known-gap test required explicit operational hold decision in the review → added statement. v50/v53 UI tests tested blank initial fixture and prior risk/status wording → preserved the old user-safety guarantees verbatim and strengthened the internal fixture test to require nonempty sample while the consumer input starts empty. visual.js now does not color an unevaluated text edit as risk. Exact green PR head dca448488330ae35d347f83e5deaf26584a94b1d at Actions 44541447774. A new CI run after this historical append and post-merge main read-back is required. Characterization test PASS confirms that RB-1 through RB-4 known gaps remain, not their resolution.


2026-11-19 UI state separation: current-turn judgment, previous unresolved risk and next action have distinct display fields. Independent-analysis start preserves prior sessions/tasks; failed start preserves input/result. Consumer internal task-edit controls remain hidden. Python 234 pass/2 skipped; Node 68 pass; Edge 1440/390 controlled browser paths pass. No policy change, real Zoro or hosted deployment claim. See docs/UI_STATE_SEPARATION_VALIDATION.md.


## 2026-11-19 · Arena 문자 신호등 미리보기
기준 main 41461f98deee145200a9ac230ab553341d56a80d. /signal과 /api/signal을 추가했습니다. 모델 요청에는 현재 문자와 빨강·주황·초록·회색을 고르는 q_signal 한 문항이 들어갑니다. 기존 11문항과 세션 처리의 호출 경로를 유지합니다.
검증: 통제 HTTP 및 업무 테스트 17건, 실제 로컬 합성 호출 6건. 인용·신고 한 건은 빨강으로 분류됐습니다. 독립 정확도, 모델 신원 인증은 미검증입니다.


2026-11-19: Integrated origin/main 636f56b by fast-forward, preserving 9ed5dac UI state separation. No conflicts or runtime code edits required. Python 237 passed / 2 skipped, Node 68 passed, Edge 1440/390 controlled session flows passed, licensing 608-file inventory passed. Signal preview HTTP checks included; live model and hosted deployment NOT_RUN in this integration. See docs/MAIN_INTEGRATION_VALIDATION_20261119.md.

## 2026-11-19 · 메인 결과 내 조로 신호등
기준 main 636f56b. 메인 판단 버튼에서 기존 Arena 평가 뒤 단일 문항 신호등 요청을 실행합니다. 신호등·근거·다음 행동을 같은 결과 카드에서 볼 수 있습니다. 기존 판단 정책과 저장소 스키마는 그대로입니다.

## 2026-11-20 · 메인 결과를 신호등과 요청 행동으로 간소화
기준 main 20652f0. signal.html과 signal.js가 메인 폼을 담당합니다. 사용자가 준 q_action.json을 configs/zoro_action_choices.json으로 가져와 행동 후보 20개를 사용합니다. 정확한 원문과 q_action, q_signal만 로컬 Zoro 요청에 담고, 등급과 행동의 응답을 동일 카드에 표시합니다. 독립 정확도 평가는 미검증입니다.


2026-11-20: Signal-only bounded context reconciliation preserves original model scores/grade/action and reports corrections. Full recognized warning/report clauses distinguish past/negated requests; unknown or sensitive-action + green conflicts defer to gray. Existing Arena policy and shadow remain unchanged. Python 244 pass/2 skipped; Node 71 pass; controlled Edge 390/1440 pass. New 8 actual public responses plus prior 12 replayed locally; not a deployed new-model test. Colloquial warning action and family-impersonation grade remain limitations. See docs/SIGNAL_CONTEXT_VALIDATION_20261120.md.


## 2026-11-20 KST · Zoro audit and optional link evidence candidate

Base 7f48096bbfca03e4d5ac1b16f112920771c68e6c. Local review candidate only.
The two-question home retains the original typed choices. The UI reports grade/action conflicts and rounded near ties, distinguishes busy/unavailable, and offers a separate /link-review screen. /arena serves the detailed session interface. Explicit self-reports gate high-impact follow-up guidance.
Read-only evidence options: operator-supplied, time-bounded PhishTank CSV for exact URL matching, or an explicitly shared hostname via the official ScamAdviser cache with a server key. Structured evidence can be passed to an optional local shadow choice. No case adjudication or authority follows from the result.
Python top-level suites: 417 passed, 2 skipped of 419. Node: 137 passed of 137. Saved model output replay: 48 case/profile pairs; 11-question guidance matched allowed labels in 18/24 under current policy, with 1/7 required pauses missed and 5/12 unnecessary benign holds. No independent human labels. This is not a score for the two-question home.
Actual provider credentials, actual Zoro checkpoint/head, hardware inference, production deployment, and pixel verification: not established. Chromium launch stopped by process socket permission. Rollback: reverse this isolated patch; no DB migration. Reproduce: python -m tools.zoro.replay_locked_audit; python -m unittest discover -s tests_v56; node --test tests*/test_*.js.


2026-11-20 KST | Integrated audit candidate from 7f48096 with main 695afc8 (PR #29). Two typed questions now use four internal review perspectives. Existing response keys, choice IDs, context reconciliation and score provenance retained. Separate optional link observations and explicit follow-up self-reports. Requirements, counterexamples, settings and rollback: docs/SIGNAL_REVIEW_PERSPECTIVES_KO.md. Live checkpoint effect, comprehension and provider quality unmeasured.
Local integration verification: Python 424 passed, 2 skipped / 426; Node 138/138; exact controlled response equality 240/240 vs 695afc8 (4 grades x 20 actions x 3 contexts). License inventory 608. Local model not configured; new live inference and real provider lookup not verified.


## 2026-11-20 KST · 신호등 네 색 선택 점수와 성능검증
기준 main 0f2aeaa. 기존 조로 응답의 네 선택 점수를 막대와 퍼센트로 표시하고, 551건의 저장 성적과 원본 CSV 지문 검증을 추가했다. 모델·정책·계약 버전은 유지한다. 로컬 Python 424 통과·2 건너뜀, Node 143 통과. 로컬 브라우저에서 실제 모델 결과와 측정 표를 확인했다. 증거와 실행 범위는 docs/SIGNAL_BENCHMARK_UI_20261120.md에 있다.


2026-11-20 KST | Signal prompt comparison on 1af8d50. Server-selected baseline, short and verify profiles, identical two-question output contract. New paired local evaluator checks pinned valid/test CSVs and authored counterexamples; validation-only score threshold is offline. Local Python 431/431 across default and supplemental runs, Node 143/143, 2538 controlled HTTP calls. Baseline is still the default. Real candidate inference NOT_RUN (no configured model here). Reproduction and rollback: docs/SIGNAL_PAIRED_EVALUATION_KO.md.


## 2026-11-20 KST · 성능검증 재측정
- 기준 main a7b7ef5. Arena와 동일한 두 신호등 질문 및 맥락 보정으로 원본 CSV 551건을 실제 로컬 모델에 재평가했다. 성능검증 화면에 이진 정확도를 추가했다.
- 로컬 실행 옵션과 비동기 진행 조회를 추가했다. 원본 지문 불일치나 모델 실패로 중단되면 마지막 완료 결과를 표시한다. 공개 데모에는 집계와 출처가 표시된다.
- 모델·시간·정오 분포 및 회귀 검증은 docs/SIGNAL_BENCHMARK_UI_20261120.md에 기록했다.


## 2026-11-20 KST · 신호등 결과의 원문 확인 구절
- 기준 `main` `fd4184968591ff5aae0e6d34e682a9ae7b3b0464`. 결과 카드의 행동 라벨을 `요청한 행동`으로 바꾸고, 그 아래 네 색 점수 위에 `확인이 필요한 부분`을 추가한다.
- 표시할 후보는 원문에서 나눈 요청성 구절을 최대 8개까지 제한된 시간 안에 로컬 Zoro의 `q_signal`로 각각 평가해 빨강과 주황 모델 점수의 합으로 고른다. 확인된 예방 경고와 과거 보고는 표시 대상에서 제외한다. `confirmation_excerpt`가 있는 경우 원문 기준 유니코드 코드 포인트 시작·끝 위치 한 쌍만 내려준다.
- 보조 평가는 기존 신호등, 네 색 점수, 행동 선택, Arena 상태 및 저장 기록에 영향을 주지 않는다. 구절 선택 품질의 독립 평가는 `NOT_RUN`이다. 패키지, Arena, typed 계약 버전은 유지한다.


## 2026-11-20 KST · 신호등 고감도 기본값과 0.45 교차 확인

- 소스 기준 `299abf171d3338cbf87c6e62b08bf0fa414b6aba`. 메인 문자 신호등 및 로컬 재측정의 기본 프로필을 `high-recall`로 설정한다.
- 고감도 `q_signal`과 기존 `q_action`을 한 요청에서 평가한다. 문맥 보정 후 고위험 행동 10종과 소수점 넷째 자리까지 반올림한 빨강·주황 점수 합 0.45를 교차 확인해 초록·회색을 주황으로 올린다. 확인된 예방 경고·과거 보고는 건너뛴다.
- 고정 CSV 551건의 실제 로컬 Zoro 응답을 사용한 저장 집계를 표시한다. 피싱 탐지율 42/50, 정상 탐지율 425/501이며 정상 탐지율은 초록·회색을 센다. 버전과 측정 한계는 [성능검증 기록](../docs/SIGNAL_BENCHMARK_UI_20261120.md)에 있다.
- 기본 프로필로 Arena 재측정 API를 실행해 209.446초에 551건 집계를 그대로 재현했다. 전체 CI 대상 로컬 회귀는 Python 270건 통과·기존 2건 건너뜀, Node 95건 통과다.
