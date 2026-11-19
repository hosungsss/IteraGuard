# 의심계 — 모델 권고 게이트 현행 계약

**제품:** IteraGuard / 의심계 · **버전:** v3.8 · **실행 상태:** 합성 고정 대본 + 운영자 선택형 외부 모델 연결 경로. 실제 Zoro-1 체크포인트 실행 여부 미검증.

## 목적 및 권한

비신뢰 발화로부터 모델 질문(Q_ACTION, Q_SPEECH, Q_SCAM, Q_CLAIM, Q_PRESSURE, Q_RISK)을 요청하고 응답을 스키마 검증한 뒤, 본문에서 관찰 가능한 행동 단서와 결합해 **비파괴적 사용자 안내**만 출력한다. 송금 차단·계좌 동결·실제 문자 전송·실전화 감청은 전혀 제공하지 않는다.

의사결정 분류는 `PAUSE_AND_VERIFY`, `CAUTION`, `NO_STRONG_SIGNAL`, `ASK_HUMAN` 네 가지뿐이다. NO_STRONG_SIGNAL은 안전 확인이 아니며, PAUSE_AND_VERIFY는 사기 범죄의 확정 판단도 금융 조치도 아니다.

## 데이터 출처 계층

1. FIXTURE: 사전 구성된 합성 원문과 작성자 주석. 독립 실제 모델 결과가 아님.
2. MODEL_RESPONSE_UNATTESTED: 운영자 설정 HTTP endpoint에서 반환된 JSON. 통신 성공·스키마 통과만으로 모델 진품/체크포인트/확률 보정이 증명되지 않는다.
3. MODEL_UNAVAILABLE_OR_INVALID: 연결 불가·계약 불일치·타임아웃·인증 실패. 반드시 ASK_HUMAN.

## Typed Decision 단일 요청

`prototype/model_bridge.py:questions()`가 6문항을 생성한다: q_action (8개 폐쇄 선택), q_speech (직접/인용/경고/불명확 4개), q_scam·q_claim·q_pressure(noul), q_risk(4단계 score). 정답 후보에 대한 확률 분포는 모델 출력이며 실세계 사기 발생률과 동일하지 않다. q_risk score 분포는 0..3 인덱스 키를 사용하며 점수는 소수일 수 있다.

## 정책 게이트

- 각 q_action, q_speech의 선택 옵션 확률이 0.70 이상이어야 하며, 이 값은 **임시 정책 휴리스틱**으로서 실증 보정되지 않았다.
- `none`/`unclear`와 직접 행동 요청 간 모순이나 높은 q_scam 응답 모순은 ASK_HUMAN.
- 위험 행동 분류에 해당하는 키워드가 정확하게 원문에 존재하지 않으면 ASK_HUMAN. 단순한 단어 위치 일치는 의미적 타당성을 보증하지 않으므로 `LEXICAL_ANCHOR_NOT_SEMANTIC_VERIFICATION`을 표기한다.
- 명백한 금지·경고·신고 단서가 존재하는데 모델이 직접 지시라고 답하면 ASK_HUMAN.
- 경고·부정은 NO_STRONG_SIGNAL(안전 보증 아님), 제삼자 인용·신고는 CAUTION, 직접 위험 행동 요청은 PAUSE_AND_VERIFY, 직접 링크·비밀 지시는 CAUTION.
- 모델 실행/형식 실패는 ASK_HUMAN. 실제 피해 예방 성능이 입증되었다는 문구를 사용하지 않는다.

## 기본 배포 환경

`DMSG_MODEL_ENABLED=1`과 `DMSG_SYSTEMONE_ENDPOINT`, `DMSG_MODEL_ID`를 운영자가 설정하기 전에는 외부 추론을 수행하지 않는다. 기본 `python -m prototype.server`는 127.0.0.1:8765에만 바인딩된다. 원격 HTTPS 및 로컬 loopback /v1/systemone 경로만 허용하며 리다이렉트는 비활성화한다. 실사용 고객 원문·OTP·전화번호 등 민감자료를 업로드하거나 기록하지 말 것.

모델 연결을 활성화하더라도 `verified_model=false`, `model_attested=false`, `calibration_status=NOT_ESTABLISHED`가 유지된다. 연결 성공·HTTP 200·ID 일치는 체크포인트 인증의 근거가 아니다.

## 실패·운영 메트릭

모델 응답 JSON 전체/자유 발화 원문은 서버 감사 로그에 남기지 않는다. 세션 이벤트 기록은 행동·이유 코드·발화 SHA-256·모델 미인증 여부를 담는다. 반환 확률은 UI 표시용으로만 사용한다. 임계값·성과는 독립 데이터에서 검증되어야 하며 지표에는 반드시 `n`과 산출 조건을 표시한다.

## 명시적인 미구현 사항

생성적 장문 추론 기반 2차 재판정, 실제 체크포인트 보증/인증, 확률 보정·리스크 보정, 실전화 텍스트화, 오프라인 모델 실행, 프로덕션 인증·접근제어, 원문 증거 의미의 독립 검수, 3개 호스트 스킬 실설치 테스트는 제공하지 않는다.
