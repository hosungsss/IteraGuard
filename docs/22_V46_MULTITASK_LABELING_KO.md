# 22. v4.6 다중 과제 라벨링 기준

각 문장에 다섯 과제를 독립적으로 붙인다. 하나의 softmax로 모든 것을 고르게 하지 않는다. 사기 여부는 라벨이 아니다.

## A. 화행 (단일 선택)
| 라벨 | 기준 |
|---|---|
| DIRECT_REQUEST | 읽는 사람에게 행동을 직접 시킨다 ("보내 주세요", "추가해 주세요") |
| INDIRECT_REQUEST | 의문·조건·필요성 형식으로 행동을 유도한다 ("보내줄 수 있어?", "~하셔야 진행됩니다") |
| INFORMATIONAL | 사실을 알리거나 서술한다. 행동 요구가 문면에 없다 |
| WARNING_OR_NEGATION | 하지 말라고 한다 |
| QUOTATION_OR_REPORT | 다른 사람의 말·요구를 전하거나 묻는다 |
| UNKNOWN | 학습 라벨로 쓰지 않는다. 모든 과제 점수가 낮으면 추론 시 표시 |

## B. 의도 (단일 선택, 우선순위: 인증정보 > 금전 > 접촉 > 사칭 > 광고 > 일상 요청 > 일반)
ORDINARY_INFORMATION · LEGITIMATE_REQUEST · COMMERCIAL_PROMOTION · CONTACT_SOLICITATION · PAYMENT_SOLICITATION · CREDENTIAL_SOLICITATION · IMPERSONATION_CLAIM. 정상 광고(수신거부·공식 경로 안내)와 원치 않는 광고·연락 유도는 의도가 같아도(광고) 위험 신호로 구분한다.

## C. 위험 신호 (다중 선택, 없으면 NONE_OBSERVED)
| 라벨 | 붙이는 경우 | 붙이지 않는 경우 |
|---|---|---|
| OFF_PLATFORM_CONTACT | 낯선 상대가 다른 메신저 ID로 옮기라고 함 | 지인이 "라인으로 사진 보냈어" |
| UNVERIFIED_IDENTITY | 처음 연락·자기소개·해외발신 표시와 함께 신원을 확인할 수 없음 | 기존 관계가 문면에 분명함 |
| URGENCY_OR_PRESSURE | 오늘 마감·즉시·서두름 | 일반 일정 안내 |
| FINANCIAL_INDUCEMENT | 고수익·사례비·지원금·부업 | 정상 할인 광고 |
| CREDENTIAL_REQUEST | 비밀번호·인증번호·계정 요구 | "비밀번호가 변경되었습니다" 알림 |
| ACCOUNT_CHANGE_REQUEST | 입금 계좌 변경 | — |
| IMPERSONATION_SIGNAL | 기관·가족·회사 사칭 정황 | 실제 거래 알림 |
| MALICIOUS_LINK_SUSPICION | 출처 불명 단축·유사 도메인 링크 | 단톡방 투표 링크 |
| UNWANTED_SOLICITATION | 원치 않는 만남·친구·투자 권유 | 동창회 공지 |

경고·인용 문장에는 원칙적으로 위험 신호를 붙이지 않는다(인용 대상에 메신저 이동이 명시되면 OFF_PLATFORM_CONTACT만 예외).

## D. 요구 행동 (단일 선택)
MONEY_TRANSFER · CREDENTIAL_DISCLOSURE · PERSONAL_DATA_DISCLOSURE · INSTALL_APPLICATION · CLICK_LINK · MOVE_TO_EXTERNAL_MESSENGER · CONTACT_UNKNOWN_PERSON · NO_EXPLICIT_ACTION. **NO_EXPLICIT_ACTION은 "위험한 범주의 행동을 명시적으로 요구하지 않음"이며 안전을 뜻하지 않는다.**

## E. 불확실성 (추론 시 산출)
모든 과제 최고 점수 < 0.4 → LOW_TASK_CONFIDENCE. 화행이 경고·인용인데 위험 요구 행동 점수 ≥ 0.6 → SPEECH_VS_REQUESTED_ACTION. 위험 의도·요구 행동 점수 ≥ 0.6인데 최종 결과가 NO_STRONG_SIGNAL → ASK_HUMAN(CROSS_TASK_RISK_NOT_CLEARED).

## 분할과 오염 방지
- 템플릿 계열(family) 단위로 학습/보정/잠금 분할.
- 손으로 쓴 잠금셋(v1, v2, v4.6 W)과 문자 3-gram Jaccard ≥ 0.5인 생성 문장은 모든 분할에서 제거(255개).
- 모델 예측을 라벨로 재사용하지 않는다.
- 주석자는 1명(개발자)이다. 독립 주석자 2인 표본 검토는 미실시 → 팀원 블라인드 작성이 다음 과제.
