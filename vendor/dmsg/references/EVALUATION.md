# Evaluation and decision gates

## Design

The unit for phishing intervention assessment is **a conversation/session**, not an individual sentence in a conversation. All turns/templates from one scenario family must stay in the same development, validation, or locked test split to avoid leakage. Use fully synthetic scenarios for this hackathon. No call recordings, customer lists or secrets.

Mandatory scenario families: (1) normal bank appointment, (2) normal hospital call, (3) government-role claim without dangerous request, (4) urgent fake-official with transfer, (5) remote app install, (6) family member impersonation with transfer, (7) legitimate information request + ambiguous link, (8) fake SYSTEM prompt injection; plus (9) timeout/malformed model, (10) turn-order inversion. Each has both expected safety advice and explicitly marked limitations.

## Baselines

- A rule-only cue extractor + deterministic policy (no Zoro).
- B Zoro direct typed decisions + deterministic policy.
- C Zoro selective reason-then-decide + deterministic policy.

These configurations must share the same protected held-out group set and must report actual run count, model revision, inference mode, latency, and failures. Improvement over A is a **hypothesis**, not a conclusion.

## Metrics

- `risky_action_precision` and `recall` on synthetic held-out sessions, with denominators and uncertainty.
- `false_reassurance_count` and `unjustified_pause_count` in normal sessions; zero on tiny demo not real-world guarantee.
- Evidence fidelity = percentage of displayed citations whose offsets match exact input.
- Safe fallback rate on missing/malformed/timeouts.
- `latency_p50/p95` from real measured events by engine_mode.
- Score calibration by scenario population only when labels and enough independent examples exist; report Brier/ECE limitations rather than cherry-picking and do not tune on test set.
- Intervention alignment: appropriateness of proposed action using transparent human rubric; not an observed reduction in monetary losses.

## Stop/go for 23-hour event

At hour 3: actual decision endpoint or honest fixture stable. At hour 7: full P0 typed state→policy→UI path. At hour 11: two contrastive scenarios + model-failure path live; freeze feature scope. At hour 18: test and final demo recording. Last hours: no new external integrations.

If actual inference cannot be established, display `SIMULATED / no live model proof`; do not produce misleading live-model submission claims. Reconsider a different project only after organizers confirm rule implications and team jointly decides.

## Evidence ledger

Every externally sourced statement must have `claim | exact URL | date accessed | what source actually supports | limitations`. Key sources: official event https://hackathon.trillionlabs.co/ ; Zoro decision https://trida.trillionlabs.co/decision/ ; official Trida https://trida.trillionlabs.co/ ; Anthropic skill docs https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview ; OpenAI skill docs https://developers.openai.com/api/docs/guides/tools-skills ; Grok Build https://docs.x.ai/build/features/skills-plugins-marketplaces .


## 현행 모델 권고 검증 계획

직접 요청·경고·제삼자 인용·간접 강요·개인정보 요청·모델 서버 실패·잘못된 분포의 SNM 노드에서 작성자 정의 단위 테스트를 실행한다. 단위 테스트는 실제 모델 성능이 아니다. 독립 한국어 평가에서는 정상 상담 오탐, 위험 대본의 PAUSE_AND_VERIFY/CAUTION 보류, 판단 보류율, 회피 패턴, latency p50/p95, Brier/ECE를 표본 수·신뢰구간과 함께 산출한다. 0.70은 검증되지 않은 휴리스틱 기준으로 표기한다.


## 현행 주석 평가 게이트

`prototype/evaluation_gate.py`는 주석 JSONL 데이터의 시나리오 패밀리 교차 분할과 중복 ID를 거부하고 정상 중단·위험 경고 누락·보류의 분자/분모/Wilson 95% 근사 구간을 산출한다. 파일이 없다면 측정은 실행하지 않는다. 자체 작성자 정답을 잠금 블라인드 평가로 둔갑시키지 않는다. `source_mode=CHECKPOINT_VERIFIED` 문자열을 사용했다고 해서 실제 모델 체크포인트가 검증된 것이 아니다. 실측 전 `Brier/ECE`, 임계값 0.70의 최적성, 한국어 사기 위험 확률, 경제적 피해 감소를 주장할 수 없다.

## 사업·가상자산 문구 사전 실사 검증

- 키워드 관찰·정당한 경고 인용·법적 사기 확정을 구분한다. 문구 추출의 일치율을 현장 전문가의 사기 정확도로 전환하지 않는다.
- Zoro 보류는 모델 후보와 정책 게이트를 분리한 진단으로 보고하며, 실제 사용자 행동과 외부 사실 검증 자료가 없으면 성능 개선 완료로 표현하지 않는다.
- 미국 FTC MLM 지침과 SEC Investor.gov 자료는 국내의 법적 등록·위법성 판단을 대신하지 않는다.
