"""Build a debug-signed Android APK of the 의심계 offline web app without any SDK binary.

Why: this build environment cannot reach Google's Android repositories, and executing
repackaged third-party copies of aapt2/d8/apksigner would put unverified code on the path
to a user's phone. Every byte of the APK is therefore produced here from public format
specifications, and the result is checked by independent parsers (androguard, apksigtool).

  classes.dex          DEX 035, one Activity: full-screen WebView over file:///android_asset/www
  AndroidManifest.xml  binary XML; no <uses-permission> at all (no INTERNET)
  resources.arsc       one mipmap entry (launcher icon)
  assets/www/*         the same web bundle as the desktop and PWA builds (apps/dist/web)
  signature            APK Signature Scheme v2, RSA-2048/SHA-256, self-signed debug key

Debug build: android:debuggable="true", signed with the repo's PUBLISHED debug key (not for store use).
v4.5: style/AppTheme (windowBackground #0B1020) + WebView background, so launch shows the brand colour, not white.
Usage: python tools/build_apk.py [--out apps/dist/IteraGuard_DoubtMeter_v4_9_android_debug.apk]
"""
from __future__ import annotations
import argparse, datetime, hashlib, io, json, struct, zipfile, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'apps' / 'dist' / 'web'
PKG = 'kr.iteraguard.doubtmeter'
ACT = 'kr.iteraguard.doubtmeter.MainActivity'
START_URL = 'file:///android_asset/www/index.html'
SHARE_EXTRA = 'android.intent.extra.TEXT'
VERSION_CODE, VERSION_NAME = 49, "4.9"
MIN_SDK, TARGET_SDK = 24, 34
# v4.5 launch surface. Framework IDs verified against AOSP core/res/res/values/public.xml
# (copy shipped in androguard/core/resources/public.xml): Theme.Black.NoTitleBar, attr windowBackground.
FW_THEME_BLACK_NOTITLE, ATTR_WINDOW_BACKGROUND = 0x01030009, 0x01010054
BRAND_BG_ARGB = 0xFF0B1020   # same as the web splash / theme-color, so there is no white flash at launch


def uleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n: return bytes(out)


def align(buf: bytearray, n: int):
    while len(buf) % n: buf.append(0)


# ----------------------------------------------------------------- DEX 035
class Dex:
    """Minimal DEX writer for one class. Index tables are sorted as the format requires."""
    T_THIS = 'Lkr/iteraguard/doubtmeter/MainActivity;'
    T_ACT, T_BUNDLE, T_CTX = 'Landroid/app/Activity;', 'Landroid/os/Bundle;', 'Landroid/content/Context;'
    T_VIEW, T_WV, T_WS, T_STR = 'Landroid/view/View;', 'Landroid/webkit/WebView;', 'Landroid/webkit/WebSettings;', 'Ljava/lang/String;'
    T_INTENT, T_B64, T_BYTES = 'Landroid/content/Intent;', 'Landroid/util/Base64;', '[B'
    # v4.7 share-sheet input: ACTION_SEND text/plain. The shared text is handed to the local page only (URL fragment,
    # base64url, UTF-8). Nothing is sent anywhere; no SMS permission is requested.

    def __init__(self):
        # (class, name, return, params)
        self.methods = [
            (self.T_ACT, '<init>', 'V', ()), (self.T_ACT, 'onCreate', 'V', (self.T_BUNDLE,)),
            (self.T_ACT, 'requestWindowFeature', 'Z', ('I',)), (self.T_ACT, 'setContentView', 'V', (self.T_VIEW,)),
            (self.T_ACT, 'onBackPressed', 'V', ()),
            (self.T_WV, '<init>', 'V', (self.T_CTX,)), (self.T_WV, 'getSettings', self.T_WS, ()),
            (self.T_WV, 'loadUrl', 'V', (self.T_STR,)), (self.T_WV, 'canGoBack', 'Z', ()), (self.T_WV, 'goBack', 'V', ()),
            (self.T_WS, 'setJavaScriptEnabled', 'V', ('Z',)), (self.T_WS, 'setDomStorageEnabled', 'V', ('Z',)),
            (self.T_WV, 'setBackgroundColor', 'V', ('I',)),
            (self.T_ACT, 'getIntent', self.T_INTENT, ()), (self.T_INTENT, 'getStringExtra', self.T_STR, (self.T_STR,)),
            (self.T_STR, 'getBytes', self.T_BYTES, (self.T_STR,)), (self.T_B64, 'encodeToString', self.T_STR, (self.T_BYTES, 'I')),
            (self.T_STR, 'concat', self.T_STR, (self.T_STR,)),
            (self.T_THIS, '<init>', 'V', ()), (self.T_THIS, 'onCreate', 'V', (self.T_BUNDLE,)), (self.T_THIS, 'onBackPressed', 'V', ()),
        ]
        self.fields = [(self.T_THIS, 'web', self.T_WV)]
        types = {t for m in self.methods for t in (m[0], m[2], *m[3])} | {f[0] for f in self.fields} | {f[2] for f in self.fields}
        shorty = lambda r, ps: ''.join('L' if t[0] in 'L[' else t for t in (r, *ps))
        self.protos_raw = sorted({(m[2], m[3]) for m in self.methods})
        strings = set(types) | {m[1] for m in self.methods} | {f[1] for f in self.fields} | {shorty(r, p) for r, p in self.protos_raw} | {START_URL, SHARE_EXTRA, 'UTF-8', '#share='}
        self.strings = sorted(strings, key=lambda s: s.encode('utf-16-be'))
        self.si = {s: i for i, s in enumerate(self.strings)}
        self.types = sorted(types, key=lambda t: self.si[t])
        self.ti = {t: i for i, t in enumerate(self.types)}
        self.protos = sorted(self.protos_raw, key=lambda p: (self.ti[p[0]], [self.ti[x] for x in p[1]]))
        self.pi = {p: i for i, p in enumerate(self.protos)}
        self.shorty = {p: shorty(*p) for p in self.protos}
        self.meths = sorted(self.methods, key=lambda m: (self.ti[m[0]], self.si[m[1]], self.pi[(m[2], m[3])]))
        self.mi = {m[:2] + (m[2], m[3]): i for i, m in enumerate(self.meths)}
        self.flds = sorted(self.fields, key=lambda f: (self.ti[f[0]], self.si[f[1]], self.ti[f[2]]))
        self.fi = {f: i for i, f in enumerate(self.flds)}

    def m(self, cls, name, ret, params=()):
        return self.mi[(cls, name, ret, tuple(params))]

    @staticmethod
    def invoke(op, method, regs):
        r = list(regs) + [0] * (5 - len(regs))
        return struct.pack('<HHH', (len(regs) << 12) | op, method, (r[3] << 12) | (r[2] << 8) | (r[1] << 4) | r[0])

    def code_init(self):
        insns = self.invoke(0x70, self.m(self.T_ACT, '<init>', 'V'), [0]) + struct.pack('<H', 0x0e)
        return (1, 1, 1, insns)

    def code_on_create(self):
        web = self.fi[(self.T_THIS, 'web', self.T_WV)]
        i = b''
        i += self.invoke(0x6f, self.m(self.T_ACT, 'onCreate', 'V', [self.T_BUNDLE]), [3, 4])   # super.onCreate(b)
        i += struct.pack('<H', (1 << 12) | (0 << 8) | 0x12)                                  # const/4 v0, 1
        i += self.invoke(0x6e, self.m(self.T_ACT, 'requestWindowFeature', 'Z', ['I']), [3, 0])  # FEATURE_NO_TITLE
        i += struct.pack('<HH', (0 << 8) | 0x22, self.ti[self.T_WV])                          # new-instance v0, WebView
        i += self.invoke(0x70, self.m(self.T_WV, '<init>', 'V', [self.T_CTX]), [0, 3])
        i += struct.pack('<HH', (3 << 12) | (0 << 8) | 0x5b, web)                             # iput-object v0, v3, web
        i += self.invoke(0x6e, self.m(self.T_WV, 'getSettings', self.T_WS), [0])
        i += struct.pack('<H', (1 << 8) | 0x0c)                                               # move-result-object v1
        i += struct.pack('<H', (1 << 12) | (2 << 8) | 0x12)                                  # const/4 v2, 1
        i += self.invoke(0x6e, self.m(self.T_WS, 'setJavaScriptEnabled', 'V', ['Z']), [1, 2])
        i += self.invoke(0x6e, self.m(self.T_WS, 'setDomStorageEnabled', 'V', ['Z']), [1, 2])
        i += struct.pack('<HI', (2 << 8) | 0x14, BRAND_BG_ARGB)                             # const v2, #0xFF0B1020
        i += self.invoke(0x6e, self.m(self.T_WV, 'setBackgroundColor', 'V', ['I']), [0, 2])  # web.setBackgroundColor(v2)
        i += self.invoke(0x6e, self.m(self.T_ACT, 'setContentView', 'V', [self.T_VIEW]), [3, 0])
        i += struct.pack('<HH', (1 << 8) | 0x1a, self.si[START_URL])                          # const-string v1, url
        # v4.7: if launched from the share sheet, append '#share=' + base64url(UTF-8 text) to the local page URL
        share = b''
        share += self.invoke(0x6e, self.m(self.T_ACT, 'getIntent', self.T_INTENT), [3])          # getIntent()
        share += struct.pack('<H', (2 << 8) | 0x0c)                                            # move-result-object v2
        skip1 = len(share)
        share += struct.pack('<Hh', (2 << 8) | 0x38, 0)                                        # if-eqz v2, :load (patched)
        share += struct.pack('<HH', (4 << 8) | 0x1a, self.si[SHARE_EXTRA])                      # const-string v4, EXTRA_TEXT
        share += self.invoke(0x6e, self.m(self.T_INTENT, 'getStringExtra', self.T_STR, [self.T_STR]), [2, 4])
        share += struct.pack('<H', (2 << 8) | 0x0c)                                            # move-result-object v2
        skip2 = len(share)
        share += struct.pack('<Hh', (2 << 8) | 0x38, 0)                                        # if-eqz v2, :load (patched)
        share += struct.pack('<HH', (4 << 8) | 0x1a, self.si['UTF-8'])
        share += self.invoke(0x6e, self.m(self.T_STR, 'getBytes', self.T_BYTES, [self.T_STR]), [2, 4])
        share += struct.pack('<H', (2 << 8) | 0x0c)
        share += struct.pack('<Hh', (4 << 8) | 0x13, 10)                                       # const/16 v4, NO_WRAP|URL_SAFE (2|8)
        share += self.invoke(0x71, self.m(self.T_B64, 'encodeToString', self.T_STR, [self.T_BYTES, 'I']), [2, 4])
        share += struct.pack('<H', (2 << 8) | 0x0c)
        share += struct.pack('<HH', (4 << 8) | 0x1a, self.si['#share='])
        share += self.invoke(0x6e, self.m(self.T_STR, 'concat', self.T_STR, [self.T_STR]), [1, 4])
        share += struct.pack('<H', (1 << 8) | 0x0c)
        share += self.invoke(0x6e, self.m(self.T_STR, 'concat', self.T_STR, [self.T_STR]), [1, 2])
        share += struct.pack('<H', (1 << 8) | 0x0c)
        share = bytearray(share)
        for at in (skip1, skip2):                                                              # branch offsets in 16-bit units
            struct.pack_into('<h', share, at + 2, (len(share) - at) // 2)
        i += bytes(share)
        i += self.invoke(0x6e, self.m(self.T_WV, 'loadUrl', 'V', [self.T_STR]), [0, 1])
        i += struct.pack('<H', 0x0e)                                                          # return-void
        return (5, 2, 2, i)

    def code_on_back(self):
        web = self.fi[(self.T_THIS, 'web', self.T_WV)]
        i = b''
        i += struct.pack('<HH', (1 << 12) | (0 << 8) | 0x54, web)                             # 0: iget-object v0, v1, web
        i += self.invoke(0x6e, self.m(self.T_WV, 'canGoBack', 'Z'), [0])                     # 2
        i += struct.pack('<H', (0 << 8) | 0x0a)                                               # 5: move-result v0
        i += struct.pack('<Hh', (0 << 8) | 0x38, 8)                                           # 6: if-eqz v0, +8 -> 14
        i += struct.pack('<HH', (1 << 12) | (0 << 8) | 0x54, web)                             # 8
        i += self.invoke(0x6e, self.m(self.T_WV, 'goBack', 'V'), [0])                        # 10
        i += struct.pack('<H', 0x0e)                                                          # 13: return-void
        i += self.invoke(0x6f, self.m(self.T_ACT, 'onBackPressed', 'V'), [1])                # 14: super.onBackPressed()
        i += struct.pack('<H', 0x0e)                                                          # 17
        return (2, 1, 1, i)

    def build(self) -> bytes:
        n_s, n_t, n_p, n_f, n_m = len(self.strings), len(self.types), len(self.protos), len(self.flds), len(self.meths)
        off_s = 0x70; off_t = off_s + 4 * n_s; off_p = off_t + 4 * n_t; off_f = off_p + 12 * n_p
        off_m = off_f + 8 * n_f; off_c = off_m + 8 * n_m; data_off = off_c + 32
        data = bytearray(); base = data_off
        def here(): return base + len(data)
        # code items (4-aligned)
        codes = {}
        for key, (regs, ins, outs, insns) in (('init', self.code_init()), ('create', self.code_on_create()), ('back', self.code_on_back())):
            align(data, 4); codes[key] = here()
            data += struct.pack('<HHHHII', regs, ins, outs, 0, 0, len(insns) // 2) + insns
        code_count = 3
        # type lists (4-aligned) for proto parameters
        align(data, 4); tl_start = here(); tl_off = {}
        for p in self.protos:
            if p[1] and p[1] not in tl_off:
                align(data, 4); tl_off[p[1]] = here()
                data += struct.pack('<I', len(p[1])) + b''.join(struct.pack('<H', self.ti[t]) for t in p[1])
        n_tl = len(tl_off)
        # string data
        sd_start = here(); str_off = []
        for s in self.strings:
            str_off.append(here())
            data += uleb(len(s.encode('utf-16-le')) // 2) + s.encode('utf-8') + b'\0'   # ASCII-only here, so MUTF-8 == UTF-8
        # class data
        cd_off = here()
        web = self.fi[(self.T_THIS, 'web', self.T_WV)]
        direct = [(self.m(self.T_THIS, '<init>', 'V'), 0x10001, codes['init'])]
        virtual = sorted([(self.m(self.T_THIS, 'onCreate', 'V', [self.T_BUNDLE]), 0x4, codes['create']),
                          (self.m(self.T_THIS, 'onBackPressed', 'V'), 0x1, codes['back'])])
        data += uleb(0) + uleb(1) + uleb(len(direct)) + uleb(len(virtual))
        data += uleb(web) + uleb(0x2)
        for group in (direct, virtual):
            prev = 0
            for idx, flags, off in group:
                data += uleb(idx - prev) + uleb(flags) + uleb(off); prev = idx
        # map list (4-aligned)
        align(data, 4); map_off = here()
        items = [(0x0000, 1, 0), (0x0001, n_s, off_s), (0x0002, n_t, off_t), (0x0003, n_p, off_p), (0x0004, n_f, off_f),
                 (0x0005, n_m, off_m), (0x0006, 1, off_c), (0x2001, code_count, codes['init']), (0x1001, n_tl, tl_start),
                 (0x2002, n_s, sd_start), (0x2000, 1, cd_off), (0x1000, 1, map_off)]
        items.sort(key=lambda x: x[2])
        data += struct.pack('<I', len(items)) + b''.join(struct.pack('<HHII', t, 0, n, o) for t, n, o in items)
        # id tables
        ids = bytearray()
        ids += b''.join(struct.pack('<I', o) for o in str_off)
        ids += b''.join(struct.pack('<I', self.si[t]) for t in self.types)
        ids += b''.join(struct.pack('<III', self.si[self.shorty[p]], self.ti[p[0]], tl_off.get(p[1], 0)) for p in self.protos)
        ids += b''.join(struct.pack('<HHI', self.ti[f[0]], self.ti[f[2]], self.si[f[1]]) for f in self.flds)
        ids += b''.join(struct.pack('<HHI', self.ti[m[0]], self.pi[(m[2], m[3])], self.si[m[1]]) for m in self.meths)
        ids += struct.pack('<IIIIIIII', self.ti[self.T_THIS], 0x1, self.ti[self.T_ACT], 0, 0xFFFFFFFF, 0, cd_off, 0)
        assert 0x70 + len(ids) == data_off
        size = data_off + len(data)
        hdr = bytearray(b'dex\n035\0' + b'\0' * 24)
        hdr += struct.pack('<IIIIIIIIIIIIIIIIIIII', size, 0x70, 0x12345678, 0, 0, map_off, n_s, off_s, n_t, off_t,
                           n_p, off_p, n_f, off_f, n_m, off_m, 1, off_c, len(data), data_off)
        out = bytearray(hdr) + ids + data
        out[12:32] = hashlib.sha1(bytes(out[32:])).digest()
        out[8:12] = struct.pack('<I', zlib.adler32(bytes(out[12:])))
        return bytes(out)


# ----------------------------------------------------------------- string pool (shared by XML and ARSC)
def string_pool(strings, utf8=True) -> bytes:
    offsets, body = [], bytearray()
    for s in strings:
        offsets.append(len(body))
        if utf8:
            b = s.encode('utf-8'); u16 = len(s.encode('utf-16-le')) // 2
            for n in (u16, len(b)):
                body += bytes([n]) if n < 0x80 else bytes([0x80 | (n >> 8), n & 0xFF])
            body += b + b'\0'
        else:
            e = s.encode('utf-16-le'); body += struct.pack('<H', len(e) // 2) + e + b'\0\0'
    align(body, 4)
    start = 28 + 4 * len(strings)
    size = start + len(body)
    return struct.pack('<HHIIIIII', 0x0001, 28, size, len(strings), 0, 0x100 if utf8 else 0, start, 0) + b''.join(struct.pack('<I', o) for o in offsets) + bytes(body)


# ----------------------------------------------------------------- binary AndroidManifest.xml
ATTR_IDS = {'theme': 0x01010000, 'label': 0x01010001, 'icon': 0x01010002, 'name': 0x01010003, 'debuggable': 0x0101000f,
            'exported': 0x01010010, 'configChanges': 0x0101001f, 'minSdkVersion': 0x0101020c, 'versionCode': 0x0101021b,
            'versionName': 0x0101021c, 'targetSdkVersion': 0x01010270, 'allowBackup': 0x01010280, 'hardwareAccelerated': 0x010102d3,
            'mimeType': 0x01010026}
T_REF, T_STRING, T_DEC, T_HEX, T_BOOL = 0x01, 0x03, 0x10, 0x11, 0x12
ANDROID_NS = 'http://schemas.android.com/apk/res/android'


def manifest_xml(icon_res_id: int, theme_res_id: int) -> bytes:
    # (tag, [(ns?, name, type, value)], children)
    tree = ('manifest', [(False, 'package', T_STRING, PKG), (True, 'versionCode', T_DEC, VERSION_CODE), (True, 'versionName', T_STRING, VERSION_NAME)], [
        ('uses-sdk', [(True, 'minSdkVersion', T_DEC, MIN_SDK), (True, 'targetSdkVersion', T_DEC, TARGET_SDK)], []),
        ('application', [(True, 'theme', T_REF, theme_res_id), (True, 'label', T_STRING, '의심계'), (True, 'icon', T_REF, icon_res_id), (True, 'debuggable', T_BOOL, True),
                         (True, 'allowBackup', T_BOOL, False), (True, 'hardwareAccelerated', T_BOOL, True)], [
            ('activity', [(True, 'name', T_STRING, ACT), (True, 'exported', T_BOOL, True), (True, 'configChanges', T_HEX, 0x0DA0)], [
                ('intent-filter', [], [
                    ('action', [(True, 'name', T_STRING, 'android.intent.action.MAIN')], []),
                    ('category', [(True, 'name', T_STRING, 'android.intent.category.LAUNCHER')], [])]),
                # v4.7: appear in the share sheet for plain text (e.g. a message long-pressed in the SMS app -> Share)
                ('intent-filter', [], [
                    ('action', [(True, 'name', T_STRING, 'android.intent.action.SEND')], []),
                    ('category', [(True, 'name', T_STRING, 'android.intent.category.DEFAULT')], []),
                    ('data', [(True, 'mimeType', T_STRING, 'text/plain')], [])])])])])
    attr_names = []
    def walk(n):
        for ns, name, *_ in n[1]:
            if ns and name not in attr_names: attr_names.append(name)
        for c in n[2]: walk(c)
    walk(tree)
    attr_names.sort(key=lambda a: ATTR_IDS[a])
    pool = list(attr_names)
    def add(s):
        if s not in pool: pool.append(s)
        return pool.index(s)
    add('android'); add(ANDROID_NS)
    def collect(n):
        add(n[0])
        for ns, name, typ, val in n[1]:
            add(name)
            if typ == T_STRING: add(val)
        for c in n[2]: collect(c)
    collect(tree)
    body = bytearray()
    body += struct.pack('<HHIIIII', 0x0100, 16, 24, 1, 0xFFFFFFFF, pool.index('android'), pool.index(ANDROID_NS))
    def emit(n):
        attrs = sorted(n[1], key=lambda a: (ATTR_IDS.get(a[1], 0) if a[0] else 0, a[1]))
        raw = bytearray()
        for ns, name, typ, val in attrs:
            ns_i = pool.index(ANDROID_NS) if ns else 0xFFFFFFFF
            if typ == T_STRING: rawv, data = pool.index(val), pool.index(val)
            elif typ == T_BOOL: rawv, data = 0xFFFFFFFF, 0xFFFFFFFF if val else 0
            else: rawv, data = 0xFFFFFFFF, val
            raw += struct.pack('<IIIHBBI', ns_i, pool.index(name), rawv, 8, 0, typ, data)
        size = 16 + 20 + len(raw)
        body.extend(struct.pack('<HHIII', 0x0102, 16, size, 1, 0xFFFFFFFF) + struct.pack('<IIHHHHHH', 0xFFFFFFFF, pool.index(n[0]), 20, 20, len(attrs), 0, 0, 0) + raw)
        for c in n[2]: emit(c)
        body.extend(struct.pack('<HHIIIII', 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, pool.index(n[0])))
    emit(tree)
    body += struct.pack('<HHIIIII', 0x0101, 16, 24, 1, 0xFFFFFFFF, pool.index('android'), pool.index(ANDROID_NS))
    sp = string_pool(pool)
    rmap = struct.pack('<HHI', 0x0180, 8, 8 + 4 * len(attr_names)) + b''.join(struct.pack('<I', ATTR_IDS[a]) for a in attr_names)
    total = 8 + len(sp) + len(rmap) + len(body)
    return struct.pack('<HHI', 0x0003, 8, total) + sp + rmap + bytes(body)


# ----------------------------------------------------------------- resources.arsc (mipmap/ic_launcher + style/AppTheme)
def resources_arsc(icon_path: str) -> tuple[bytes, int, int]:
    pkg_id = 0x7F
    gpool = string_pool([icon_path])
    types = string_pool(['mipmap', 'style'], utf8=False); keys = string_pool(['ic_launcher', 'AppTheme'], utf8=False)
    config = struct.pack('<I', 64) + b'\0' * 60
    def spec(type_id): return struct.pack('<HHIBBHI', 0x0202, 16, 16 + 4, type_id, 0, 0, 1) + struct.pack('<I', 0)
    def ttype(type_id, entry):
        start = 20 + 64 + 4
        return struct.pack('<HHIBBHII', 0x0201, 20 + 64, start + len(entry), type_id, 0, 0, 1, start) + config + struct.pack('<I', 0) + entry
    # mipmap/ic_launcher -> string "res/mipmap/ic_launcher.png" (global pool index 0)
    icon_entry = struct.pack('<HHI', 8, 0, 0) + struct.pack('<HBBI', 8, 0, T_STRING, 0)
    # style/AppTheme: complex entry, parent Theme.Black.NoTitleBar, windowBackground = #FF0B1020
    style_entry = (struct.pack('<HHI', 16, 0x0001, 1) + struct.pack('<II', FW_THEME_BLACK_NOTITLE, 1) +
                   struct.pack('<I', ATTR_WINDOW_BACKGROUND) + struct.pack('<HBBI', 8, 0, 0x1C, BRAND_BG_ARGB))
    name = 'kr.iteraguard.doubtmeter'.encode('utf-16-le').ljust(256, b'\0')
    hdr_size = 288
    type_off = hdr_size; key_off = hdr_size + len(types)
    pkg_body = types + keys + spec(1) + ttype(1, icon_entry) + spec(2) + ttype(2, style_entry)
    pkg = struct.pack('<HHII', 0x0200, hdr_size, hdr_size + len(pkg_body), pkg_id) + name + struct.pack('<IIIII', type_off, 2, key_off, 2, 0) + pkg_body
    table = struct.pack('<HHII', 0x0002, 12, 12 + len(gpool) + len(pkg), 1) + gpool + pkg
    return table, (pkg_id << 24) | (1 << 16), (pkg_id << 24) | (2 << 16)


# ----------------------------------------------------------------- zip with 4-byte alignment for stored entries
def write_zip(entries) -> bytes:
    buf = io.BytesIO(); central = []
    for name, data, store in entries:
        nm = name.encode()
        comp = data if store else zlib.compress(data, 9)[2:-4]
        method = 0 if store else 8
        crc = zlib.crc32(data) & 0xFFFFFFFF
        off = buf.tell()
        extra = b''
        if store:
            pad = (-(off + 30 + len(nm))) % 4
            extra = b'\0' * pad
        buf.write(struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, 0, method, 0, 0x5A21, crc, len(comp), len(data), len(nm), len(extra)) + nm + extra + comp)
        central.append(struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 20, 20, 0, method, 0, 0x5A21, crc, len(comp), len(data), len(nm), 0, 0, 0, 0, 0, off) + nm)
    cd_off = buf.tell(); cd = b''.join(central); buf.write(cd)
    buf.write(struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(central), len(central), len(cd), cd_off, 0))
    return buf.getvalue()


# ----------------------------------------------------------------- APK Signature Scheme v2
def sign_v2(apk: bytes, key, cert_der: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import serialization
    eocd = apk.rfind(b'PK\x05\x06'); cd_off = struct.unpack('<I', apk[eocd + 16:eocd + 20])[0]
    sections = [apk[:cd_off], apk[cd_off:eocd], apk[eocd:]]
    def chunked_digest(secs):
        chunks = []
        for s in secs:
            for i in range(0, len(s), 1 << 20):
                c = s[i:i + (1 << 20)]
                chunks.append(hashlib.sha256(b'\xa5' + struct.pack('<I', len(c)) + c).digest())
        return hashlib.sha256(b'\x5a' + struct.pack('<I', len(chunks)) + b''.join(chunks)).digest()
    lp = lambda b: struct.pack('<I', len(b)) + b
    ALG = 0x0103  # RSASSA-PKCS1-v1_5 with SHA2-256
    digest = chunked_digest(sections)
    signed_data = lp(lp(struct.pack('<I', ALG) + lp(digest))) + lp(lp(cert_der)) + lp(b'')
    sig = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    pub = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    signer = lp(signed_data) + lp(lp(struct.pack('<I', ALG) + lp(sig))) + lp(pub)
    v2 = lp(lp(signer))
    pair = struct.pack('<QI', len(v2) + 4, 0x7109871a) + v2
    size = len(pair) + 8 + 16
    block = struct.pack('<Q', size) + pair + struct.pack('<Q', size) + b'APK Sig Block 42'
    new_eocd = bytearray(sections[2]); new_eocd[16:20] = struct.pack('<I', cd_off + len(block))
    return sections[0] + block + sections[1] + bytes(new_eocd)


KEY_DIR = ROOT / 'apps' / 'mobile' / 'debug-key'


def debug_key():
    """Debug-only signing identity, kept in the repo (like Android's public debug.keystore) so
    that a rebuilt APK installs over the previous one and the build is byte-reproducible.
    Never use this key for a store release."""
    from cryptography.hazmat.primitives import serialization
    kp, cp = KEY_DIR / 'debug_key_DO_NOT_USE_FOR_RELEASE.pem', KEY_DIR / 'debug_cert.der'
    if kp.is_file() and cp.is_file():
        return serialization.load_pem_private_key(kp.read_bytes(), password=None), cp.read_bytes()
    key, cert = _new_debug_key()
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    kp.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    cp.write_bytes(cert)
    return key, cert


def _new_debug_key():
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'IteraGuard Debug'), x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'IteraGuard (hackathon demo)')])
    now = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now).not_valid_after(now + datetime.timedelta(days=365 * 30))
            .sign(key, hashes.SHA256()))
    return key, cert.public_bytes(serialization.Encoding.DER)


def build(out: Path) -> dict:
    if not (WEB / 'index.html').is_file():
        raise SystemExit('apps/dist/web missing: run python tools/build_apps.py first')
    icon_name = 'res/mipmap/ic_launcher.png'
    arsc, icon_id, theme_id = resources_arsc(icon_name)
    dex = Dex().build()
    manifest = manifest_xml(icon_id, theme_id)
    entries = [('AndroidManifest.xml', manifest, False), ('classes.dex', dex, False), ('resources.arsc', arsc, True),
               (icon_name, (WEB / 'icons/icon-192.png').read_bytes(), True)]
    for p in sorted(x for x in WEB.rglob('*') if x.is_file()):
        rel = p.relative_to(WEB).as_posix()
        if rel == 'sw.js':
            continue  # service workers do not apply to file:///android_asset
        entries.append(('assets/www/' + rel, p.read_bytes(), p.suffix == '.png'))
    unsigned = write_zip(entries)
    key, cert = debug_key()
    apk = sign_v2(unsigned, key, cert)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(apk)
    return {'apk': out.relative_to(ROOT).as_posix() if out.is_relative_to(ROOT) else str(out), 'bytes': len(apk), 'sha256': hashlib.sha256(apk).hexdigest(),
            'dex_sha256': hashlib.sha256(dex).hexdigest(), 'cert_sha256': hashlib.sha256(cert).hexdigest(),
            'entries': len(entries), 'min_sdk': MIN_SDK, 'target_sdk': TARGET_SDK, 'debuggable': True, 'permissions': []}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=str(ROOT / 'apps/dist/IteraGuard_DoubtMeter_v4_9_android_debug.apk'))
    print(json.dumps(build(Path(ap.parse_args().out)), indent=1))
