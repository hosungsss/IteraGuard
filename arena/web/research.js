'use strict';
/* Curated official-source scam TYPE reconstructions, never original victim texts.
 * This presentation-only library doesn't train/modify Zoro, classify safety,
 * execute a model, write sessions, or transmit data. URLs are source references
 * in docs/research/SCAM_EVIDENCE_ATLAS_2026_KO.md, not phishing addresses.
 */
(function () {
  const text = document.getElementById('text');
  const note = document.getElementById('researchNotice');
  if (!text || !note) return;
  const examples = Object.freeze({
    delivery: '배송 안내입니다. 배송지 주소에 오류가 있어 보관 중이니 발송인이 알려준 링크로 주소를 갱신해 주세요.',
    wedding: '오랜만이야. 결혼 소식을 전해. 청첩장을 보려면 휴대전화에 안내 프로그램을 설치해줘.',
    card: '[가상 카드상담] 신청하지 않은 카드가 발급됐습니다. 취소 상담에 필요한 원격도움 앱을 설치하세요.',
    invoice: '[거래처를 사칭한 이메일] 이번 정산부터 지급 계좌가 변경됐습니다. 기존 계좌 대신 신규 계좌로 송금해 주세요.',
    toll: '[가상 도로관리] 미납 통행료가 있어 연체료가 붙기 전에 금일 납부하세요.',
    safety: '정보보안팀 공지: 거래처에서 수취계좌 변경을 요청해도 원래 등록된 전화번호로 확인하기 전에는 송금하지 마세요.'
  });
  for (const button of (document.querySelectorAll?.('[data-research]') || [])) {
    button.addEventListener('click', () => {
      if (text.disabled) return;
      const value = examples[button.dataset.research];
      if (!value) return;
      text.value = value;
      text.dispatchEvent(new Event('input', { bubbles: true }));
      note.textContent = '공식기관 자료 기반 재구성 합성 문장입니다. 원문 피해 사례나 검증된 정답이 아닙니다. 판단 버튼을 누르기 전 내용을 확인하세요.';
      text.focus();
    });
  }
}());
