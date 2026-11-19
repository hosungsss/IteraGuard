# IteraGuard · 공식 근거 기반 문자·이메일 사기 유형 아틀라스

작성: 2026-11-19 KST. 공식 발표·경고의 유형에 근거한 연구용 예시집입니다. **실제 범죄 유형과 아래 합성 문장을 혼동하지 마세요.** 실제 피해자의 문자 원문을 수집하지 않았고, 모든 예문은 직접 재구성했습니다. 실제 연락처·계좌·피싱 URL·악성파일은 포함하지 않습니다.

## 범위·증거성

공개 공식 자료 15개, 사기 유형 기반 합성 사례 30개(SMS/이메일/메신저), 보호 경고·과거 인용·일반 메시지 반례 12개를 포함합니다. 세계의 모든 사건과 모든 데이터를 망라할 수 없습니다. 사기 유형의 공식 기록은 **각 합성 문장이 실제로 발신되었다는 증거가 아닙니다.** 재구성된 예시는 독립 전문가의 정답 레이블이 없으므로 정확도 지표에 사용하지 않습니다.

## I. 공식 공개 자료

| ID | 기관·주제/발표 | 원문 |
|---|---|---|
| KISA24 | KISA 118 스미싱 주의보 2024 | [기관 원문](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000030&menuNo=205027&nttId=71280) |
| KISA25A | KISA 지인·청첩장 사칭 2025-03-11 | [기관 원문](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71676&pageIndex=1) |
| KISA25B | KISA 카드 배송·원격제어 2025-02-18 | [기관 원문](https://boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205020&nttId=71661&pageIndex=2&searchCnd=1&searchWrd=) |
| KISA25C | KISA 소액결제 피해 사칭 2025-09-07 | [기관 원문](https://boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71862) |
| KISA26A | KISA 명절 공공기관·선물 2026-02-12 | [기관 원문](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205021&nttId=71966&pageIndex=1&searchCnd=&searchWrd=) |
| KISA26B | KISA 택배 사칭 2026-08-04 | [기관 원문](https://spam.kisa.or.kr/spam/na/ntt/selectNttInfo.do?bbsId=1101&mi=1221&nttSn=3241) |
| FTC25 | FTC 예기치 않은 문자 2025-04 | [기관 원문](https://consumer.ftc.gov/consumer-alerts/2025/04/unexpected-text-scam) |
| FTC23 | FTC 배송 사칭 2023-12 | [기관 원문](https://consumer.ftc.gov/consumer-alerts/2023/12/fake-shipping-notification-emails-text-messages-what-you-need-know-holiday-season) |
| FTC26 | FTC 일자리·작업 사기 2026-04 | [기관 원문](https://consumer.ftc.gov/consumer-alerts/2026/04/job-offer-text-probably-scam) |
| FTC26I | FTC 기관 사칭 2026-11-10 | [기관 원문](https://consumer.ftc.gov/consumer-alerts/2026/11/how-spot-fake-ftc-websites-and-ftc-impersonators) |
| FTC25L | FTC 사기 경보 목록 2025 | [기관 원문](https://consumer.ftc.gov/scams?page=2) |
| IC3 | FBI IC3 BEC 유형 | [기관 원문](https://www.ic3.gov/CrimeInfo/BEC) |
| IC3-17 | FBI BEC 계좌·임원·부동산 2017 | [기관 원문](https://www.ic3.gov/PSA/2017/PSA170504) |
| IC3-22 | FBI 가짜 결제취소 메시지 2022 | [기관 원문](https://www.ic3.gov/PSA/2022/PSA220414) |
| CFPB | CFPB 은행 확인 요청 피싱 | [기관 원문](https://www.consumerfinance.gov/ask-cfpb/i-received-an-email-from-my-bank-or-credit-union-asking-me-to-verify-my-account-information-what-should-i-do-en-999/) |

## II. 실제 보고된 공격 유형에 근거한 합성 재구성 사례

### KR01 · 택배 배송 주소 오류
- 채널: SMS / 공식 출처: [KISA24](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000030&menuNo=205027&nttId=71280), [KISA26B](https://spam.kisa.or.kr/spam/na/ntt/selectNttInfo.do?bbsId=1101&mi=1221&nttSn=3241)
- **기관 자료에서 지지하는 패턴:** 외부 주소수정 유도
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 택배] 주소 확인이 필요합니다. 배송정보를 다시 입력해주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR02 · 지인 부고 메시지
- 채널: SMS / 공식 출처: [KISA24](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000030&menuNo=205027&nttId=71280)
- **기관 자료에서 지지하는 패턴:** 지인 사칭 링크
- **자체 재구성 합성 문장(실제 원문 아님):** “지인 가족의 부고입니다. 장례식 장소 확인 안내를 열어주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR03 · 건강보험검진 사칭
- 채널: SMS / 공식 출처: [KISA24](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000030&menuNo=205027&nttId=71280)
- **기관 자료에서 지지하는 패턴:** 기관 사칭 링크
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 건강보험] 검진 결과가 도착했습니다. 별도 링크에서 내용을 확인하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR04 · 세금 압류 예고
- 채널: SMS / 공식 출처: [KISA24](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000030&menuNo=205027&nttId=71280)
- **기관 자료에서 지지하는 패턴:** 법적 위협
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 기관] 납부금액이 확인되지 않아 압류 예정입니다. 바로 처리하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR05 · 벌금 징수 사칭
- 채널: SMS / 공식 출처: [KISA24](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000030&menuNo=205027&nttId=71280)
- **기관 자료에서 지지하는 패턴:** 법적 위협·긴급성
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 기관] 벌금 납부가 누락됐습니다. 오늘까지 미납금을 조회하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR06 · 모바일 청첩장 설치
- 채널: SMS / 공식 출처: [KISA25A](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71676&pageIndex=1)
- **기관 자료에서 지지하는 패턴:** 앱 설치 유도
- **자체 재구성 합성 문장(실제 원문 아님):** “결혼식 청첩장 보냈어. 안내한 전용 앱을 설치해서 장소를 확인해줘.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR07 · 지인 전화번호 악용
- 채널: MESSENGER / 공식 출처: [KISA25A](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71676&pageIndex=1)
- **기관 자료에서 지지하는 패턴:** 기존 연락처 신뢰 악용
- **자체 재구성 합성 문장(실제 원문 아님):** “지인입니다. 새 청첩장을 보내니 휴대전화에서 파일을 설치해주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR08 · 가짜 카드 발급 통지
- 채널: SMS / 공식 출처: [KISA25B](https://boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205020&nttId=71661&pageIndex=2&searchCnd=1&searchWrd=)
- **기관 자료에서 지지하는 패턴:** 가짜 콜백
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 카드센터] 카드 발급 완료. 신청한 적이 없으면 문자 속 상담번호로 연락해주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR09 · 카드 취소 원격앱
- 채널: SMS / 공식 출처: [KISA25B](https://boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205020&nttId=71661&pageIndex=2&searchCnd=1&searchWrd=)
- **기관 자료에서 지지하는 패턴:** 원격 앱 설치
- **자체 재구성 합성 문장(실제 원문 아님):** “카드발급 취소를 위해 원격도움 앱 설치가 필수입니다.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR10 · 소액결제 환불 OTP
- 채널: SMS / 공식 출처: [KISA25C](https://boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71862)
- **기관 자료에서 지지하는 패턴:** OTP 노출
- **자체 재구성 합성 문장(실제 원문 아님):** “결제 피해 환불을 위해 승인번호를 회신해주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR11 · 소액결제 앱 설치
- 채널: SMS / 공식 출처: [KISA25C](https://boho.or.kr/kr/bbs/view.do?bbsId=B0000133&menuNo=205020&nttId=71862)
- **기관 자료에서 지지하는 패턴:** 악성앱 유도
- **자체 재구성 합성 문장(실제 원문 아님):** “소액결제 피해 확인을 위해 전용 조회 앱 설치가 필요합니다.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR12 · 명절 선물 재배송
- 채널: SMS / 공식 출처: [KISA26A](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205021&nttId=71966&pageIndex=1&searchCnd=&searchWrd=)
- **기관 자료에서 지지하는 패턴:** 선물 사칭 개인정보 요구
- **자체 재구성 합성 문장(실제 원문 아님):** “선물 배송지가 잘못됐습니다. 지금 수령지정보를 다시 입력해주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR13 · 정부 과태료 고지
- 채널: SMS / 공식 출처: [KISA26A](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205021&nttId=71966&pageIndex=1&searchCnd=&searchWrd=)
- **기관 자료에서 지지하는 패턴:** 정부기관 사칭
- **자체 재구성 합성 문장(실제 원문 아님):** “과태료를 오늘까지 납부하지 않으면 불이익이 있습니다.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR14 · SNS 계정 보호 사칭
- 채널: SMS / 공식 출처: [KISA26A](https://www.boho.or.kr/kr/bbs/view.do?bbsId=B0000133&categoryCode=&menuNo=205021&nttId=71966&pageIndex=1&searchCnd=&searchWrd=)
- **기관 자료에서 지지하는 패턴:** 계정탈취
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 SNS] 계정 보호를 위해 로그인 정보를 다시 인증해주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### KR15 · 보관장소 조회
- 채널: SMS / 공식 출처: [KISA26B](https://spam.kisa.or.kr/spam/na/ntt/selectNttInfo.do?bbsId=1101&mi=1221&nttSn=3241)
- **기관 자료에서 지지하는 패턴:** 택배 URL
- **자체 재구성 합성 문장(실제 원문 아님):** “부재중 택배가 보관 중입니다. 안내 링크에서 보관 장소를 확인하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US16 · 은행 이상 거래 통지
- 채널: SMS / 공식 출처: [FTC25](https://consumer.ftc.gov/consumer-alerts/2025/04/unexpected-text-scam), [CFPB](https://www.consumerfinance.gov/ask-cfpb/i-received-an-email-from-my-bank-or-credit-union-asking-me-to-verify-my-account-information-what-should-i-do-en-999/)
- **기관 자료에서 지지하는 패턴:** 사칭 상담센터
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 은행] 결제에 문제가 있습니다. 문자에 적힌 연락처로 전화주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US17 · 가짜 결제 취소
- 채널: SMS / 공식 출처: [IC3-22](https://www.ic3.gov/PSA/2022/PSA220414)
- **기관 자료에서 지지하는 패턴:** 역이체 유도
- **자체 재구성 합성 문장(실제 원문 아님):** “즉시결제를 취소하려면 담당자가 안내하는 계좌로 먼저 이체하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US18 · 배송비 재결제
- 채널: EMAIL / 공식 출처: [FTC23](https://consumer.ftc.gov/consumer-alerts/2023/12/fake-shipping-notification-emails-text-messages-what-you-need-know-holiday-season)
- **기관 자료에서 지지하는 패턴:** 배송비 피싱
- **자체 재구성 합성 문장(실제 원문 아님):** “배송 실패. 소액 재배송료를 결제하면 발송을 재개합니다.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US19 · 미납 통행료
- 채널: SMS / 공식 출처: [FTC25L](https://consumer.ftc.gov/scams?page=2)
- **기관 자료에서 지지하는 패턴:** 요금 사칭
- **자체 재구성 합성 문장(실제 원문 아님):** “미납 통행료가 있으니 연체 전 결제하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US20 · 교통 범칙금
- 채널: SMS / 공식 출처: [FTC25L](https://consumer.ftc.gov/scams?page=2)
- **기관 자료에서 지지하는 패턴:** 공공기관 사칭
- **자체 재구성 합성 문장(실제 원문 아님):** “교통위반 미납 벌금을 납부하지 않으면 면허 이용이 제한됩니다.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US21 · 쇼핑 환불 안내
- 채널: SMS / 공식 출처: [FTC25L](https://consumer.ftc.gov/scams?page=2)
- **기관 자료에서 지지하는 패턴:** 환불 피싱
- **자체 재구성 합성 문장(실제 원문 아님):** “최근 구매 상품 환불이 지연됐습니다. 환불을 위해 개인정보를 다시 입력하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US22 · 클라우드 용량 경고
- 채널: EMAIL / 공식 출처: [FTC25L](https://consumer.ftc.gov/scams?page=2)
- **기관 자료에서 지지하는 패턴:** 결제정보 탈취
- **자체 재구성 합성 문장(실제 원문 아님):** “저장공간이 가득 찼습니다. 서비스 지속을 위해 결제 정보를 갱신하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US23 · 일자리 사칭 가짜 수표
- 채널: SMS / 공식 출처: [FTC26](https://consumer.ftc.gov/consumer-alerts/2026/04/job-offer-text-probably-scam)
- **기관 자료에서 지지하는 패턴:** 선지출·가짜 수표
- **자체 재구성 합성 문장(실제 원문 아님):** “재택 직무 채용 확정. 장비비 지급 수표를 받은 후 먼저 정산해주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US24 · 태스크 사기 선입금
- 채널: MESSENGER / 공식 출처: [FTC26](https://consumer.ftc.gov/consumer-alerts/2026/04/job-offer-text-probably-scam)
- **기관 자료에서 지지하는 패턴:** 선입금 요구
- **자체 재구성 합성 문장(실제 원문 아님):** “작업 수익을 출금하려면 계정 충전금을 먼저 입금해야 합니다.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US25 · 거래처 계좌 변경 BEC
- 채널: EMAIL / 공식 출처: [IC3](https://www.ic3.gov/CrimeInfo/BEC), [IC3-17](https://www.ic3.gov/PSA/2017/PSA170504)
- **기관 자료에서 지지하는 패턴:** 계좌 변경
- **자체 재구성 합성 문장(실제 원문 아님):** “[거래처 사칭] 이번 청구서부터 정산 계좌가 변경됐으니 새 계좌로 송금하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US26 · 임원 사칭 인사정보
- 채널: EMAIL / 공식 출처: [IC3-17](https://www.ic3.gov/PSA/2017/PSA170504)
- **기관 자료에서 지지하는 패턴:** 개인정보 수집
- **자체 재구성 합성 문장(실제 원문 아님):** “[임원 사칭] 직원들의 세금·신분 자료를 개인 이메일로 보내주세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US27 · 부동산 잔금 계좌
- 채널: EMAIL / 공식 출처: [IC3-17](https://www.ic3.gov/PSA/2017/PSA170504)
- **기관 자료에서 지지하는 패턴:** 정산 사칭
- **자체 재구성 합성 문장(실제 원문 아님):** “[중개사 사칭] 잔금 지급 계좌가 바뀌었습니다. 오늘 새 계좌로 입금하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US28 · 배송 첨부파일
- 채널: EMAIL / 공식 출처: [FTC23](https://consumer.ftc.gov/consumer-alerts/2023/12/fake-shipping-notification-emails-text-messages-what-you-need-know-holiday-season)
- **기관 자료에서 지지하는 패턴:** 가짜 첨부
- **자체 재구성 합성 문장(실제 원문 아님):** “배송 실패 확인서를 첨부하오니 파일을 열어 수령내역을 확인하세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US29 · FTC 기관 사칭 보호계좌
- 채널: SMS / 공식 출처: [FTC26I](https://consumer.ftc.gov/consumer-alerts/2026/11/how-spot-fake-ftc-websites-and-ftc-impersonators)
- **기관 자료에서 지지하는 패턴:** 기관 사칭 송금
- **자체 재구성 합성 문장(실제 원문 아님):** “[가상 기관] 자금보호를 위해 별도 안전계좌로 돈을 옮기세요.”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

### US30 · 잘못 보낸 번호 접근
- 채널: SMS / 공식 출처: [FTC25](https://consumer.ftc.gov/consumer-alerts/2025/04/unexpected-text-scam)
- **기관 자료에서 지지하는 패턴:** 대화 유도; 단독 문장으로 확정 불가
- **자체 재구성 합성 문장(실제 원문 아님):** “실례합니다. 어제 약속했던 분이신가요? 잠시 대화할 수 있나요?”
- 개별 사기 확정·모델 정답·학습 결과: NOT_VERIFIED / NOT_LABELED / NOT_TRAINED

## III. 오탐 방지 반례: 의도적으로 만든 합성 문장

아래는 정상 메시지 또는 경고를 상정한 자체 작성 문장입니다. 적법·정상 발신임을 제삼자가 독립 인증한 데이터는 아닙니다.

| ID | 유형 | 합성 문장 | 화행 연구 가설 |
|---|---|---|---|
| N01 | 보호 경고 | 받은 인증번호를 절대 공유하지 마세요. | WARNING |
| N02 | 이체 확인 지시 | 계좌 변경을 요구하면 원래 등록된 공식번호로 확인하세요. | WARNING |
| N03 | 과거 인용 | 어제 누군가가 ‘OTP를 보내 주세요’라고 말했지만 응하지 않았습니다. | PAST_QUOTE |
| N04 | 은행 공식 경고 | 은행은 문자로 비밀번호를 요청하지 않습니다. | WARNING |
| N05 | 정상 배송 안내 | 배송이 오늘 완료됐고 추가 요금은 없습니다. | INFORMATION |
| N06 | 결혼식 알림 | 친구 결혼식은 토요일 오후 2시입니다. | INFORMATION |
| N07 | 결제 보류 공지 | 새 수취계좌를 승인하기 전까지 결제는 보류합니다. | INFORMATION |
| N08 | 정산 진행 보고 | 지급 요청서는 결재 대기이며 아직 송금하지 않았습니다. | INFORMATION |
| N09 | 안전 링크 경고 | 수상한 링크 대신 기관 공식 웹페이지에 직접 접속하세요. | WARNING |
| N10 | 회의 공지 | 내일 회의는 오전 10시에 시작합니다. | INFORMATION |
| N11 | 교육자료 속 예시 | 교육자료에는 ‘지금 입금하세요’라는 피싱 사례가 나옵니다. | PAST_QUOTE |
| N12 | 정보 부족 | 확인이 필요하지만 자세한 방법이 안내되지 않았습니다. | AMBIGUOUS |

## IV. SNM·4D·독립 평가

- **현재 지시 vs 예방 경고:** OTP·송금·설치 같은 단어만으로 사기 확정 금지. 금지·부정 어법 구분.
- **과거 인용 vs 현재 요청:** 과거 설명 끝에 붙은 현재의 위험 요청을 놓치는 미탐과, 단순 과거 설명을 위험으로 판단하는 오탐을 모두 점검.
- **정보 누락·모순:** 발신자 표시, 공식기관·지인 명칭만으로 신원 확정 금지. 실제 링크·메일발송자·수취계좌 확인은 별도 승인된 과정.
- **사람 확인:** 사용자가 확인했다고 보고한 것과 기관/은행이 독립 검증한 것은 구분.
- **모델 장애/역순:** 새 보조 모델 실패나 API 402가 기존 Zoro의 미해결 위험을 자동 해제하지 않음.
- **개인정보:** 실제 피해자 문자·메일, OTP, 전화번호, 계좌번호 등을 외부 API·공개 GitHub로 무단 전송하지 않음.
- **구조:** 메시지→화행/행동→모델 제안→독립 정책→Task→검증근거.
- **시간:** 과거 인용과 현재 지시, 기관 경고일, 모델 버전·세션 순서.
- **관점:** 정상 발신인·수신인·피해자·기관·운영자 관점의 오탐과 미탐 비용.
- **방향·역검증:** 사례↔공식 출처; 출력↔원문·정책·모델/프롬프트 버전.

## V. Zoro 학습과 사용 제한

이 자료는 **문서·평가 후보**입니다. GitHub에 Markdown을 추가해도 Zoro-1 또는 Jev 가중치가 자동으로 학습되는 것은 아닙니다. 실제 fine-tuning은 라이선스·원본 접근권·PII 제거·인간 라벨러 합의·동일 템플릿의 train/test 분리·학습 GPU와 학습 스크립트·결정 헤드 및 온도 재보정·훈련/검증 로그가 있어야 합니다. 현재 실학습, 실모델 호출 품질 개선, 독립 정답률은 NOT_RUN입니다.

데이터 누출을 막기 위해 **본 파일을 테스트 결과의 실제 정답 레이블로 간주하지 않습니다.** 성능 평가는 별도 잠금 평가셋에서 Precision/Recall/F1, FNR/FPR, 보류율, 미해결 Task, 지연 및 비용을 함께 측정해야 합니다.

## VI. 인수인계와 안전

공식 출처의 요지와 비식별 자체 합성 문장만 사용하며 장문의 공식 문서 원문을 재배포하지 않았습니다. 외부 링크의 보안 위험성은 개별 검증 대상입니다. 문서 추가는 모델 훈련 완료나 자동 사기 탐지 완성을 뜻하지 않습니다.
