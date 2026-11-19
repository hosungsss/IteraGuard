# 25. LinkGuard — 링크·앱 파일 다층 검사와 보안 감사 (v4.7)

## 1. 범위와 원칙

| 단계 | v4.7 상태 | 실행 위치 | 외부 전송 |
|---|---|---|---|
| P2 LinkIntake (URL 추출·정규화·위험 구조) | 구현·검증 | 기기 안 (JS) / Python 정본 | 없음 |
| P3 평판 조회 (Safe Browsing·VirusTotal) | 어댑터 계약만 구현, 조회는 **NOT_RUN** | 서버 필요 | 동의 + 서버 키가 있을 때만 (현재 없음) |
| P4 격리 웹 분석 | **BLOCKED** (이 릴리스에 포함되지 않음) | — | — |
| P5 APK 정적 분석 | 구현·검증 | 기기 안 (JS) / Python 정본 | 없음 |
| P6·P7 정책·결합 | 구현·검증 | 기기 안 | 없음 |
| P1 Android 공유 입력 | APK에 `ACTION_SEND text/plain` 추가, **실기기 NOT_RUN** | 기기 안 | 없음 |

- 문자 읽기 권한(READ_SMS·RECEIVE_SMS)은 추가하지 않았다. Play 정책상 기본 SMS 앱이 아닌 앱은 이 권한을 쓰기 어렵다 [추론, 정책 원문 재확인 필요]. 공유 시트와 붙여넣기만으로 입력을 받는다.
- 링크는 열지 않는다. HTTP(S)가 아닌 스킴(`intent:`, `javascript:`, `tel:` 등)은 분류만 하고 실행하지 않는다.
- 쿼리 문자열과 프래그먼트는 외부로 나가는 주소(`external_url`)에서 지운다. 긴 불투명 경로 토큰과 민감 키(`token`, `otp`, `password` 등)의 값은 화면 표시에서도 가린다.
- **위협이 탐지되지 않았다는 것은 안전하다는 뜻이 아니다.** 초록색 체크 표시는 없고, 수행하지 않은 단계는 `미실행`·`차단`으로 표시한다.

## 2. 정책 상태

`KNOWN_MALICIOUS` > `SUSPICIOUS` > `SCAN_FAILED` > `INCONCLUSIVE` > `NOT_SCANNED` > `NO_KNOWN_THREAT_FOUND` 순으로 합친다.

- 메시지 안내와는 높이기만 하는 방향으로 결합한다. `KNOWN_MALICIOUS`면 잠시 멈춤, `SUSPICIOUS`면 최소 주의다.
- 링크 결과가 메시지 안내를 낮추는 경로는 코드에 없다(`downgraded: false`).
- 평판 조회를 하지 않은 일반 링크는 `NOT_SCANNED`(형식만 확인)로 표시한다. 오프라인 차단 목록이 로드됐고 아무 신호가 없을 때만 `NO_KNOWN_THREAT_FOUND`가 된다.

## 3. 외부 평판 서비스 조건 (2026-11-02 확인, 원문 재확인 권장)

- **Google Safe Browsing API**
  - 비상업 용도로 한정된다. 상업 용도는 Web Risk API를 써야 한다.
  - 경고 문구에는 단정하지 않는 표현과 "Advisory provided by Google" 표기가 필요하다.
  - 캐시된 판정은 유효 기간 안에서만 쓸 수 있다.
  - 보호가 완전하지 않다는 고지가 필요하다.
- **VirusTotal Public API**
  - 하루 500회, 분당 4회, 비상업 용도로 한정된다.
  - 파일을 기여하지 않는 업무 흐름에서는 쓸 수 없다.
  - 다중 계정을 금지한다.
- 따라서 v4.7은 조회 코드를 앱에 넣지 않았고, 키도 앱에 넣지 않았다. 서버에서 사용자의 동의를 받고, 토큰을 제거한 URL만 조회하는 구조를 설계로만 남긴다.

## 4. APK 정적 분석

자체 파서로 다음을 읽는다:
- ZIP 중앙 디렉터리: 경로 탈출, 중복 항목, 암호화 표시, 압축률
- 바이너리 XML 매니페스트: 권한, 외부 노출 구성요소, SMS 수신 필터, 디버그 여부
- APK 서명 블록 v2/v3: 인증서 SHA-256, CN, 유효기간. 서명의 암호학적 검증은 하지 않는다(`SIGNATURE_NOT_VERIFIED`).
- DEX 문자열·타입 표: 위험 API 표식, 코드 속 URL·IPv4, 난독화 비율
- 네이티브 라이브러리 목록과 내장 패키지

판정 원칙:
- 권한 하나만으로는 위험으로 보지 않는다. 'SMS + 접근성', '접근성 + 화면 위 그리기', 'SMS 수신 후킹 + 화면 제어' 같은 **조합**이 있을 때만 `SUSPICIOUS`다.
- 난독화는 `OBFUSCATION_LIKELY`로 표시만 한다.
- 실행 동작, 개발사 서버 코드, 네이티브 코드 내용, 내려받는 추가 코드는 확인하지 않는다(`not_checked`).

## 5. 검증 결과 (이 환경에서 실제 실행)

| 항목 | 결과 |
|---|---|
| LinkGuard Python↔JS 적합성 | `apps/conformance/run_linkguard.js` 7,639/7,639 (intake 1,467 · policy 5,868 · fuse 294 · punycode 10) |
| APK Python↔JS 일치 | 57/57 (말뭉치 9개 + 절단·바이트 변조 48개) |
| APK 독립 대조 (androguard 4.1.4) | 패키지·권한 5/5 일치 |
| 시나리오 매트릭스 (P9) | `internal/evidence/v47/v47_validation_matrix.md` — PASS / NOT_RUN / BLOCKED를 구분해 기록 |

말뭉치는 실행 코드가 없는 합성 고정 자료다. DEX에는 문자열 표만 있다. 정상 APK 표본은 우리가 직접 빌드한 디버그 APK 하나뿐이다. 실제 악성·정상 앱 집단에 대한 탐지율은 **측정하지 않았다.**

## 6. 보안 감사 메모

- 변조 입력 테스트에서 Python 파서가 `zlib.error`로 중단되는 결함을 찾아 `INFLATE_FAILED`로 처리하도록 고쳤다. JS 쪽도 같은 코드를 쓴다.
- Python `re.IGNORECASE`는 'ı'·'ſ'·켈빈 기호 같은 유니코드 글자도 영문자로 접는다. 그래서 JS와 URL 경계가 달랐다. 대소문자 무시를 ASCII 문자 클래스로 명시해 두 구현을 일치시켰다.
- 앱 CSP는 `script-src 'self'`, `connect-src 'self'`를 유지한다. LinkGuard는 네트워크 API를 호출하지 않는다.
- Android 셸에 추가된 메서드는 `getIntent`, `getStringExtra`, `String.getBytes`, `Base64.encodeToString`, `String.concat`이다. 네트워크·리플렉션·동적 로딩 타입은 금지 목록 검사(`tools/verify_apk.py`)를 통과해야 한다. 권한은 0개다.
- 공유된 원문은 `#share=` 프래그먼트로 로컬 페이지에 한 번 전달된다. 앱은 읽은 즉시 주소창에서 지운다. 원문은 세션 기록에 남지 않는다.
- 파일 선택기는 Spec-built APK(WebView 단독, WebChromeClient 없음)에서 동작하지 않는다(**BLOCKED**). 웹·PWA·데스크톱에서는 동작한다.
