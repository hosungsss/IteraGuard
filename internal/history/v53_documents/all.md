# IteraGuard v5.3 선택·정책·UI 진단 후보

2026-11-12. 기본 판단 계약 v5.1 유지. 소스/화면 설명 및 Windows 배포 도구 수정 후보다. 실제 Zoro 추론 0회, 사용자 원시 사건 미재현, 정책·질문·임계값 변경 없음.

먼저 docs/V53_VALIDATION_REPORT.md, docs/IteraGuard_Zoro_Jev_Strategy_Review_2026-11-12_v1.1.md를 읽는다. 변경 내역은 internal/VERSION_LEDGER.md에 있다. internal/evidence/v53/가 이번 실행 기록이다. v51/v52 기록은 과거 증거다.

## 실행
프로젝트 루트에서 `python -X utf8 tools/replay_choice_path_v53.py`와 `node tests_v53/test_choice_ui.js`로 오프라인 재현한다.
Arena는 `python -X utf8 -m arena.server --port 8769`로 시작한다. 실모델은 기존 운영자 설정과 검증된 endpoint가 별도로 필요하다. 미연결 시 실제 결과를 모의 결과로 숨겨 대체하지 않는다.
단문 데스크톱은 `bun apps/desktop/server.js --port=8770 --no-browser`. 번들 자산은 재생성했다.

## 버전 구분
외부 패키지 v5.3, 판단 엔진/생성 앱 내부 버전 5.1. 기존 모델/프로필 지문은 유지한다. Android는 디버그 빌드이고 실기기 미검증이다. 이 폴더 안의 구버전 skill/APK는 보존 자료다. 현재 스킬 별칭 dmsg.skill/dmsg.zip은 진단 안내를 포함한다. 새 MANIFEST_V53_SHA256.json만 현재 패키지 파일 무결성 기준이다. 이전 manifest는 해당 시점 기록이다.

# 선택·정책·UI 경로 검증 보고서

2026-11-12 / v5.3 SOURCE_REVIEW_CANDIDATE / 기본 판단 엔진 v5.1 유지

## 결론
실제 사용자 사건은 요청·응답이 없어 NOT_REPRODUCED이다. 모델 자체의 선택 결함을 확정하지 않았다. 확인된 문제는 단문 UI가 행동 확률 하나만 ‘확신’으로 표시하고 발화 유형 확률을 숨긴 점, Arena 보류 화면이 처리 완료와 다음 확인을 충분히 설명하지 못한 점이다. 수정은 표시 계층에 한정한다.

## 재현 결과
- 기존 v5.1 테스트 응답 10건을 현재 11문항 정책에 재생했다. 새 모델 추론/독립 정확도 평가가 아니다.
- 7문항 기준 정책의 통제 fixture: 행동 otp=0.75, 화행 direct_request=2/3 → ASK_HUMAN / MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS. 화행을 0.71로 바꾸고 잔여 확률을 재배분 → PAUSE_AND_VERIFY. 기본 11문항 후보의 일반 결과로 확대하지 않는다.
- SQLite Arena에 저장 응답을 주입: 위험 요청 PAUSE 후 정상 요청의 현재 턴 NSS, 세션 ASK / PRIOR_RISK_UNRESOLVED. 정상적인 과거 위험 유지 경로다.
- 실제 production UI JavaScript를 최소 DOM에서 실행했다. 새 회귀 요구 2건이 원본에서 실패, 수정본에서 통과했다. 기존 14건 포함 16건 통과. 실제 브라우저 시각 렌더링이나 사용자 실측으로 표현하지 않는다.
- 정책·모델·확률·threshold 변경 없음. 실패한 사용자의 실제 JSON이 확보돼야 사건 원인을 특정할 수 있다.

## 재현 방법
프로젝트 루트에서 `python -X utf8 tools/replay_choice_path_v53.py`, `node tests_v53/test_choice_ui.js` 실행. 원본 비교 시 DMSG_TEST_ROOT를 원본 v5.2 경로로 지정한다. 원본은 읽기만 한다. 자세한 출력은 internal/evidence/v53/ 에 있다.

## 증거 분리
LIVE_MODEL_CALLS=0; USER_INCIDENT=NOT_REPRODUCED; UI_MODE=NODE_VM_MINIMAL_DOM; ANDROID_DEVICE=NOT_RUN. 과거 evidence/v51, v52는 이번 실행 결과가 아니다.

## 반례와 추적
창작 질문(역사적 인용 아님): ‘선택을 했다는 사실과 실행 권한을 얻었다는 사실은 같은가?’ ‘보류의 이유를 숨기면 사용자는 무엇을 기다리는가?’ ‘더 높은 확률은 새로운 증거인가?’
전제 반례: Zoro가 otp를 선택해도 화행 게이트 또는 과거 미해결 위험 때문에 ASK가 될 수 있다. 따라서 무반응을 곧 Zoro 미선택으로 부르지 않는다.
PRD: 불확실한 경우 명시적 안내 → Prompt: 모델 제안과 실행 권한 분리 → Architecture: raw/정책/session/UI 분리 → Code: apps/web/app.js, arena/web/main.js → Tests: tests_v53/test_choice_ui.js, tools/replay_choice_path_v53.py.
구조는 선택/정책/UI, 시간은 현재 턴/과거 위험, 관점은 사용자/개발자, 역검증은 화면→reason→확률→요청을 따른다. 늦은 응답·재조회·입력 변경·사람 검토 경로는 기존 UI 회귀검사로 보호한다.

## 검사 집계 및 실행 제한
- v5.1 전체 75개: 73 PASS, 선택적 개발 응답 replay 2 SKIP. 초기 패키징 9오류는 Windows 생성 텍스트 줄바꿈 차이 수정 후 해소됐다.
- v5.2: 21 PASS. UI 16 PASS(기존14+신규2), 별도 세션 UI 6 PASS. 중복된 검사를 더해 독립 정확도처럼 표시하지 않는다.
- 배포 32자산 정합성 PASS: 원본 웹→PWA→APK→데스크톱 임베디드 자산 비교. APK 설치·서명 독립검사·실제 브라우저 화면 검증은 NOT_RUN.
- Windows 빌더: 생성 텍스트 LF 고정, 하위 Python UTF-8 지정, 재귀 삭제 대신 선언된 자산만 덮어쓰고 미등록 파일/심볼릭 링크 거부, 서비스워커 자체를 캐시 지문 계산에서 제외.
- 시스템 Python에는 cryptography가 없어 실제 APK 재생성에는 기존 번들 Python(cryptography 50.0.2)을 사용했다. 신규 의존성 다운로드 없음.
- 패키지 버전은 v5.3 소스 진단 후보다. 정책·앱 내부 계약과 Android versionName은 기존 5.1이다. 가중치·정책 성능 업그레이드 또는 Android 정식 릴리스로 주장하지 않는다. 이전 버전 파일은 보존 자료이며 현재 웹 배포는 apps/dist/web, Arena는 arena/web이다.
