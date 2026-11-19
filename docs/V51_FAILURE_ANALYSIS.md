# v5.1 잔여 실패 분석 — 고정 후보의 실제 저장 응답 기준

작성: 2026-11-04. 대상은 `v51-specific-candidate` 11문항 + `legacy` + `v51-semantic/4`다. 실행 manifest는 `48b0bbd05a51de8d2612186f7420090e0ab4330071f42abdb856b195838afdb7`이다. 이 보고서는 저장된 응답·고정 라벨·실행 trace를 분석하며 **새 모델 호출, 규칙 수정, 가중치 학습, 잠금 검증셋을 사용한 추가 튜닝을 하지 않았다.**

v5.1은 전체 파이프라인에서 개선됐지만 핵심 판단 성능이 완성된 상태가 아니다. 필수 중단 누락 5건, 통상 비용 문장의 기존 과잉 중단 1건, 잠금 24건 안의 정상 불필요 보류 5건이 남았다. 특히 높은 모델 응답이 있어도 좁은 어휘 규칙 때문에 보류되는 경우와, 모델의 발화·현재성 판단 자체가 불확실한 경우를 구분해야 한다.

## 1. 숫자의 범위와 해석

이 문서의 기대 결과는 기존 AI 작성 평가 라벨이다. 실제 발신자·계좌 안전성이 인증됐다는 뜻이 아니며, 독립 인간 평가 결과도 아니다. `PAUSE_AND_VERIFY`는 잠시 중단 후 확인, `ASK_HUMAN`은 자동 판단 보류, `CAUTION`은 주의, `NO_STRONG_SIGNAL`은 뚜렷한 위험 신호 미감지다. 미감지는 안전 보증이 아니다. 필수 중단 누락 5건은 모두 ASK로 남은 경우이며 위험 문장을 NSS로 통과시킨 5건이 아니다.

| 데이터 | 사례 수 | 기대일치 기존7 → 후보11 | 필수중단 누락 기존 → 후보 / 필수중단 수 | 정상 불필요 ASK 기존 → 후보 |
|---|---:|---:|---:|---:|
| 기존 V2 | 48 (빈 입력 1 포함) | 35 → 40 | 7 → 2 / 9 | 6 → 6 |
| 이전 AI25 | 25 | 7 → 17 | 4 → 0 / 10 | 12 → 6 |
| 새 AI25 | 25 | 14 → 22 | 3 → 1 / 8 | 8 → 2 |
| 개발 AI36 | 36 | 8 → 28 | 11 → 0 / 12 | 16 → 7 |
| 잠금 AI24 | 24 | 7 → 17 | 6 → 2 / 7 | 11 → 5 |

전체 158쌍 중 실제 비어 있지 않은 문장은 157개다. 두 프로필의 저장 응답 314개를 재처리했고, 빈 입력 양쪽의 ASK 마커 2개를 별도로 보존했다. Python/JavaScript의 정책 결과와 전체 결과 628개 객체 비교가 일치했다. 원기록 action/reason/probs도 빈 마커 포함 316건 일치했다. 다섯 세트 모두 기존 허용 결과 손실, 신규 위험/불명 NSS, 신규 정상 PAUSE, 신규 필수중단 누락은 0이었다. 이는 잔여 문제가 0이라는 뜻이 아니다. 개발36의 정상 PAUSE 1건은 기존에도 있던 사례다.

여기서 전체 파이프라인은 현재 문장에 대한 프로필·응답 계약 검증, 정책, 표시 근거, 사용자 검토(false), 오프라인 LinkGuard까지다. 이번 저장 응답에서는 로컬 후처리로 action/reason이 바뀐 사례가 0이다. Arena의 이전 위험 유지·세션 종료/재개는 별도 상태 계층이며 이 성능 분모에 섞지 않는다.

출처: [전체 재처리 결과](../internal/evidence/v51/full_pipeline_validation/results.json), [사례별 trace](../internal/evidence/v51/full_pipeline_validation/per_case.jsonl), [재현 스크립트](../internal/evidence/v51/full_pipeline_validation/replay_full_pipeline.py).

## 2. 모델·규칙·UI를 나누는 기준

아래 11개 상세 사례의 **분석용 주원인 태그**는 모델 분류/확신 제약 5건, 어휘/문맥 규칙 제약 3건, 두 요인의 혼합 2건, 기존 정책 목표/범위 1건이다. UI만으로 만들어진 잘못된 action은 이 11개에서 0건이다. 이 태그는 고정 응답과 코드 경로에 대한 설명이며, 요인별 대조 실험으로 인과 기여율을 추정한 통계가 아니다. 낮은 확률을 보였다고 곧바로 모델이 실제 사실을 틀렸다고 단정하지 않는다.

- 모델 쪽 관찰: 현재 요청을 reported/unclear로 고르거나 여러 행동 사이에 확률을 분산시킴, 현재 요청·근거 충분성 문항이 필요한 확신에 도달하지 못함.
- 규칙 쪽 관찰: 일회용 확인 코드·2천만 원 같은 표현을 사전/정규식이 못 찾거나, 부정·인용된 민감어가 문장 전체 금지 조건으로 남음. 규칙이 코드대로 실행됐어도 제품의 목표 의미를 충분히 반영하지 못할 수 있다.
- 정책 범위: 기존 PAUSE를 새 문항으로 해제하지 않는 설계가 정상 송금의 과잉 중단도 보존함. 이 설계 변경은 별도 후보로 등록하고 독립 평가로 확인해야 하는 판단이다.
- UI 쪽 관찰: 아래 경고 예시에서 단일 action 확률을 ‘확신’으로 표시해 전체 보류 이유와 모순처럼 보일 수 있다. 이것은 숫자 설명 문제이며 underlying ASK 자체를 UI가 생성했다는 증거는 없다.

각 표는 **후보11 응답 안의 기존 7개 ID와 추가 4개 필드**를 보여 준다. 비교 arm인 원래 baseline7의 확률표가 아니다. 기존 ID 중 `q_evidence`는 문구를 개선한 후보 버전이다. 확률은 정규화된 저장 응답을 소수 넷째 자리로 표시하며, 사기 확률·신원 인증·실제 위험도의 보정값이 아니다. `q_claim`과 `q_risk`는 이 후보 중단/정상화 조건의 직접 입력으로 사용되지 않는다. `q_evidence`는 no>=0.70일 때 정상화/주의를 막는 조건이며 yes>=0.70을 모든 판단에 요구하는 구조가 아니다.

## 3. 남은 필수 중단 누락 5건

### V18 — 계좌 변경 뒤 송금 요청: 이상 징후는 잡았지만 현재 요청 확신 조건을 통과하지 못함

> 계좌가 바뀌었습니다. 이번 송금부터 첨부된 계좌를 사용해 주세요.

기대: `PAUSE_AND_VERIFY`. 실제: `ASK_HUMAN` / `REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE`. 데이터: `V2_48`. 주원인 태그: **모델 분류/확신 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | transfer 0.6701, none 0.1796, unclear 0.1237 |
| 기존 7 ID | `q_speech` | reported_or_quoted 0.4942, unclear 0.2518, direct_request 0.1241 |
| 기존 7 ID | `q_scam` | yes 0.0319 / no 0.9681 |
| 기존 7 ID | `q_claim` | yes 0.0789 / no 0.9211 |
| 기존 7 ID | `q_pressure` | yes 0.0416 / no 0.9584 |
| 기존 7 ID | `q_risk` | 최댓값 none 0.3458; high 0.1480 |
| 기존 7 ID | `q_evidence` | yes 0.5888 / no 0.4112 |
| 추가 4 | `q_request_scope` | no_request 0.1248, other_request 0.0316, sensitive_request 0.6489, unclear 0.1947 |
| 추가 4 | `q_current_exposure` | yes 0.0078 / no 0.9922 |
| 추가 4 | `q_payment_anomaly` | yes 0.9107 / no 0.0893 |
| 추가 4 | `q_request_specified` | yes 0.8416 / no 0.1584 |

**확인된 기존 경로:** 기존 q_speech의 최댓값은 reported_or_quoted 0.4942다. 코드가 두 번째 절의 직접 요청 단서를 찾으므로 REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE가 먼저 발동했다. 낮은 확률 조건도 참이지만 이미 선택된 원인은 문맥 충돌이다.

**확인된 추가 규칙:** 신규 q_payment_anomaly=yes 0.9107은 높지만 현재 요청 합계(other+sensitive)는 0.6805로 0.70 미만이다. 따라서 CURRENT_ANOMALOUS_PAYMENT가 거짓이다. 보조 경로 SCOPED_PAYMENT_CORROBORATION도 sensitive 0.6489 및 q_scam=yes 0.0319가 각각 0.70에 못 미쳐 발동하지 않는다. 금전 문맥과 계좌 변경 단서는 실제로 잡혔다. q_evidence=no 0.4112는 강한 근거 부족 거부 조건이 아니다.

**해석·다음 확인점:** 새 이상결제 문항 하나의 정보는 유용했지만, 현재성·기존 사기 단서와 AND로 묶인 정책에서 활용되지 못한 사례다. 위험을 전혀 못 읽었다고 요약하면 사실과 다르다. 0.70을 이 문장에 맞춰 낮추면 된다는 결론도 낼 수 없다.

### V19 — 금액 표현·송금 어휘 누락: 모델은 직접 송금으로 분류했지만 원문 매칭이 실패함

> 지금 거래처에 2천만 원 보내고 결과만 문자로 알려줘.

기대: `PAUSE_AND_VERIFY`. 실제: `ASK_HUMAN` / `NO_GROUNDED_ACTION_ANCHOR`. 데이터: `V2_48`. 주원인 태그: **어휘/문맥 규칙 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | transfer 0.8820, none 0.0636, unclear 0.0359 |
| 기존 7 ID | `q_speech` | direct_request 0.7153, unclear 0.1366, informational 0.0730 |
| 기존 7 ID | `q_scam` | yes 0.1242 / no 0.8758 |
| 기존 7 ID | `q_claim` | yes 0.0668 / no 0.9332 |
| 기존 7 ID | `q_pressure` | yes 0.2853 / no 0.7147 |
| 기존 7 ID | `q_risk` | 최댓값 moderate 0.3148; high 0.2644 |
| 기존 7 ID | `q_evidence` | yes 0.6218 / no 0.3782 |
| 추가 4 | `q_request_scope` | no_request 0.0443, other_request 0.0445, sensitive_request 0.8344, unclear 0.0768 |
| 추가 4 | `q_current_exposure` | yes 0.0111 / no 0.9889 |
| 추가 4 | `q_payment_anomaly` | yes 0.3661 / no 0.6339 |
| 추가 4 | `q_request_specified` | yes 0.7158 / no 0.2842 |

**확인된 기존 경로:** q_action=transfer 0.8820, q_speech=direct_request 0.7153으로 기존 두 주축이 모두 0.70 이상이다. 그러나 transfer anchor 목록에 송금·이체·입금·돈을 보내 등은 있고 이 문장의 표현은 없다. _choose_anchor가 None이므로 NO_GROUNDED_ACTION_ANCHOR가 선택됐다.

**확인된 추가 규칙:** 신규 현재 요청 합계는 0.8789, sensitive는 0.8344다. 그럼에도 payment_context=False, payment_clause_count=0이다. 금액 정규식은 수 뒤 선택적 단위 하나(만|천|억)만 허용하므로 2천만 원의 복합 단위를 잡지 못한다. q_payment_anomaly=yes 0.3661도 낮으며, 보조 결제 경로의 q_scam=yes 0.1242 조건도 충족하지 못한다.

**해석·다음 확인점:** 직접 송금이라는 모델 분류를 최종 안내로 잇는 어휘 사전·금액 구조의 표현 범위가 병목이다. 대표·거래처라는 실제 신원은 인증되지 않았지만, 그 사실과 명시적 금전 요청을 원문에서 못 찾은 문제는 구분해야 한다.

### V50-AI-21 — 거절 인용 뒤 새 위협·보증금 요구: 발화·강요 단서가 약하게 나옴

> 오늘 업무를 중단시키겠습니다. 보증금을 먼저 보내야 해결됩니다.

기대: `PAUSE_AND_VERIFY`. 실제: `ASK_HUMAN` / `UNSUPPORTED_QUOTATION_LABEL`. 데이터: `AI25_new`. 주원인 태그: **모델 분류/확신 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | transfer 0.7112, none 0.2139, unclear 0.0655 |
| 기존 7 ID | `q_speech` | reported_or_quoted 0.4709, unclear 0.2110, direct_request 0.1460 |
| 기존 7 ID | `q_scam` | yes 0.1080 / no 0.8920 |
| 기존 7 ID | `q_claim` | yes 0.0200 / no 0.9800 |
| 기존 7 ID | `q_pressure` | yes 0.3654 / no 0.6346 |
| 기존 7 ID | `q_risk` | 최댓값 high 0.3572; high 0.3572 |
| 기존 7 ID | `q_evidence` | yes 0.5805 / no 0.4195 |
| 추가 4 | `q_request_scope` | no_request 0.1226, other_request 0.0418, sensitive_request 0.7091, unclear 0.1265 |
| 추가 4 | `q_current_exposure` | yes 0.0052 / no 0.9948 |
| 추가 4 | `q_payment_anomaly` | yes 0.4120 / no 0.5880 |
| 추가 4 | `q_request_specified` | yes 0.6218 / no 0.3782 |

**확인된 기존 경로:** q_speech는 reported_or_quoted 0.4709를 선택했다. 하지만 기존 어휘 규칙은 이 표현을 report_cue로 인식하지 않아 UNSUPPORTED_QUOTATION_LABEL로 보류했다. transfer 0.7112는 높지만 직접 요청 확신은 0.1460이다.

**확인된 추가 규칙:** 현재 요청 합계 0.7509와 sensitive 0.7091은 기준을 넘는다. 그러나 q_payment_anomaly=yes 0.4120으로 직접 결제 중단 경로가 거짓이고, 보조 경로는 q_scam=yes 0.1080 때문에 거짓이다. 코드의 explicit_anomaly=True지만 q_pressure=yes 0.3654, 어휘 pressure_cue=False다. 위협과 현재 요구가 한 묶음으로 충분히 반영되지 않았다.

**해석·다음 확인점:** 원문 전체를 보고 나온 발화 분류와 강요 관련 확률, 제한된 위협 어휘가 함께 원인 후보다. 기존 거절을 언급한 절과 뒤의 현재 보증금 요구를 별도 역할로 해석하는 성능이 필요하다는 추론이며, 해당 잠금 문장에 맞춘 규칙 수정은 하지 않았다.

### V51-F13_ARCHIVE_READING_ACCESS-03 — 일회용 확인 코드: 새 노출 문항까지 높지만 동의어 매칭이 없음

> 본인에게 전송된 일회용 확인 코드를 이 메시지의 답장으로 보내세요.

기대: `PAUSE_AND_VERIFY`. 실제: `ASK_HUMAN` / `NO_GROUNDED_ACTION_ANCHOR`. 데이터: `AI24_locked`. 주원인 태그: **어휘/문맥 규칙 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | otp 0.9704, none 0.0106, unclear 0.0096 |
| 기존 7 ID | `q_speech` | direct_request 0.7164, unclear 0.1767, reported_or_quoted 0.0613 |
| 기존 7 ID | `q_scam` | yes 0.2181 / no 0.7819 |
| 기존 7 ID | `q_claim` | yes 0.0615 / no 0.9385 |
| 기존 7 ID | `q_pressure` | yes 0.0403 / no 0.9597 |
| 기존 7 ID | `q_risk` | 최댓값 none 0.4233; high 0.1192 |
| 기존 7 ID | `q_evidence` | yes 0.5521 / no 0.4479 |
| 추가 4 | `q_request_scope` | no_request 0.0193, other_request 0.0835, sensitive_request 0.8242, unclear 0.0730 |
| 추가 4 | `q_current_exposure` | yes 0.8869 / no 0.1131 |
| 추가 4 | `q_payment_anomaly` | yes 0.0113 / no 0.9887 |
| 추가 4 | `q_request_specified` | yes 0.7999 / no 0.2001 |

**확인된 기존 경로:** otp 0.9704, direct_request 0.7164로 기존 모델 주축은 명확하다. 그러나 OTP·인증번호·일회용 비밀번호·verification code라는 기존 anchor에는 일회용 확인 코드가 없어 NO_GROUNDED_ACTION_ANCHOR가 발생했다.

**확인된 추가 규칙:** 신규 sensitive 0.8242, 현재 요청 합계 0.9077, q_current_exposure=yes 0.8869, q_request_specified=yes 0.7999도 높다. 그런데 exposure_terms에도 일회용 확인 코드가 없어 exposure_context=False, active_exposure_count=0, direct_exposure_count=0이다. 따라서 CURRENT_SENSITIVE_EXPOSURE와 SCOPED_SENSITIVE_REQUEST가 모두 거짓이다. 접속에 따른 indirect_redirect_cue=True는 일반 요청 정상화 경로만 막는 조건이며, 이번 민감 요청 중단 실패의 직접 원인은 아니다.

**해석·다음 확인점:** 이 사례를 모델이 OTP 요청을 못 알아봤다고 분류하면 잘못이다. 관찰된 주된 병목은 높은 모델 정보를 확인할 독립 어휘 근거를 너무 좁게 정의한 데 있다. 이는 안전용 근거 조건의 표현 범위 문제이지 높은 모델 확률을 무조건 믿자는 근거는 아니다.

### V51-F17_REFRIGERATED_WAREHOUSE_ACCESS-02 — 링크와 일회용 번호가 함께 있는 복합 요구: 확률 분산과 매칭 누락

> 긴급 접속 링크를 열고 휴대폰에 뜬 일회용 번호를 관리자에게 전송하세요.

기대: `PAUSE_AND_VERIFY`. 실제: `ASK_HUMAN` / `MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS`. 데이터: `AI24_locked`. 주원인 태그: **모델+어휘 혼합**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | otp 0.3977, link 0.2864, remote_install 0.1994 |
| 기존 7 ID | `q_speech` | direct_request 0.7885, unclear 0.0918, reported_or_quoted 0.0748 |
| 기존 7 ID | `q_scam` | yes 0.2519 / no 0.7481 |
| 기존 7 ID | `q_claim` | yes 0.0659 / no 0.9341 |
| 기존 7 ID | `q_pressure` | yes 0.7552 / no 0.2448 |
| 기존 7 ID | `q_risk` | 최댓값 high 0.4847; high 0.4847 |
| 기존 7 ID | `q_evidence` | yes 0.7332 / no 0.2668 |
| 추가 4 | `q_request_scope` | no_request 0.0780, other_request 0.0737, sensitive_request 0.7039, unclear 0.1445 |
| 추가 4 | `q_current_exposure` | yes 0.6963 / no 0.3037 |
| 추가 4 | `q_payment_anomaly` | yes 0.0188 / no 0.9812 |
| 추가 4 | `q_request_specified` | yes 0.7943 / no 0.2057 |

**확인된 기존 경로:** q_action이 otp 0.3977, link 0.2864, remote_install 0.1994로 나뉘었다. direct_request 0.7885는 높지만 단일 action 최댓값이 0.70 미만이므로 MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS가 선택됐다.

**확인된 추가 규칙:** 신규 현재 요청 합계는 0.7776이고 pressure=yes 0.7552, evidence=yes 0.7332다. q_current_exposure=yes 0.6963은 직접 노출 경로의 0.70보다 조금 낮다. 별도 SCOPED_SENSITIVE_REQUEST는 exposure=no 0.3037<0.70을 허용하지만, 일회용 번호가 exposure_terms에 없어 active/direct exposure 절 수가 모두 0이라 역시 거짓이다. 문장에 링크가 있어 action_mentioned=True인 것과 민감 노출 어휘를 찾은 것은 다른 검사다.

**해석·다음 확인점:** 단일 action 분류의 다중 행동 정보 손실과 새 노출 어휘 범위가 함께 드러난 사례다. 확률 기준만 낮춰도 active_exposure가 없다는 다른 조건은 남는다. 어떤 하나의 임계값만 문제라고 볼 수 없다.

## 4. 정상 문장의 기존 PAUSE 1건

### V51-F03_THEATRE_RESERVATION_FEE-01 — 통상 공동비용 송금: 광범위한 기존 중단 정책을 그대로 보존함

> 기존 공동 장부에 적힌 계좌로 이번 주 안에 입금해 주세요.

기대: `CAUTION, ASK_HUMAN`. 실제: `PAUSE_AND_VERIFY` / `MODEL_DIRECT_ACTION_ADVISORY`. 데이터: `AI36_development`. 주원인 태그: **기존 정책 목표/범위**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | transfer 0.7826, none 0.1441, unclear 0.0522 |
| 기존 7 ID | `q_speech` | direct_request 0.8623, unclear 0.0716, reported_or_quoted 0.0403 |
| 기존 7 ID | `q_scam` | yes 0.0771 / no 0.9229 |
| 기존 7 ID | `q_claim` | yes 0.0265 / no 0.9735 |
| 기존 7 ID | `q_pressure` | yes 0.2952 / no 0.7048 |
| 기존 7 ID | `q_risk` | 최댓값 none 0.3587; high 0.1871 |
| 기존 7 ID | `q_evidence` | yes 0.6806 / no 0.3194 |
| 추가 4 | `q_request_scope` | no_request 0.0302, other_request 0.0409, sensitive_request 0.8062, unclear 0.1227 |
| 추가 4 | `q_current_exposure` | yes 0.0044 / no 0.9956 |
| 추가 4 | `q_payment_anomaly` | yes 0.2094 / no 0.7906 |
| 추가 4 | `q_request_specified` | yes 0.8543 / no 0.1457 |

**확인된 기존 경로:** 작성 라벨은 통상 비용이며 CAUTION 또는 ASK_HUMAN을 허용한다. 모델의 transfer 0.7826, direct_request 0.8623과 입금 anchor는 현재 직접 송금이라는 문장 사실에 맞는다. 기존 정책은 사기/이상성 확률과 무관하게 직접 transfer를 PAUSE_AND_VERIFY로 보내므로 MODEL_DIRECT_ACTION_ADVISORY가 발동했다.

**확인된 추가 규칙:** 신규 q_payment_anomaly=no 0.7906, q_scam=no 0.9229로 이상 징후가 약하다는 정보도 있다. 그러나 baseline_action이 이미 PAUSE이므로 PRESERVE_EXISTING_PAUSE가 가장 먼저 적용된다. 추가 문항은 기존 중단을 해제하는 권한이 없다. 이 과잉 중단은 baseline에도 있던 1건으로 신규 회귀는 아니다.

**해석·다음 확인점:** 모델이 통상 송금을 위험 범죄라고 판정한 것으로 설명하면 부정확하다. 직접 금전 요청이면 멈춘다는 넓은 제품 정책과 정상 상황 허용 라벨 간 차이다. 해결하려면 기존 중단 보존 원칙의 제품 의사결정·안전 평가가 필요하며, 이 보고서에서 해제하지 않는다.

## 5. 잠금 24건의 정상 불필요 ASK 5건

### V51-F14_ANIMAL_TRANSPORT_BOOKING-03 — 결제 완료 알림: no_request는 높지만 기존 발화 최댓값이 reported임

> 예약이 완료되었습니다. 현장에서 추가로 낼 금액은 없습니다.

기대: `NO_STRONG_SIGNAL`. 실제: `ASK_HUMAN` / `MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS`. 데이터: `AI24_locked`. 주원인 태그: **모델 분류/확신 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | none 0.9322, unclear 0.0420, transfer 0.0080 |
| 기존 7 ID | `q_speech` | reported_or_quoted 0.4070, informational 0.3683, unclear 0.1078 |
| 기존 7 ID | `q_scam` | yes 0.0234 / no 0.9766 |
| 기존 7 ID | `q_claim` | yes 0.0130 / no 0.9870 |
| 기존 7 ID | `q_pressure` | yes 0.0146 / no 0.9854 |
| 기존 7 ID | `q_risk` | 최댓값 none 0.4932; high 0.0658 |
| 기존 7 ID | `q_evidence` | yes 0.5316 / no 0.4684 |
| 추가 4 | `q_request_scope` | no_request 0.8960, other_request 0.0245, sensitive_request 0.0460, unclear 0.0336 |
| 추가 4 | `q_current_exposure` | yes 0.0090 / no 0.9910 |
| 추가 4 | `q_payment_anomaly` | yes 0.0433 / no 0.9567 |
| 추가 4 | `q_request_specified` | yes 0.0777 / no 0.9223 |

**확인된 기존 경로:** q_action=none 0.9322는 높다. q_speech는 reported_or_quoted 0.4070, informational 0.3683으로 나뉘어 어떤 발화도 0.70을 넘지 못한다. 기존 경로는 MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS로 보류했다.

**확인된 추가 규칙:** 신규 no_request 0.8960, exposure=no 0.9910, payment_anomaly=no 0.9567 및 두 강요 보조 no가 모두 높고 evidence=no 0.4684는 거부 기준 아래다. 그러나 EXPLICIT_INFORMATION_ONLY는 기존 selected_speech가 정확히 informational이어야 한다. 실제 선택은 reported_or_quoted이므로 해당 조건에서 막힌다.

**해석·다음 확인점:** 새 문항은 현재 요청 부재를 잘 구분했으나, 기존 발화 head에 대한 의존이 정상화 경로에 남아 있다. 단순 none을 모두 정상으로 바꾸는 대신 보고·완료 알림·현재 요청의 구분을 별도 새 평가로 확인할 필요가 있다.

### V51-F16_TRANSLATION_MANUSCRIPT_REVIEW-01 — 문학 속 송금 대사 설명: 발화 확률 분산과 근거 부족 응답

> 등장인물이 상대에게 돈을 보내라고 했다는 설명이 있을 뿐입니다.

기대: `NO_STRONG_SIGNAL, CAUTION`. 실제: `ASK_HUMAN` / `MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS`. 데이터: `AI24_locked`. 주원인 태그: **모델 분류/확신 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | transfer 0.7593, none 0.1781, unclear 0.0468 |
| 기존 7 ID | `q_speech` | informational 0.2768, unclear 0.2468, reported_or_quoted 0.2325 |
| 기존 7 ID | `q_scam` | yes 0.0574 / no 0.9426 |
| 기존 7 ID | `q_claim` | yes 0.0190 / no 0.9810 |
| 기존 7 ID | `q_pressure` | yes 0.0738 / no 0.9262 |
| 기존 7 ID | `q_risk` | 최댓값 none 0.4243; high 0.0901 |
| 기존 7 ID | `q_evidence` | yes 0.2812 / no 0.7188 |
| 추가 4 | `q_request_scope` | no_request 0.8381, other_request 0.0216, sensitive_request 0.0698, unclear 0.0705 |
| 추가 4 | `q_current_exposure` | yes 0.0107 / no 0.9893 |
| 추가 4 | `q_payment_anomaly` | yes 0.0646 / no 0.9354 |
| 추가 4 | `q_request_specified` | yes 0.2397 / no 0.7603 |

**확인된 기존 경로:** q_action=transfer 0.7593은 언급된 행동을 잡았지만 q_speech는 informational 0.2768, unclear 0.2468, reported_or_quoted 0.2325 등으로 분산됐다. 낮은 발화 확률로 MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS가 선택됐다. 원문 report_cue는 True다.

**확인된 추가 규칙:** no_request 0.8381과 노출/이상결제 no가 높고 selected_speech는 informational이다. 하지만 q_evidence=no 0.7188이 강한 근거 부족 기준 0.70 이상이므로 ev_sufficient=False, EXPLICIT_INFORMATION_ONLY가 거짓이다. 현재 규칙에는 이 경우를 독립적인 명확한 인용 CAUTION으로 복구하는 추가 분기가 없다.

**해석·다음 확인점:** 인용의 의미가 명확하다는 작성자 라벨과 모델의 불충분 판단이 충돌한다. 근거 부족 응답을 무시할지 여부는 별도 검증 대상이며, 이 한 사례를 보고 자동으로 거부 조건을 없앨 수 없다.

### V51-F16_TRANSLATION_MANUSCRIPT_REVIEW-02 — 인용문 뒤 맞춤법 요청: 문장 전체 금전 어휘가 정상 요청을 가림

> “돈을 보내라”를 실행할 필요는 없고, 그 문장의 띄어쓰기만 확인해 주세요.

기대: `NO_STRONG_SIGNAL`. 실제: `ASK_HUMAN` / `MODEL_NONE_BUT_ACTION_TERMS_PRESENT`. 데이터: `AI24_locked`. 주원인 태그: **모델+어휘 혼합**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | none 0.8369, transfer 0.0996, unclear 0.0507 |
| 기존 7 ID | `q_speech` | direct_request 0.4381, unclear 0.2015, informational 0.1773 |
| 기존 7 ID | `q_scam` | yes 0.0677 / no 0.9323 |
| 기존 7 ID | `q_claim` | yes 0.0349 / no 0.9651 |
| 기존 7 ID | `q_pressure` | yes 0.0753 / no 0.9247 |
| 기존 7 ID | `q_risk` | 최댓값 low 0.3521; high 0.0722 |
| 기존 7 ID | `q_evidence` | yes 0.3930 / no 0.6070 |
| 추가 4 | `q_request_scope` | no_request 0.3129, other_request 0.4503, sensitive_request 0.1094, unclear 0.1275 |
| 추가 4 | `q_current_exposure` | yes 0.0177 / no 0.9823 |
| 추가 4 | `q_payment_anomaly` | yes 0.0798 / no 0.9202 |
| 추가 4 | `q_request_specified` | yes 0.6357 / no 0.3643 |

**확인된 기존 경로:** q_action=none 0.8369, q_speech=direct_request 0.4381이다. 문장 전체의 돈을 보내가 action_mentioned=True로 잡혀 MODEL_NONE_BUT_ACTION_TERMS_PRESENT가 먼저 발동했다. 기존 절 분리는 이 인용과 편집 요청을 분리하지 않고, report/warning 단서도 잡지 못해 해당 절을 clean_imperative=True로 취급한다.

**확인된 추가 규칙:** 신규 other_request가 최댓값이지만 0.4503으로 낮고, q_request_specified=yes 0.6357도 기준 미만이다. 두 일반 요청 선택 경로가 모두 막힌다. 여기에 문장 전체 payment_context=True와 action_mentioned=True도 EXPLICIT_OTHER_REQUEST의 추가 금지 조건이다. 노출/이상결제 no와 evidence 조건은 통과했다.

**해석·다음 확인점:** 모델의 일반 요청 확신 부족과 인용 범위를 무시한 전역 어휘 금지가 함께 있다. q_request_specified 확률만 올려도 전역 금전 조건이 그대로 남으므로 문항 하나만의 해결책으로 환원할 수 없다.

### V51-F18_ONLINE_MUSIC_LESSON_RECOVERY-02 — 화면 상태 확인: 일반 질문을 불명확 발화로 분류함

> 박자 표시가 한 줄로 보이는지 두 줄로 보이는지 알려 주세요.

기대: `NO_STRONG_SIGNAL`. 실제: `ASK_HUMAN` / `MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS`. 데이터: `AI24_locked`. 주원인 태그: **모델 분류/확신 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | none 0.7257, unclear 0.2284, remote_install 0.0147 |
| 기존 7 ID | `q_speech` | unclear 0.6104, informational 0.2123, direct_request 0.0884 |
| 기존 7 ID | `q_scam` | yes 0.0140 / no 0.9860 |
| 기존 7 ID | `q_claim` | yes 0.0532 / no 0.9468 |
| 기존 7 ID | `q_pressure` | yes 0.0728 / no 0.9272 |
| 기존 7 ID | `q_risk` | 최댓값 none 0.3621; high 0.1949 |
| 기존 7 ID | `q_evidence` | yes 0.5179 / no 0.4821 |
| 추가 4 | `q_request_scope` | no_request 0.3836, other_request 0.3267, sensitive_request 0.0209, unclear 0.2689 |
| 추가 4 | `q_current_exposure` | yes 0.0099 / no 0.9901 |
| 추가 4 | `q_payment_anomaly` | yes 0.0531 / no 0.9469 |
| 추가 4 | `q_request_specified` | yes 0.4931 / no 0.5069 |

**확인된 기존 경로:** q_action=none 0.7257은 기준 이상이지만 q_speech=unclear 0.6104라 MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS로 보류했다. 실제 어휘 request_cue=True이며 금전·노출 문맥은 없다.

**확인된 추가 규칙:** 신규 q_request_scope도 no_request 0.3836, other_request 0.3267, unclear 0.2689로 분산됐다. q_request_specified=yes 0.4931도 낮다. 일반 요청 경로는 선택 라벨과 확신 조건에서 막히고, 정보 알림 경로도 no_request>=0.70 및 informational 조건을 만족하지 못한다. 노출/이상결제 no와 evidence 조건은 모두 통과했다.

**해석·다음 확인점:** 어휘 규칙이 정상 요청을 위험 어휘로 오해한 사례라기보다, 질문/답장 요구의 범위를 모델이 충분히 확신하지 못한 사례다. 요청 자체가 없다고 봐야 하는지, 민감하지 않은 요청인지의 구분을 더 안정적으로 평가할 필요가 있다.

### V51-F20_WINTER_RESPONSE_CENTER-03 — 개인정보를 보낼 필요 없다는 부정문: 전역 민감어 금지가 남음

> 문장 번호만 표시해 주세요. 비용이나 개인정보를 보내실 일은 없습니다.

기대: `NO_STRONG_SIGNAL`. 실제: `ASK_HUMAN` / `MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS`. 데이터: `AI24_locked`. 주원인 태그: **어휘/문맥 규칙 제약**.

| 구분 | 질문 | 이번 11문항 응답의 핵심 확률 |
|---|---|---|
| 기존 7 ID | `q_action` | unclear 0.4987, none 0.4719, personal_data 0.0104 |
| 기존 7 ID | `q_speech` | direct_request 0.7258, unclear 0.1006, informational 0.1001 |
| 기존 7 ID | `q_scam` | yes 0.0281 / no 0.9719 |
| 기존 7 ID | `q_claim` | yes 0.0733 / no 0.9267 |
| 기존 7 ID | `q_pressure` | yes 0.0644 / no 0.9356 |
| 기존 7 ID | `q_risk` | 최댓값 none 0.3359; high 0.1416 |
| 기존 7 ID | `q_evidence` | yes 0.3222 / no 0.6778 |
| 추가 4 | `q_request_scope` | no_request 0.1145, other_request 0.7966, sensitive_request 0.0244, unclear 0.0645 |
| 추가 4 | `q_current_exposure` | yes 0.0089 / no 0.9911 |
| 추가 4 | `q_payment_anomaly` | yes 0.0582 / no 0.9418 |
| 추가 4 | `q_request_specified` | yes 0.7974 / no 0.2026 |

**확인된 기존 경로:** 기존 action은 unclear 0.4987와 none 0.4719로 나뉘어 MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS가 선택됐다. direct_request 0.7258은 높다.

**확인된 추가 규칙:** 새 other_request 0.7966, specified=yes 0.7974는 모두 기준 이상이다. 노출=no 0.9911, 이상결제=no 0.9418, 사기/강요 no, evidence=no 0.6778도 일반 요청 정상화 조건에 맞는다. 그러나 전체 문장의 개인정보 때문에 exposure_context=True가 되어 EXPLICIT_OTHER_REQUEST가 거짓이다. 기존 warning 패턴은 보내실 일은 없습니다를 잡지 못해 후반 절을 active exposure로 남긴다. 강한 exposure=no 덕분에 잘못된 PAUSE는 막았지만, 정상화도 막혔다.

**해석·다음 확인점:** 새 모델 정보는 일반 요청과 노출 부재를 충분히 구분했는데, 문장 전체에 민감어가 있으면 정상화하지 않는 규칙이 상쇄한다. 부정 범위를 다루는 정책 경계가 주된 병목으로 보인다. 잠금 문구만 사전에 넣어 예외 처리하지 않았다.

## 6. 화면의 경고 예시가 계속 보류된 이유와 확인 한계

[실브라우저 경고 예시 기록](../internal/evidence/v51/browser/desktop_warning.txt)의 입력은 “은행 직원도 인증번호를 요구하지 않습니다. OTP는 누구에게도 알려주지 마세요.”다. 화면은 실제 조로 경로에서 `ASK_HUMAN`, “모델의 확신이 기준보다 낮거나 판단을 보류했어요”, `secrecy / negated_or_warning · 확신 0.83`을 표시했다. 표시 근거는 2개 후보 구간 중 1개만 가능하며 일부 확인 불가라고 알렸다. 이 예시는 위 158쌍 데이터의 별도 추가 점수로 합산하지 않는다.

**확인된 사실:** [apps/web/app.js](../apps/web/app.js)의 모델 답 출력(작성 시 390행)은 `action_probability`만 소수 둘째 자리로 보여 준다. 따라서 0.83은 모든 11문항을 종합한 판단 확신이 아니다. 보류에는 speech 확률, 질문 간 충돌, 새 요청 범위, 근거 거부 등 다른 조건이 관여할 수 있다. 경고임을 표시하는 밑줄도 표시용 어휘 문맥이며 판단을 해제하는 권한이 없다.

**미확인:** 이 브라우저 스냅샷에는 해당 11문항 전체 raw/trace가 없으므로 어느 신규 조건이 마지막으로 false였는지 수치까지 복원할 수 없다. 다른 화면의 trace를 이 예시의 응답으로 대체하거나 새 모델 호출로 과거 원인을 추정하지 않았다. 따라서 “확률 0.83인데 버그로 보류됐다”, “특정 새 문항이 틀렸다”는 결론은 하지 않는다.

**UI 후속 과제:** 단일 action 확률을 전체 ‘확신’으로 오해하지 않도록 이름과 적용 범위를 명확히 하고, 실제로 적용된 보류 조건을 trace에서 설명하는 것이 필요하다. 다만 설명 개선만으로 현재 ASK 판정이 해결되는 것은 아니다. 이번 문서 작업에서는 UI를 수정하지 않았다.

## 7. 표시 근거의 개선과 남은 한계

[표시 품질 집계](../internal/evidence/v51/full_pipeline_validation/evidence_display_quality.json)에서 후보 158문장 중 빈 입력 1개를 제외한 157개는 AVAILABLE 35, PARTIAL 13, UNAVAILABLE 88, NOT_APPLICABLE 21이다. 표시가 하나라도 있는 문장은 48/157개다. 어휘 후보절 163개 중 52개를 표시(31.9%), 111개는 표시 불가(68.1%)였다. 기존 decision evidence span은 19개였으며 9개를 확장 표시하고 10개는 표시하지 않았다. invalid upstream span은 0개다.

표시 52개 모두 원문 Unicode code point 시작·끝·인용 문자열이 일치했다. 표시 전후 157건의 action/reason/message와 원래 execution evidence trace는 바뀌지 않았다. **좌표가 맞다는 사실이 의미가 맞다는 뜻은 아니다.** 개발36 AI 주석의 문자 범위 중 표시가 덮은 비율은 38.5%, 잠금24는 32.5%였다. 반대로 표시 문자가 AI 주석 안에 들어간 비율은 각각 71.3%, 66.3%였다. 주석 키는 `evidence[]`의 `start_cp/end_cp/quote`이며 독립 인간 gold가 아니다.

절을 통째로 보여 주면서 좁은 주석보다 넓게 강조하는 사례도 있다. 개발 `V51-F06_PRINTER_SERVICE_CONTRAST-02`에서는 앞의 원격 앱 설치 경고까지 함께 보여 AI 주석 밖 33 code point를 포함했다. 잠금 `V51-F14_ANIMAL_TRANSPORT_BOOKING-01`에서는 예약금 요청 앞의 비용·날짜 대조 문맥까지 보여 주석 밖 35 code point가 포함됐다. 이런 확장은 설명에 도움이 될 수도, 핵심 행동을 흐릴 수도 있으므로 의미 정확도는 `NOT_INDEPENDENTLY_EVALUATED`로 남긴다.

## 8. 중간 해석 계층은 이미 있고, 별도 LLM 서버가 필수라는 증거는 없음

현재 기본 모델 경로는 다음과 같다.

```text
한 문장의 Zoro 11개 typed 응답
  → 프로필·질문 순서·응답 schema/binding 검증
  → 기존 7개 ID로 legacy 판단
  → 추가 4개 응답과 독립 원문 단서를 이용한 v5.1 규칙 해석
  → 표시용 근거 확장(판정 변경 없음)
  → 사용자 검토·오프라인 LinkGuard
  → 현재 문장 결과
  → Arena에서만 이전 위험 유지/세션 상태 적용
```

이 중간 계층은 [integration/v51.py](../integration/v51.py), [integration/v51_policy.py](../integration/v51_policy.py)와 대응하는 [v51-contract.js](../apps/shared/v51-contract.js), [v51-semantic.js](../apps/shared/v51-semantic.js)에 구현돼 있다. 별도 생성형 LLM이 사유를 읽고 다시 결론을 만드는 구조가 아니다. 추가 4개 필드는 현재 요청 범위, 민감정보/원격 노출, 이상 결제, 요청 구체성 정보를 더 받는 것이다. 학습된 새 신경망 head를 추가했다는 뜻도 아니다. 가중치 미세조정·재학습은 수행하지 않았다. DRA 비교는 검증된 원래 7문항 프로필에 묶여 있으며 새 11문항 raw를 그대로 보내지 않는다.

현재 실패 중에는 정보가 이미 충분한데 사전/범위 규칙이 막는 사례가 있으므로, 모든 문제를 추가 LLM 호출로 해결해야 한다고 볼 근거가 없다. 별도 middleware 프로세스가 필요한지보다 동일 의미 계약과 trace를 유지하면서 어디에서 정보가 손실되는지 먼저 확인해야 한다. 더 복잡한 의미 해석이 필요하다는 가설은 남지만, 별도 LLM 서버의 효과·비용·오류·기존 위험 해제 가능성에 대한 비교 실험은 하지 않았다.

보정은 여전히 미확립이다. 로컬 모델 서버 설정의 temperature 1.52는 관찰한 실행 설정이며 이 플랫폼에서 위험 확률을 새로 보정했다는 증거가 아니다. 0.70도 현재 정책 기준이며 독립 검증된 안전 경계로 주장하지 않는다.

## 9. 관측된 지연 비용과 측정하지 않은 부분

저장된 실제 비어 있지 않은 요청은 각 arm 157회다. 이미 올라와 있던 로컬 GPU 서버의 warm ModelClient 지연에서 baseline7의 p50/p95는 **145.3 / 156.608 ms**, candidate11은 **275.9 / 289.008 ms**였다. p50 차이는 약 130.6 ms, 비율은 약 1.90배다. 질문을 늘린 후보에서 더 긴 요청 지연이 관측된 비용을 공개한다.

다만 프로필 실행 순서와 prefix cache 상태가 섞였고 무작위화되지 않았다. 이 수치만으로 차이 전부를 질문 4개 때문이라고 인과적으로 단정할 수 없다. GPU cold start, 동시 요청 부하, 브라우저 전체 지연, 단계별 병목은 별도로 측정하지 않았다. 기존 서버 프로세스 재시작 시험도 상주 Zoro 모델의 cold start 시험이 아니다. 별도 LLM middleware 추가 호출은 0회다. 따라서 사용자 체감이 느린 원인을 이번 측정만으로 확정하지 않는다. 근거 파일: `deliverables/v51_implementation_20261104/latency_summary.json`(원본 작업공간 기록).

## 10. 다음 실험의 경계

현재 잠금24는 결과를 열어 원인을 분석했으므로 앞으로 새 후보를 고르는 미열람 검증셋으로 재사용할 수 없다. 기존 158문장은 알려진 회귀·진단 세트로 보존한다. 다음 버전은 **새로 모집한 사람이 서로 보지 않고 작성·판정한 fresh blind 세트**와 사전 등록한 채택 조건으로 검증해야 한다. 후보 선택·문항/정책 튜닝에 쓰는 개발 자료와 마지막 검증 자료도 분리해야 한다.

우선 검증할 가설은 다음과 같다. 여기 적힌 것은 구현 승인이나 성능 보장이 아니다.

1. 명시된 금액과 인증 수단을 문자열 목록만으로 찾을 때 생기는 누락을 줄일 수 있는가. 일회용 코드의 여러 표현·복합 금액·부정/인용 대조쌍을 새로 만들고, 독립 근거 없는 모델 단독 중단도 함께 측정한다.
2. 한 문장 안에서 과거 인용·금지·현재 직접 요구를 분리하면 전역 어휘 금지 때문에 생기는 정상 보류가 줄어드는가. 현재 요구가 뒤에 새로 등장하는 위험 문장을 반드시 함께 검증한다.
3. 일반 답장·편집 요청, 완료 알림, 요청 없음의 문항 분류가 새 상황에서도 일관적인가. 근거 부족 head나 기존 speech head의 조건을 바꾼다면 한 번에 한 가설로 분리해 검증한다.
4. 통상 송금과 이상 송금의 안내 수준을 구분할 것인가. 이는 기존 PAUSE 보존 규칙과 제품 안전 목표에 대한 결정이며, 사용자 확인 보고만으로 위험을 해제하는 기능과 섞지 않는다.
5. 모든 후보에서 위험/불명 NSS, 필수중단 누락, 정상 PAUSE, 허용 결과 손실, 불필요 보류, 표시 범위·누락, 단계별 지연을 함께 공개한다. 정확도나 정상화율 하나만 보고 채택하지 않는다.

## 11. 재현 자료와 코드 위치

- 실제 raw: [개발 후보 응답](../internal/evidence/v51/experiments/stage5_specified_candidate/specified_raw.jsonl), [잠금 후보 응답](../internal/evidence/v51/experiments/stage7_locked_validation24/specified_raw.jsonl). 개발 후보 응답은 stage5에서 받았지만 현재 판정 비교 기준은 **v4로 재처리한 stage6**이며, 폐기된 v3 판정을 현재 결과로 쓰지 않았다.
- 최종 정책 원기록: [stage6](../internal/evidence/v51/experiments/stage6_final_policy_replay/specified_results.jsonl), [stage7](../internal/evidence/v51/experiments/stage7_locked_validation24/specified_results.jsonl).
- 라벨·데이터 hash·질문 묶음은 각 stage의 `protocol.json`에 있다. 전체 재처리 결과의 `input_sha256`와 `manifest_fingerprint`로 입력·정책 출처를 확인할 수 있다.
- [기존 모델 bridge](../vendor/dmsg/prototype/model_bridge.py): 작성 시 58–64행 anchor, 118–140행 충돌/낮은 확률/정보 알림 우선순위, 163–187행 anchor 및 직접 송금 중단·근거 부족 규칙.
- [현재 v5.1 정책](../integration/v51_policy.py): 작성 시 16–17행 active 절, 34–44행 금전/노출, 45–66행 일반/정보/경고 정상화 조건, 70–76행 기존 PAUSE 보존과 순차 적용.
- [현재 규칙 사전](../configs/v51_semantic_rules.json), [문맥 어휘·절 분리](../vendor/dmsg/prototype/context_guard.py), [표시 전용 근거](../integration/v51_evidence.py).

이 문서의 상세 11사례는 전체 잔여 오답의 완전 목록이 아니라 요청된 필수중단 누락·정상 PAUSE·잠금 정상 과보류의 목록이다. 개발 세트의 다른 정상 보류 사례도 전체 결과 JSON에 남아 있다. 추가 학습 없이 보고서를 작성했다는 사실과, 앞으로 충분한 성능이 보장된다는 주장은 구분한다.
