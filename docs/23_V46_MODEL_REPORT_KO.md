# 23. v4.6 모델 성능 보고서 — v4.5 대비 (같은 문장 · 같은 정책 파이프라인)

기준일 2026-11-02 KST. 모든 수치는 이 환경(Linux x64, CPU 2코어, RAM 7 GB, GPU·NPU 없음)에서 실제 실행한 결과다. 원자료: `tools/nlp/eval/v46_vs_v45_locked_report.json`, `internal/evidence/v46_compare*.json`, `internal/evidence/v46_nlp_parity.json`.

## 1. 기준선과 재현
- 기준선 v4.5: FULL `2f66ea4f…`, APK `6317879e…`, 가중치 `52da5443…`, 헤드 `de1f791a…` (`internal/evidence/v46/BASELINE_V45.json`).
- v4.5 실제 구조(가정 없이 파일로 확인): KoELECTRA-small-v3 int8 동결 인코더 → [CLS; 평균] 512 → 화행 5클래스 LR(인코더 특징 + 0.5×문자 n-gram) · 행동 7클래스 LR(문자 n-gram만) → 행동 존재 확률로 주변화한 typed 계약 → 정책. 이 구조에는 의도·위험 신호·요구 행동 과제가 없다.
- 문제 재현: CASE A/B는 원본 스크린샷이 이번 작업에 첨부되지 않아 프롬프트의 묘사로 **재구성한 문장**(W01, W02)이다. v4.5는 W01을 ASK_HUMAN, W02를 NO_STRONG_SIGNAL("뚜렷한 위험 없음")로 냈다 — 묘사된 결함과 같은 방향.

## 2. 무엇을 바꿨나
| 구성 | v4.5 | v4.6 |
|---|---|---|
| 인코더 | 동결 | **상위 8층 미세조정**(JAX, 2 epoch), int8 재양자화 |
| 과제 | 화행·행동 주제 | 화행 · 의도 · 요구 행동 · **위험 신호 9종(다중 라벨)** · 행동 주제(v4.5 헤드 재사용) · 불확실성 |
| 근거 | 행동 단어 위치 | + **구조적 근거 추출**(외부 메신저 ID, URL, 전화, 금액, 해외발신 표시, 계좌 변경 문구) — 모델 해석과 분리 |
| 정책 | 화행·행동 → 4상태 | + 위험 신호 정책(절대 하향 없음, 구조적 근거가 있을 때만 CAUTION/PAUSE, 모델 단독 신호는 0.8 이상에서 ASK_HUMAN) + 과제 간 교차 점검 |

## 3. 후보와 선정 (잠금셋 미사용)
| 후보 | 설명 | 보정 분할 평균* | 개발셋 D1 기대행동 |
|---|---|---|---|
| c0 | 인코더 동결 + 새 헤드 | 0.610 | 0.889 |
| b2h | 상위 2층 + n-gram 융합 | 0.617 | 0.867 |
| b4h | 상위 4층 + n-gram | 0.618 | 0.911 |
| b4hl | 상위 4층 + n-gram, 낮은 학습률 | 0.622 | 0.867 |
| b4n | 상위 4층, 신경망만 | 0.605 | 0.889 |
| **b8n** | **상위 8층, 신경망만** | **0.640** | **0.911** |

\* 화행·의도·요구 행동 macro-F1과 위험 신호 micro-F1의 평균. 선정 기준은 실행 전에 정했고 잠금셋은 쓰지 않았다(`tools/nlp/eval/v46_model_selection.json`). 새로 학습한 행동 주제 헤드는 개발셋에서 v4.5보다 나빠(macro-F1 0.553 vs 0.797) 버리고 v4.5 헤드를 유지했다. 후보 2(KoELECTRA-Base 계열)는 가중치를 받을 경로가 없어 **BLOCKED**(Hugging Face 차단, npm 등 대체 출처 미확인).

## 4. 잠금 평가 (한 번 실행)
95% Wilson 구간. W = v4.6 잠금셋(49: 위험 25·정상 24), V2 = v4.5 최종 잠금셋(48: 위험 27·정상 21). 둘 다 개발자 작성.

| 세트 | 시스템 | 기대 행동 일치 | 위험 개입 | 정상 불필요 개입 | 보류 |
|---|---|---|---|---|---|
| W | v4.5 | 0.510 [0.375, 0.644] | 0.120 [0.042, 0.300] | 0.042 | 0.102 |
| W | **v4.6** | **0.878 [0.758, 0.943]** | **0.600 [0.407, 0.766]** | 0.125 [0.043, 0.310] | 0.204 |
| W | 인코더 동결(c0) | 0.755 | 0.440 | 0.125 | 0.204 |
| V2 | v4.5 | 0.833 [0.704, 0.913] | 0.667 | 0.190 | 0.250 |
| V2 | **v4.6** | **0.792 [0.657, 0.883]** | **0.741** | **0.238** | 0.271 |
| V2 | 인코더 동결(c0) | 0.854 | 0.704 | 0.190 | 0.250 |

짝지은 정확 McNemar(기대 행동 일치): W에서 v4.6만 맞힌 19건 vs v4.5만 맞힌 1건, p < 0.001. V2에서 v4.6만 맞힌 2건 vs v4.5만 맞힌 4건, p = 0.69(차이 입증 안 됨).

**해석:** 새 과제 체계로 쓴 W에서는 크게 나아졌다. 하지만 W는 개선 목표(연락 유도·금전 유인 등)를 알고 같은 개발자가 쓴 문장이라 v4.6 설계에 유리하다. 기존 V2에서는 위험 개입이 늘고(+2건) 정상 오탐도 늘어(+1건) 기대 행동 일치가 2건 줄었다. **인코더 동결 c0가 V2에서는 v4.6보다 낫다** — 미세조정이 기존 분포에서 약간의 손해를 낸다는 신호다.

과제별(W): 화행 macro-F1 0.481 → 0.733, 의도 0.743, 요구 행동 0.828, 위험 신호 micro PR-AUC 0.860 · micro-F1 0.714 · "신호 없음" 정확도 0.837. ECE: 화행 0.114, 의도 0.084, 요구 행동 0.072 (49문장이라 불안정). 생성 잠금(G, 467)에서는 화행 macro-F1이 v4.5·v4.6 모두 0.26대로 낮다 — 생성 템플릿의 화행 라벨 관례가 손글씨와 달라 의미 있는 비교가 아니다(보고만 함). v4.5 잠금 프레임(F, 297): 화행 0.884 → 0.906.

## 5. 절제 실험 (W, v4.6)
| 제거한 구성 | 기대 행동 | 위험 개입 | 정상 오탐 | 보류 |
|---|---|---|---|---|
| 없음(출하본) | 0.878 | 0.600 | 0.125 | 0.204 |
| 위험 신호 정책 | 0.816 | 0.200 | 0.000 | 0.367 |
| 구조적 근거 | 0.857 | 0.200 | 0.000 | 0.408 |
| 모델 기여 구간 | 0.878 | 0.480 | 0.125 | 0.265 |
| 과제 간 교차 점검 | 0.816 | 0.600 | 0.125 | 0.122 |

위험 개입 향상의 대부분은 "위험 신호 + 원문의 구조적 근거" 조합에서 나온다. 구조적 근거를 빼면 정상 오탐은 0이 되지만 위험 개입이 0.2로 떨어진다.

## 6. 양자화
int8(출하) vs fp32(같은 미세조정): W·V2 정책 결과 동일, W 의도 macro-F1 0.743 vs 0.770, 요구 행동 0.828 vs 0.814, 생성셋 차이 ±0.005 이내. 크기는 v4.5와 같다(14,654,232 B).

## 7. 놓친 것·과한 것 (W)
- W01(CASE A 재구성) → PAUSE_AND_VERIFY. 개입은 했지만 기대(주의·보류)보다 강하다.
- W09 낯선 사람의 만남 제안(메신저 ID 없음) → NO_STRONG_SIGNAL. 놓침.
- W27 "검사라며 돈 옮기라는 전화 받았대" 인용 → NO_STRONG_SIGNAL. 놓침.
- W10 가족 사칭 송금(직접 요구) → ASK_HUMAN(보류). 기대는 PAUSE.
- W18 원격 앱 설치 → ASK_HUMAN(교차 점검). 기대는 PAUSE.
- 정상 W43 "점심 투표 링크 눌러주세요" → ASK_HUMAN.
- V2에서 v4.6만 틀린 4건: 경고문 V01과 기관 계좌 변경 안내 V46 → PAUSE(과잉), 인용 V07 → PAUSE(과잉), 일상 V45 → ASK_HUMAN. v4.6만 맞힌 2건: 경고문 V04(v4.5는 PAUSE 과잉), 연애 송금 부탁 V25(v4.5는 위험 없음).

## 8. 실행 환경과 속도
- JS(출하 런타임)와 Python 기준 구현: 221개 입력에서 토큰·n-gram·특징(코사인 ≥ 0.99999999999)·모든 과제 확률(최대 오차 9.4e-6)·근거 구간·불확실성·최종 정책 221/221 일치. 출하 JS로 W를 다시 돌린 결과도 잠금 평가와 49/49 같다(`tools/nlp/eval/v46_golden_snapshot.json`).
- 지연(Node CPU 단일 스레드): p50 406 ms, p95 906 ms (n=218). Chromium 화면 1회 약 1.1 s + 모델 로드 약 0.6 s. 메모리: Node RSS 146 → 179 MB(자산 문자열 포함). **Android 실기기 지연·메모리·배터리·발열: NOT_MEASURED.**
- 실행 공급자: 순수 JavaScript CPU. XNNPACK·NNAPI·NPU: **NOT_RUN**. NPU를 홍보 문구로 쓰지 않는다.

## 9. Android
- APK v4.6(versionCode 46) 빌드·서명 v2·구조·테마 해석 검증 PASS, 권한 0개. 웹 자산(모델 포함)이 웹 빌드와 바이트 동일.
- 같은 웹 자산을 Chromium(모바일 크기, file://)에서 실행: 모델 로드·추론·위험 신호 표시 PASS, 뒤로 가기·화면 회전(뷰포트 전환)·300 px 폭 넘침 0.
- **실제 Android 기기 설치·실행: NOT_RUN** (기기·에뮬레이터 없음). 매니페스트 `configChanges`에 회전·화면 크기가 포함돼 회전 시 Activity가 재생성되지 않도록 설정되어 있다(실기기 미확인).

## 10. Zoro-1
공식 페이지(2026-11-02 재확인): 모델 `trillionlabs/Zoro-1`, Qwen3.5-4B 기반, kev 서버 `POST /v1/systemone`, 요청 `state` + `questions{type: noul|choice|score, instructions, criteria}`, 보정 온도 2.19 표기, 하드웨어 요구사항 미기재. 이 환경: Hugging Face 차단·RAM 7 GB·GPU 없음 → **BLOCKED**. 비교 하네스(`tools/compare_engines.py`)는 Zoro endpoint가 설정되면 같은 W·V2로 바로 실행된다. 모의 응답을 Zoro로 표기한 곳은 없다.

## 11. 승격 판단
v4.6을 기본 모델로 승격한다. 근거: W에서 유의한 개선(p < 0.001), V2에서 유의한 악화 없음(p = 0.69), 크기·지연 동일 수준, CASE A/B 재구성 모두 "위험 없음"으로 끝나지 않음. 대가: V2 정상 오탐 +1건, 기대 일치 −2건, c0가 V2에서 더 나음. **이 판단은 개발자 작성 문장에 기댄 것이며 독립 평가가 아니다.** 팀원 블라인드 문장으로 재평가하기 전에는 "실제 사기 탐지 성능이 좋아졌다"고 말하지 않는다. 롤백: `models/`에 v4.5 가중치는 없으나 v4.5 릴리스(FULL/APK/스킬)가 해시와 함께 보존되어 있다.

## 12. 재현
```bash
python tools/nlp/make_dataset_v46.py out/ds                        # 데이터(잠금셋 오염 제거 포함)
python tools/nlp/finetune_v46.py --onnx enc_fp32.onnx --tok tokenizer.json --v46 out/ds --v45 tools/nlp/data --out out/b8n --top-k 8 --epochs 3 --lr-enc 3e-5
python tools/nlp/compose_heads_v46.py out/b8n/heads.json <v4.5 heads.json> out/b8n/heads_ship.json
python tools/nlp/eval_v46.py --onnx enc_fp32.onnx --tok tokenizer.json --system A_v45=<v4.5 bin>,<v4.5 heads> --system V46=out/b8n/weights_int8.bin,out/b8n/heads_ship.json --gen out/ds/v46_locked.jsonl --frames tools/nlp/data/locked.jsonl --out report.json
python tools/nlp/build_nlp_assets.py out/b8n/weights_int8.bin vocab.txt out/b8n/heads_ship.json apps/shared/nlp
python tools/nlp/make_nlp_reference.py ... && node tools/nlp/nlp_parity.js && node tools/nlp/regress_cases_v46.js
```
의존성: Python 3.13, jax/jaxlib 0.12.0.1, optax 0.2.8, onnxruntime 1.29, tokenizers, scikit-learn; Node 22. 단일 CPU 실행 기준 b8n 학습 약 5분.
