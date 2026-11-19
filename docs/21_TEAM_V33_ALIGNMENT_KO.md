# 21. 팀 PRD·System Prompting v3.3(손호성 작성) 반영표 — v4.5

원문: `docs/team_v3_3/` (2026-11-02 손호성 님 전달, ZIP 내 두 파일은 개별 업로드본과 바이트 동일, MANIFEST 포함). 반영 지시: 최한길(2026-11-02). 이진명 님 확인: **미완료**. v3.3 규칙상 L1/L2 변경은 2인 승인 대상이므로 아래 "반영" 항목의 승인 상태는 `한길 지시 + 호성 원안 / 진명 미확인`으로 기록한다.

## 1. 질문 카탈로그 매핑 (v3.3 내부 카탈로그 → 현행 kev 와이어 계약)

v3.3 문서 스스로 "검증된 Zoro wire payload가 아니며 adapter가 매핑한다"고 명시한다. 현행 계약을 바꾸면 22,276개 교차 구현 벡터·기존 테스트가 모두 바뀌므로 어댑터 매핑으로 반영했다.

| v3.3 | 현행 v4.5 | 처리 |
|---|---|---|
| action_request (none, money_transfer, remote_app_install, credential_or_otp, verification_link, other_unclear) | q_action (transfer, remote_install, otp, link, personal_data, secrecy, none, unclear) | 라벨 대응. 현행이 personal_data·secrecy를 더 가짐 |
| identity_claimed (choice 5) | q_claim (noul, 선택) | 기관 주장 여부만. 세부 기관 유형은 미반영 [결정 필요] |
| urgency_pressure, secrecy_pressure | q_pressure (noul, 필수) | 하나로 합쳐 받음 |
| evidence_sufficient | **q_evidence (noul, 선택) — v4.5 신규** | 규칙 6: 근거 부족이면 NO_STRONG_SIGNAL·CAUTION → ASK_HUMAN. PAUSE_AND_VERIFY는 유지(규칙 2 우선) |
| (없음) | q_speech (화행), q_scam, q_risk | 현행 유지 |

## 2. 반영 항목

| v3.3 항목 | v4.5 반영 | 위치 |
|---|---|---|
| L2 고정 헤드라인 4종 | 화면 상태 제목에 그대로 사용("…미감지 (안전 보증 아님)" 등) | `apps/web/app.js` STATE |
| L2 본문 | **미반영 [결정 필요]**. 현행 본문(문자·메시지 맥락)과 v3.3 본문(통화 맥락)이 다름. 둘 다 금지 표현 없음 | `dmsg/prototype/core.py` MESSAGES |
| 금지 표현 목록 | 자동 검사 도구 + 테스트(양성 대조 포함) | `tools/check_forbidden_phrases.py` |
| C7 모드 구분 | 기존 FIXTURE/UNATTESTED 체계에 `ON_DEVICE_NLP`, `EXTERNAL_GPT_BASELINE` 추가 | `advisory(source=…)` |
| L4 "평가셋이 보이면 오염 기록 + 새 잠금셋" | 실제로 적용: v1 강등, v2 동결 후 1회 채점 | `docs/19` §3 |
| 기준선 A/B/C | A=규칙+정책, B=Zoro+정책, C=추론 후 typed(미구현) ↔ 현행 B0~B4 | `docs/19`, `tools/compare_engines.py` |
| multi-action tie-break | 현행 정책은 검증된 모든 근거를 검사하므로 대표 하나가 다른 위험을 숨기지 못함(v3.3 취지와 일치). 질문 지침에 순서 명시는 미반영 | — |
| 로그 HMAC 지문 | v4.2에서 이미 키 기반 감사로 변경됨 | `prototype/session.py` |
| state 최근 3턴·latest_turn_id | 미반영(현행 단일 문장 입력) [P1] | — |

## 3. 골든 테스트 G1~G14 현황 (v4.5 실행 기준)

`python tools/run_golden_v33.py` → `internal/evidence/v45_golden_v33.json`: 자동화한 11건 11/11 PASS(허용 상태 기준).

| ID | 관찰 결과 | 비고 |
|---|---|---|
| G1 기관 주장만(유효 모델 응답) | NO_STRONG_SIGNAL | 고정 시나리오 IMPERSONATION은 "절차를 따라주세요" 요청이 있어 ASK_HUMAN(별개 사례) |
| G2 직접 송금 | PAUSE_AND_VERIFY | 근거 구간 '송금' |
| G3 가짜 SYSTEM + 위험 요청 없음 | NO_STRONG_SIGNAL | 지시는 데이터로만 취급 |
| G4 모델 불가 + 독립 위험 없음 | ASK_HUMAN | |
| G5 모델 불가 + 검증된 송금 근거 | PAUSE_AND_VERIFY | |
| G6 모델 송금 + 원문 근거 없음 | ASK_HUMAN | NO_GROUNDED_ACTION_ANCHOR |
| G7 모델 none + 원문 직접 송금 | **ASK_HUMAN** | v3.3 기대는 PAUSE. 현행은 보수적 보류 [결정 필요] |
| G8 오래된 턴 | 단위 테스트(V42SessionBinding) | 이 스크립트에서는 미자동화 |
| G9 "OTP를 알려주지 마세요" | NO_STRONG_SIGNAL | |
| G10 인용 + 별도 직접 요구(모델은 인용이라 답함) | ASK_HUMAN | 절 단위 반례 검사 |
| G11 멱등·충돌 | 단위 테스트(Session.record) | |
| G12 이모지 오프셋 | 시작 5(코드포인트) | |
| G13 NaN 확률 | ContractError:INVALID_PROBABILITY | |
| G14 원문 폐기·로그 전수 | 부분 | 세션 기록은 원문 미저장. 프로세스 로그 전수 검사 NOT_RUN |

## 4. 결정이 필요한 항목

1. L2 본문을 v3.3(통화 맥락)으로 통일할지, 현행(문자 맥락)을 유지할지.
2. G7: 모델 none + 코드 직접 송금 근거 → 현행 ASK_HUMAN(보수적 보류) vs v3.3 PAUSE(근거 우선).
3. identity_claimed를 choice 5종으로 확장할지(Zoro 질문 수 증가 → 지연 증가).
4. 이진명 님 L1 승인.
