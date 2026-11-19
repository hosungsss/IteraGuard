"""v4.6 multi-task synthetic dataset (author-generated; NOT real messages).

Tasks per row (None = not annotated -> masked in the loss):
  speech      DIRECT_REQUEST | INDIRECT_REQUEST | INFORMATIONAL | WARNING_OR_NEGATION | QUOTATION_OR_REPORT
  intent      ORDINARY_INFORMATION | LEGITIMATE_REQUEST | COMMERCIAL_PROMOTION | CONTACT_SOLICITATION |
              PAYMENT_SOLICITATION | CREDENTIAL_SOLICITATION | IMPERSONATION_CLAIM
  indicators  multi-label subset of INDICATORS (empty list = NONE_OBSERVED)
  req_action  MONEY_TRANSFER | CREDENTIAL_DISCLOSURE | PERSONAL_DATA_DISCLOSURE | INSTALL_APPLICATION | CLICK_LINK |
              MOVE_TO_EXTERNAL_MESSENGER | CONTACT_UNKNOWN_PERSON | NO_EXPLICIT_ACTION
  topic       v4.5-compatible action topic: transfer | otp | remote_install | personal_data | link | secrecy | none
UNKNOWN / REVIEW_REQUIRED are produced at inference by the uncertainty layer, never as training targets.

Families are split as a whole (train / calib / locked) so templates never leak across splits.
Labeling guide: docs/22_V46_MULTITASK_LABELING_KO.md.
Usage: python tools/nlp/make_dataset_v46.py <outdir> [--seed 46]
"""
from __future__ import annotations
import json, random, string, sys, hashlib
from pathlib import Path

SPEECH = ['DIRECT_REQUEST', 'INDIRECT_REQUEST', 'INFORMATIONAL', 'WARNING_OR_NEGATION', 'QUOTATION_OR_REPORT']
INTENT = ['ORDINARY_INFORMATION', 'LEGITIMATE_REQUEST', 'COMMERCIAL_PROMOTION', 'CONTACT_SOLICITATION',
          'PAYMENT_SOLICITATION', 'CREDENTIAL_SOLICITATION', 'IMPERSONATION_CLAIM']
INDICATORS = ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE', 'FINANCIAL_INDUCEMENT', 'CREDENTIAL_REQUEST',
              'ACCOUNT_CHANGE_REQUEST', 'IMPERSONATION_SIGNAL', 'MALICIOUS_LINK_SUSPICION', 'UNWANTED_SOLICITATION']
REQ = ['MONEY_TRANSFER', 'CREDENTIAL_DISCLOSURE', 'PERSONAL_DATA_DISCLOSURE', 'INSTALL_APPLICATION', 'CLICK_LINK',
       'MOVE_TO_EXTERNAL_MESSENGER', 'CONTACT_UNKNOWN_PERSON', 'NO_EXPLICIT_ACTION']
TOPIC = ['transfer', 'otp', 'remote_install', 'personal_data', 'link', 'secrecy', 'none']

R = random.Random(46)
pick = lambda xs: R.choice(xs)
def uid(n=None):
    n = n or R.randint(4, 8)
    base = ''.join(R.choice(string.ascii_lowercase) for _ in range(n))
    return base + (str(R.randint(1, 999)) if R.random() < .7 else '') + (R.choice(['_kr', '_88', '.k', '']) if R.random() < .3 else '')
def amount(): return pick(['30만원', '50만 원', '100만원', '2천만 원', '1,200,000원', '80만원', '15만원', '300만원'])
def url():
    a = pick(['kb-safe', 'nh-check', 'cj-dlvry', 'post-kr', 'gov24-help', 'toss-event', 'naver-secure', 'kakao-auth', 'coupang-refund'])
    return pick(['http://', 'https://', '']) + a + pick(['.com', '.top', '.xyz', '.co', '.net']) + pick(['', '/k2', '/a?id=' + str(R.randint(10, 99))])
OVERSEAS = ['[국제발신]', '[해외발신]', '[국외발신]']
MSG = [('라인', 'LINE'), ('라인 아이디', 'LINE'), ('LINE ID', 'LINE'), ('텔레그램', 'TG'), ('텔레', 'TG'), ('위챗', 'WC'), ('왓츠앱', 'WA'),
       ('카톡 아이디', 'KT'), ('카카오톡 오픈채팅', 'KT'), ('오픈톡', 'KT'), ('인스타 DM', 'IG')]
NAMES = ['지은', '수아', '민서', '하나', '유진', 'Jenny', 'Mia', 'Lily', '서연', '다은', 'Kevin', '준호']
INST = ['서울중앙지검', '경찰청 사이버수사대', '금융감독원', '국세청', '국민건강보험공단', 'OO은행 고객센터', 'OO카드', '우체국 택배', '법원 등기과']
FAM = ['엄마', '아빠', '이모', '삼촌', '누나', '형']

def L(speech, intent, ind, req, topic):
    return {'speech': speech, 'intent': intent, 'indicators': sorted(set(ind)), 'req_action': req, 'topic': topic}

# ---------------------------------------------------------------- families: each returns (text, labels)
F = {}
def fam(cat):
    def deco(fn):
        F.setdefault(cat, []).append(fn); return fn
    return deco

# --- stranger contact -> off-platform messenger (CASE A shape); no imperative in several variants
@fam('contact')
def _(): m, _k = pick(MSG); return (f"{pick(OVERSEAS)} 안녕하세요 갑자기 연락드려 죄송해요. {pick(['프로필 보고', '번호가 저장돼 있어서', '추천 친구에 떠서'])} 대화해보고 싶었어요. {m} {uid()} 로 연락 주실래요?",
    L('INDIRECT_REQUEST', 'CONTACT_SOLICITATION', ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'UNWANTED_SOLICITATION'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('contact')
def _(): m, _k = pick(MSG); return (f"{pick(OVERSEAS + [''])} 저는 {pick(NAMES)}이에요. 한국 친구를 사귀고 싶어요. 제 {m}는 {uid()} 입니다",
    L('INFORMATIONAL', 'CONTACT_SOLICITATION', ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'UNWANTED_SOLICITATION'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('contact')
def _(): m, _k = pick(MSG); return (f"이 번호는 곧 정지돼요. 앞으로는 {m} {uid()} 로만 연락 가능합니다",
    L('INFORMATIONAL', 'CONTACT_SOLICITATION', ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('contact')
def _(): m, _k = pick(MSG); return (f"{pick(['혹시 기억하세요?', '오랜만이에요!', '잘 지내셨죠?'])} 예전에 {pick(['모임', '행사', '동호회'])}에서 뵌 {pick(NAMES)}예요. {m} {uid()} 추가해 주세요",
    L('DIRECT_REQUEST', 'CONTACT_SOLICITATION', ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('contact')
def _(): return (f"{pick(OVERSEAS)} Hi, I'm {pick(NAMES)}. 한국어 조금 해요. {pick(['Add my', 'My'])} {pick(['Line', 'Telegram', 'WhatsApp'])} {uid()} {pick(['please', 'pls', ''])}",
    L('INDIRECT_REQUEST', 'CONTACT_SOLICITATION', ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'UNWANTED_SOLICITATION'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('contact')
def _(): return (f"문자로는 길게 얘기하기 어려워서요 ㅎㅎ 편하실 때 {pick(MSG)[0]}에서 {uid()} 검색해 주세요",
    L('INDIRECT_REQUEST', 'CONTACT_SOLICITATION', ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'UNWANTED_SOLICITATION'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))

# --- meeting / personal approach from unknown sender (CASE B shape)
@fam('meet')
def _(): return (f"{pick(OVERSEAS + [''])} 이번 {pick(['주말', '금요일', '저녁'])}에 {pick(['서울', '부산', '근처'])} 가는데 시간 되면 만나요. {pick(['사례는 넉넉히 할게요', '용돈도 드릴게요', '맛있는 거 사드릴게요'])}. {pick(MSG)[0]} {uid()}",
    L('INDIRECT_REQUEST', 'CONTACT_SOLICITATION', ['OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'FINANCIAL_INDUCEMENT', 'UNWANTED_SOLICITATION'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('meet')
def _(): return (f"처음 연락드려요. {pick(['사진 보고', '우연히 번호를 알게 돼서', '소개받아서'])} 한번 뵙고 싶어요. 오늘 {pick(['저녁', '밤', '점심'])} 어떠세요?",
    L('INDIRECT_REQUEST', 'CONTACT_SOLICITATION', ['UNVERIFIED_IDENTITY', 'UNWANTED_SOLICITATION'], 'CONTACT_UNKNOWN_PERSON', 'none'))
@fam('meet')
def _(): return (f"외로워서 연락했어요. 조건 맞으면 만나서 {amount()} 드릴 수 있어요",
    L('INFORMATIONAL', 'CONTACT_SOLICITATION', ['UNVERIFIED_IDENTITY', 'FINANCIAL_INDUCEMENT', 'UNWANTED_SOLICITATION'], 'CONTACT_UNKNOWN_PERSON', 'none'))

# --- financial inducement (side jobs, investment)
@fam('inducement')
def _(): return (f"{pick(OVERSEAS + ['[Web발신]', ''])} 하루 {pick(['30분', '1시간', '10분'])} 투자로 월 {pick(['300', '500', '200'])} 가능한 부업 있습니다. 관심 있으면 {pick(MSG)[0]} {uid()}",
    L('INFORMATIONAL', 'CONTACT_SOLICITATION', ['FINANCIAL_INDUCEMENT', 'OFF_PLATFORM_CONTACT', 'UNWANTED_SOLICITATION', 'UNVERIFIED_IDENTITY'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('inducement')
def _(): return (f"{pick(['코인', '주식', '해외선물'])} 리딩방 VIP 회원 모집 중. 수익 {pick(['보장', '200% 달성', '원금 보장'])}, 오늘 마감",
    L('INFORMATIONAL', 'COMMERCIAL_PROMOTION', ['FINANCIAL_INDUCEMENT', 'URGENCY_OR_PRESSURE', 'UNWANTED_SOLICITATION'], 'NO_EXPLICIT_ACTION', 'none'))
@fam('inducement')
def _(): return (f"고객님 앞으로 {pick(['미수령 환급금', '지원금', '보상금', '당첨금'])} {amount()}이 확인되었습니다. {pick(['기한 내 신청하지 않으면 소멸됩니다', '오늘까지 접수 가능합니다'])}",
    L('INFORMATIONAL', 'IMPERSONATION_CLAIM', ['FINANCIAL_INDUCEMENT', 'URGENCY_OR_PRESSURE', 'UNVERIFIED_IDENTITY'], 'NO_EXPLICIT_ACTION', 'none'))
@fam('inducement')
def _(): return (f"{pick(['재택 알바', '쇼핑몰 리뷰 알바', '좋아요 누르기 부업'])} 일당 {amount()} 즉시 지급! 링크 들어오세요 {url()}",
    L('DIRECT_REQUEST', 'CONTACT_SOLICITATION', ['FINANCIAL_INDUCEMENT', 'MALICIOUS_LINK_SUSPICION', 'UNWANTED_SOLICITATION'], 'CLICK_LINK', 'link'))

# --- direct transfer
@fam('transfer')
def _(): f = pick(FAM); return (f"{f} 나 폰 액정 깨져서 이 번호로 연락해. 급한데 {amount()}만 {pick(['이 계좌로', '친구 계좌로'])} 보내줘",
    L('DIRECT_REQUEST', 'PAYMENT_SOLICITATION', ['UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE', 'IMPERSONATION_SIGNAL'], 'MONEY_TRANSFER', 'transfer'))
@fam('transfer')
def _(): return (f"{pick(INST)}입니다. {pick(['명의 도용', '범죄 연루', '불법 대출'])} 확인을 위해 {pick(['안전계좌로', '지정 계좌로'])} {pick(['이체하세요', '자금을 옮기세요', '송금 바랍니다'])}",
    L('DIRECT_REQUEST', 'PAYMENT_SOLICITATION', ['IMPERSONATION_SIGNAL', 'UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE'], 'MONEY_TRANSFER', 'transfer'))
@fam('transfer')
def _(): return (f"{pick(['대표님', '사장님'])} 지시입니다. 회의 중이라 통화 어려우니 {pick(['거래처에', '아래 계좌로'])} {amount()} 바로 보내고 결과만 알려주세요",
    L('DIRECT_REQUEST', 'PAYMENT_SOLICITATION', ['IMPERSONATION_SIGNAL', 'URGENCY_OR_PRESSURE', 'UNVERIFIED_IDENTITY'], 'MONEY_TRANSFER', 'transfer'))
@fam('transfer')
def _(): return (f"이번 {pick(['달', '분기'])}부터 {pick(['결제 계좌가', '입금 계좌가', '대금 계좌가'])} 변경되었습니다. 새 계좌로 입금 부탁드립니다",
    L('DIRECT_REQUEST', 'PAYMENT_SOLICITATION', ['ACCOUNT_CHANGE_REQUEST', 'UNVERIFIED_IDENTITY'], 'MONEY_TRANSFER', 'transfer'))
# --- indirect transfer pressure
@fam('transfer_indirect')
def _(): return (f"{pick(['대출 실행', '보험금 지급', '환불 처리'])} 전에 {pick(['보증금', '수수료', '인지세'])}를 먼저 {pick(['납부하셔야', '내셔야'])} 진행이 가능합니다",
    L('INDIRECT_REQUEST', 'PAYMENT_SOLICITATION', ['FINANCIAL_INDUCEMENT', 'UNVERIFIED_IDENTITY'], 'MONEY_TRANSFER', 'transfer'))
@fam('transfer_indirect')
def _(): return (f"{pick(['자기야', '여보'])} 나 {pick(['공항', '세관', '병원'])}인데 {pick(['통관비', '수술비', '벌금'])}가 모자라. {amount()}만 먼저 보내줄 수 있어?",
    L('INDIRECT_REQUEST', 'PAYMENT_SOLICITATION', ['UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE', 'FINANCIAL_INDUCEMENT'], 'MONEY_TRANSFER', 'transfer'))
@fam('transfer_indirect')
def _(): return (f"고객님 자산 보호를 위해 {pick(['보유 자금을', '예금을'])} 안전한 곳으로 옮기는 조치가 필요합니다",
    L('INDIRECT_REQUEST', 'PAYMENT_SOLICITATION', ['IMPERSONATION_SIGNAL', 'UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE'], 'MONEY_TRANSFER', 'transfer'))
@fam('transfer_indirect')
def _(): return (f"{pick(['물품 통관 보류', '배송 보류'])} 상태입니다. 미납 {pick(['관세', '수수료'])} {amount()}이 확인되어야 배송이 재개됩니다",
    L('INFORMATIONAL', 'PAYMENT_SOLICITATION', ['IMPERSONATION_SIGNAL', 'UNVERIFIED_IDENTITY'], 'MONEY_TRANSFER', 'transfer'))

# --- credential theft
@fam('cred')
def _(): return (f"{pick(['[Web발신]', ''])} {pick(['회원님 계정', '고객님 계좌', '카드'])}에서 {pick(['해외 로그인', '이상 거래'])}이 감지되었습니다. 본인 확인을 위해 {pick(['아이디와 비밀번호를', '인증번호를', '주민번호 뒷자리를'])} 회신해 주세요",
    L('DIRECT_REQUEST', 'CREDENTIAL_SOLICITATION', ['CREDENTIAL_REQUEST', 'IMPERSONATION_SIGNAL', 'URGENCY_OR_PRESSURE'], 'CREDENTIAL_DISCLOSURE', 'otp'))
@fam('cred')
def _(): return (f"방금 {pick(['문자로 간', '받으신'])} {pick(['6자리 번호', '인증 숫자', '확인 코드'])}만 {pick(['불러주시면', '알려주시면'])} 바로 처리됩니다",
    L('INDIRECT_REQUEST', 'CREDENTIAL_SOLICITATION', ['CREDENTIAL_REQUEST', 'UNVERIFIED_IDENTITY'], 'CREDENTIAL_DISCLOSURE', 'otp'))
@fam('cred')
def _(): return (f"보안 업데이트 대상입니다. {url()} 에서 {pick(['공동인증서 비밀번호', '계좌 비밀번호', '로그인 정보'])}를 다시 등록하세요",
    L('DIRECT_REQUEST', 'CREDENTIAL_SOLICITATION', ['CREDENTIAL_REQUEST', 'MALICIOUS_LINK_SUSPICION', 'IMPERSONATION_SIGNAL'], 'CLICK_LINK', 'personal_data'))
@fam('cred')
def _(): return (f"{pick(['채용 확정', '합격'])}되셨습니다. 급여 계좌 등록을 위해 {pick(['신분증 사진과 통장 비밀번호를', '체크카드와 비밀번호를'])} 보내 주세요",
    L('DIRECT_REQUEST', 'CREDENTIAL_SOLICITATION', ['CREDENTIAL_REQUEST', 'FINANCIAL_INDUCEMENT', 'UNVERIFIED_IDENTITY'], 'PERSONAL_DATA_DISCLOSURE', 'personal_data'))
# --- impersonation claim without explicit action
@fam('imperson')
def _(): return (f"{pick(INST)}입니다. 귀하 명의 {pick(['계좌가', '휴대폰이', '카드가'])} {pick(['범죄에 연루되어', '도용되어'])} {pick(['조사가 필요합니다', '연락드렸습니다'])}",
    L('INFORMATIONAL', 'IMPERSONATION_CLAIM', ['IMPERSONATION_SIGNAL', 'UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE'], 'NO_EXPLICIT_ACTION', 'none'))
@fam('imperson')
def _(): return (f"{pick(['검찰', '경찰', '금감원'])} 담당자입니다. 이 통화 내용은 {pick(['가족에게도', '은행 직원에게도'])} 말씀하시면 안 됩니다",
    L('DIRECT_REQUEST', 'IMPERSONATION_CLAIM', ['IMPERSONATION_SIGNAL', 'UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE'], 'NO_EXPLICIT_ACTION', 'secrecy'))
# --- app install / link
@fam('install')
def _(): return (f"{pick(['상담', '보안 점검', '피해 확인'])}을 위해 {pick(['보내드린 앱을', '원격 지원 앱을', '팀뷰어를'])} 설치하고 {pick(['화면 공유를 켜 주세요', '실행해 주세요'])}",
    L('DIRECT_REQUEST', 'CREDENTIAL_SOLICITATION', ['UNVERIFIED_IDENTITY', 'IMPERSONATION_SIGNAL'], 'INSTALL_APPLICATION', 'remote_install'))
@fam('link')
def _(): return (f"{pick(['[택배]', '[CJ대한통운]', '[우체국]', ''])} {pick(['주소지 불명', '수취인 부재', '운송장 오류'])}로 {pick(['반송 예정', '보관 중'])}. {pick(['주소 수정', '확인'])} {url()}",
    L('DIRECT_REQUEST', 'IMPERSONATION_CLAIM', ['MALICIOUS_LINK_SUSPICION', 'IMPERSONATION_SIGNAL', 'URGENCY_OR_PRESSURE'], 'CLICK_LINK', 'link'))
@fam('link')
def _(): return (f"{pick(['청첩장', '부고', '돌잔치 초대장', '모바일 쿠폰'])} 보내드려요 확인해 주세요 {url()}",
    L('DIRECT_REQUEST', 'CONTACT_SOLICITATION', ['MALICIOUS_LINK_SUSPICION', 'UNVERIFIED_IDENTITY'], 'CLICK_LINK', 'link'))

# --- warnings & quotations (mention risky things, but not requests)
@fam('warn')
def _(): return (f"모르는 사람이 {pick(MSG)[0]}로 옮기자고 하면 {pick(['조심하세요', '응하지 마세요', '대화를 멈추세요'])}",
    L('WARNING_OR_NEGATION', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('warn')
def _(): return (f"{pick(['인증번호는', '비밀번호는', 'OTP는'])} 누구에게도 {pick(['알려주지 마세요', '말하면 안 돼요'])}. {pick(['은행은 절대 묻지 않습니다', '기관도 요구하지 않아요', ''])}",
    L('WARNING_OR_NEGATION', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'otp'))
@fam('warn')
def _(): return (f"{pick(['검찰이나 경찰은', '금융기관은'])} {pick(['돈을 옮기라고 하지 않습니다', '안전계좌를 요구하지 않습니다'])}. 이런 전화는 끊으세요",
    L('WARNING_OR_NEGATION', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'transfer'))
@fam('warn')
def _(): return (f"문자 속 링크는 {pick(['누르지 마시고', '열지 말고'])} 공식 앱에서 직접 확인하세요",
    L('WARNING_OR_NEGATION', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'link'))
@fam('quote')
def _(): return (f"{pick(['어떤 사람이', '모르는 번호로'])} {pick(MSG)[0]}로 연락하라는 문자가 왔는데 {pick(['이거 스팸이지?', '무시해도 되지?', '어떡해?'])}",
    L('QUOTATION_OR_REPORT', 'ORDINARY_INFORMATION', ['OFF_PLATFORM_CONTACT'], 'NO_EXPLICIT_ACTION', 'none'))
@fam('quote')
def _(): return (f"{pick(FAM)}가 {pick(['검사라는 사람한테', '은행 직원이라는 사람한테'])} {pick(['돈 옮기라는', '인증번호 알려달라는'])} 전화를 받았대",
    L('QUOTATION_OR_REPORT', 'ORDINARY_INFORMATION', ['IMPERSONATION_SIGNAL'], 'NO_EXPLICIT_ACTION', pick(['transfer', 'otp'])))
@fam('quote')
def _(): return (f"뉴스 봤어? {pick(['택배 문자 링크', '부고 문자 링크', '청첩장 링크'])} 누르면 {pick(['돈 빠져나간대', '폰 해킹된대'])}",
    L('QUOTATION_OR_REPORT', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'link'))

# --- legitimate commercial promotion
@fam('ad')
def _(): return (f"(광고) {pick(['OO마트', '동네 빵집', 'OO헬스', 'OO안경'])} {pick(['주말 특가', '신규 오픈 기념', '시즌 세일'])}! {pick(['전 품목 20% 할인', '1+1 행사', '첫 방문 사은품'])}. 무료수신거부 080-{R.randint(100,999)}-{R.randint(1000,9999)}",
    L('INFORMATIONAL', 'COMMERCIAL_PROMOTION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('ad')
def _(): return (f"{pick(['카카오톡 채널', '공식 앱'])}에서 {pick(['쿠폰을 받으세요', '이벤트에 참여하세요'])}. 매장 방문 시 추가 할인 (광고)",
    L('DIRECT_REQUEST', 'COMMERCIAL_PROMOTION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('ad')
def _(): return (f"[{pick(['OO통신', 'OO보험', 'OO카드'])}] {pick(['요금제 변경 안내', '혜택 안내', '포인트 소멸 예정 안내'])}입니다. 자세한 내용은 {pick(['고객센터', '공식 홈페이지', '앱'])}에서 확인하세요 (광고)",
    L('INFORMATIONAL', 'COMMERCIAL_PROMOTION', [], 'NO_EXPLICIT_ACTION', 'none'))
# --- unwanted ads (gambling-ish / loan spam)
@fam('spam')
def _(): return (f"{pick(['무직자', '저신용', '연체자'])}도 {pick(['당일 대출', '비대면 대출'])} 가능! 한도 {amount()} 상담은 {pick(MSG)[0]} {uid()}",
    L('INFORMATIONAL', 'COMMERCIAL_PROMOTION', ['FINANCIAL_INDUCEMENT', 'OFF_PLATFORM_CONTACT', 'UNWANTED_SOLICITATION'], 'MOVE_TO_EXTERNAL_MESSENGER', 'none'))
@fam('spam')
def _(): return (f"{pick(['첫 충전', '신규 가입'])} 보너스 {pick(['100%', '50%', '3만원'])} 지급. 가입 코드 {uid()} {url()}",
    L('INFORMATIONAL', 'COMMERCIAL_PROMOTION', ['FINANCIAL_INDUCEMENT', 'MALICIOUS_LINK_SUSPICION', 'UNWANTED_SOLICITATION'], 'CLICK_LINK', 'link'))

# --- ordinary / legitimate (hard negatives include messenger names, money, links, overseas tag)
@fam('normal')
def _(): return (f"{pick(['민지야', '수현아', '형', '언니'])} 카톡이 안 돼서 {pick(['라인으로', '텔레그램으로', '인스타 DM으로'])} 사진 보냈어 확인해봐",
    L('DIRECT_REQUEST', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"{pick(['팀 공지는', '동아리 공지는', '스터디 공지는'])} 이제 {pick(['텔레그램 방', '카톡 단톡방', '라인 그룹'])}에 올라와요",
    L('INFORMATIONAL', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"{pick(['다음 주', '이번 주말'])} {pick(['동창회', '가족 모임', '회식'])}은 {pick(['강남역', '시청역', '홍대입구역'])} 근처야. 회비는 {pick(['만원씩', '2만원씩'])} 걷을게",
    L('INFORMATIONAL', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"{pick(['부장님', '팀장님', '선배님'])} {pick(['출장비 정산 서류', '주간 보고서', '회의록'])} 올렸습니다. 확인 부탁드립니다",
    L('INDIRECT_REQUEST', 'LEGITIMATE_REQUEST', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"{pick(['병원', '치과', '미용실'])}입니다. 내일 {pick(['오전 10시', '오후 3시'])} 예약 있으시니 {pick(['10분 전', '조금 일찍'])} 와 주세요",
    L('DIRECT_REQUEST', 'LEGITIMATE_REQUEST', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"[{pick(['OO은행', 'OO카드', 'OO증권'])}] {pick(['예금 만기', '결제 예정', '포인트 적립'])} 안내입니다. 자세한 내용은 {pick(['영업점', '공식 앱'])}에서 확인하세요",
    L('INFORMATIONAL', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"{pick(OVERSEAS)} 해외 결제 승인 USD {R.randint(5,99)}.{R.randint(10,99)} {pick(['Netflix', 'Apple', 'Amazon', 'Steam'])}. 본인 사용이 아니면 카드사 대표번호로 문의하세요",
    L('INFORMATIONAL', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"{pick(['급여가', '용돈이', '환급금이'])} {pick(['입금되었습니다', '들어왔어요'])}. {pick(['이번 달도 수고하셨습니다', '확인해 보세요', ''])}",
    L('INFORMATIONAL', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'transfer'))
@fam('normal')
def _(): return (f"{pick(['점심 메뉴 투표', '설문 조사', '회의 일정 조율'])} 링크 단톡방에 올렸어요. 다들 {pick(['눌러주세요', '참여해 주세요'])}",
    L('DIRECT_REQUEST', 'LEGITIMATE_REQUEST', [], 'CLICK_LINK', 'link'))
@fam('normal')
def _(): return (f"{pick(FAM)} {pick(['학원비', '관리비', '병원비'])} 이번 달 {amount()} 보내 줄 수 있어요? {pick(['선생님이 내일까지래요', '이번 주까지예요', ''])}",
    L('INDIRECT_REQUEST', 'LEGITIMATE_REQUEST', [], 'MONEY_TRANSFER', 'transfer'))
@fam('normal')
def _(): return (f"{pick(['오늘 저녁', '내일 점심', '주말에'])} {pick(['강남에서', '학교 앞에서', '집 근처에서'])} 보자! {pick(['늦으면 카톡 줘', '도착하면 연락해', ''])}",
    L('DIRECT_REQUEST', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"{pick(['택배가', '등기가'])} {pick(['경비실에', '문 앞에'])} {pick(['보관되어 있습니다', '도착했습니다'])}. {pick(['퇴근길에 찾아가세요', '확인 부탁드려요'])}",
    L('DIRECT_REQUEST', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'none'))
@fam('normal')
def _(): return (f"회원님 {pick(['비밀번호가 변경되었습니다', '로그인 알림입니다'])}. 본인이 아니라면 {pick(['공식 앱', '고객센터 대표번호'])}에서 확인하세요",
    L('INFORMATIONAL', 'ORDINARY_INFORMATION', [], 'NO_EXPLICIT_ACTION', 'otp'))

# ---------------------------------------------------------------- augmentation (robustness)
def augment(t):
    r = R.random()
    if r < .15: t = t.replace(' ', '')                                       # spacing loss
    elif r < .25: t = t.replace('요', pick(['여', '용', '요'])).replace('세요', pick(['세여', '셈', '세요']))
    elif r < .32: t = t + pick([' ㅎㅎ', ' ㅋㅋ', ' ^^', ' 🙏', ' !!'])
    elif r < .38:                                                              # sentence order swap
        parts = [p for p in t.replace('. ', '.\n').split('\n') if p.strip()]
        if len(parts) > 1: R.shuffle(parts); t = ' '.join(parts)
    return t

GREET = ['안녕하세요', '고객님 안녕하세요', '좋은 아침입니다', '바쁘신데 죄송해요']
def multiturn(t):
    return pick(GREET) + '\n' + t if R.random() < .12 else t

def _g3(t):
    t = ''.join(t.split()); return {t[i:i + 3] for i in range(len(t) - 2)}


def decontaminate(rows, locked_texts, thr=0.5):
    """Drop generated rows whose char-3gram Jaccard with ANY hand-written locked sentence is >= thr.
    The same author wrote templates and locked sets, so near-duplicates are expected and must not train."""
    lg = [_g3(t) for t in locked_texts]; keep, drop = [], 0
    for r in rows:
        g = _g3(r['text'])
        if any(len(g & x) / max(1, len(g | x)) >= thr for x in lg): drop += 1
        else: keep.append(r)
    return keep, drop


def build(outdir, per_family=110, locked_files=()):
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    locked_texts = [json.loads(l)['text'] for f in locked_files for l in Path(f).read_text('utf8').splitlines() if l.strip()]
    rows = {'train': [], 'calib': [], 'locked': []}
    for cat, fams in F.items():
        for j, fn in enumerate(fams):
            # whole family -> one split; every category keeps most families in train
            split = 'train' if len(fams) < 3 else ('locked' if j == len(fams) - 1 else ('calib' if j == len(fams) - 2 and len(fams) >= 4 else 'train'))
            seen = set()
            for _ in range(per_family * 3):
                text, lab = fn()
                text = multiturn(augment(text)) if split == 'train' else (text if R.random() < .6 else augment(text))
                if text in seen: continue
                seen.add(text)
                rows[split].append({'text': text, **lab, 'family': f'{cat}:{j}', 'cat': cat, 'split': split, 'source': 'AUTHORED_SYNTHETIC_V46'})
                if len(seen) >= per_family: break
    dropped = {}
    for k in rows:
        rows[k], dropped[k] = decontaminate(rows[k], locked_texts)
    (out / 'v46_decontamination.json').write_text(json.dumps({'threshold_jaccard_char3': 0.5, 'locked_files': [Path(f).name for f in locked_files], 'dropped': dropped}), 'utf8')
    for k, v in rows.items():
        R.shuffle(v)
        (out / f'v46_{k}.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in v), 'utf8')
    return {k: len(v) for k, v in rows.items()}


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    print(json.dumps(build(sys.argv[1], locked_files=[here / 'locked_v46_multitask.jsonl', here / 'locked_handwritten_v2.jsonl', here / 'locked_handwritten.jsonl'])))
