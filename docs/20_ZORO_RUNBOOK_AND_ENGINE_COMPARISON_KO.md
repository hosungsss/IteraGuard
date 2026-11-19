# 20. Zoro 실추론 경로·엔진 비교 실행서 (v4.5)

기준일 2026-11-02 KST. 이 문서의 Zoro·GPT 경로는 **이 개발 환경에서 실행되지 않았다(NOT_RUN)**. 코드와 절차만 준비되어 있다.

## 1. 팀 제안에 대한 결정 (2026-11-02)

이진명 님 제안: Zoro를 메인으로, GPT API와 규칙 기반을 나란히 놓고 비교 시연.

| 항목 | 결정 | 이유 |
|---|---|---|
| Zoro 메인 | 채택 | Track 1 핵심은 공식 모델이 판단 경로에 기여한다는 재현 가능한 증거 |
| rule·NLP·Zoro·GPT 비교 | 채택(사전등록) | 같은 문장·같은 정책·엔진만 교체. 프로토콜 해시를 실행 전에 기록 |
| "Zoro 수치가 좋게 나오게" | 기각 | 결과를 정한 비교는 심사 질의 한 번에 무너진다. 나온 수치를 그대로 쓴다 |
| GPT API | 비교용 외부 기준선(선택) | 유료(0원 조건 충돌)·원문 외부 전송. 팀원 키·비용 승인·합성 문장만 |
| "GPT보다 빨라 금융사고 예방" | 지연만 측정해 주장 | 같은 장비·같은 문장 p50/p95. 사고 감소 인과는 측정 불가라 발표에서 제외 |

결과 구조:

```
T0 온디바이스 NLP (항상, 0원, 오프라인, ~0.3–0.8 s CPU)
   └─ T1 Zoro typed decision (Track 1, 로컬 GPU 또는 주최 측 endpoint)
        └─ T2 결정론적 정책 게이트 (Python 정본 = JS 이식본)
외부 기준선: GPT (제품 경로 아님)
```

공식 페이지(2026-11-02 재확인)는 Zoro API 제공·GPU 제공·외부 API 허용 여부를 밝히지 않았고 `hackathon@trillionlabs.co` 문의를 안내한다. "대회가 API를 제공할 것"은 가정이다.

## 2. 주최 측 문의 초안

> 제목: [Track 1] Zoro-1 사용 환경 문의 (팀 IteraGuard)
> 1) 본선에서 Zoro-1/Trida 추론 endpoint를 제공하나요? 제공한다면 요청 형식(예: /v1/systemone)과 호출 한도는요?
> 2) GPU 서버가 제공되나요, 아니면 참가자 노트북에서 실행해야 하나요?
> 3) 출품작 안에서 외부 상용 API(예: OpenAI)를 비교 기준선으로 호출해도 되나요?
> 4) 사전에 개발한 코드·모델 가중치를 가져와도 되나요?

## 3. 로컬 Zoro 실행 (VRAM 16 GB 노트북 기준)

체크포인트 BF16 약 9.31 GiB(공개 모델 카드 기준). 이 개발 환경(RAM 7 GB, Hugging Face 차단, 게이트 토큰 없음)에서는 불가.

1. Hugging Face에서 Trillion Labs 라이선스 동의 → 본인 토큰 발급(팀원 개인 계정, 저장소·ZIP에 넣지 않음).
2. kev/trida 서버 실행 → `http://127.0.0.1:8008/v1/systemone`.
3. 증거 수집(REAL_ZORO 표기 조건):
   - `huggingface-cli scan-cache` 출력 또는 체크포인트 파일 SHA-256, 사용한 revision(커밋 해시)
   - 서버 기동 로그(모델 경로·dtype·장치)
   - GPU 이름·드라이버(`nvidia-smi`)
   - 아래 비교 실행의 `v45_zoro_raw_responses.json`

## 4. 비교 실행

```bash
# 0원·오프라인 엔진 (항상 가능)
python tools/compare_engines.py --locked tools/nlp/locked_handwritten_v2.jsonl --out internal/evidence/v45_compare.json --engines rule,nlp

# Zoro 추가 (로컬 서버)
export DMSG_SYSTEMONE_ENDPOINT=http://127.0.0.1:8008/v1/systemone DMSG_MODEL_ENABLED=1 DMSG_MODEL_TIMEOUT_S=20
python tools/compare_engines.py --locked <잠금셋> --out internal/evidence/v45_compare_zoro.json --engines rule,nlp,zoro

# 주최 측 원격 endpoint라면 (운영자 허용 필수)
export DMSG_REMOTE_TEXT_CONSENT=1 DMSG_REMOTE_HOST_ALLOWLIST=<호스트> DMSG_MODEL_API_KEY=<주최 측 키>

# GPT 기준선 (유료, 팀 승인 후에만)
export OPENAI_API_KEY=<팀원 본인 키>
python tools/compare_engines.py --locked <잠금셋> --out internal/evidence/v45_compare_gpt.json --engines rule,nlp,zoro,gpt --allow-paid --gpt-model <모델 ID> --max-items 60
```

출력: 엔진별 기대 행동 일치·위험 개입 재현율·정상 불필요 개입·보류율(Wilson 95% 구간), 지연 p50/p95, 엔진 쌍별 정확 McNemar p. 지연 비교는 **같은 컴퓨터에서 같은 실행으로 잰 값만** 비교한다. GPT 결과는 확률이 없어 one-hot으로 기록된다(`EXTERNAL_PAID_BASELINE_ONEHOT_LABELS`).

현재 결과(rule vs NLP, v2 48문장): 0.688 vs 0.833, McNemar p=0.092. Zoro·GPT NOT_RUN.

## 5. 독립 잠금셋 만들기 (가장 싼 신뢰도 향상)

1. 손호성·이진명 님이 **서로 보지 않고** 각각 20~30문장 작성: 위험(직접·간접·인용·경고 혼합)과 정상을 반씩. 실제 문자 원문·실명·실계좌·실 URL 금지(합성).
2. 각 문장에 `expect`(허용 정책 상태 목록), `risky`, `speech`, `action` 기입. 형식은 `tools/nlp/locked_handwritten_v2.jsonl`과 동일.
3. 파일을 받은 즉시 해시 동결(`*.freeze.json`) → 어떤 엔진도 튜닝 전에 실행하지 않음 → `compare_engines.py` 1회.
4. 작성자 간 이견(같은 문장 기대 상태가 다름)은 평가 전에 기록하고 합의 규칙을 정한다.

## 6. 시연 대본 (사전등록 비교를 보여 주는 방법)

1. 같은 문장 3개(정상 안내·간접 송금 요구·경고문)를 rule → NLP → Zoro 순서로 실행.
2. 표는 "엔진만 바꿨다"를 보여 주는 동일 정책 행 + 잠금셋 표(n, 구간, p 포함).
3. Zoro가 이기지 못한 지표도 그대로 보여 주고, Zoro만 주는 것(옵션별 확률, 질문 독립 응답, `evidence_sufficient`)을 설명한다.
