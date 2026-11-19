"""LinkIntake — find and describe URLs in a message without opening them.

Deterministic, offline, no network. The JS port (apps/shared/dmsg-linkguard.js) must produce identical
output (checked by tools/linkguard/make_vectors.py + apps/conformance/run_linkguard.js).

Design rules
* Nothing is executed or fetched here. Non-HTTP schemes are reported, never opened.
* Offsets are Unicode code points into the original message.
* `display_url` / `external_url` are redacted: credential-like query values, userinfo and long opaque
  path tokens are replaced, so logs and any external lookup never carry them.
* IDN handling: per-label lower-casing + RFC 3492 Punycode (no full UTS-46 mapping; documented limit).
* "Registrable domain" uses a small built-in suffix list, not the full Public Suffix List (documented limit).
"""
from __future__ import annotations
import re

MAX_TEXT = 4000
MAX_URLS = 20

# ---------------------------------------------------------------- reference data (exported to JS)
TLDS = sorted({
    'com', 'net', 'org', 'info', 'biz', 'io', 'co', 'me', 'ly', 'app', 'dev', 'xyz', 'top', 'site', 'online', 'shop', 'store',
    'club', 'live', 'link', 'click', 'icu', 'vip', 'win', 'cc', 'tk', 'ml', 'ga', 'cf', 'gq', 'pw', 'ws', 'su', 'ru', 'cn', 'hk',
    'tw', 'jp', 'kr', 'us', 'uk', 'de', 'fr', 'in', 'vn', 'th', 'ph', 'sg', 'my', 'id', 'to', 'gl', 'do', 'la', 'at', 'be', 'nl',
    'tv', 'fm', 'am', 'cloud', 'page', 'work', 'world', 'today', 'news', 'kim', 'xn--3e0b707e', 'gov', 'edu', 'mobi', 'pro', 'one',
    'test', 'invalid', 'example', 'localhost'})
TWO_LEVEL_SUFFIXES = sorted({'co.kr', 'or.kr', 'go.kr', 'ac.kr', 'ne.kr', 're.kr', 'pe.kr', 'ms.kr', 'hs.kr', 'es.kr', 'sc.kr', 'kg.kr',
                             'seoul.kr', 'co.jp', 'ne.jp', 'or.jp', 'com.cn', 'net.cn', 'com.hk', 'co.uk', 'org.uk', 'com.tw',
                             'com.vn', 'com.ph', 'com.sg', 'com.my', 'co.id', 'appspot.com', 'github.io', 'blogspot.com',
                             'web.app', 'firebaseapp.com', 'pages.dev', 'vercel.app', 'netlify.app', 'herokuapp.com'})
SHORTENERS = sorted({'bit.ly', 'han.gl', 'me2.do', 'url.kr', 'vo.la', 't.ly', 'tinyurl.com', 'goo.gl', 'ow.ly', 'buly.kr', 'c11.kr',
                     't.co', 'is.gd', 'cutt.ly', 'rebrand.ly', 'shorturl.at', 'naver.me', 'kko.to', 'abit.ly', 'zrr.kr', 'muz.so',
                     'tny.kr', 'lrl.kr', 'bitly.ws', 'buly.co'})
MESSENGER_HOSTS = sorted({'line.me', 'lin.ee', 'liff.line.me', 't.me', 'telegram.me', 'telegram.dog', 'open.kakao.com',
                          'pf.kakao.com', 'qr.kakao.com', 'wa.me', 'api.whatsapp.com', 'chat.whatsapp.com', 'm.me',
                          'weixin.qq.com', 'u.wechat.com', 'discord.gg', 'snapchat.com'})
APP_STORE_HOSTS = sorted({'play.google.com', 'apps.apple.com', 'onestore.co.kr', 'm.onestore.co.kr', 'galaxystore.samsung.com'})
# brand token -> registrable domains that legitimately carry it (for lookalike detection only, not an allow-list)
BRANDS = {
    'naver': ['naver.com', 'naver.me'], 'kakao': ['kakao.com', 'kakaocorp.com', 'kakaobank.com', 'kko.to'],
    'toss': ['toss.im', 'tossbank.com'], 'kbstar': ['kbstar.com'], 'kbcard': ['kbcard.com'], 'shinhan': ['shinhan.com', 'shinhancard.com'],
    'woori': ['wooribank.com', 'wooricard.com'], 'hana': ['hanabank.com', 'hanacard.co.kr'], 'nonghyup': ['nonghyup.com'],
    'ibk': ['ibk.co.kr'], 'epost': ['epost.go.kr'], 'cjlogistics': ['cjlogistics.com'], 'coupang': ['coupang.com'],
    'hometax': ['hometax.go.kr'], 'nhis': ['nhis.or.kr'], 'police': ['police.go.kr'], 'fss': ['fss.or.kr'],
    'samsung': ['samsung.com'], 'google': ['google.com', 'google.co.kr', 'goo.gl'], 'apple': ['apple.com'], 'netflix': ['netflix.com'],
    'paypal': ['paypal.com'], 'gov24': ['gov.kr'], 'kbank': ['kbanknow.com'], 'tmoney': ['tmoney.co.kr'],
}
SENSITIVE_KEYS = sorted({'token', 'access_token', 'id_token', 'refresh_token', 'auth', 'authorization', 'key', 'apikey', 'api_key',
                         'session', 'sessionid', 'sid', 'code', 'otp', 'password', 'passwd', 'pw', 'pwd', 'pin', 'sig', 'signature',
                         'jwt', 'secret', 'ssn', 'rrn', 'phone', 'tel', 'email', 'account', 'acct', 'card', 'cvc', 'jsessionid'})
SCHEME_CLASS = {'http': 'WEB', 'https': 'WEB', 'hxxp': 'WEB', 'hxxps': 'WEB', 'intent': 'DEEPLINK', 'market': 'APP_STORE',
                'kakaotalk': 'DEEPLINK', 'line': 'DEEPLINK', 'tg': 'DEEPLINK', 'whatsapp': 'DEEPLINK', 'tel': 'DEEPLINK', 'sms': 'DEEPLINK',
                'smsto': 'DEEPLINK', 'mailto': 'DEEPLINK', 'javascript': 'DANGEROUS', 'data': 'DANGEROUS', 'file': 'DANGEROUS',
                'content': 'DANGEROUS', 'ftp': 'OTHER'}
# IPv4 special-purpose ranges (RFC 6890 family) as (network int, prefix, category)
V4_RESERVED = [('0.0.0.0', 8, 'THIS_NETWORK'), ('10.0.0.0', 8, 'PRIVATE'), ('100.64.0.0', 10, 'CGNAT'), ('127.0.0.0', 8, 'LOOPBACK'),
               ('169.254.0.0', 16, 'LINK_LOCAL'), ('172.16.0.0', 12, 'PRIVATE'), ('192.0.0.0', 24, 'IETF'), ('192.0.2.0', 24, 'DOCUMENTATION'),
               ('192.168.0.0', 16, 'PRIVATE'), ('198.18.0.0', 15, 'BENCHMARK'), ('198.51.100.0', 24, 'DOCUMENTATION'),
               ('203.0.113.0', 24, 'DOCUMENTATION'), ('224.0.0.0', 4, 'MULTICAST'), ('240.0.0.0', 4, 'RESERVED'), ('255.255.255.255', 32, 'BROADCAST')]
CONFUSABLES = {'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', 'і': 'i', 'ј': 'j', 'ѕ': 's', 'һ': 'h', 'ԁ': 'd',
               'ո': 'n', 'ο': 'o', 'ν': 'v', 'α': 'a', 'ρ': 'p', 'τ': 't', 'ι': 'i', 'κ': 'k', 'ⅼ': 'l', 'ı': 'i', '０': '0', '１': '1',
               '0': 'o', '1': 'l', 'ɡ': 'g', 'ɑ': 'a', 'ӏ': 'l', 'Ӏ': 'l', 'ԛ': 'q', 'ԝ': 'w', 'ɩ': 'i', 'ɵ': 'o', 'ⅰ': 'i', 'ｌ': 'l'}

# ---------------------------------------------------------------- extraction
def _ci(word):
    # explicit ASCII-only case-insensitivity; re.IGNORECASE would also fold 'ı', 'ſ' and the Kelvin sign, unlike JS
    return ''.join('[%s%s]' % (c, c.upper()) if 'a' <= c <= 'z' else re.escape(c) for c in word)


_SCHEMES = '|'.join(_ci(x) for x in sorted(SCHEME_CLASS, key=len, reverse=True))
_HOSTCH = r'[A-Za-z0-9À-ɏͰ-ϿЀ-ӿ가-힣一-鿿぀-ヿ０-９-]'
_TLD_ALT = '|'.join(_ci(x) for x in sorted(TLDS, key=len, reverse=True))
URL_RX = re.compile(
    r'(?:(?<![A-Za-z0-9])(?:' + _SCHEMES + r'):(?://)?[^\s<>"　]+)'                      # explicit scheme
    r'|(?:(?<![A-Za-z0-9@._-])(?:' + _HOSTCH + r'+(?:\.|\[\.\]|\(\.\)))+(?:' + _TLD_ALT + r')(?![A-Za-z0-9])(?::[0-9]{1,5})?(?:/[^\s<>"　]*)?)'
    r'|(?:(?<![A-Za-z0-9.])[0-9]{1,3}(?:\.[0-9]{1,3}){3}(?::[0-9]{1,5})?(?:/[^\s<>"　]*)?)',
    )
TRAIL = '.,;:!?)]}\'"’”>'
OPEN_CLOSE = {')': '(', ']': '[', '}': '{'}


def _is_hangul(ch): return '가' <= ch <= '힣' or 'ᄀ' <= ch <= 'ᇿ' or '㄰' <= ch <= '㆏'


def _trim(raw):
    s = raw
    # stop at Korean text glued to an ASCII URL (e.g. "bit.ly/abc에서"), but keep Hangul inside a hostname
    host_end = _authority_end(s)
    for i, ch in enumerate(s):
        if i >= host_end and _is_hangul(ch):
            s = s[:i]; break
    while s and s[-1] in TRAIL:
        c = s[-1]
        if c in OPEN_CLOSE and s.count(OPEN_CLOSE[c]) >= s.count(c): break
        s = s[:-1]
    return s


def _authority_end(s):
    m = re.match(r'(?:[A-Za-z][A-Za-z0-9+.-]*:(?://)?)?', s)
    start = m.end() if m else 0
    for i in range(start, len(s)):
        if s[i] in '/?#': return i
    return len(s)


def extract(text: str):
    if type(text) is not str:
        raise TypeError('TEXT_REQUIRED')
    text = text[:MAX_TEXT]
    out = []
    for m in URL_RX.finditer(text):
        raw = _trim(m.group(0))
        if not raw or ('.' not in raw and ':' not in raw and '[.]' not in raw):
            continue
        out.append({'raw': raw, 'start': m.start(), 'end': m.start() + len(raw)})
        if len(out) >= MAX_URLS: break
    return out


# ---------------------------------------------------------------- punycode (RFC 3492)
_BASE, _TMIN, _TMAX, _SKEW, _DAMP, _IBIAS, _IN = 36, 1, 26, 38, 700, 72, 128


def _adapt(delta, n, first):
    delta = delta // _DAMP if first else delta // 2
    delta += delta // n; k = 0
    while delta > ((_BASE - _TMIN) * _TMAX) // 2:
        delta //= _BASE - _TMIN; k += _BASE
    return k + (_BASE - _TMIN + 1) * delta // (delta + _SKEW)


def _digit(d): return chr(d + 22 + 75 * (d < 26))


def punycode_encode(label: str) -> str:
    cps = [ord(c) for c in label]
    out = [chr(c) for c in cps if c < 0x80]
    b = h = len(out)
    if out: out.append('-')
    n, delta, bias = _IN, 0, _IBIAS
    while h < len(cps):
        m = min(c for c in cps if c >= n)
        delta += (m - n) * (h + 1); n = m
        for c in cps:
            if c < n: delta += 1
            if c == n:
                q = delta; k = _BASE
                while True:
                    t = _TMIN if k <= bias else (_TMAX if k >= bias + _TMAX else k - bias)
                    if q < t: break
                    out.append(_digit(t + (q - t) % (_BASE - t))); q = (q - t) // (_BASE - t); k += _BASE
                out.append(_digit(q)); bias = _adapt(delta, h + 1, h == b); delta = 0; h += 1
        delta += 1; n += 1
    return ''.join(out)


def punycode_decode(s: str):
    try:
        b = s.rfind('-'); out = [ord(c) for c in s[:b]] if b > 0 else []
        i, n, bias, pos = 0, _IN, _IBIAS, (b + 1 if b > 0 else 0)
        while pos < len(s):
            oldi, w, k = i, 1, _BASE
            while True:
                if pos >= len(s): return None
                c = s[pos]; pos += 1
                d = ord(c) - 48 + 26 if '0' <= c <= '9' else (ord(c.lower()) - 97 if 'a' <= c.lower() <= 'z' else -1)
                if d < 0: return None
                i += d * w
                t = _TMIN if k <= bias else (_TMAX if k >= bias + _TMAX else k - bias)
                if d < t: break
                w *= _BASE - t; k += _BASE
            bias = _adapt(i - oldi, len(out) + 1, oldi == 0); n += i // (len(out) + 1); i %= len(out) + 1
            if n > 0x10FFFF: return None
            out.insert(i, n); i += 1
        return ''.join(chr(c) for c in out)
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------- helpers
def _script(ch):
    o = ord(ch)
    if ch.isascii():
        return 'LATIN' if ch.isalpha() else 'COMMON'
    if 0x00C0 <= o <= 0x024F: return 'LATIN'
    if 0x0370 <= o <= 0x03FF: return 'GREEK'
    if 0x0400 <= o <= 0x04FF: return 'CYRILLIC'
    if 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F: return 'HANGUL'
    if 0x4E00 <= o <= 0x9FFF: return 'HAN'
    if 0x3040 <= o <= 0x30FF: return 'KANA'
    if 0xFF10 <= o <= 0xFF19: return 'FULLWIDTH_DIGIT'
    return 'OTHER'


def _ipv4_parse(host):
    """Dotted quad, or the obfuscated single-number / hex / octal forms browsers still accept."""
    parts = host.split('.')
    if not 1 <= len(parts) <= 4 or any(p == '' for p in parts): return None, False
    vals = []
    obfuscated = len(parts) != 4
    for p in parts:
        pl = p.lower()
        try:
            if pl.startswith('0x'):
                if not re.fullmatch(r'[0-9a-f]*', pl[2:]): return None, False
                v = int(pl[2:] or '0', 16); obfuscated = True
            elif len(pl) > 1 and pl.startswith('0') and all(c in '01234567' for c in pl): v = int(pl, 8); obfuscated = True
            elif pl.isdigit() and pl.isascii(): v = int(pl)
            else: return None, False
        except ValueError:
            return None, False
        vals.append(v)
    if len(vals) == 4 and all(v < 256 for v in vals): num = (vals[0] << 24) | (vals[1] << 16) | (vals[2] << 8) | vals[3]
    elif len(vals) == 1 and vals[0] < 2 ** 32: num = vals[0]
    elif len(vals) == 2 and vals[0] < 256 and vals[1] < 2 ** 24: num = (vals[0] << 24) | vals[1]
    elif len(vals) == 3 and vals[0] < 256 and vals[1] < 256 and vals[2] < 2 ** 16: num = (vals[0] << 24) | (vals[1] << 16) | vals[2]
    else: return None, False
    return num, obfuscated


def _v4_str(num): return '.'.join(str((num >> s) & 255) for s in (24, 16, 8, 0))


def v4_category(num):
    for net, pre, cat in V4_RESERVED:
        a = [int(x) for x in net.split('.')]; n = (a[0] << 24) | (a[1] << 16) | (a[2] << 8) | a[3]
        mask = (0xFFFFFFFF << (32 - pre)) & 0xFFFFFFFF
        if (num & mask) == n: return cat
    return 'PUBLIC'


def v6_category(h):
    h = h.lower()
    if h in ('::1',): return 'LOOPBACK'
    if h in ('::',): return 'UNSPECIFIED'
    if h.startswith('::ffff:'):
        num, _ = _ipv4_parse(h[7:])
        return 'MAPPED_' + v4_category(num) if num is not None else 'RESERVED'
    head = h.split(':')[0]
    try: first = int(head or '0', 16)
    except ValueError: return 'INVALID'
    if first & 0xFE00 == 0xFC00: return 'PRIVATE'
    if first & 0xFFC0 == 0xFE80: return 'LINK_LOCAL'
    if first & 0xFF00 == 0xFF00: return 'MULTICAST'
    if first == 0x2001 and h.split(':')[1:2] == ['db8']: return 'DOCUMENTATION'
    return 'PUBLIC'


def registrable(host_ascii):
    labels = host_ascii.split('.')
    if len(labels) >= 3 and '.'.join(labels[-2:]) in TWO_LEVEL_SUFFIXES: return '.'.join(labels[-3:])
    return '.'.join(labels[-2:]) if len(labels) >= 2 else host_ascii


def _redact_path(path):
    segs = path.split('/')
    out = []
    for s in segs:
        if len(s) >= 24 and re.fullmatch(r'[A-Za-z0-9_\-.~%=+]+', s) and re.search(r'[0-9]', s) and re.search(r'[A-Za-z]', s):
            out.append('{REDACTED}')
        else:
            out.append(s)
    return '/'.join(out)


def _redact_query(q):
    if not q: return '', [], False
    keys, parts, hit = [], [], False
    for kv in q.split('&'):
        k, eq, v = kv.partition('=')
        kl = k.lower()
        keys.append(k)
        if kl in SENSITIVE_KEYS or (len(v) >= 32 and re.fullmatch(r'[A-Za-z0-9_\-.~%=+/]+', v or '-')):
            parts.append(k + ('=REDACTED' if eq else '')); hit = True
        else:
            parts.append(kv)
    return '&'.join(parts), keys, hit


# ---------------------------------------------------------------- analysis
def analyze(raw: str) -> dict:
    flags, notes = [], []
    s = raw
    defanged = False
    if re.match(r'[hH][xX][xX][pP][sS]?:', s): s = 'http' + s[3:]; defanged = True
    if '[.]' in s or '(.)' in s: s = s.replace('[.]', '.').replace('(.)', '.'); defanged = True
    if defanged: flags.append('DEFANGED')
    m = re.match(r'([A-Za-z][A-Za-z0-9+.-]*):(//)?', s)
    scheme = m.group(1).lower() if m and m.group(1).lower() in SCHEME_CLASS else ''
    explicit = bool(scheme)
    if not explicit: scheme, rest = 'http', s; notes.append('NO_SCHEME_ASSUMED_HTTP')
    else: rest = s[m.end():]
    sclass = SCHEME_CLASS.get(scheme, 'OTHER')
    res = {'raw': raw, 'scheme': scheme, 'scheme_class': sclass, 'explicit_scheme': explicit}
    if sclass in ('DEEPLINK', 'DANGEROUS', 'OTHER') or (sclass == 'APP_STORE' and scheme == 'market'):
        flags.append('NON_HTTP_SCHEME')
        if sclass == 'DANGEROUS': flags.append('DANGEROUS_SCHEME')
        if scheme in ('intent', 'kakaotalk', 'line', 'tg', 'whatsapp'): flags.append('MESSENGER_OR_APP_DEEPLINK')
        res.update(host_ascii=None, host_unicode=None, port=None, registrable_domain=None, display_url=scheme + ':' + ('…' if rest else ''),
                   external_url=None, ip=None, idn=None, query_keys=[], flags=sorted(set(flags)), notes=notes, fetchable=False)
        return res
    # authority / path / query / fragment
    end = len(rest)
    for i, ch in enumerate(rest):
        if ch in '/?#': end = i; break
    authority, tail = rest[:end], rest[end:]
    userinfo = None
    if '@' in authority:
        userinfo, authority = authority.rsplit('@', 1); flags.append('USERINFO_AT')
    port = None
    host = authority
    if authority.startswith('['):
        close = authority.find(']')
        host = authority[1:close] if close > 0 else authority[1:]
        after = authority[close + 1:] if close > 0 else ''
        if after.startswith(':') and after[1:].isdigit(): port = int(after[1:])
    elif ':' in authority:
        h, _, p = authority.rpartition(':')
        if p.isdigit() and p.isascii(): host, port = h, int(p)
    if port is not None and (port == 0 or port > 65535): flags.append('INVALID_PORT')
    elif port is not None and port not in (80, 443): flags.append('NONSTANDARD_PORT')
    host = host.rstrip('.')
    path, query, frag = tail, '', ''
    if '#' in path: path, frag = path.split('#', 1)
    if '?' in path: path, query = path.split('?', 1)
    # host: IP literal?
    ip = None; host_ascii = host_unicode = None; idn = None
    if ':' in host and all(c in '0123456789abcdefABCDEF:.' for c in host):
        cat = v6_category(host); ip = {'version': 6, 'address': host.lower(), 'category': cat, 'obfuscated': False}
        host_ascii = host_unicode = '[' + host.lower() + ']'
    else:
        num, obf = _ipv4_parse(host) if host and all(c in '0123456789abcdefxABCDEFX.' for c in host) else (None, False)
        if num is not None:
            cat = v4_category(num); ip = {'version': 4, 'address': _v4_str(num), 'category': cat, 'obfuscated': obf}
            host_ascii = host_unicode = _v4_str(num)
            if obf: flags.append('OBFUSCATED_IP')
        else:
            labels = [l.lower() for l in host.split('.')]
            asc, uni, nonascii, scripts_mixed, puny = [], [], False, False, False
            for l in labels:
                if l.startswith('xn--'):
                    dec = punycode_decode(l[4:]); puny = True
                    uni.append(dec if dec is not None else l); asc.append(l)
                    if dec is None: notes.append('INVALID_PUNYCODE')
                    lab_u = dec or ''
                elif l.isascii():
                    asc.append(l); uni.append(l); lab_u = l
                else:
                    nonascii = True; asc.append('xn--' + punycode_encode(l)); uni.append(l); lab_u = l
                sc = {_script(c) for c in lab_u} - {'COMMON', 'FULLWIDTH_DIGIT'}
                if len(sc) > 1 and not (sc <= {'HAN', 'KANA', 'HANGUL'}): scripts_mixed = True
                if any(_script(c) == 'FULLWIDTH_DIGIT' for c in lab_u): scripts_mixed = True
            host_ascii, host_unicode = '.'.join(asc), '.'.join(uni)
            is_idn = nonascii or puny
            idn = {'is_idn': is_idn, 'punycode_in_text': puny, 'mixed_script': scripts_mixed}
            if is_idn: flags.append('IDN')
            if puny: flags.append('PUNYCODE')
            if scripts_mixed: flags.append('MIXED_SCRIPT')
    if ip:
        flags.append('IP_LITERAL')
        if ip['category'] != 'PUBLIC': flags.append('NON_PUBLIC_IP')
    reg = registrable(host_ascii) if host_ascii and not ip else None
    # lookalike: brand token in host (after confusable skeleton) but registrable domain is not one of the brand's
    if host_unicode and not ip:
        skel = ''.join(CONFUSABLES.get(c, c) for c in host_unicode.lower())
        for brand, doms in BRANDS.items():
            if brand in skel and (reg not in doms):
                flags.append('HOMOGLYPH_BRAND' if brand not in host_unicode.lower() else 'BRAND_NOT_OFFICIAL_DOMAIN')
                res['brand'] = brand; break
    if host_ascii and not ip:
        if host_ascii in SHORTENERS or reg in SHORTENERS: flags.append('SHORTENER')
        if host_ascii in MESSENGER_HOSTS or reg in MESSENGER_HOSTS: flags.append('MESSENGER_LINK')
        if host_ascii in APP_STORE_HOSTS: flags.append('APP_STORE_LINK')
        if len(host_ascii.split('.')) >= 5: flags.append('DEEP_SUBDOMAIN')
        if reg and reg.split('.')[-1] in ('test', 'invalid', 'example', 'localhost'): flags.append('RESERVED_TLD')
    pl = path.lower()
    if re.search(r'\.(?:apk|xapk|apks|apkm)(?:$|[/?#])', pl) or re.search(r'\.(?:apk|xapk|apks)(?:&|$)', query.lower()): flags.append('APK_DOWNLOAD')
    q_red, keys, sens = _redact_query(query)
    if sens: flags.append('SENSITIVE_QUERY')
    p_red = _redact_path(path)
    if p_red != path: flags.append('OPAQUE_PATH_TOKEN')
    if userinfo is not None: notes.append('USERINFO_REMOVED_FROM_DISPLAY')
    hostport = (host_ascii or '') + (':' + str(port) if port is not None else '')
    display = scheme + '://' + hostport + (p_red or '') + ('?' + q_red if q_red else '')
    external = scheme + '://' + hostport + (p_red or '/')       # query and fragment never leave the device
    res.update(host_ascii=host_ascii, host_unicode=host_unicode, port=port, registrable_domain=reg, display_url=display,
               external_url=external, ip=ip, idn=idn, query_keys=keys, flags=sorted(set(flags)), notes=notes,
               fetchable=bool(host_ascii) and 'INVALID_PORT' not in flags and not (ip and ip['category'] != 'PUBLIC'))
    return res


def intake(message: str, *, message_id: str = '', consent: dict | None = None, extra_urls=()) -> dict:
    """Stage 1 of LinkGuard. Never performs network access."""
    if type(message) is not str or len(message) > MAX_TEXT:
        raise ValueError('INVALID_MESSAGE')
    found = extract(message)
    for u in extra_urls:
        if type(u) is str and u.strip(): found.append({'raw': u.strip()[:2048], 'start': None, 'end': None})
    urls = []
    for f in found[:MAX_URLS]:
        a = analyze(f['raw']); a['start'], a['end'] = f['start'], f['end']; urls.append(a)
    c = consent or {}
    return {'message_id': message_id, 'url_count': len(urls), 'urls': urls,
            'consent': {'external_reputation': bool(c.get('external_reputation')), 'web_analysis': bool(c.get('web_analysis'))},
            'stage': 'INTAKE_DONE', 'network_used': False}
