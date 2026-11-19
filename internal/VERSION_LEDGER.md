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
