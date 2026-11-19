"""Conformance vectors for the LinkGuard JS port (apps/conformance/linkguard_vectors.json)."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from linkguard import intake as LI, policy as PO  # noqa: E402

AUTHORED = ['택배 주소 확인 바랍니다 bit.ly/3AbC9xYz에서 확인', '엄마 나 폰 고장났어 https://xn--80ak6aa92e.com/login?token=abcd1234efgh5678ijkl9012mnop3456&x=1 여기',
            'http://0x7f000001/admin', '라인 추가 line.me/ti/p/abc', 'https://nаver.com-secure.top/a.apk', 'intent://scan/#Intent;scheme=zxing;end',
            'http://[::1]:8080/', 'naver[.]com/x', '공지 https://www.yna.co.kr/view/AKR2026 참고', 'javascript:alert(1)', 'tel:01012345678',
            'https://www.naver.com@evil.top/login', 'http://2130706433/', 'http://0177.0.0.1/', 'http://10.1.2.3:99999/', 'hxxps://bad[.]top/x',
            'https://münchen.de/', 'https://한국.kr/', 'http://kbstar-login.top/x', 'https://obank.kbstar.com/', 'open.kakao.com/o/abc',
            'https://dl.example.top/app/update.apk?x=1', 'https://example.com/reset/aZ09aZ09aZ09aZ09aZ09aZ09aZ?token=s3cr3t&lang=ko#frag',
            '(https://a.com/x)', '[링크](https://b.co.kr/y)', '😀 https://e.xyz/😀 끝', 'http://[fe80::1]/', 'http://[::ffff:127.0.0.1]/',
            'https://a.b.c.d.e.example.com/', 'http://192.168.0.1:8080/', 'https://xn--invalid-!!.com/', 'market://details?id=x',
            '3.14 와 1.2.3.4 그리고 v1.2.3.4', 'abc@naver.com 으로 메일', 'ＡＢＣ.com', 'https://ｇｏｏｇｌｅ.com', 'http://1.1.1.1/', 'data:text/html,hi',
            'https://kakao.com.secure-login.xyz/', 'https://pay.toss.im/', 'https://toss-event.site/', 'https://www.google.co.kr/search?q=x&key=ABC']
FRAG = ['http://', 'https://', 'www.', 'naver', 'kakao', '.com', '.co.kr', '.top', '/', '?', '&', '=', 'token', 'id', '#', ':8080', '@', '[.]', 'xn--',
        'ａ', 'а', 'ο', '0x', '127', '.0', '.1', '10', '한', '글', ' ', ')', '(', '.', '-', 'bit.ly', 'apk', '😀', 'ı', 'İ', 'ß']

def main():
    rnd = random.Random(4707)
    corpus = list(AUTHORED)
    for _ in range(1500):
        corpus.append(''.join(rnd.choice(FRAG) for _ in range(rnd.randint(1, 12))))
    corpus = list(dict.fromkeys(corpus))
    V = {'intake': [], 'policy': [], 'fuse': [], 'puny': []}
    bl = {'domains': ['evil.top', 'bad.top', 'com-secure.top'], 'source': 'fixture', 'as_of': '2026-11-02'}
    for t in corpus:
        try:
            r = LI.intake(t, message_id='m', consent={'web_analysis': rnd.random() < 0.3, 'external_reputation': rnd.random() < 0.3})
        except (ValueError, TypeError) as e:
            V['intake'].append({'text': t, 'error': str(e)}); continue
        V['intake'].append({'text': t, 'consent': r['consent'], 'out': r})
        for b in (None, bl):
            for kp in (False, True):
                V['policy'].append({'intake': r, 'blocklist': b, 'keys_present': kp, 'out': PO.assess_message(r, blocklist=b, keys_present=kp)})
    for base in ('NO_STRONG_SIGNAL', 'CAUTION', 'ASK_HUMAN', 'PAUSE_AND_VERIFY', 'BOGUS', None):
        for st in PO.STATES + [None]:
            for ap in PO.STATES + [None]:
                V['fuse'].append({'adv': {'policy_action': base} if base else None, 'link': {'overall': st} if st else None, 'apk': ap,
                                  'out': PO.fuse({'policy_action': base} if base else None, {'overall': st} if st else None, ap)})
    for w in ['münchen', '한국', 'bücher', 'пример', 'aéb', '日本語', 'ab-cd', 'ğ', 'naver', 'nаver']:
        V['puny'].append({'in': w, 'enc': LI.punycode_encode(w), 'dec': LI.punycode_decode(LI.punycode_encode(w))})
    out = ROOT / 'apps/conformance/linkguard_vectors.json'
    out.write_text(json.dumps(V, ensure_ascii=False), encoding='utf8')
    print({k: len(v) for k, v in V.items()})

if __name__ == '__main__':
    main()
