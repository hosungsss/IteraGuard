# IteraGuard / 의심계 v5.0 개발 후보

2026-11-04. **실행·상태관리·배포 기반 수정은 검증했고, 조로의 핵심 판단 성능 개선은 아직 완료하지 못했다.** 정상 과보류와 일부 필수중단 누락이 남아 있다. 이 폴더는 사용자 지정 버전 모음에 정리한 현행 v5 소스다.

먼저 [현재 상태](CURRENT_PROJECT_STATE.md), [전체 이해 문서](all.md), [미해결 과제](docs/V50_OPEN_ISSUES.md), [문서 안내](docs/00_DOCUMENT_MAP.md)를 읽는다. 상세 변경 이력은 [VERSION_LEDGER](internal/VERSION_LEDGER.md)에만 기록한다. 기존 보고서와 로그는 해당 시점의 증거로 보존한다.

이번 폴더 정리는 문서와 배치만 변경했다. 최초 검증 v5의 실행 코드·질문·정책·모델·APK/PWA를 변경하거나 추가 성능 개선을 주장하지 않는다. 같은 버전의 이전 작업본은 workspace에 보존돼 있다.

## 실행

Python 3.12 이상과 Node.js가 필요하다. 승인된 Zoro-1 Typed 서버는 별도 환경에서 실행한다. 모델 가중치·토큰·GPU 런타임은 배포물에 포함하지 않는다.

```bash
DMSG_MODEL_ENABLED=1 DMSG_SYSTEMONE_ENDPOINT=http://127.0.0.1:8008/v1/systemone DMSG_MODEL_ID=trillionlabs/Zoro-1 DMSG_SEND_MODEL_FIELD=1 DMSG_REQUIRE_MODEL_ECHO=1 python -m arena.server --port 8769
```

`http://127.0.0.1:8769`에서 합성 문장 → 현재 턴 판단 → 확인 작업 → 자기보고 관측 → 새 문장 재판단을 실행한다. endpoint 미설정/장애는 아레나에서 `MODEL_UNAVAILABLE`/`ASK_HUMAN`으로 표시하고, 공통 trace는 `MODEL_UNAVAILABLE_OR_INVALID`로 기록한다. 실행 manifest 자체가 잘못되면 HTTP 503 `EXECUTION_CONTRACT_UNAVAILABLE`을 반환한다. fixture로 대신하지 않는다. v5 제품의 Typed 전송은 loopback만 허용한다. 원격 relay는 제외한다.

PC 단일 문장 앱은 최신 자산을 빌드한 뒤 `bun apps/desktop/server.js --port=8770 --no-browser`로 연다. 동일한 `DMSG_*` 모델 환경 변수를 사용한다. 아레나의 SQLite 작업/세션 기능은 이 앱에 복제하지 않았다. APK/PWA의 기기 내 NLP는 별도 모델이며 실제 조로로 표시하지 않는다.

## 현재 실행 범위

- Python/JS가 같은 질문 순서·정책·실행 manifest와 공통 로컬 후처리를 사용한다. 기본은 기존 `legacy`, `dra`는 비교 후보이다. 이는 실행면 일치용 기준선이며 최적 정책 확정이 아니다.
- trace는 각 조건 충족과 실제 최종 적용 규칙을 구분하고, 현재 턴/과거 위험/작업 상태를 분리한다. 모델에 보내는 것은 현재 문장뿐이다.
- `OPEN ↔ CLOSED_UNRESOLVED` 종료/재개는 과거 위험을 해제하지 않는다. 사용자 확인 완료도 실제 기관 확인이나 안전 인증이 아니다.
- LinkGuard는 오프라인 후처리다. 저장 trace에는 입력 원문·인용·URL을 남기지 않으며 분포·offset·작업·관측 등 파생정보는 남는다.
- T=1.52는 로컬 제공자 실행 설정이다. 제품의 모델 인증은 false, 사기 도메인 확률 보정은 NOT_ESTABLISHED다.
- 실제 조로로 질문별 4조건×97개=388회 새 비교를 수행했다. 세 후보 모두 새 회귀가 있어 제품 질문은 원본 7문항을 유지한다. AI 초안 25개는 개발 데이터이며 사람 독립 평가가 아니다.

## 검증·빌드

```bash
python tools/validate_v50.py --report-dir ../v50_validation
python tools/build_distribution_v50.py
python tools/build_release_v50.py ../v50_delivery
python tools/verify_release.py ../v50_delivery/IteraGuard_DoubtMeter_v5_0_FULL_CANDIDATE.zip
```

현재 빌더는 `_v50.py`이다. `build_apps.py`, `_v49.py` 등 이전 진입점은 역사 보존용이다. `validate_v50.ps1`은 통합 검사의 PowerShell 래퍼다. 소스 검사, 실제 Typed 호출, APK 정적 검사, 실기기 실행, 독립 정확도는 별도로 기록한다.

새 배포 파일은 `apps/dist/IteraGuard_DoubtMeter_v5_0_web_pwa.zip`, `apps/dist/IteraGuard_DoubtMeter_v5_0_android_debug.apk`, 루트 `IteraGuard_DoubtMeter_v5.0.apk`이다. Android versionCode 50/versionName 5.0이며 디버그 서명이다. Android 실기기·iOS·데스크톱 크로스컴파일 실행은 NOT_RUN이다. APK는 오프라인 기능이며 PC의 조로 모델을 포함하지 않는다.

## 보존 범위

PAYLOCK, LinkGuard/APK 정적 분석, 도메인 텍스트 검토, 메모리/harness와 기존 테스트는 유지한다. 공개 `trillionlabs/Zoro` 생성 비교는 별도 모델/별도 화면이며 Typed 정책이나 지급 승인에 사용하지 않는다. CallShield/Factory/SRE는 별도 계보다. L2 본문·G7·기관 질문·L1 승인 등 구체 팀 결정은 기존 상태를 유지한다. 실연락·은행 제어·외부 평판 조회를 수행하지 않는다.
