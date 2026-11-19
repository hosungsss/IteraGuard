# 의심계 v4.6 온디바이스 모델 카드

| 항목 | 값 |
|---|---|
| 이름 | koelectra-small-v3-ft8-int8 + dmsg-multitask (v4.6) |
| 기반 인코더 | KoELECTRA-small-v3 판별기 (ELECTRA, 12층, hidden 256, 임베딩 128, 어휘 35,000) |
| 기반 가중치 출처 | npm `kakaotalk-chat-analyzer-models@0.2.1`에 포함된 ONNX(fp32). 패키지가 `monologg/koelectra-small-v3-discriminator`라고 밝힘. Hugging Face 원본과 바이트 대조는 하지 못함(이 환경에서 HF 접근 차단) |
| 기반 ONNX SHA-256 | `09def51608076f8c0c49430ecfeb591249c6f7b05e4eee5accef39b308b48c48` |
| 미세조정 | 상위 8층 + 과제별 선형 헤드, JAX(CPU), 2 epoch 선택(보정 분할 기준), AdamW, 클래스 가중 CE + 양성 가중 BCE |
| 배포 가중치 | `koelectra_small_v3_ft8_int8.bin` — 릴리스 용량 한도 때문에 이 폴더에 중복 저장하지 않음. 앱 자산 `apps/shared/nlp/dmsg-nlp-weights.js`(base64)에서 `python tools/nlp/extract_model_weights.py out.bin`으로 복원·해시 검증, 채팅에서 별도 파일로도 제공. (DMSGNLP1 컨테이너, 행렬 int8 대칭·출력 열 단위 스케일, 어휘 임베딩 행 단위) 14,654,232 B, SHA-256 `5430e71a…9b36` |
| 헤드 | `dmsg_nlp_heads_v46.json` (schema `dmsg-nlp-heads/3`) SHA-256 `2a1aa9e8…7f39` |
| 과제 | 화행(softmax 5) · 의도(7) · 요구 행동(8) · 위험 신호(sigmoid 9, 라벨별 임계값) · 행동 주제(v4.5 문자 n-gram 헤드 재사용, 인코더 무관) |
| 토크나이저 | `tokenizer.json` (WordPiece, BertNormalizer: clean_text·한자 분리·소문자화 없음), 최대 128 토큰, 초과 시 앞 127 + [SEP] |
| 확률 보정 | 과제별 온도(보정 분할 NLL 최소). 위험 신호는 라벨별 온도 + F1 최대 임계값(0.05–0.95). 실제 사기 확률이 아님 |
| 학습 데이터 | 작성 합성 v4.6(3,534) + v4.5 작성 합성·3i4k(CC BY-SA 4.0) 6,430. 잠금 문장과 문자 3-gram Jaccard ≥ 0.5인 생성 문장 255개 제거 |
| 라이선스 | 인코더 Apache-2.0(KoELECTRA로 알려짐, 출처 한계 위 참조). 미세조정 가중치·헤드: 3i4k 사용으로 CC BY-SA 4.0 표기 |
| 실행 | 순수 JavaScript(CPU). NNAPI·NPU·XNNPACK 미사용 |
| 알려진 한계 | `docs/23_V46_MODEL_REPORT_KO.md` |
