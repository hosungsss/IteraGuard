> v4.9 안내: 이 문서의 이전 사양은 보존된 v4.8 기록입니다. 현재 확장 명세는 PRD_v49.md 및 SYSTEM_PROMPTING_v49.md를 먼저 읽으십시오. 실제 생성과 Typed Decision을 구분합니다.

# Zoro-1 / Trida 실모델 계약 검증

## 1. 명칭과 검증의 경계

모델명 `Zoro-1`, 특정 `Trida` 체크포인트명, 서빙 엔드포인트는 독립 확인 전까지 동일한 구현으로 간주하지 않는다. 서버의 실제 배포 모델·revision·응답 스키마·호스팅 환경·추론 설정을 수집한다. 공개 자료에 제시된 calibration temperature 또는 처리 속도는 한국어 사기통화 성능 보증이나 본 시연의 실측값이 아니다.

## 2. 내부 요청

`prototype/typed_contract.py`의 `request_for_synthetic_state()`가 합성 텍스트와 `choice` / `noul` 형식의 typed 질문을 구성한다. 질문은 `request_action`과 `direct_instruction`이다. 이 객체는 앱의 내부 후보 계약이며 서버 공식 API와 일치한다고 가정하지 않는다.

## 3. 검증 게이트

1. 모델 체크포인트와 리비전, 라이선스, 접근 권한 확인.
2. 인가된 서빙 구현에서 `/v1/systemone` 노출 여부 확인. 일반적인 채팅 완성 API가 이 기능을 자동 제공하지는 않는다.
3. 합성 텍스트로 정확한 원문 요청/응답을 기록하되 인증키·개인정보는 기록하지 않는다.
4. `normalize_response()`의 키·enum·확률·합계 검사를 실제 스키마와 맞게 검토한다.
5. 독립 검토된 엔드포인트 증거 없이 `REAL_ZORO`를 활성화하지 않는다.
6. 모델이 제안한 문장 의미 라벨을 확인하기 위한 별도 검수 또는 보수적 정책을 마련한다.

## 4. 오류와 수치 해석

- 임의의 `logit` 가중치 조합은 surrogate 모형이지 실제 모델의 내부 추론 관측값이 아니다.
- `confidence`·`choice probability`는 실제 사기 발생률을 뜻하지 않는다.
- 누락/NaN/정규화 오류/타임아웃 시 허위 성공 대신 `ASK_HUMAN` 등 안전 보류를 제공한다.
- 실측 latency p50/p95는 각 모델 모드와 장비·표본 크기를 명시하여 별도 보고한다.

## 5. 실행환경 구분

| 모드 | 사용자에게 표시할 수 있는 사실 |
|---|---|
| `FIXTURE` | 합성 시나리오에 대한 주석 기반 로컬 정책 시연 |
| `SURROGATE` | 별도 명시된 모사 모델 결과이며 실제 Zoro 아님 |
| `REAL_ZORO` | 식별 가능한 실제 서버 추론과 모델/revision 증거 확보 시에만 사용 |

참고 소스: https://trida.trillionlabs.co/decision/ ; https://trida.trillionlabs.co/ . 문서의 표기와 사용 가능 계약은 실제 접속 시 다시 확인해야 한다.


## 현행 선택형 네트워크 연결

요청은 `prototype/model_bridge.py`의 `questions()`를 따르며, `ModelClient`는 운영자 구성의 HTTPS 또는 loopback 경로 `/v1/systemone`만 사용한다. 서버가 돌려준 `model` 문자열이 지정 모델 ID와 일치하는지 확인하지만 이것은 인증된 체크포인트에 대한 암호학적 확인이 아니다. `ModelClient.status()`의 `verified_model`은 항상 false다. 자유 발화는 실제 민감 원문을 넣지 않는 합성 실험에만 사용한다. 생성형 2단계 추론은 구현되어 있지 않으며 미검증이다.


## 현행 전송 보안 및 인증 상태

외부 HTTPS 연결은 사전에 확인한 공인 IP로 실제 TCP 연결을 고정하고 원래 호스트명으로 TLS SNI/인증서를 검사한다. 운영자 동의·호스트 허용목록이 없는 경우 원문을 외부로 전송하지 않는다. 단일 프로세스의 합성 모형 테스트는 실제 원격 서버, 네트워크 인증, 체크포인트 정본 또는 침투 테스트를 대체하지 않는다. 운영자 제공 서버가 `model` 이름을 응답하는 것과 모델 가중치의 실제 일치도는 구별한다.


## 공개 kev 형태와의 정합 (2026-11-01 확인)

공개 자료로 확인한 사실과 확인하지 못한 사실을 분리한다.

| 항목 | 공개 자료 | 현행 처리 |
|---|---|---|
| 경로 | `POST /v1/systemone`, 예시 서버 `localhost:8008` (HF 모델카드) | 경로 고정, loopback HTTP 또는 허용목록 HTTPS |
| 요청 | `state`, `questions{type, instructions, criteria}`; 점수형 `criteria`는 라벨 배열 | 같은 형태. `model` 필드는 기본 미전송 |
| 응답 | `answers[qid]`; `noul` 확률, `probabilities` 사전, `type` | 그대로 검증. `type` 불일치 거부 |
| 점수형 응답 키 | 공개되지 않음 | 라벨 키 또는 위치 인덱스 키만 허용, 형식 기록 |
| 응답 `model` 반향 | 공개되지 않음 | 있으면 일치 필요, 없으면 `ABSENT` 기록 |
| 보정 온도 | trida 페이지 2.19, HF 모델카드 1.52 (불일치) | 적용하지 않음 |
| 하드웨어 | 벤치마크는 서버당 H100 1장, BF16 safetensors | 현장 노트북 실행·지연 미측정 |

실제 서버에 붙이기 전 `scripts/smoke_zoro.py`로 응답 형태를 캡처하고, 위 표의 "공개되지 않음" 두 줄을 실측값으로 바꾼다. 캡처 결과가 어댑터와 다르면 어댑터를 고치기 전까지 모델 경로를 시연에 쓰지 않는다.
