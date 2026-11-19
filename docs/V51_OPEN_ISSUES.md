# v5.1 미해결 문제와 후속 게이트

기준일: 2026-11-04. 개선 방향을 보인 것과 문제가 사라진 것은 다르다. final24 이후 현재 결정 코드를 점수에 맞춰 재조정하지 않는다.

| ID | 현재 근거/잔여 문제 | 다음 완료 조건 |
|---|---|---|
| P0-PAUSE-MISS | 개발 최종 필수중단 누락3/39, 잠금AI24에서는2/7 | 실패 원인을 후속 개발로 분리. 정책 변경 후 새 잠금셋에서 확인. ASK도 필수중단 성공으로 세지 않음 |
| P0-OVER-ASK | 개발 불필요 정상 ASK21/64, 잠금AI24에서5/12 | 허용된 ASK와 불필요 ASK를 나누고 현재 요구·부정/인용·맥락부족 경계를 함께 검증 |
| P0-FALSE-PAUSE | 신규 개발36의 정상 false PAUSE1건이 기준선·후보 모두 존재 | 기존 PAUSE 보존 경계로 해결하지 못한 오류. 회귀를 막는 별도 프로토콜 없이 자동 해제하지 않음 |
| P0-FINAL-PIPELINE | 로컬 현재 턴 처리 일치 확인 완료; 세션은 별도 상태 검증으로 보호 | PASS — 비빈157개×2조건=314개 raw에 대해 Python/JS 정책 및 전체 처리 객체628개 일치. user-review/LinkGuard 경로의 action/reason 변경0. 세션 위험은 별도 UI 경로로 확인; 현재 턴과 세션 분모 분리 |
| P0-LOCKED-GATES | 잠금24 및 전체 자료의 신규 회귀 게이트 확인 완료; 잔여 오류는 별도 미해결 | PASS — 잠금24를 포함한158개 기준선/후보 쌍에서 기존 허용 안내 손실·새 위험/맥락부족 NO_STRONG_SIGNAL·새 정상 PAUSE·새 필수중단 누락 모두0; 판단 변경이면 새 잠금셋 필요 |
| P0-INDEPENDENT | AI36/24는 인간 독립 평가 아님 | 진명·호성 독립 작성/주석, 이견 해결, 최종 실행 동결 뒤 독립 검증. 현재 NOT_RUN |
| P1-EVIDENCE | 의미 구간·Unicode/경고 범위 수정과 표시율 집계 완료. 낮은 coverage·과도한 포함과 독립 의미 평가가 미해결 | PARTIAL — 비빈157문장 중48문장에52구간 표시; offset/quote52/52 일치와 표시 전후 정책/원본 앵커157/157 보존. 표시 coverage와 과도한 포함 문제가 남으며 인간 의미 평가는 NOT_RUN; 전부 숨겨 오류0을 만드는 방식은 통과 아님 |
| P1-RUNTIME | 실제 브라우저·코드·자산 검사 집계 완료. FULL/독립 추출은 외부 영수증으로 확인 | 실제 Typed 브라우저8요청 성공. 정상 NSS·OTP PAUSE와 근거, 아레나 현재NSS/세션ASK, 자기보고·종료·새로고침·재개 뒤 위험/작업 보존 확인. 일반 Node 브라우저 연결 실패 후 CUA 경로로 확인; 경고문 ASK 잔여, Python 181건 중179 PASS·선택적 개발 replay2 SKIP, Node UI/desktop/session59 PASS·근거18 PASS. 원본 Python core26개 hash 동일. 최종 로그: internal/evidence/v51/consolidated_checks/summary.json, PWA/APK/desktop 자산32 PASS, APK 독립 구조·v2 서명·변조검출 PASS(실기기 NOT_RUN). FULL/독립추출 검증 영수증은 배포 ZIP 옆 [Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json](<../../Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json>) 참고 |
| P1-DEVICE | Android 정적 검사와 실기기 실행은 별도. iOS도 미실행 | 설치·입력·오프라인/모드·화면 검사. 현재 NOT_RUN |
| P1-TEAM | L2 본문/G7/기관 질문/L1 승인 항목 현행 유지 | 실제 구체 합의 기록이 생긴 항목만 갱신 |

semantic policy /3의 위험 정상처리 실패와 /4 수정 기록을 삭제하지 않는다. 원본 7문항 기준선과 과거 v5.0 후보의 HOLD는 역사 증거다. threshold0.70, T=1.52, 선택확률, 모델 인증, 도메인 보정의 의미를 합치지 않는다.

행사 GPU/API·외부 API 허용·제출 조건의 새 공식 확인은 이번 로컬 구현 범위에 포함하지 않는다. 추가 reasoning LLM 미들웨어가 필수라는 근거도 아직 없으며, 필요하면 잔여 실패를 대상으로 효익·지연·비용·회귀를 별도로 검증한다.

## P2 런타임 경계 관측

- 직접 `Arena()`를 생성하면 호환성 기준선 profile이 기본이다. 실제 서버 CLI는11문항 profile을 명시한다. 직접 생성 API의 기본값과 현재 서버 선택을 혼동하지 않는다.
- 브라우저 자체가 소스 진품성을 독립 인증하는 것은 아니다. 계약/자산 정합성은 생성기·배포 게이트에 의존한다.
- 비기본 직접 API에서 `source=SIMULATED_RESPONSE`를 넘기면 semantic mode 문자열이 상속될 수 있다. 활성 앱의 simulator는 별도 경로이며 확인된 현재 배포 경로 결함으로 확정하지 않는다.

위3개는 범위 관측이며 이번에 소스를 추가 수정하지 않았다. 정본: internal/evidence/v51/final_runtime_review.json. 사례별 실패 분석은 [V51_FAILURE_ANALYSIS](V51_FAILURE_ANALYSIS.md)를 따른다.

지연 게이트는 상주 로컬 GPU의 warm 요청 관측에 한정한다. 기준선/후보157회씩의 p50=145.3/275.9ms, p95=156.608/289.008ms이며 cache·순서가 통제된 인과 실험은 아니다. 모델 cold start·부하/동시성은 NOT_RUN이다. 앱 서버 재시작을 모델 cold start 성공으로 집계하지 않는다.
