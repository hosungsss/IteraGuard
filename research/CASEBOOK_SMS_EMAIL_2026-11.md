# 공식 스미싱·피싱·BEC 공격 유형 근거집 (2026-11-19)

**검증 구분:** 이 문서는 KISA·FTC·FBI가 실제 경고한 **공격 유형**을 정리합니다. 아래 메시지는 기관에 접수된 원문이 아니라 공개 권고를 기반으로 연구용으로 작성한 **합성 재구성 예시**입니다. 실제 피해자 메시지를 원문 채집했다고 주장하지 않습니다.

**자료 범위:** 기관 경고문 23개, 서로 다른 합성 문장 34개(공격·사회공학 유형 28건, 경고·과거인용 등 대조 6건). 인터넷 전체의 모든 문자·이메일 사례가 아니며, 표본 대표성이나 독립 레이블이 아닙니다. 실제 개인·금융정보, 작동하는 악성 URL은 포함하지 않습니다.

**학습 상태: NOT_TRAINED.** Zoro-1의 가중치·결정 헤드는 이번 수집으로 변경되지 않습니다. 사례는 차후 주석 검토 및 사전등록 실험의 개발/학습 후보로만 사용하십시오. 이 사례를 검증용 잠금 데이터와 섞으면 오염입니다. 상업적 모델 학습을 위한 외부 출처의 재이용 라이선스는 별도 확인해야 합니다.

## 유형별 합성 사례 및 검토 가이드

| ID | 채널 | 공식 자료에 보고된 사기 유형 | 연구용 합성 문장 | 예비 화행 분류 | 공식 근거 |
|---|---|---|---|---|---|
| K-SMS-01 | SMS | 택배 주소 오류 | 배송 주소가 달라 배송이 보류되었습니다. [안전하지 않은 링크 생략]에서 수정하세요. | CURRENT_SENSITIVE_REQUEST | [KISA-01](#kisa-01) |
| K-SMS-02 | SMS | 부고장 앱 설치 | 지인의 부고 안내입니다. 모바일 부고장 보기를 누르고 앱 설치를 진행해 주세요. | CURRENT_SENSITIVE_REQUEST | [KISA-01](#kisa-01) |
| K-SMS-03 | SMS | 가짜 청첩장 | 동창의 모바일 청첩장입니다. 행사 확인을 위해 앱 설치가 필요합니다. | CURRENT_SENSITIVE_REQUEST | [KISA-02](#kisa-02) |
| K-SMS-04 | SMS | 과태료 납부 | 교통 범칙금 미납 안내입니다. 본인확인을 위해 링크에 인증번호를 입력해 주세요. | CURRENT_SENSITIVE_REQUEST | [KISA-03](#kisa-03) |
| K-SMS-05 | SMS | 고유가 지원금 사칭 | 지원금 신청 기한이 오늘 끝납니다. 정부24 확인용 PDF 뷰어 앱을 설치해 주세요. | CURRENT_SENSITIVE_REQUEST | [KISA-04](#kisa-04) |
| K-SMS-06 | SMS | 메신저 계정 탈취 | 메신저 계정이 정지됩니다. 받은 인증코드를 복사하여 이 채팅으로 보내주세요. | CURRENT_SENSITIVE_REQUEST | [KISA-05](#kisa-05) |
| K-SMS-07 | SMS | 카드 계정 검증 | 카드 사용이 제한되었습니다. 안내된 링크에서 카드번호와 비밀번호를 확인해 주세요. | CURRENT_SENSITIVE_REQUEST | [KISA-06](#kisa-06) |
| K-MAIL-08 | EMAIL | 공공기관 이용정지 사칭 | [긴급] 공공기관 이용정지 예정. 유예 신청을 위해 지금 링크에서 인증번호를 입력해 주세요. | CURRENT_SENSITIVE_REQUEST | [KISA-07](#kisa-07) |
| K-MAIL-09 | EMAIL | 수사기관 출석 요구 | 귀하는 금융사기 사건 조사대상입니다. 출석요구서 파일을 내려받아 앱을 설치해 제출하세요. | CURRENT_SENSITIVE_REQUEST | [KISA-07](#kisa-07) |
| K-MAIL-10 | EMAIL | 개인정보 보상금 | 개인정보 유출 피해 보상 대상입니다. 보상 신청 링크에서 계좌와 비밀번호를 입력하세요. | CURRENT_SENSITIVE_REQUEST | [KISA-07](#kisa-07) |
| K-SMS-11 | SMS | 코인 보상금 사칭 | 가상자산 보상금이 지급됩니다. 복구를 위해 지갑 복구 문구를 입력하세요. | CURRENT_SENSITIVE_REQUEST | [KISA-08](#kisa-08) |
| K-MAIL-12 | EMAIL | 큐싱 로그인 유도 | 설문 참여를 위해 첨부된 QR코드를 촬영하고 SNS 계정으로 로그인하세요. | CURRENT_SENSITIVE_REQUEST | [KISA-09](#kisa-09) |
| K-SMS-13 | SMS | OTT 유출 사고 사칭 | OTT 개인정보 유출 보상 신청이 열렸습니다. 링크에서 본인정보를 등록하세요. | CURRENT_SENSITIVE_REQUEST | [KISA-10](#kisa-10) |
| US-SMS-14 | SMS | 배송 재결제 | 소포 배송에 문제가 발생했습니다. 재배송 수수료를 결제해 주세요. | CURRENT_SENSITIVE_REQUEST | [FTC-01](#ftc-01) |
| US-SMS-15 | SMS | 온라인 작업 부업 | 집에서 리뷰 업무를 하면 수익을 드립니다. 수익을 출금하려면 예치금부터 보내세요. | CURRENT_SENSITIVE_REQUEST | [FTC-01](#ftc-01) |
| US-SMS-16 | SMS | 가짜 은행 보안 문자 | 계좌에서 이상 결제가 감지됐습니다. 예방을 위해 다른 안전 계좌로 자금을 이체하세요. | CURRENT_SENSITIVE_REQUEST | [FTC-01](#ftc-01) |
| US-SMS-17 | SMS | 통행료 미납 | 고속도로 통행료가 미납됐습니다. 오늘 중 링크를 열고 카드 정보로 납부해 주세요. | CURRENT_SENSITIVE_REQUEST | [FTC-02](#ftc-02) |
| US-SMS-18 | SMS | 잘못 보낸 문자 신뢰유도 | 안녕하세요, 약속 장소를 잘못 보낸 것 같네요. 혹시 대화를 이어가실래요? | SOCIAL_ENGINEERING_CONTACT | [FTC-01](#ftc-01) |
| US-MAIL-19 | EMAIL | 허위 청구서 | 미지급 청구서가 발생했습니다. 첨부 양식을 열고 새로운 결제정보를 등록해 주세요. | CURRENT_SENSITIVE_REQUEST | [FTC-03](#ftc-03) |
| US-MAIL-20 | EMAIL | 가짜 초대장 | 모임 초대장이 도착했습니다. 초대장을 열려면 이메일 로그인 정보와 코드를 입력해 주세요. | CURRENT_SENSITIVE_REQUEST | [FTC-04](#ftc-04) |
| US-MAIL-21 | EMAIL | 공급업체 계좌 변경 BEC | 이번 공급대금부터 수취 계좌가 변경되었습니다. 기존 계좌 대신 새 계좌로 오늘 송금 바랍니다. | CURRENT_SENSITIVE_REQUEST | [FBI-01](#fbi-01) |
| US-MAIL-22 | EMAIL | 지자체 허가 수수료 사칭 | 건축 허가 심사 비용을 지급해야 합니다. 안내된 외부 계좌로 수수료를 입금하세요. | CURRENT_SENSITIVE_REQUEST | [FBI-02](#fbi-02) |
| US-MAIL-23 | EMAIL | OAuth 문서 동의 피싱 | 요청하신 기사 원고를 검토해 주세요. 공유 문서 접근 권한에 동의해야 열람됩니다. | CURRENT_SENSITIVE_REQUEST | [FBI-03](#fbi-03) |
| US-MAIL-24 | EMAIL | 직원 급여 포털 사칭 | 급여 명세서 확인을 위해 직원 셀프서비스 페이지에 다시 로그인하세요. | CURRENT_SENSITIVE_REQUEST | [FBI-05](#fbi-05) |
| US-SMS-25 | SMS | FBI IC3 사칭 환불 | 사기 피해 복구 담당자입니다. 피해금 반환을 위해 신청 수수료를 먼저 납부하세요. | CURRENT_SENSITIVE_REQUEST | [FBI-06](#fbi-06) |
| US-MAIL-26 | EMAIL | 정부기관 조사 사칭 | 법 집행기관의 조사 대상입니다. 오늘까지 수사 협조비를 납부하지 않으면 처벌됩니다. | CURRENT_SENSITIVE_REQUEST | [FBI-07](#fbi-07) |
| US-MAIL-27 | EMAIL | 클라우드 이메일 침해 BEC | 평소 거래처 담당자입니다. 결제 계좌가 바뀌어 정산을 새 계좌로 부탁드립니다. | CURRENT_SENSITIVE_REQUEST | [FBI-08](#fbi-08) |
| US-SMS-28 | SMS | 고위 공무원 사칭 | 공식 정책 회의 담당자입니다. 부서 연결을 위해 비공개 문서를 메신저로 전달하세요. | CURRENT_SENSITIVE_REQUEST | [FBI-04](#fbi-04) |
| CTRL-29 | SMS | 예방 경고 | 보안 공지: 인증번호를 누구에게도 보내지 마세요. 이상하면 공식 번호로 확인하세요. | PROTECTIVE_WARNING | [KISA-05](#kisa-05) |
| CTRL-30 | EMAIL | 과거 요청 인용 | 어제 거래처가 새 계좌로 보내 달라고 했는데, 아직 확인하지 않았습니다. | PAST_REPORT_NOT_CURRENT_REQUEST | [FBI-01](#fbi-01) |
| CTRL-31 | EMAIL | 정상 정산 진행보고 | 오늘의 정산내역은 이전과 같습니다. 새 계좌로 송금하라는 안내는 없습니다. | ORDINARY_INFORMATION | [FBI-01](#fbi-01) |
| CTRL-32 | SMS | 링크 없는 일정 | 내일 11시에 회의실에서 회의를 시작합니다. 자료는 미리 준비해 주세요. | ORDINARY_INFORMATION | [FTC-03](#ftc-03) |
| CTRL-33 | EMAIL | 주의 공지에 공격 구문 인용 | 이메일 보안 교육입니다. '송금하세요'라는 문구가 오면 실제 송금하기 전에 거래처 대표번호로 확인하세요. | PROTECTIVE_WARNING | [FBI-01](#fbi-01) |
| CTRL-34 | SMS | 과거 사칭 사례 설명 | 최근 가짜 범칙금 납부 링크가 돌았다는 소식을 들었습니다. 주소는 클릭하지 마세요. | PAST_REPORT_NOT_CURRENT_REQUEST | [KISA-03](#kisa-03) |

## 공식 출처 목록과 정확한 해석

<a id="kisa-01"></a>
**KISA-01 · KISA — 스미싱 관련 118 상담 민원 사례 — 택배 및 부고**

- 원문: https://boho.or.kr/kr/bbs/view.do?bbsId=B0000030&menuNo=205027&nttId=71280
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-02"></a>
**KISA-02 · KISA — 청첩장 등 지인 사칭 스미싱 주의 권고**

- 원문: https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71676
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-03"></a>
**KISA-03 · KISA — 과태료, 범칙금 등 행정처분 스미싱 주의 권고**

- 원문: https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71846
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-04"></a>
**KISA-04 · KISA — 고유가 지원금 사칭 스미싱·피싱**

- 원문: https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=72060
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-05"></a>
**KISA-05 · KISA — 계정 탈취 유형 스미싱·피싱 주의 권고 (2026-07)**

- 원문: https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=72139
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-06"></a>
**KISA-06 · KISA — 특정 카드사 사칭 스미싱 주의 권고**

- 원문: https://boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=72131
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-07"></a>
**KISA-07 · KISA — 공공기관 사칭 해킹메일을 통한 악성 앱 유포**

- 원문: https://www.krcert.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=72202
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-08"></a>
**KISA-08 · KISA — 코인 지갑 보상금 사칭 스미싱 주의**

- 원문: https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205023&nttId=72219
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-09"></a>
**KISA-09 · KISA — QR코드 촬영 유도 큐싱 주의 권고**

- 원문: https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205021&nttId=71936
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="kisa-10"></a>
**KISA-10 · KISA — OTT 플랫폼 개인정보 유출 사고 악용 스미싱**

- 원문: https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205021&nttId=72078
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="ftc-01"></a>
**FTC-01 · FTC — Top Text Message Scams of 2024 (2025 report)**

- 원문: https://www.ftc.gov/news-events/news/press-releases/2025/04/new-ftc-data-show-top-text-message-scams-2024-overall-losses-text-scams-hit-470-million
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="ftc-02"></a>
**FTC-02 · FTC — Got a text about unpaid tolls?**

- 원문: https://consumer.ftc.gov/consumer-alerts/2025/01/got-text-about-unpaid-tolls-its-probably-scam
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="ftc-03"></a>
**FTC-03 · FTC — Protect yourself from phishing scams**

- 원문: https://consumer.ftc.gov/consumer-alerts/2025/04/protect-yourself-phishing-scams
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="ftc-04"></a>
**FTC-04 · FTC — Fake party invite asks for email login**

- 원문: https://consumer.ftc.gov/consumer-alerts/2026/05/asked-enter-your-email-address-and-password-open-party-invite-thats-scam
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="ftc-05"></a>
**FTC-05 · FTC — Run a small business? Pay your bills, not scammers**

- 원문: https://consumer.ftc.gov/consumer-alerts/2026/05/run-small-business-pay-your-bills-not-scammers
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-01"></a>
**FBI-01 · FBI IC3 — Business Email Compromise**

- 원문: https://www.ic3.gov/CrimeInfo/BEC
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-02"></a>
**FBI-02 · FBI IC3 — Government planning/zoning permit phishing emails (2026-03)**

- 원문: https://www.ic3.gov/PSA/2026/PSA260309
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-03"></a>
**FBI-03 · FBI IC3 — OAuth consent phishing via emails or personal messages (2026-09)**

- 원문: https://www.ic3.gov/PSA/2026/PSA260901
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-04"></a>
**FBI-04 · FBI IC3 — Senior US officials impersonated via messages**

- 원문: https://www.ic3.gov/PSA/2025/PSA250515
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-05"></a>
**FBI-05 · FBI IC3 — Employee self-service phishing websites (2025-04)**

- 원문: https://www.ic3.gov/PSA/2025/PSA250424
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-06"></a>
**FBI-06 · FBI IC3 — Scammers impersonating IC3 (2026-07)**

- 원문: https://www.ic3.gov/PSA/2026/PSA260720
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-07"></a>
**FBI-07 · FBI IC3 — Government/law enforcement impersonation (2026-09)**

- 원문: https://www.ic3.gov/PSA/2026/PSA260917
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

<a id="fbi-08"></a>
**FBI-08 · FBI IC3 — BEC through breached cloud email**

- 원문: https://www.ic3.gov/PSA/2020/PSA200406
- 확인 수준: 기관이 *공격 유형*을 공식 경고. 구체적인 합성 문장의 사실성·실제 발생·완전성까지 인증한 것은 아님

## 반례·설계 원칙

1. '인증번호를 보내지 마세요'는 인증번호 어휘가 있다고 곧바로 사기 명령이 아닙니다. 현재 요청/예방 경고/과거 인용을 분리하십시오.
2. 송신자 주소나 발신번호가 익숙하더라도 실제 계정 탈취가 가능하므로 진짜 요청이라는 확증이 아닙니다.
3. 합성 사례에 반복해서 맞춘 룰의 성공률을 독립 실세계 성능으로 발표하지 마십시오.
4. 실제 위험을 놓치는 미탐과 일반 경고의 과보류를 동시에, 피해 비용을 고려해 검토하십시오.
5. 어떤 모델이든 확률 출력은 정답률·피해확률·실제 기관 확인을 의미하지 않습니다.
6. 금융 송금·OTP·원격 앱 설치는 독립적으로 확인된 채널을 사용하도록 안내합니다. 보고한 사용자 의견만으로 위험을 자동 해제하지 않습니다.

## 데이터 통제·재현 계획

- 입력의 출처/공개 날짜, 기관, 문서URL, 사례ID, 행동 후보, 부정문·인용문 여부와 독립 인간 주석을 분리 기록
- 동일 출처·템플릿의 유사 문장은 학습/평가 양쪽에 나누지 않으며 홀드아웃 데이터는 수집이 끝난 후 잠금
- Zoro 가중치 파인튜닝은 모델·결정 헤드 버전, 학습 권한, 실행 GPU, 학습 코드와 독립 평가가 확보되기 전까지 실행·완료라고 기록하지 않음
- 외부 API로 원문 전송 금지; 사례 업데이트와 정책 반영은 승인·검증·버전 장부 후 진행
