# 의심계 v4.9 최종 업데이트·검증 보고서

2026-11-04 KST. 배포 범위는 로컬 프로토타입이며 상용 인증·대회 제출·수상 성능 검증 완료를 의미하지 않는다.

## 요청 사항별 결과

| 핵심 요청 | 실행 결과 | 판정 |
|---|---|---|
| 조로 로컬 달아서 돌리기 | 공식 공개 Zoro를 RTX 3060에 로드하고 v4.9 서버/proxy로 합성 문장 4개 실제 생성 | PASS: 공개 생성 경로 |
| 문제점 찾기 | 종료 토큰·출력 형식·SQLite 연결·Windows 인코딩·문서 사본·오래된 화면 결과·서버 응답 계약 검토 | 발견·기록 |
| 최종 업데이트 | 기존 전체 소스 + v4.9 아레나 + PRD/프롬프트/스킬/실행 도구/증거 통합 | 로컬 배포 산출물 완성 |
| Zoro-1 Typed Decision | 실제 127.0.0.1:8008 요청 4개, 유효 응답 0개 | FAIL 연결 / 판단 헤드 추론 NOT_RUN |

원본: [v4.8 프로젝트](https://drive.google.com/drive/folders/1LPPM0Mng8u1VAdVGLHQ4Cz6INwa5SIto). 새 저장 위치: [사용자 지정 배포 폴더](https://drive.google.com/drive/folders/1CosYeNIQUJQLNuOYx5PzjGLsdj0hWfMY). 기존 자료는 덮어쓰거나 삭제하지 않는다. 실제 전송 완료는 별도 업로드 영수증과 재다운로드 해시 검증으로 확인한다.

## 1. 최신 기반과 버전

원본 Drive의 최신 배포명은 v4.8이다. 로컬 동기화 사본의 최초 복사 파일 230개는 원본 배포 manifest와 모두 일치했다. source_inventory.json은 이 변경 전 확인 기록이다. 의도적으로 수정한 문서·코드는 최종 MANIFEST_SHA256.json에 새 해시로 기록한다.

이번 v4.9는 이전 실험 키트의 파일명만 바꾼 것이 아니라 apps/dmsg/tools/models/evaluation/linkguard 등 원본 프로젝트 자산을 함께 통합한 전체 소스 배포다. 모델 실행에 필요한 9.68GB Zoro 가중치와 Python 환경은 별도이며 ZIP에 넣지 않는다. 내부 수신 자료·원시 개인정보·키·실험 DB도 배포에서 제외한다.

v4.9의 새 주 실행 경로는 arena다. apps/dist의 v4_8 APK/PWA 파일은 이름과 함께 보존된 **이전 배포물**이다. 이를 v4.9 APK로 바꾸어 표시하지 않았다. 새 Android 빌드·실기기 설치는 NOT_RUN이다.

## 2. 조로 실제 실행

실제 모델은 사용자가 제공한 **trillionlabs/Zoro**다. `Zoro-1` 판단 헤드를 가진 모델과 별개다. 생성 비교는 세션 정책·도구 권한·확률 입력으로 승격하지 않는다.

- 체크포인트 revision: e8b7dc33b6e30b01ba59c46364fced85342ff4ff.
- 가중치 크기: 9,680,472,424바이트.
- 가중치 SHA-256: fb015df41f21b290d0103a35a23859144b6add47686190fa4aa75be7ca9c24b1.
- RTX 3060 12GB / BF16 / torch 2.11.0+cu128 / transformers 5.22.1.
- eager attention, PyTorch reference kernels, greedy causal generation, cache 비활성. self-spec 가속 실험이 아님.
- 8010 생성 서버 → 8766 아레나 proxy → 실제 응답. current live_http.json에 요청별 기록.

| 합성 개발 예문 유형 | 실제 생성 레이블 | 모델 측 생성 시간 | 전체 HTTP 왕복 |
|---|---|---:|---:|
| warning | UNCLEAR | 281 ms | 6906 ms |
| direct | DIRECT_REQUEST | 219 ms | 266 ms |
| quoted | UNCLEAR | 219 ms | 266 ms |
| mixed | DIRECT_REQUEST | 219 ms | 265 ms |

모든 출력은 단일 레이블 계약을 충족했다. 의미 정확도 100%를 뜻하지 않는다. 경고문이 UNCLEAR인 한계는 그대로 남았다. quoted는 보고/인용을 표현할 선택지가 없는 3레이블 비교 조건에서 UNCLEAR를 반환했다. 새 독립 평가가 아닌 개발 회귀 예문이며, 이 4건으로 일반 성능·속도 향상률을 산출하지 않는다. 첫 요청의 전체 왕복에는 모델 생성 구간 외 초기화 비용 등이 포함되므로 생성 시간과 분리했다.

## 3. 문제 발견과 수정

| 문제 | 반영 | 검증·한계 |
|---|---|---|
| 생성 답에 역할/설명 이어짐 | checkpoint endoftext=248044와 tokenizer im_end=248046을 런타임 종료 목록에 함께 적용 | 이전 실제 전후 실행 보존. 원본 가중치/설정 파일은 수정하지 않음 |
| 첫 단어만 잘라 정답처럼 처리할 위험 | 출력 전체 exact-label 확인, 불일치 INVALID | 모의 확률/one-hot 분포 생성 없음 |
| Windows 콘솔 시작 오류 | 시작 메시지 ASCII 사용 | v4.9 서버 실제 기동 |
| SQLite 연결 미종료 | finally close로 연결 해제 | 저장·재개·충돌 테스트 |
| 확인 계획 기록으로 끝나는 흐름 | 작업 ID, OPEN/REPORTED_COMPLETE, 관측과 새 version, 재조회 | 실제 기관 확인이 아닌 로컬 상태 효과 |
| 입력 편집 후 이전 결과 표시 | 편집 시 비교/근거 폐기·재평가 안내, 추론 중 입력 잠금 | 스크립트 구문 확인. 별도 사용자 UX 시험 아님 |
| 잘못된 생성 서버 응답 | label 자료형·모드·해시 선언·유한 지연·중복 JSON 검증 | 오류 응답은 502/GENERATION_UNAVAILABLE로 구분, 관련 회귀 추가 |
| PRD 사본 불일치 | skill/product 문서 사본 동기화 | 실패를 확인한 후 325개 회귀 재실행 PASS |
| 정상 경고 의미 판단·높은 보류 | 미해결로 공개, 기본 정책에 생성 비교 적용 금지 | Zoro-1 실험과 별도 독립 평가 필요 |

## 4. 실제 검증 결과

- 신규·아레나·전송 경계 테스트: **42개 PASS** (`tests_v49.txt`). 모델 대역을 쓰는 테스트는 실제 모델 평가가 아니다.
- 기존 제품 회귀: **325개 PASS** (`source_tests.txt`). 문서 불일치 수정 후의 최종 실행이다.
- 실제 공개 Zoro 생성/proxy: **4개 응답**, 4개 형식 VALID (`live_http.json`).
- 실제 SQLite 확인 작업: 두 번의 판단 요청 후 version 2, UNRESOLVED 관측·작업 재조회 PASS. 이 경로의 Typed 모델은 미연결 상태로 명시한다.
- 실제 Typed endpoint 연결: **0/4 유효 응답** (`typed_attempt.json`), fixture 대체 없음.
- JavaScript 구문 검사 PASS. 새 플랫폼·상용 정확도·독립 사용자 실험 NOT_RUN.

예전 자료는 evidence/previous_v49_rc1/에 보존했다. 이번 실행과 합산하지 않는다. 공개 생성 모델 실행과 Typed 모델 실패를 한 성공 수치로 묶지 않는다.

## 5. 문서와 실행

- README.md / CURRENT_PROJECT_STATE.md / CHANGELOG.md.
- docs/PRD_v4_9.md / docs/SYSTEM_PROMPTING_v4_9.md.
- dmsg 고정 skill 이름 보존, references의 현재 사양과 CHANGELOG 갱신.
- run_arena.ps1 / run_local_zoro.ps1 / validate_v49.ps1 / tools/build_release_v49.py.

PRD·System Prompting은 요청→판단→정책→로컬 확인 작업→관측→재판단을 명시한다. 이전 7문항/0.70 정책은 보존하며 이를 최적화·도메인 보정된 문턱으로 주장하지 않는다. 사용자 확인 결과는 USER_REPORTED이며 과거 PAUSE를 자동 해제하지 않는다.

## 6. 남은 필수 작업

1. 승인된 Zoro-1 원본 가중치+jev_head.pt, kev export/runtime 확보 후 실제 7문항 검증. 공식 저장소의 접근 제한과 모델 차이를 임의 우회하지 않는다.
2. 정상 경고·무해한 요청·인용/혼합 절을 별도 개발/미열람 평가로 구분하고 실제 판단 헤드에서 보류 원인을 분해한다.
3. 실제 Typed 경로로 모델→작업→관측→재판단을 반복 재현한다. 현재는 생성 경로와 정책/작업 검증을 분리해 수행했다.
4. Android v4.9 빌드·기기 검증, 독립 정확도/오개입/보류/coverage 평가. 현재 성공으로 표시하지 않는다.

공식 모델 설명: [Zoro](https://huggingface.co/trillionlabs/Zoro), [Zoro-1](https://huggingface.co/trillionlabs/Zoro-1). 대상 해커톤·Trida 기획 자료는 원본 문서와 이전 검토 기록을 함께 보존했다. 제출·수상은 별도다.


## 추가 배포 검사

배포 스킬 quick_validate: PASS. Python/JavaScript conformance 24,488개 PASS. 이는 정책 구현 간 일치 검사이며 모델 정확도 표본 수가 아니다. 전체 ZIP CRC 및 개별 파일 SHA-256을 대조했다.
