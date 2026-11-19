# 의심계 — 실행·검증·시연 가이드

## 1. 실행 전제

- Python 3.11+; 현재 배포물은 표준 라이브러리만 사용한다.
- 현재 웹 시연은 `FIXTURE / SIMULATED`이며 실제 Zoro 모델을 호출하지 않는다.
- 로컬 입력 실험에서 임의 수동 텍스트는 실제 의미 주석이 없으므로 `ASK_HUMAN`으로 보류된다.
- 실사용 금융/통신/개인정보 시스템 연동은 허용되지 않는다.

## 2. 재현 명령

```bash
cd dmsg
python -m unittest discover -s tests -v
python scripts/validate_skill.py
python -m prototype.server
```

브라우저 `http://127.0.0.1:8765`로 접속하여 합성 시나리오를 선택한다. 정상·위험·모호·인용·부정·오류를 각각 평가하고, 독립 확인 **계획**을 기록한 다음 새로운 턴을 처리한다. HTTP API에는 `/api/start`, `/api/turn`, `/api/ack`, `/api/fixtures`가 있다.

## 3. Zoro-1 실모델 적합성 게이트

**현재 실모델 통합 시험: NOT_VERIFIED.** 운영자가 실제 지정 서버, 권한, 정확한 모델명/revision, API 스키마를 확인한 뒤 합성 텍스트에 한하여 `scripts/smoke_zoro.py`를 실행한다. 인가된 URL에만 요청을 보내며 API 키는 환경변수로 제공한다. 성공 후에도 반환된 JSON을 **독립 확인**하기 전에는 `REAL_ZORO`로 표시하지 않는다. 이 스크립트의 실행 기록은 모델 추론 성능의 일반화 증거가 아니다.

```bash
# 인가 받은 환경에서만 실행
python scripts/smoke_zoro.py \
  --url https://YOUR_AUTHORIZED_HOST/v1/systemone \
  --model-id EXACT_MODEL_ID \
  --revision EXACT_REVISION \
  --out ./local_smoke_result.json
```

비밀키, 실제 통화, 개인정보를 테스트에 제공하지 않는다. `local_smoke_result.json`은 모델 응답을 포함하므로 내부에서 검토 후 필요한 범위만 공유한다.

## 4. 시연 수용 게이트

| 게이트 | 통과 조건 |
|---|---|
| 재현성 | 동일 환경에서 unittest, 스킬 정적 검증, 14개 합성 fixture 재실행 |
| 안전성 | 모델 실패·임의 입력 시 안전 보증 없음, 외부 부작용 없음 |
| 화면 | 출처 모드·근거·비확실성·실행되지 않은 행동을 명확히 표시 |
| 증거 | 실제 모델 호출은 식별자와 캡처된 응답이 있어야 주장 가능 |
| 팀 운영 | 팀원 신청/역할/제출·발표 및 권리 공동 확인 |
| 데이터 | 외부 평가 수치를 표시한다면 표본·분할·단위·불확실성 포함 |

**제출 전 사람의 수동 점검:** 브라우저 레이아웃, 작은 화면, 글자 잘림, 탭 이동·포커스, 오류 및 느린 응답 상황, 비밀정보가 화면/로그에 남지 않는지 검수한다. 문서에 결과가 없으면 완료로 표기하지 않는다.

## 5. 데이터·정확도 관련 금지 주장

- '사기 탐지 정확도 99%', '실시간 전화 차단', '10분 계좌 동결', '100% 개인정보 보호', 'Zoro-1 검증 완료' 등 **현행 증거로 확인할 수 없는 표현**을 사용하지 않는다.
- 모델의 선택확률과 현실 범죄 발생확률을 동일시하지 않는다.
- 모의 확인 계획 기록을 실제 이용자 기관 확인의 완료로 표현하지 않는다.

## 6. 공식 문의가 필요한 쟁점

실제 지정 모델·endpoint 및 배포 방식, 팀원 개별 신청 여부, 사전개발 허용 범위, 외부 모델 및 API 권한, 하드웨어 제공 조건, 심사·시연 규정, 공동 IP와 라이선스. 주최 답변이 도착하면 원문·수신일·해석·제약을 별도 증거로 확인한다.

## 로컬 안전 실행/개발 점검

```bash
cd dmsg
python -m unittest discover -s tests -q
python scripts/evaluate_fixtures.py
python scripts/metamorphic_audit.py
python scripts/validate_skill.py
python -m prototype.server
```

`http://127.0.0.1:8765`를 사용한다. 서버는 127.0.0.1에만 바인딩하며 Origin/Fetch-Site/요청 프레이밍 경계를 확인한다. 이 보호 조치는 외부망 공개 허가가 아니며, 특히 세션 ID는 인증토큰을 대체하지 못한다. 모델 호출은 로컬 합성 시연과 분리되어 있다.


## PAYLOCK 합성 지급 요청 검토 화면

로컬 실행 후 `http://127.0.0.1:8765/paylock.html`을 연다. 등록 거래처·청구서 데이터를 이용해 6개 가상 지급 요청의 계좌·금액·발신 주소 주장 차이를 검사한다. `request_id`를 재사용하면서 본문을 바꾸면 상충 재시도로 거절한다. 다른 검토 담당자의 `CALLBACK_SIMULATED`는 확인 보고만 기록하며 실제 연락처 인증이나 은행 연동은 없다. 기본 모델 요청은 꺼져 있다. `python scripts/paylock_ablation.py`는 작성자 합성 6건의 참고 결과만 출력하며 실제 Zoro-1 성능이 아니다.
