# 의심계 v5.0 전체 이해 문서

기준일: 2026-11-04 KST. 팀 IteraGuard, 제품 의심계(Doubt Meter), 스킬 식별자는 dmsg다. 이 문서는 현재 제품의 전체 이해/NotebookLM 진입점이다. 상세 변경 이력은 [변경 원장](internal/VERSION_LEDGER.md)에서 확인한다.

## 현재 결론

**실행·상태관리·디버깅·개발 실험·배포 기반은 수정했지만, 조로의 핵심 판단 성능 개선은 미완료다.** 정상 문장 과보류와 일부 위험 요청의 필수중단 누락이 남는다. 버전 5라는 이름은 완성·정확도 인증·대회 최종 제출을 뜻하지 않는다.

## 주력 제품 흐름

합성 현재 문장 → 승인된 Zoro-1 Typed 응답 → 공통 정규화/정책/로컬 후처리 → 현재 턴 안내 → 확인 작업 → 사용자의 새 관측 보고 → 새 문장 재판단으로 이어진다. 모델은 현재 문장만 읽고 서버가 과거 위험을 유지한다. 공식 기관에 실제 연락하거나 송금/통화를 제어하지 않는다.

아레나는 SQLite로 세션·작업·관측을 보관한다. OPEN과 CLOSED_UNRESOLVED 사이에서 보관/재개해도 prior_pause를 지우지 않는다. 사용자가 확인했다고 보고한 것은 기관 인증이나 안전 해제가 아니다. 현재 문장이 NO_STRONG_SIGNAL이어도 과거 위험 때문에 세션은 ASK_HUMAN일 수 있으며, 두 상태를 구분해서 표시한다.

PC 단문 앱/PWA/Android는 현재 문장 분석 도구다. 단문 앱 기록에 이전 위험을 결합하지 않는다. 기기 내 NLP는 Zoro와 별도 모델이며 indicator도 NLP 전용이다. GPU Zoro는 앱에 내장되지 않는다. 아레나와 단문 앱의 기능 범위를 구분한다.

## 현재 계약과 의미

- 정책 행동은 NO_STRONG_SIGNAL / CAUTION / PAUSE_AND_VERIFY / ASK_HUMAN이다. NO_STRONG_SIGNAL은 안전 판정이 아니다.
- 원본 7문항과 선택지 순서를 유지한다. 기본 legacy의 0.70은 기존 데모 heuristic이며, 보정된 최적값이 아니다. DRA는 비교 후보다.
- 공통 실행 계약은 integration/v50.py와 apps/shared/v50-contract.js, 정본은 configs/v50_contract.json이다. 평가 후 사용자 검토/오프라인 LinkGuard를 한 번 적용한다.
- trace에서 충족 조건·적용 가능성·실제 규칙·최종 행동·세션 결합을 구분한다. 원문 없는 trace는 입력 재생 자료가 아니다.
- 실제 제공자 설정은 RTX 5080 BF16·T=1.52다. 제품의 model_attested=false, 도메인 보정 NOT_ESTABLISHED는 별도 상태다. 모델 이름 에코는 신원 인증이 아니다.
- 전송은 loopback 전용이다. 모델 미연결/응답 스키마 오류는 명시적으로 보류하며 fixture를 숨겨 대신하지 않는다. 실행 manifest 자체의 불량은 HTTP 503 EXECUTION_CONTRACT_UNAVAILABLE로 구분한다.
- DB에는 원문·인용·URL을 남기지 않지만 분포·offset·작업·사용자 보고 등 파생정보는 남는다. 합성 데이터 개발 범위를 유지한다.

## 실험 결과

기존 V2 48개(빈 문장 1개 추론 제외), 기존 AI 25개, 새 AI 25개 중 비어 있지 않은 97개를 원본/action만/speech만/evidence만의 네 조건으로 새 호출했다. 388/388 응답이 VALID이며, 세 변경 후보는 새 회귀 때문에 모두 HOLD했다. 새 25개는 정상 12개·위험 10개·맥락 부족 3개이고 AI 초안이므로 인간 독립 평가가 아니다. 원본 조건의 기존 72개 재호출은 이전 확률/정책 출력과 일치했다.

| 조건 | 신규 25개 legacy 기대 일치 | 신규 25개 DRA 기대 일치 | 제품 반영 |
|---|---:|---:|---|
| 원본 | 14/25 | 17/25 | 비교 기준 유지 |
| action만 | 14/25 | 16/25 | 미채택 |
| speech만 | 17/25 | 17/25 | 미채택 |
| evidence만 | 16/25 | 20/25 | 미채택 |

이는 개발 주석과의 기대 일치다. 일부 수치가 높아져도 다른 사례/정책에서 필수중단이 보류로 바뀌거나 과개입이 생겼다. 따라서 이 표로 성능 개선 완료를 주장하지 않는다. 실제 제공자 요청 399회는 질문 비교 388회+재시작 검사 4회+브라우저 7회이며, 설정 오류로 거부된 1회를 제외하면 398회 수용이다. mock/replay는 실제 추론 수에 합산하지 않는다.

## 구현 및 검증 범위

공통 실행 계약/trace, legacy 기준 일치, 미해결 종료·재개, 보고 완료 후 반복 과제 완화, 긴 한글 입력/요청 설정/모듈 경로 오류 수정, PWA/APK/스킬/FULL 정합성을 확인했다. 최초 배포본을 별도 추출한 검사에서는 v5 42개·v4.9 64개가 통과했다. dmsg 325개, Python/JS 일치 24,488개, NLP 일치 221개·고정 49개, 실제 서버 재시작 3회와 브라우저 경로를 검증했다. 검사 종류와 분모가 달라 단일 정확도로 합산하지 않는다.

APK는 독립 서명/구조/자산 검사만 했으며 Android 실기기는 NOT_RUN이다. 숫자별 근거는 [구현 보고서](docs/V50_IMPLEMENTATION_REPORT.md)와 internal/evidence/v50에 있다. 이번 폴더 정리에서 이 실행 검사를 다시 수행한 것은 아니다.

## 보존 기능과 별도 계보

PAYLOCK의 지급 검토 권한 경계, LinkGuard/APK 정적 분석, 사업/투자/가상자산 도메인 텍스트 검토, 메모리/harness는 보존한다. 실제 은행·외부 평판·격리 웹·기관 확인 권한을 부여한 것은 아니다. 공개 trillionlabs/Zoro 생성 비교는 Zoro-1 Typed와 별도이고 정책에 적용하지 않는다.

상위 Package의 실험 키트 v1.x, Trida 교재, iteraguard/의 별도 앱, CallShield/Factory/SRE 제안은 의심계 제품 v5의 구현 실적으로 합치지 않는다. 옛 문서에 적힌 Typed NOT_RUN은 당시 환경의 기록이다. 현재 Typed 실행 근거와 독립 평가 미완료를 함께 표시한다.

## 남은 일과 기록 원칙

우선 정상 과보류와 필수중단 누락을 줄일 schema/rubric 후보를 설계하고 검증해야 한다. 인간 독립 평가·실기기·세부 팀 합의는 별도로 미완료다. L2 본문/GOLDEN-V33-G7/기관 질문/L1은 현행을 유지한다. 자세한 과제와 완료 조건은 [미해결 목록](docs/V50_OPEN_ISSUES.md)에 있다. 별도 추론 LLM 미들웨어가 필수라는 근거는 아직 없다.

지정 폴더 정리는 문서만 갱신했다. 기존 버전과 최초 v5 FULL(b2ab…73ae)은 보존한다. 이 폴더가 이후 작업 기준이며, 문서 정리 후 manifest/스킬/FULL을 새로 만든다. 새 ZIP은 상위 폴더에 두고 검증 결과·해시는 상위 LATEST_VERSION.json과 정리 영수증에 기록한다. 이전 workspace에서 실행 중인 서버는 이번 정리로 재시작하지 않았으며 실행 코드는 동일하다.

## 읽는 순서

[README](README.md) → [현재 상태](CURRENT_PROJECT_STATE.md) → [미해결 목록](docs/V50_OPEN_ISSUES.md) → [PRD](docs/PRD_v50.md)·[시스템 지침](docs/SYSTEM_PROMPTING_v50.md) → [구현 보고서](docs/V50_IMPLEMENTATION_REPORT.md) → [추적표](docs/V50_TRACEABILITY.json) → [변경 원장](internal/VERSION_LEDGER.md).

전체 Markdown 분류는 [문서 안내](docs/00_DOCUMENT_MAP.md), 역사 원문 출처는 [보존 영수증](internal/history/PROVENANCE.json)에서 확인한다.
