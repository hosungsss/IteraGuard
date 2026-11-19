"""Training data for the on-device NLP heads.

Two sources, kept separate and documented:
  1. 3i4k (warnikchow/3i4k, CC BY-SA 4.0, human-labelled conversational Korean): general
     directive-vs-statement signal. Mapping: command->DIRECT_REQUEST, rhetorical command->
     INDIRECT_REQUEST, statement/question/rhetorical question->INFORMATION; fragments and
     intonation-dependent utterances are dropped. Every 3i4k row gets action='none'.
  2. Author-generated domain sentences (this file): risky-action categories and the speech acts
     3i4k does not label (WARNING, QUOTATION). SYNTHETIC. Split by sentence-frame family and by
     held-out action phrasings, so calibration/locked splits contain frames never trained on.
Usage: python tools/nlp/make_dataset.py <fci.txt> <outdir>
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path

# action phrasings: forms = (imperative, polite request, obligation, negation, quote, past, noun-ish)
A = {
 'transfer': [
  ('송금하세요', '송금해 주세요', '송금하셔야 합니다', '송금하지 마세요', '송금하라고', '송금했어요', '송금'),
  ('이체하세요', '이체해 주세요', '이체하셔야 합니다', '이체하지 마세요', '이체하라고', '이체했어요', '이체'),
  ('입금하세요', '입금해 주세요', '입금하셔야 합니다', '입금하지 마세요', '입금하라고', '입금했어요', '입금'),
  ('돈을 보내세요', '돈을 보내 주세요', '돈을 보내셔야 합니다', '돈을 보내지 마세요', '돈을 보내라고', '돈을 보냈어요', '돈 보내기'),
  ('안전계좌로 옮기세요', '안전계좌로 옮겨 주세요', '안전계좌로 옮기셔야 합니다', '안전계좌로 옮기지 마세요', '안전계좌로 옮기라고', '안전계좌로 옮겼어요', '안전계좌 이동'),
  ('수수료를 납부하세요', '수수료를 납부해 주세요', '수수료를 먼저 납부하셔야 합니다', '수수료를 납부하지 마세요', '수수료를 내라고', '수수료를 냈어요', '수수료 납부'),
  ('대금을 새 계좌로 보내세요', '대금을 새 계좌로 보내 주세요', '대금은 변경된 계좌로 보내셔야 합니다', '대금을 바뀐 계좌로 보내지 마세요', '대금을 새 계좌로 보내라고', '대금을 새 계좌로 보냈어요', '계좌 변경'),
  ('결제하세요', '결제해 주세요', '결제하셔야 합니다', '결제하지 마세요', '결제하라고', '결제했어요', '결제'),
  ('현금을 인출해서 전달하세요', '현금을 찾아서 전달해 주세요', '현금을 인출하셔야 합니다', '현금을 인출해 전달하지 마세요', '현금을 찾아 오라고', '현금을 찾아서 줬어요', '현금 전달'),
  ('투자금을 입금하세요', '투자금을 넣어 주세요', '투자금을 먼저 넣으셔야 합니다', '투자금을 넣지 마세요', '투자금을 넣으라고', '투자금을 넣었어요', '투자금 입금'),
 ],
 'otp': [
  ('인증번호를 알려주세요', '인증번호 좀 불러 주세요', '인증번호를 알려주셔야 합니다', '인증번호를 알려주지 마세요', '인증번호를 알려 달라고', '인증번호를 알려줬어요', '인증번호'),
  ('OTP 번호를 말씀하세요', 'OTP 번호를 입력해 주세요', 'OTP 번호를 입력하셔야 합니다', 'OTP 번호를 말하지 마세요', 'OTP 번호를 불러 달라고', 'OTP 번호를 알려줬어요', 'OTP'),
  ('비밀번호를 입력하세요', '비밀번호를 알려 주세요', '비밀번호를 확인하셔야 합니다', '비밀번호를 알려주지 마세요', '비밀번호를 알려 달라고', '비밀번호를 알려줬어요', '비밀번호'),
  ('보안카드 번호를 전부 입력하세요', '보안카드 번호를 보내 주세요', '보안카드 번호 전체가 필요합니다', '보안카드 번호를 보내지 마세요', '보안카드 번호를 보내라고', '보안카드 번호를 보냈어요', '보안카드'),
  ('문자로 온 번호를 불러주세요', '문자로 받은 숫자를 알려 주세요', '문자로 간 번호만 확인해 주시면 됩니다', '문자로 온 번호를 남에게 알려주지 마세요', '문자로 온 번호를 불러 달라고', '문자로 온 번호를 알려줬어요', '확인 번호'),
 ],
 'remote_install': [
  ('원격제어 앱을 설치하세요', '원격제어 앱을 깔아 주세요', '원격 지원 앱을 설치하셔야 합니다', '원격제어 앱을 설치하지 마세요', '원격 앱을 깔라고', '원격 앱을 깔았어요', '원격제어 앱'),
  ('보안 앱을 설치하세요', '보안 앱을 다운받아 주세요', '보안 점검 앱을 설치하셔야 합니다', '모르는 보안 앱은 설치하지 마세요', '보안 앱을 설치하라고', '보안 앱을 설치했어요', '보안 앱'),
  ('팀뷰어를 실행하세요', '팀뷰어를 켜 주세요', '팀뷰어 연결이 필요합니다', '팀뷰어를 켜지 마세요', '팀뷰어를 켜라고', '팀뷰어를 켰어요', '팀뷰어'),
  ('설치 파일을 열어 주세요', '보내드린 apk 파일을 설치해 주세요', '보내드린 파일을 설치하셔야 처리됩니다', '출처 모를 apk는 설치하지 마세요', 'apk 파일을 설치하라고', 'apk 파일을 설치했어요', '설치 파일'),
 ],
 'personal_data': [
  ('주민등록번호를 입력하세요', '주민번호를 알려 주세요', '주민등록번호 확인이 필요합니다', '주민등록번호를 알려주지 마세요', '주민번호를 알려 달라고', '주민번호를 알려줬어요', '주민등록번호'),
  ('신분증 사진을 보내세요', '신분증 앞뒤 사진을 보내 주세요', '신분증 사본을 제출하셔야 합니다', '신분증 사진을 보내지 마세요', '신분증 사진을 보내라고', '신분증 사진을 보냈어요', '신분증'),
  ('카드 번호와 유효기간을 보내세요', '카드 앞뒤 사진 좀 보내 주세요', '카드 정보 확인이 필요합니다', '카드 사진을 보내지 마세요', '카드 사진을 보내라고', '카드 사진을 보냈어요', '카드 정보'),
  ('통장 사본과 비밀번호를 보내세요', '통장 사본을 보내 주세요', '통장과 체크카드를 맡기셔야 합니다', '통장이나 체크카드를 넘기지 마세요', '통장을 빌려 달라고', '통장을 빌려줬어요', '통장'),
 ],
 'link': [
  ('링크를 클릭하세요', '아래 링크를 눌러 주세요', '링크에 접속하셔야 합니다', '모르는 링크는 누르지 마세요', '링크를 누르라고', '링크를 눌렀어요', '링크'),
  ('주소로 접속하세요', '이 주소로 들어가 주세요', '사이트에서 확인하셔야 합니다', '수상한 사이트에 접속하지 마세요', '사이트에 들어가라고', '사이트에 들어갔어요', '사이트 주소'),
  ('URL을 열어 재입력하세요', 'URL에서 정보를 수정해 주세요', '안내된 URL에서 다시 입력하셔야 합니다', '문자 속 URL은 열지 마세요', 'URL을 열라고', 'URL을 열었어요', 'URL'),
 ],
 'secrecy': [
  ('아무에게도 말하지 마세요', '가족에게는 비밀로 해 주세요', '이 내용은 외부에 알리시면 안 됩니다', None, '비밀로 하라고', None, '비밀 유지'),
  ('전화를 끊지 마세요', '통화 중에는 끊지 말아 주세요', '조사가 끝날 때까지 통화를 유지하셔야 합니다', None, '전화를 끊지 말라고', None, '통화 유지'),
 ],
}
# phrasings reserved for calibration/locked so that eval contains unseen wordings
HELD_OUT = {('transfer', 9), ('otp', 4), ('remote_install', 3), ('personal_data', 3), ('link', 2)}
ACTORS = ['검찰 수사관입니다.', '금융감독원 직원입니다.', '은행 고객센터입니다.', '택배 배송센터입니다.', '카드사 보안팀입니다.', '국세청 안내입니다.',
          '경찰청 사이버수사대입니다.', '거래처 회계팀입니다.', '대표님 지시입니다.', '엄마 나야.', '아빠, 나 폰 고장났어.', '고객님,', '회원님,',
          '중고거래 판매자인데요,', '채용 담당자입니다.', '투자 리딩방 안내입니다.', '쇼핑몰 고객센터입니다.', '', '', '']
URGENCY = ['', '', '지금 바로 ', '오늘 안에 ', '급하게 ', '즉시 ', '']
REASONS = ['', '', '본인 확인을 위해 ', '계좌가 범죄에 연루되어 ', '배송 주소가 불일치하여 ', '환급을 받으시려면 ', '대출 승인을 위해 ', '보안 점검을 위해 ']
WARN_SRC = ['', '은행: ', '경찰청 안내: ', '공지: ', '엄마, ', '']
QUOTERS = ['어떤 사람이', '모르는 번호로', '검찰이라는 사람이', '은행 직원이라면서', '택배사라고', '방금 전화로', '친구가 받은 문자에서']
INFO_SUBJ = ['요청하신', '어제', '이번 달', '정상적으로', '']
EVERYDAY = ['내일 몇 시에 볼까?', '점심 맛있게 먹어.', '회의 자료 공유드립니다.', '오늘 날씨 정말 좋다.', '퇴근하고 전화할게.', '주말에 영화 보러 가자.',
            '보고서 초안 검토 부탁드립니다.', '생일 축하해!', '도착하면 연락해.', '다음 주 일정 확인 부탁드려요.', '우산 챙겨 가.', '사진 잘 받았어.',
            '택배 잘 받았습니다. 감사합니다.', '이번 주 금요일 회식 있습니다.', '병원 예약 내일 오전 10시야.', '숙제 다 했니?', '창문 좀 닫아 줄래?',
            '프린터 용지 좀 채워 주세요.', '오늘 저녁은 집에서 먹을게.', '서류는 책상 위에 두었습니다.']

# frame families per speech act; f(actor, urg, reason, forms) -> sentence
FRAMES = {
 'DIRECT_REQUEST': [
  lambda a, u, r, f: f'{a} {r}{u}{f[0]}.',
  lambda a, u, r, f: f'{a} {u}{f[1]}.',
  lambda a, u, r, f: f'{r}{u}{f[1]}. 확인 부탁드립니다.',
  lambda a, u, r, f: f'{a} {f[0]}. {u}처리 안 하시면 불이익이 있습니다.',
  lambda a, u, r, f: f'{u}{f[1]}!! 급해요.',
  lambda a, u, r, f: f'{a} 지금 {f[0]}. 시간이 없습니다.',
  lambda a, u, r, f: f'{r}{f[0]}. 완료되면 회신 주세요.',
  lambda a, u, r, f: f'[Web발신] {r}{f[1]}',
 ],
 'INDIRECT_REQUEST': [
  lambda a, u, r, f: f'{a} {r}{f[2]}.',
  lambda a, u, r, f: f'{r}{f[2]}. 협조 부탁드립니다.',
  lambda a, u, r, f: f'{a} 처리하려면 {f[6]} 절차가 필요합니다.',
  lambda a, u, r, f: f'{r}{f[6]}만 진행해 주시면 바로 해결됩니다.',
  lambda a, u, r, f: f'{a} {J(f[6], '을를')} 하지 않으시면 계좌가 정지될 수 있습니다.',
  lambda a, u, r, f: f'혹시 {f[6]} 좀 가능할까요? {u}필요해서요.',
  lambda a, u, r, f: f'{r}{f[2].replace("합니다", "할 것 같습니다")}.',
  lambda a, u, r, f: f'{a} 고객님 보호를 위해 {f[6]} 절차를 진행해야 합니다.',
 ],
 'WARNING': [
  lambda a, u, r, f: f'{a} {f[3]}.',
  lambda a, u, r, f: f'{a} 절대 {f[3]}.',
  lambda a, u, r, f: f'누가 {J(f[6], '을를')} 요구하면 사기입니다. {f[3]}.',
  lambda a, u, r, f: f'공공기관은 {J(f[6], '을를')} 요구하지 않습니다. {f[3]}.',
  lambda a, u, r, f: f'{a} 어떤 경우에도 {f[3]}. 의심되면 112에 신고하세요.',
  lambda a, u, r, f: f'요즘 {f[6]} 사기가 많대. {f[3]}.',
  lambda a, u, r, f: f'{f[6]} 관련 문자는 피싱입니다. 응하지 마세요.',
  lambda a, u, r, f: f'주의: {f[3]}.',
 ],
 'QUOTATION': [
  lambda a, u, r, f: f'{a} {f[4]} 문자가 왔어요.',
  lambda a, u, r, f: f'{a} {f[4]} 했는데 이상해요.',
  lambda a, u, r, f: f'방금 {f[4]} 하는 전화를 받았어.',
  lambda a, u, r, f: f'"{u}{f[0]}"라는 문자를 받았는데 사기 맞나요?',
  lambda a, u, r, f: f'{a} {f[4]} 해서 신고하려고요.',
  lambda a, u, r, f: f'엄마가 {f[4]} 연락을 받았대.',
  lambda a, u, r, f: f'기사에서 범인이 {f[4]} 했다더라.',
  lambda a, u, r, f: f'{a} {f[4]} 했다고 들었어요.',
 ],
 'INFORMATION': [
  lambda a, u, r, f: f'{J(f[6], '이가')} 정상 처리되었습니다.',
  lambda a, u, r, f: f'어제 {f[5]}.' if f[5] else '어제 처리했어요.',
  lambda a, u, r, f: f'{f[6]} 내역을 안내드립니다.',
  lambda a, u, r, f: f'이번 달 {f[6]} 관련 수수료가 인하됩니다.',
  lambda a, u, r, f: f'{f[5]} 확인해 봐.' if f[5] else '처리 완료했어.',
  lambda a, u, r, f: f'{f[6]} 일정이 다음 주로 변경되었습니다.',
  lambda a, u, r, f: f'오늘 은행 가서 {f[6]} 문의했어.',
  lambda a, u, r, f: f'{f[6]} 안내 자료를 첨부합니다.',
 ],
}
QUOTER_FIX = lambda s: s.replace('  ', ' ').strip()


def J(noun: str, pair: str) -> str:
    """Attach the right Korean particle: pair is '을를', '이가' or '은는' (batchim decides)."""
    ch = noun.strip()[-1]
    has = 0xAC00 <= ord(ch) <= 0xD7A3 and (ord(ch) - 0xAC00) % 28 != 0
    if not (0xAC00 <= ord(ch) <= 0xD7A3):
        has = ch.isalpha() and ch.upper() in 'LMNR'   # OTP, URL ... read as 'el', 'em' etc.
    return noun + (pair[0] if has else pair[1])


def frame_split(i: int) -> str:
    return 'train' if i < 5 else ('calib' if i == 5 else 'locked')   # frames 0-4 train, 5 calib, 6-7 locked


def authored(rnd: random.Random):
    rows = []
    for sp, frames in FRAMES.items():
        for fi, frame in enumerate(frames):
            split = frame_split(fi)
            for act, phrasings in A.items():
                for pi, forms in enumerate(phrasings):
                    if sp == 'WARNING' and forms[3] is None: continue
                    if sp == 'INFORMATION' and act == 'secrecy': continue
                    held = (act, pi) in HELD_OUT
                    s2 = split if not held else ('calib' if split == 'train' and fi == 0 else ('locked' if split != 'train' else None))
                    if s2 is None: continue
                    for _ in range(3 if s2 == 'train' else 1):
                        a = rnd.choice(QUOTERS) if sp == 'QUOTATION' else (rnd.choice(WARN_SRC) if sp == 'WARNING' else rnd.choice(ACTORS))
                        txt = QUOTER_FIX(frame(a, rnd.choice(URGENCY), rnd.choice(REASONS), forms))
                        rows.append({'text': txt, 'speech': sp, 'action': act if sp != 'INFORMATION' else act, 'split': s2,
                                     'family': f'{sp}:{fi}', 'source': 'AUTHORED_SYNTHETIC'})
    for i, t in enumerate(EVERYDAY):
        sp = 'DIRECT_REQUEST' if any(x in t for x in ('부탁', '줄래', '해 주세요', '가자', '챙겨', '연락해', '전화할게')) else 'INFORMATION'
        rows.append({'text': t, 'speech': sp, 'action': 'none', 'split': 'train' if i % 4 else 'calib', 'family': 'EVERYDAY', 'source': 'AUTHORED_SYNTHETIC'})
    return rows


def from_3i4k(path: str, rnd: random.Random, per_class: int = 2500):
    # 3i4k questions include information requests such as '...알려줘'; their scheme differs from
    # ours (disclosure requests are risky directives here), so question labels 2/4 are not used.
    m = {'3': 'DIRECT_REQUEST', '5': 'INDIRECT_REQUEST', '1': 'INFORMATION'}
    by = {}
    for line in open(path, encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) != 2 or p[0] not in m or not p[1].strip(): continue
        by.setdefault(p[0], []).append(p[1].strip())
    rows = []
    for lab, texts in sorted(by.items()):
        rnd.shuffle(texts)
        for j, t in enumerate(texts[:per_class]):
            rows.append({'text': t, 'speech': m[lab], 'action': 'none', 'split': 'train' if j % 10 else 'calib',
                         'family': f'3i4k:{lab}', 'source': '3i4k_CC_BY_SA_4.0'})
    return rows


def main():
    fci, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(4500)
    rows = authored(rnd) + from_3i4k(fci, rnd)
    seen = set(); uniq = []
    for r in rows:
        if r['text'] in seen: continue
        seen.add(r['text']); uniq.append(r)
    for split in ('train', 'calib', 'locked'):
        with open(out / f'{split}.jsonl', 'w', encoding='utf-8') as f:
            for r in uniq:
                if r['split'] == split: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    stats = {}
    for r in uniq:
        k = (r['split'], r['source'][:7], r['speech']); stats[str(k)] = stats.get(str(k), 0) + 1
    print(json.dumps({'total': len(uniq), 'by_split_source_speech': dict(sorted(stats.items()))}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
