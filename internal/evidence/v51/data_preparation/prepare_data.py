"""Author and freeze AI synthetic v5.1 data; no inference or source edits."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata

ROOT = Path('/home/ljmpc12/Documents/hackton')
BASE = ROOT / '20261028수_해커톤 준비_IteraGuard-20261104T055702Z-1-002/20261028수_해커톤 준비_IteraGuard'
W = BASE / '[v5.1] IteraGuard_DoubtMeter'
O = ROOT / 'deliverables/v51_implementation_20261104/data_preparation'

# Each family is a distinct authored scenario/workflow, not a label category.
# Within-family contrast triplets stay together. Validation families are never
# used as development families. All labels precede candidate inference.
FAMILIES = [
('F01_PLANETARIUM_ACCESS', 'development', [
 ('천체관측실은 렌즈 교체가 끝나 이번 주 토요일부터 다시 문을 엽니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '완결된 시설 운영 사실이며 청자에게 행동을 요청하지 않는다.', [('이번 주 토요일부터 다시 문을 엽니다.', 'informational', None)]),
 ('별자리 설명 자막이 잘 보이는지 확인하고, 글자가 작으면 손을 들어 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '청자에게 손을 들라는 명확하고 무해한 요청이 있다. 민감 행동 범주가 없다는 이유로 요청 자체를 없다고 주석하지 않는다.', [('글자가 작으면 손을 들어 주세요.', 'direct', 'outside_listed_categories')]),
 ('관측실 출입증 복구를 맡았습니다. 지금 휴대폰에 도착한 일회용 인증번호를 저에게 읽어 주세요.', 'otp', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '역할 자칭의 진위와 별개로 일회용 인증번호를 상대에게 전달하라는 명시적 현재 요청이다.', [('지금 휴대폰에 도착한 일회용 인증번호를 저에게 읽어 주세요.', 'direct', 'otp')]),
]),
('F02_REUSE_FURNITURE_PICKUP', 'development', [
 ('재사용 가구 창고에 등록된 책상 수량은 열두 개이며, 오늘 추가 입고는 없습니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '재고 상황 설명만 있다.', [('오늘 추가 입고는 없습니다.', 'informational', None)]),
 ('가져가실 의자에 붙은 분류표를 떼지 말고 접수대 위에 놓아 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '부정 표현이 일부 있어도 전체는 의자를 놓아 달라는 무해한 직접 요청이다.', [('분류표를 떼지 말고 접수대 위에 놓아 주세요.', 'direct', 'outside_listed_categories')]),
 ('가구 배송 등록을 대신하려면 주민등록증 앞뒤 사진과 집 주소를 이 채팅으로 보내 주세요.', 'personal_data', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '신분증 이미지와 주소를 상대 채팅으로 보내라는 명시적 민감정보 제공 요청이다.', [('주민등록증 앞뒤 사진과 집 주소를 이 채팅으로 보내 주세요.', 'direct', 'personal_data')]),
]),
('F03_THEATRE_RESERVATION_FEE', 'development', [
 ('극단 모임에서 함께 정한 대관비 분담금은 1만 5천 원입니다. 기존 공동 장부에 적힌 계좌로 이번 주 안에 입금해 주세요.', 'transfer', 'direct_request', 'present', False, ['CAUTION', 'ASK_HUMAN'], False,
  '작성 맥락은 통상적인 공동비용 요청이나 문장만으로 계좌나 발신자를 인증할 수 없다. 송금 행동 자체는 transfer이고 확인 안내 또는 보류를 허용한다.', [('기존 공동 장부에 적힌 계좌로 이번 주 안에 입금해 주세요.', 'direct', 'transfer')]),
 ('공연팀 명단에서 빠지기 싫으면 회계 담당자에게는 묻지 말고, 방금 바꾼 계좌로 대관비를 즉시 이체하세요.', ['transfer', 'secrecy'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '기존 담당자 확인을 막고 변경 계좌로 즉시 이체하도록 압박한다. 계좌 변경만이 아니라 직접 이체와 확인 방해를 함께 근거로 삼는다.', [('회계 담당자에게는 묻지 말고', 'direct', 'secrecy'), ('방금 바꾼 계좌로 대관비를 즉시 이체하세요.', 'direct', 'transfer')]),
 ('지난 공연의 대관비 정산은 끝났습니다. 이번 안내에 답장하거나 추가 입금할 필요는 없습니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '완료 사실과 추가 행동 불필요를 명시한다. 입금이라는 단어를 현재 송금 지시로 보지 않는다.', [('정산은 끝났습니다.', 'informational', None), ('답장하거나 추가 입금할 필요는 없습니다.', 'negated', None)]),
]),
('F04_COMMUNITY_GARDEN_SETTLEMENT', 'development', [
 ('텃밭에서 공동 구매한 씨앗값을 나눠 낼 차례입니다. 본인이 받은 품목을 장부와 대조한 뒤 원래 회비 계좌에 보내 주세요.', 'transfer', 'direct_request', 'present', False, ['CAUTION', 'ASK_HUMAN'], False,
  '정상 정산으로 작성했지만 실제 거래를 확인하지 못한다. 신중한 확인 안내나 보류를 허용하고 안전 인증은 기대하지 않는다.', [('장부와 대조한 뒤 원래 회비 계좌에 보내 주세요.', 'direct', 'transfer')]),
 ('씨앗값 중복 청구를 되돌려 드립니다. 환불받으려면 먼저 보증금을 별도 계좌로 송금하고 다른 조합원에게는 알리지 마세요.', ['transfer', 'secrecy'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '환불을 명목으로 선행 송금과 은폐를 직접 요구한다.', [('먼저 보증금을 별도 계좌로 송금하고', 'direct', 'transfer'), ('다른 조합원에게는 알리지 마세요.', 'direct', 'secrecy')]),
 ('씨앗 수령 목록에서 빠진 품목이 있으면 이름 대신 구획 번호와 품목명만 적어 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '합성 구획의 품목 확인 요청이며 인증정보·개인정보 제공이나 송금을 요청하지 않는다.', [('구획 번호와 품목명만 적어 주세요.', 'direct', 'outside_listed_categories')]),
]),
('F05_ROBOTICS_CLUB_LOGIN', 'development', [
 ('로봇 동아리 계정의 인증번호는 운영진에게도 읽어 주지 마세요. 운영진이 대신 입력해 준다는 말도 거절하세요.', 'none', 'negated_or_warning', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '현재 인증번호 전달을 막는 보호 경고이며 전달 요구가 아니다.', [('인증번호는 운영진에게도 읽어 주지 마세요.', 'negated', None)]),
 ('동아리 공용 계정 접속을 제가 대신 끝내겠습니다. 문자로 받은 인증번호 여섯 자리를 지금 말해 주세요.', 'otp', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '상대가 대신 접속한다며 현재 일회용 인증번호를 요구한다.', [('문자로 받은 인증번호 여섯 자리를 지금 말해 주세요.', 'direct', 'otp')]),
 ('어제 누군가 동아리 운영진인 척하며 인증번호를 말하라고 했다고 후배가 알려 줬습니다.', 'none', 'reported_or_quoted', 'none', None, ['CAUTION', 'ASK_HUMAN'], False,
  '과거 타인의 요청을 보고한다. 현재 전달 요청은 없지만 실제 사건·후속 위험을 문장만으로 해소할 수 없어 주의나 보류를 허용한다.', [('인증번호를 말하라고 했다고 후배가 알려 줬습니다.', 'quoted', None)]),
]),
('F06_PRINTER_SERVICE_CONTRAST', 'development', [
 ('상담원이 프린터 수리를 하려면 원격 앱을 깔라고 했다는데, 저는 아직 설치하지 않았어요.', 'none', 'reported_or_quoted', 'none', None, ['CAUTION', 'ASK_HUMAN'], False,
  '청자가 재현한 이전 상담 요구이며 현재 화자의 직접 설치 지시는 아니다. 아직 설치하지 않았다는 보고는 공식 확인 완료가 아니다.', [('원격 앱을 깔라고 했다는데', 'quoted', None)]),
 ('모르는 사람이 보낸 원격 앱은 설치하면 안 됩니다. 다만 지금 제 점검용 원격제어 앱은 설치하고 화면 조작 권한을 켜 주세요.', 'remote_install', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '앞의 경고와 별개로 현재 원격제어 설치와 권한 부여를 요청하는 뒤 절이 존재한다.', [('제 점검용 원격제어 앱은 설치하고 화면 조작 권한을 켜 주세요.', 'direct', 'remote_install')]),
 ('프린터 기사에게 원격 앱을 깔라는 말을 들었다면, 설치 여부만 예 또는 아니오로 적어 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '위험 요청을 인용하지만 현재 청자에게 요구하는 것은 설치 여부에 대한 간단한 응답이다. 원격 앱 설치를 현재 행동으로 지정하지 않는다.', [('설치 여부만 예 또는 아니오로 적어 주세요.', 'direct', 'outside_listed_categories')]),
]),
('F07_FERRY_CHANGE_NOTICE', 'development', [
 ('강 건너는 도선의 첫 운항이 안개 때문에 취소됐고, 발권 건은 자동 환불 처리됐습니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '완료된 취소·환불 안내이고 추가 조작 요구가 없다.', [('발권 건은 자동 환불 처리됐습니다.', 'informational', None)]),
 ('운항 변경 표를 확인하려면 안내문 아래의 시간표 링크를 열어 보세요.', 'link', 'direct_request', 'present', False, ['CAUTION', 'ASK_HUMAN'], False,
  '일반 안내로 작성한 링크 열기 요청이다. 실제 링크 신원을 확인하지 못하므로 주의 또는 보류를 허용한다.', [('안내문 아래의 시간표 링크를 열어 보세요.', 'direct', 'link')]),
 ('취소표 환불을 받으려면 제가 준 링크를 열고 여권 사진과 주소를 올리세요. 정해진 시간이 지나면 환불은 없어집니다.', ['personal_data', 'link'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '링크 진입과 민감 신분증 이미지 제출을 현재 요청하며 환불 상실로 압박한다. 링크 라벨 하나로 민감정보 요청을 가리지 않는다.', [('제가 준 링크를 열고', 'direct', 'link'), ('여권 사진과 주소를 올리세요.', 'direct', 'personal_data')]),
]),
('F08_SUBSCRIPTION_TECH_SUPPORT', 'development', [
 ('구독 장비 점검 예약만 접수됐으며, 계정 비밀번호나 인증번호를 받는 절차는 없습니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '예약 완료 및 불필요한 정보 제출 부재를 명시한다.', [('점검 예약만 접수됐으며', 'informational', None), ('계정 비밀번호나 인증번호를 받는 절차는 없습니다.', 'informational', None)]),
 ('구독 장비 연결 오류를 고치려면 원격지원 앱을 설치해 제어를 허용하고, 이어서 뜨는 일회용 로그인 번호를 저에게 알려 주세요.', ['otp', 'remote_install'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '원격제어 권한과 일회용 자격증명 전달이라는 두 현재 고위험 행동이 동시에 요청된다.', [('원격지원 앱을 설치해 제어를 허용하고', 'direct', 'remote_install'), ('일회용 로그인 번호를 저에게 알려 주세요.', 'direct', 'otp')]),
 ('연결 오류 설명 화면에서 글자가 잘린 부분이 있는지만 답해 주세요. 계정 정보는 적지 않아도 됩니다.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '화면 표시 상태에 대한 무해한 응답 요청이다. 계정 정보 제출을 명시적으로 요구하지 않는다.', [('글자가 잘린 부분이 있는지만 답해 주세요.', 'direct', 'outside_listed_categories')]),
]),
('F09_CONTEST_ELIGIBILITY_THREAT', 'development', [
 ('심사표에 누락된 팀 번호가 있는지만 확인해 주세요. 참가비 처리는 모두 끝났습니다.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '팀 번호 목록 확인 요청이고 이미 끝난 참가비는 새 송금 요청이 아니다.', [('누락된 팀 번호가 있는지만 확인해 주세요.', 'direct', 'outside_listed_categories')]),
 ('본선 명단에 남고 싶으면 내가 시키는 절차를 끝내. 무슨 절차인지는 따로 알려 줄 테니 지금은 이유를 묻지 마.', 'unclear', 'direct_request', 'present', None, ['ASK_HUMAN'], False,
  '요청과 압박은 있으나 수행할 행동이 아직 주어지지 않았다. 명확한 무해 행동이나 특정 고위험 행동으로 추정하지 않는다.', [('내가 시키는 절차를 끝내.', 'direct', 'unclear'), ('무슨 절차인지는 따로 알려 줄 테니', 'unclear', 'unclear')]),
 ('심사 탈락 처리를 막으려면 공식 접수창구에는 문의하지 말고, 내 개인 계좌로 보완 심사비를 지금 보내세요.', ['transfer', 'secrecy'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '불이익을 명목으로 개인 계좌 송금과 독립 확인 방해를 직접 요구한다.', [('공식 접수창구에는 문의하지 말고', 'direct', 'secrecy'), ('내 개인 계좌로 보완 심사비를 지금 보내세요.', 'direct', 'transfer')]),
]),
('F10_UNRESOLVED_PRODUCTION_REFERENCE', 'development', [
 ('아까 얘기한 그걸 넘겨 주세요. 자세한 건 다시 쓰지 않겠습니다.', 'unclear', 'direct_request', 'present', None, ['ASK_HUMAN'], False,
  '직접 요구는 있으나 지시 대상이 앞 문맥에 의존하며 현재 입력에 없다.', [('아까 얘기한 그걸 넘겨 주세요.', 'unclear', 'unclear')]),
 ('아까 언급한 것은 전시 제목 후보입니다. 후보 제목 중 더 짧은 하나를 골라 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '현재 입력에서 지시 대상이 전시 제목으로 해결된 무해한 선택 요청이다.', [('후보 제목 중 더 짧은 하나를 골라 주세요.', 'direct', 'outside_listed_categories')]),
 ('아까 말한 숫자는 방금 도착한 로그인 일회용 인증번호입니다. 접속을 마무리하게 그 번호를 제게 전달하세요.', 'otp', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '현재 입력 안에서 지시어가 일회용 인증번호로 해소되며 상대에게 전달하라고 명시한다.', [('방금 도착한 로그인 일회용 인증번호입니다.', 'informational', 'otp'), ('그 번호를 제게 전달하세요.', 'direct', 'otp')]),
]),
('F11_PUBLIC_RECORDS_CLAIM', 'development', [
 ('기록자료센터 담당자라고 소개드립니다. 지난 전시의 공개 사진 목록은 정리 중입니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '기관 역할은 자칭일 뿐이나 현재 위험 행동 요청은 없다. 역할 자칭만으로 사기나 안전을 확정하지 않는다.', [('공개 사진 목록은 정리 중입니다.', 'informational', None)]),
 ('기록자료센터 담당자입니다. 공개 사진의 색감이 너무 어두운지만 알려 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '기관 주장과 무해한 감상 응답을 분리한다.', [('공개 사진의 색감이 너무 어두운지만 알려 주세요.', 'direct', 'outside_listed_categories')]),
 ('기록자료센터 권리 확인팀입니다. 오늘 안에 주민등록증 사본과 자택 주소를 이 대화창에 제출하지 않으면 등록을 삭제하겠습니다.', 'personal_data', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '삭제 위협과 함께 신분증·주소 제출을 현재 상대 대화창으로 요청한다.', [('주민등록증 사본과 자택 주소를 이 대화창에 제출하지 않으면', 'direct', 'personal_data')]),
]),
('F12_SAVINGS_GROUP_SECRECY', 'development', [
 ('적금 모임의 이름을 대는 사람이 비밀번호를 물어도 알려 주지 마세요. 모임장에게도 공개할 필요가 없습니다.', 'none', 'negated_or_warning', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '자격증명 보호를 위한 부정 지시이며 위험 은폐 요구가 아니다.', [('비밀번호를 물어도 알려 주지 마세요.', 'negated', None)]),
 ('이번 확인 과정에 관해 가족이나 다른 모임 회원에게는 말하지 마세요. 저와만 이야기하면 됩니다.', 'secrecy', 'direct_request', 'present', None, ['CAUTION', 'ASK_HUMAN'], False,
  '독립 상담을 막는 현재 비밀 유지 요청이다. 아직 특정 송금·정보 제공은 없어 바로 필수중단으로 단정하지 않는다.', [('가족이나 다른 모임 회원에게는 말하지 마세요.', 'direct', 'secrecy')]),
 ('모임 자금이 조사 중이니 가족에게는 숨기고 보호용 계좌로 전액 이체하세요. 누구에게 확인하면 보호 조치가 취소됩니다.', ['transfer', 'secrecy'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '자금 보호를 주장하며 은폐와 전액 송금, 독립 확인 방해를 요구한다.', [('가족에게는 숨기고', 'direct', 'secrecy'), ('보호용 계좌로 전액 이체하세요.', 'direct', 'transfer')]),
]),
('F13_ARCHIVE_READING_ACCESS', 'validation', [
 ('옛 신문 열람 계정은 자료관 방문 없이도 열람 기간이 자동 연장됐습니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '계정 연장 완료 사실이며 추가 접근·인증 행위 요청이 없다.', [('열람 기간이 자동 연장됐습니다.', 'informational', None)]),
 ('옛 신문 검색 결과에서 날짜 표기가 빠진 줄에만 별표를 붙여 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '검색 결과에 표시를 추가하는 무해한 직접 요청이다.', [('날짜 표기가 빠진 줄에만 별표를 붙여 주세요.', 'direct', 'outside_listed_categories')]),
 ('열람 권한을 갱신하려고 제가 접속 중입니다. 본인에게 전송된 일회용 확인 코드를 이 메시지의 답장으로 보내세요.', 'otp', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '다른 사람이 대신 접속하며 본인 일회용 확인 코드를 전달하도록 요청한다.', [('본인에게 전송된 일회용 확인 코드를 이 메시지의 답장으로 보내세요.', 'direct', 'otp')]),
]),
('F14_ANIMAL_TRANSPORT_BOOKING', 'validation', [
 ('반려동물 이동 서비스 예약서의 비용과 날짜를 먼저 대조하시고, 처음 계약서에 기재된 계좌로 예약금을 입금해 주세요.', 'transfer', 'direct_request', 'present', False, ['CAUTION', 'ASK_HUMAN'], False,
  '정상 계약금 납부 상황으로 작성했지만 문장만으로 서비스나 계좌를 검증할 수 없어 확인 안내·보류를 허용한다.', [('처음 계약서에 기재된 계좌로 예약금을 입금해 주세요.', 'direct', 'transfer')]),
 ('이동 차량이 출발 직전입니다. 본사에는 전화하지 말고 기사 개인 계좌로 추가 보증금을 즉시 보내야 동물을 태워 드립니다.', ['transfer', 'secrecy'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '서비스 거절을 압박하며 개인 계좌 추가 송금과 독립 문의 차단을 요구한다.', [('본사에는 전화하지 말고', 'direct', 'secrecy'), ('기사 개인 계좌로 추가 보증금을 즉시 보내야', 'direct', 'transfer')]),
 ('이동 서비스 이용료 결제 내역이 확정돼 예약이 완료되었습니다. 현장에서 추가로 낼 금액은 없습니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '결제·예약 완료를 알리며 추가 지급 요청은 없다.', [('예약이 완료되었습니다.', 'informational', None), ('추가로 낼 금액은 없습니다.', 'informational', None)]),
]),
('F15_RESIDENT_VOTING_ENROLLMENT', 'validation', [
 ('주민 투표 안건 설명이 길면 어려운 낱말에 밑줄을 그어 주세요. 이름이나 연락처는 쓰지 마세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '문서 난이도 검토라는 무해한 요청이고 연락처 제공을 요구하지 않는다.', [('어려운 낱말에 밑줄을 그어 주세요.', 'direct', 'outside_listed_categories')]),
 ('모르는 사람에게 투표 인증번호를 주지 말라고 안내받았죠. 이번에는 제가 보낸 등록 링크를 열고 거기에 로그인 인증번호와 신분증 사진을 입력하세요.', ['otp', 'personal_data', 'link'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '앞의 보호 경고를 인용한 뒤 별개의 현재 링크 진입·자격증명·신분증 제출을 요구한다. 대표 행동 하나로 다른 요구를 숨기지 않는다.', [('제가 보낸 등록 링크를 열고', 'direct', 'link'), ('거기에 로그인 인증번호와 신분증 사진을 입력하세요.', 'direct', 'otp'), ('신분증 사진을 입력하세요.', 'direct', 'personal_data')]),
 ('투표 등록을 도와준다며 인증번호와 신분증 사진을 보내라는 메시지를 받았다는 주민 신고가 접수됐습니다.', 'none', 'reported_or_quoted', 'none', None, ['CAUTION', 'ASK_HUMAN'], False,
  '다른 사람이 받았던 요구에 관한 신고이며 현재 청자에게 정보 제공을 지시하지 않는다. 신고의 실제 위험 해소 상태는 알 수 없다.', [('인증번호와 신분증 사진을 보내라는 메시지를 받았다는 주민 신고', 'quoted', None)]),
]),
('F16_TRANSLATION_MANUSCRIPT_REVIEW', 'validation', [
 ('번역 원고에는 등장인물이 상대에게 돈을 보내라고 했다는 설명이 있을 뿐입니다.', 'none', 'reported_or_quoted', 'none', False, ['NO_STRONG_SIGNAL', 'CAUTION'], False,
  '문학 원고 속 타인의 발화를 설명하며 현재 청자의 송금을 요청하지 않는다. 명확한 인용에는 미감지 또는 주의 안내를 허용한다.', [('등장인물이 상대에게 돈을 보내라고 했다는 설명', 'quoted', None)]),
 ('원고 속 대사인 “돈을 보내라”를 실행할 필요는 없고, 그 문장의 띄어쓰기만 확인해 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '송금 대사는 인용이며 현재 직접 요청은 문장 편집이다.', [('그 문장의 띄어쓰기만 확인해 주세요.', 'direct', 'outside_listed_categories'), ('“돈을 보내라”를 실행할 필요는 없고', 'negated', None)]),
 ('원고에 나온 “원격 앱을 조심하라”는 대사는 잊으세요. 지금 교정 작업을 위해 제 원격제어 프로그램을 설치하고 키보드 제어를 허용하세요.', 'remote_install', 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '인용된 경고와 분리된 현재 원격제어 설치·권한 요청이 뒤에 있다.', [('제 원격제어 프로그램을 설치하고 키보드 제어를 허용하세요.', 'direct', 'remote_install')]),
]),
('F17_REFRIGERATED_WAREHOUSE_ACCESS', 'validation', [
 ('냉장 창고 출입 카드 교체는 끝났고, 기존 사용자들의 출입 일정에는 변화가 없습니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '출입 설비 교체 완료와 일정 유지 안내만 있다.', [('출입 카드 교체는 끝났고', 'informational', None), ('출입 일정에는 변화가 없습니다.', 'informational', None)]),
 ('창고 문이 잠겨 물건이 상할 수 있으니, 긴급 접속 링크를 열고 휴대폰에 뜬 일회용 번호를 관리자에게 전송하세요.', ['otp', 'link'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '물품 손실을 내세우며 링크 진입과 일회용 번호 제삼자 전달을 현재 요청한다.', [('긴급 접속 링크를 열고', 'direct', 'link'), ('휴대폰에 뜬 일회용 번호를 관리자에게 전송하세요.', 'direct', 'otp')]),
 ('창고 쪽은 지금 그대로 두면 곤란해집니다. 전에 말한 조치를 해 두면 되는데, 구체적인 내용은 여기서 적지 않겠습니다.', 'unclear', 'direct_request', 'present', None, ['ASK_HUMAN'], False,
  '압박은 있으나 어떤 조치를 하라는지 현재 문장으로 알 수 없다.', [('전에 말한 조치를 해 두면 되는데', 'unclear', 'unclear'), ('구체적인 내용은 여기서 적지 않겠습니다.', 'unclear', 'unclear')]),
]),
('F18_ONLINE_MUSIC_LESSON_RECOVERY', 'validation', [
 ('화상 악기 수업 복구 창이 떴는데, 그 부분은 이미 된 건가요?', 'unclear', 'unclear', 'unclear', None, ['ASK_HUMAN'], False,
  '지시 대상과 수행 요구 여부가 모두 앞 맥락에 의존한다. 기술 상태 문의인지 민감 조작 요구인지 확정하지 않는다.', [('그 부분은 이미 된 건가요?', 'unclear', 'unclear')]),
 ('화상 악기 수업 화면에서 박자 표시가 한 줄로 보이는지 두 줄로 보이는지 알려 주세요.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '현재 화면의 단순 표시 상태를 답하도록 요청하며 계정·인증 정보는 요청하지 않는다.', [('박자 표시가 한 줄로 보이는지 두 줄로 보이는지 알려 주세요.', 'direct', 'outside_listed_categories')]),
 ('수업 계정 복구를 위해 원격 조작 앱을 설치해 화면을 공유하세요. 다음으로 전송될 일회용 인증번호도 제가 입력할 수 있게 불러 주세요.', ['otp', 'remote_install'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '원격 조작 앱과 화면 접근, 일회용 인증번호 전달이라는 복수의 현재 민감 행동을 요구한다.', [('원격 조작 앱을 설치해 화면을 공유하세요.', 'direct', 'remote_install'), ('일회용 인증번호도 제가 입력할 수 있게 불러 주세요.', 'direct', 'otp')]),
]),
('F19_WORKPLACE_REVIEW_PRESSURE', 'validation', [
 ('인사 검토 결과는 아직 확정되지 않았습니다. 이번 공지는 진행 상황만 알리는 글입니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '진행 상태만 알리며 청자 행동을 요구하지 않는다.', [('이번 공지는 진행 상황만 알리는 글입니다.', 'informational', None)]),
 ('평가에서 불이익을 받지 않으려면 이 면담 이야기를 동료나 인사 담당자에게 절대 꺼내지 마세요.', 'secrecy', 'direct_request', 'present', None, ['CAUTION', 'ASK_HUMAN'], False,
  '불이익을 이유로 상담·보고를 막는 비밀 유지 요구다. 송금·인증정보 요청까지는 명시되지 않아 주의·보류를 허용한다.', [('이 면담 이야기를 동료나 인사 담당자에게 절대 꺼내지 마세요.', 'direct', 'secrecy')]),
 ('내일 평가에 어떤 결과가 나올지는 지금 당신이 어떻게 하느냐에 달렸습니다. 알아서 잘 판단하세요.', 'unclear', 'unclear', 'unclear', None, ['ASK_HUMAN'], False,
  '암시적 위협일 수 있지만 구체 요청 행동이나 대상이 없다. 정보가 명확히 무해하다고도 단정할 수 없다.', [('지금 당신이 어떻게 하느냐에 달렸습니다.', 'unclear', 'unclear'), ('알아서 잘 판단하세요.', 'unclear', 'unclear')]),
]),
('F20_WINTER_RESPONSE_CENTER', 'validation', [
 ('제설 안내센터라고 합니다. 오늘 눈길 안내문은 오후에 한 차례 더 게시될 예정입니다.', 'none', 'informational', 'none', False, ['NO_STRONG_SIGNAL'], False,
  '기관 자칭과 공지 예정 사실만 있다. 기관의 실제 신원은 검증하지 않는다.', [('오늘 눈길 안내문은 오후에 한 차례 더 게시될 예정입니다.', 'informational', None)]),
 ('제설 지원 순번이 취소되지 않으려면 담당 부서에는 확인하지 말고, 새로 안내한 개인 계좌로 긴급 처리비를 이체하세요.', ['transfer', 'secrecy'], 'direct_request', 'present', True, ['PAUSE_AND_VERIFY'], True,
  '지원 취소를 압박하며 새 개인 계좌 이체와 부서 확인 방해를 요구한다.', [('담당 부서에는 확인하지 말고', 'direct', 'secrecy'), ('새로 안내한 개인 계좌로 긴급 처리비를 이체하세요.', 'direct', 'transfer')]),
 ('눈길 안내문을 읽은 뒤 이해하기 어려운 문장 번호만 표시해 주세요. 비용이나 개인정보를 보내실 일은 없습니다.', 'outside_listed_categories', 'direct_request', 'present', False, ['NO_STRONG_SIGNAL'], False,
  '안내문 가독성 확인 요청이고 비용·정보 제공은 명시적으로 필요 없다.', [('이해하기 어려운 문장 번호만 표시해 주세요.', 'direct', 'outside_listed_categories')]),
]),
]

CANONICAL_ACTIONS = {'transfer','otp','remote_install','personal_data','link','secrecy','none','unclear'}
SPEECH = {'direct_request','reported_or_quoted','negated_or_warning','unclear','informational'}
GUIDANCE = {'NO_STRONG_SIGNAL','CAUTION','PAUSE_AND_VERIFY','ASK_HUMAN'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def build_rows():
    rows=[]
    for family,split,cases in FAMILIES:
        for ix,item in enumerate(cases,1):
            text,actions,speech,presence,risky,allowed,pause,rationale,anchors=item
            actions=actions if isinstance(actions,list) else [actions]
            requested=actions[0]
            canonical='none' if requested=='outside_listed_categories' else requested
            action_list=[a for a in actions if a not in {'none','unclear','outside_listed_categories'}]
            scope='outside_listed_categories' if requested=='outside_listed_categories' else ('unresolved' if requested=='unclear' else ('listed' if action_list else 'none'))
            evidence=[]
            for quote,directness,action in anchors:
                assert text.count(quote)==1,(family,ix,'ambiguous span')
                start=text.index(quote)
                evidence.append({'start_cp':start,'end_cp':start+len(quote),'quote':quote,'kind':'AI_ANNOTATED_SEMANTIC_CLAUSE','directness':directness,'action':action,'semantic_verification':False,'annotation_status':'AI_PROPOSED_NOT_HUMAN_VALIDATED'})
            rows.append({
                'schema_version':'v51-development-annotation-1',
                'id':f'V51-{family}-{ix:02d}', 'family_id':family,'contrast_id':ix,
                'text':text,'synthetic':True,'authorship':'AI_GENERATED',
                'author_id':'codex_requirements_audit_20261104',
                'independent_eval':False,'independent_eval_eligible':False,
                'split':split,'label_status':'AI_PROPOSED_BEFORE_INFERENCE_NOT_HUMAN_VALIDATED',
                'action':canonical,'requested_action':requested,'action_list':action_list,
                'additional_requested_actions':actions[1:], 'action_scope':scope,
                'request_presence':presence,'speech':speech,
                'risk':{'context':('BENIGN_AUTHORED_CONTEXT' if risky is False else 'RISKY_AUTHORED_CONTEXT' if risky is True else 'UNKNOWN_AUTHORED_CONTEXT'),'fraud_truth':'NOT_KNOWN','signal_present':risky},
                'risky':risky,'allowed_guidance':allowed,'expect':allowed,
                'pause_required':pause,'rationale':rationale,'evidence':evidence,
                'model_context_scope':'CURRENT_TEXT_ONLY',
                'annotation_priority_note':'main action is a scoring pointer; action_list preserves all explicit current listed actions',
            })
    return rows

def chargrams(s):
    s=re.sub(r'[^가-힣A-Za-z0-9]', '', unicodedata.normalize('NFKC',s)).lower()
    return {s[i:i+3] for i in range(max(0,len(s)-2))}

def overlap(a,b):
    a,b=chargrams(a),chargrams(b)
    return len(a & b)/len(a | b) if a | b else 0.0

def validate(rows):
    errors=[]
    def check(ok,msg):
        if not ok:errors.append(msg)
    check(len(rows)==60,'total_count')
    check(len({r['id'] for r in rows})==60,'unique_ids')
    check(len({r['text'] for r in rows})==60,'unique_texts')
    family_sets={s:{r['family_id'] for r in rows if r['split']==s} for s in ['development','validation']}
    check(not(family_sets['development'] & family_sets['validation']),'family_leakage')
    check(len(family_sets['development'])==12 and len(family_sets['validation'])==8,'family_count')
    check(sum(r['split']=='development' for r in rows)==36,'development_count')
    check(sum(r['split']=='validation' for r in rows)==24,'validation_count')
    for family in family_sets['development']|family_sets['validation']:
        fr=[r for r in rows if r['family_id']==family]
        check(len(fr)==3,f'{family}:triplet')
        check(len({tuple(r['expect']) for r in fr})>=2,f'{family}:contrast')
    for r in rows:
        p=r['id']
        check(r['action'] in CANONICAL_ACTIONS,p+':action')
        check(r['requested_action'] in CANONICAL_ACTIONS|{'outside_listed_categories'},p+':requested_action')
        check(r['speech'] in SPEECH,p+':speech')
        check(r['request_presence'] in {'none','present','unclear'},p+':request_presence')
        check(r['action_scope'] in {'none','listed','outside_listed_categories','unresolved'},p+':scope')
        check(r['risky'] is None or type(r['risky']) is bool,p+':risk_type')
        check(r['expect']==r['allowed_guidance'] and len(r['expect'])>0 and len(set(r['expect']))==len(r['expect']) and set(r['expect'])<=GUIDANCE,p+':guidance')
        check(not r['independent_eval'] and not r['independent_eval_eligible'] and r['synthetic'],p+':provenance')
        check(len(r['text'])<=2000,p+':length')
        check(not re.search(r'https?://|hf_[A-Za-z0-9]+|\d{3}[- ]\d{3,4}[- ]\d{4}',r['text']),p+':no_live_contact_or_secret')
        if r['pause_required']:
            check(r['risky'] is True and r['expect']==['PAUSE_AND_VERIFY'],p+':pause')
            check(bool(set(r['action_list']) & {'transfer','otp','remote_install','personal_data'}),p+':pause_action')
        if r['action_scope']=='outside_listed_categories':
            check(r['action']=='none' and r['request_presence']=='present' and r['action_list']==[],p+':outside_contract')
        if r['request_presence']=='none':check(r['action_list']==[],p+':no_current_request')
        check(len(set(r['action_list']))==len(r['action_list']),p+':action_uniqueness')
        check(set(r['action_list']) <= CANONICAL_ACTIONS-{'none','unclear'},p+':action_list')
        for a in r['action_list']:
            check(any(e['action']==a and e['directness']=='direct' for e in r['evidence']),p+':action_evidence_'+a)
        for e in r['evidence']:
            check(type(e['start_cp']) is int and type(e['end_cp']) is int and 0<=e['start_cp']<e['end_cp']<=len(r['text']),p+':offset_range')
            check(r['text'][e['start_cp']:e['end_cp']]==e['quote'],p+':offset_quote')
            check(e['directness'] in {'direct','negated','quoted','informational','unclear'},p+':directness')
            check(e['semantic_verification'] is False,p+':not_human_semantic_proof')
    old_sources=[ROOT/'deliverables/zoro_iteration_20261104/V2_48.jsonl',ROOT/'deliverables/zoro_iteration_20261104/AI25.jsonl',W/'data/v50_ai_development25.jsonl']
    old=[];source_receipts=[]
    for p in old_sources:
        b=p.read_bytes(); source_receipts.append({'path':str(p),'sha256':sha(b)})
        old.extend(json.loads(s) for s in b.decode().splitlines() if s.strip())
    check(len(old)==98,'existing_98_count')
    exact=[r['id'] for r in rows if r['text'] in {x.get('text','') for x in old}]
    check(not exact,'old_exact_duplicates')
    nearest=[]
    for r in rows:
        best=max(((overlap(r['text'],x.get('text','')),x.get('id')) for x in old),key=lambda z:z[0])
        nearest.append({'id':r['id'],'old_id':best[1],'char_trigram_jaccard':best[0]})
    # High lexical overlap is a review trigger, not proof of semantic novelty.
    lexical_flags=[x for x in nearest if x['char_trigram_jaccard']>=0.45]
    check(not lexical_flags,'old_high_lexical_overlap')
    cross=max(({'development_id':a['id'],'validation_id':b['id'],'char_trigram_jaccard':overlap(a['text'],b['text'])} for a in rows if a['split']=='development' for b in rows if b['split']=='validation'),key=lambda x:x['char_trigram_jaccard'])
    check(cross['char_trigram_jaccard']<0.45,'cross_split_high_lexical_overlap')
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'counts':{'total_cases':len(rows),'development':36,'validation':24,'families':20,'development_families':12,'validation_families':8,'semantic_spans':sum(len(r['evidence']) for r in rows)},'checks':{'schema':'PASS' if not errors else 'SEE_ERRORS','family_split':'PASS' if not (family_sets['development'] & family_sets['validation']) else 'FAIL','exact_text_duplicates_in_existing98':exact,'all_spans_codepoint_match':not any('offset_' in e for e in errors),'existing98_max_trigram_jaccard':max(x['char_trigram_jaccard'] for x in nearest),'existing98_threshold_review_flags':lexical_flags,'cross_split_max_trigram_jaccard':cross['char_trigram_jaccard'],'existing98_semantic_novelty':'Distinct newly authored scenario/workflow families; lexical scan is only a safeguard, not an independent semantic novelty proof.'},'existing_sources':source_receipts,'model_calls':0,'independent_eval':False,'validation_content_disclosed_to_parent':False}

def main():
    targets={'development':W/'data/v51_development36.jsonl','validation':W/'data/v51_validation24.jsonl'}
    assert not any(p.exists() for p in targets.values()),'Frozen targets already exist; do not overwrite.'
    rows=build_rows(); result=validate(rows)
    O.mkdir(parents=True,exist_ok=True)
    (O/'validation_record.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    if result['status']!='PASS':
        print(json.dumps({'status':'FAIL','errors':result['errors']},ensure_ascii=False));return 1
    receipt={'schema':'v51.ai_synthetic_data_freeze.v1','frozen_utc':datetime.now(timezone.utc).isoformat(),'candidate_outputs_observed_before_freeze':False,'model_calls':0,'independent_eval':False,'independent_eval_eligible':False,'authorship':'AI_GENERATED','labels_status':'AI_PROPOSED_NOT_HUMAN_VALIDATED','family_assignment':'12 preassigned development families; 8 disjoint preassigned validation families; 3 contrast cases each','validation_use':'candidate-selection validation, not independent human held-out evaluation','files':[],'existing_sources':result['existing_sources'],'prepared_by_script_sha256':sha(Path(__file__).read_bytes()),'pre_inference_validation_sha256':sha((O/'validation_record.json').read_bytes()),'rubric_sha256':sha((O/'ANNOTATION_RUBRIC.md').read_bytes()),'existing_files_modified':False}
    for split,p in targets.items():
        subset=[r for r in rows if r['split']==split]
        content=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in subset).encode()
        p.write_bytes(content)
        receipt['files'].append({'path':str(p),'split':split,'cases':len(subset),'families':len({r['family_id'] for r in subset}),'bytes':len(content),'sha256':sha(content)})
    (O/'freeze_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'FROZEN','files':receipt['files']},ensure_ascii=False))
    return 0

if __name__=='__main__':raise SystemExit(main())
