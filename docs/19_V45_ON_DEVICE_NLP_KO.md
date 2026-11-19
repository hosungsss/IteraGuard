# 19. v4.5 온디바이스 한국어 의미 분석 (T0) — 설계·학습·평가·한계

기준일 2026-11-02 KST. 모든 수치는 이 문서의 명령으로 이 개발 환경(Linux x64, CPU 2코어, Node 22, Chromium headless)에서 실제로 실행한 결과다. 실기기(Android·iOS·Windows·macOS) 지연은 측정하지 않았다.

## 1. 무엇을 만들었나

| 구성 | 내용 | 근거 수준 |
|---|---|---|
| 인코더 | KoELECTRA-small-v3 판별기(임베딩 128→256, 12층, 4헤드, FF 1024), 행렬 가중치 int8 대칭 양자화(출력 열/어휘 행 단위 스케일), 14,654,232 바이트 | 가중치 출처: npm `kakaotalk-chat-analyzer-models@0.2.1`의 ONNX가 `monologg/koelectra-small-v3-discriminator`라고 **주장**. 원본 체크포인트와의 바이트 대조는 하지 않음(Hugging Face 접근 차단) |
| 화행 헤드 | [CLS; 평균] 512차원 표준화 + 0.5×문자 n-gram → 5클래스 다항 로지스틱 회귀, 온도 보정 | 학습·보정·평가 실행됨 |
| 행동 헤드 | 문자 1–3gram 해시(2,048) → 7클래스 로지스틱 회귀 | 어휘 기반. **깊은 의미 모델이 아님** |
| 근거 구간 | 행동 헤드의 어절 가림(occlusion) 기여도 최대 어절 | 설명 보조. 의미 증명 아님 |
| 정책 | 기존 `advisory()` + 절 단위 반례 검사, `source='ON_DEVICE_NLP'`, 임계값 0.5(보정 분할에서 선택) | Python·JS 교차 일치 검증 |
| 런타임 | 순수 JavaScript(`apps/shared/dmsg-nlp.js`), 가중치는 base64 JS 파일(파일 URL에서도 로드됨) | 네트워크·키 없음 |

ONNX Runtime Web을 쓰지 않은 이유: `file://`(Android WebView 자산)에서 동적 import가 CORS로 실패했다. 순수 JS 전방 계산은 ORT fp32 결과를 기준(oracle)으로 맞췄다.

## 2. 데이터

- 3i4k(warnikchow/3i4k, **CC BY-SA 4.0**): 명령·수사적 명령·서술 문장 각 최대 2,500개, 행동 라벨 `none`. 질문형("알려줘")은 라벨 체계 충돌로 제외.
- 작성자 합성 문장(`tools/nlp/make_dataset.py`): 송금·OTP·원격앱·개인정보·링크·비밀유지 × 직접/간접/경고/인용/서술 프레임. 프레임 계열(family) 단위로 학습/보정/잠금 분할, 일부 표현형(HELD_OUT)은 학습에서 제외.
- 크기: 학습 6,430 · 보정 717 · 잠금 프레임 297 (`tools/nlp/data/`).
- 손글씨 잠금셋 v1 45문장(`locked_handwritten.jsonl`) · v2 48문장(`locked_handwritten_v2.jsonl`). **둘 다 개발자 작성이며 독립 주석이 아니다.**

헤드 가중치는 3i4k를 일부 학습에 사용했으므로 CC BY-SA 4.0으로 표기한다. 인코더는 Apache-2.0(KoELECTRA)으로 알려져 있으나 위 출처 한계를 함께 적는다.

## 3. 평가 경위 (투명성을 위해 순서대로)

1. **v1 첫 실행(동결 인코더 특징만)**: 손글씨 v1에서 B2 기대 행동 0.733, 위험 개입 재현율 0.185, 보류 0.756. 행동 헤드 정확도 0.444로 실패. 결과 파일 `tools/nlp/eval/eval_v1_frozen_heads_first_touch.json`.
2. v1을 본 이상 v1은 **개발셋으로 강등**. 설계 변경(행동 헤드를 문자 n-gram으로, 화행 확률을 행동 존재 확률로 주변화, 가림 기반 근거 구간, 보정 분할에서 임계값 선택) **전에** v2를 작성·해시 동결(`956467fb…`).
3. 설계 고정 후 v2를 **한 번** 채점. 그 뒤 모델·정책 매개변수를 v2 결과로 조정하지 않았다.

## 4. 결과

보정 분할(717): 화행 정확도 0.866, macro-F1 0.885, ECE 0.027 · 행동 정확도 0.983, ECE 0.006.
잠금 프레임(297, 미학습 표현형 포함): 화행 0.889 · 행동 0.747(ECE 0.14).

손글씨 잠금 v2(48 = 위험 27 · 정상 21), 95% Wilson 구간:

| 기준선 | 기대 행동 일치 | 위험 개입 재현율 | 정상 불필요 개입 | 보류율 |
|---|---|---|---|---|
| B0 v4.4 (직접 입력 = 항상 ASK_HUMAN) | 0.667 | 0.000 | 0.000 | 1.000 |
| 규칙만(절 단위 어휘) | 0.688 | 0.370 | 0.143 | 0.229 |
| B1 NLP 헤드만(정책 없음) | 0.833 | 0.815 | 0.190 | 0.000 |
| **B2 NLP + 정책 (출하본)** | **0.833 [0.704, 0.913]** | **0.667 [0.478, 0.814]** | **0.190 [0.077, 0.400]** | 0.250 |
| B2 − 근거 구간(절제) | 0.833 | 0.296 | 0.000 | 0.542 |
| B3 실제 Zoro-1 | NOT_RUN | | | |

- 규칙 대비 NLP: 규칙만 맞힌 3건, NLP만 맞힌 10건, 정확 McNemar p=0.092. **5% 수준에서 우월성이 입증되지 않았다.**
- 위험 27건 중 3건(BEC 송금 지시, 연애 송금 부탁, 택배 링크 V13)을 `NO_STRONG_SIGNAL`로 놓쳤다. 화면은 이 상태를 "안전 보증 아님"으로 표시하지만 실제 놓침이다.
- 정상 21건 중 4건에 불필요 개입(예: "회비 2만 원은 총무 계좌로…"는 기대 범위 안, "새 비밀번호는 8자 이상…"·"택배 기사님, 경비실에…" 계열 일부가 과잉).
- 근거 구간 절제: 구간을 빼면 오탐은 0이 되지만 위험 재현율이 0.296으로 떨어진다. 구간은 "주세요." 같은 요청 어미를 고르는 경우가 있어 **설명으로서 품질이 낮다**(P1).

## 5. 교차 구현 일치·지연

`node tools/nlp/nlp_parity.js`: 171개 입력(잠금 v1·v2, 이모지·전각·한자·제어문자·300자 등 경계, 무작위 조합)에서 토큰 171/171, n-gram 171/171, 풀링 특징 코사인 최소 0.9999999999987(ORT 대비), 헤드 확률 최대 오차 5.2e-5, 근거 구간 171/171, 최종 정책 171/171.

지연(문장당, 전방 계산 + 헤드 + 가림 + 정책): Node CPU 단일 스레드 p50 306 ms, p95 611 ms(n=171) / 잠금 v2 p50 399 ms, p95 788 ms(n=48). Chromium 화면 1회 예시 809 ms + 모델 로드 553 ms. 휴대폰 지연 미측정.

## 6. 재현

```bash
python tools/nlp/make_dataset.py <3i4k fci.txt> tools/nlp/data          # 데이터
python tools/nlp/train_heads.py --enc enc_fp32.onnx --bin koelectra_small_v3_int8.bin \
  --tok tokenizer.json --data tools/nlp/data --dev tools/nlp/locked_handwritten.jsonl \
  --locked tools/nlp/locked_handwritten_v2.jsonl --out out/ [--final]
python tools/nlp/build_nlp_assets.py <bin> <vocab.txt> out/dmsg_nlp_heads.json apps/shared/nlp
python tools/nlp/make_nlp_reference.py ... tools/nlp/nlp_reference_vectors.json && node tools/nlp/nlp_parity.js
python tools/compare_engines.py --locked tools/nlp/locked_handwritten_v2.jsonl --out internal/evidence/v45_compare.json
```
ONNX·토크나이저 원본은 위 npm 패키지에서 받는다(릴리스에 포함하지 않음). `--final`은 잠금셋을 채점하므로 설계 고정 후 한 번만 쓴다.

## 7. 한계와 다음 실험

- 독립 주석자가 쓴 잠금셋이 없다. 팀원 2명이 서로 보지 않고 20~30문장씩 작성하면 첫 독립 평가가 된다(`docs/20` 절차).
- 행동 헤드는 어휘 기반이라 "통관비만 먼저 보내줄 수 있어?" 같은 우회 표현을 놓친다.
- 임계값 0.5는 허용 범위 하한이며 보정 분할이 작성 데이터라 낙관적일 수 있다.
- NPU·GPU 가속 없음(CPU). 실기기 지연·메모리 미측정.
