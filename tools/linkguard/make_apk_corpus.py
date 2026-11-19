"""Build the inert APK test corpus for LinkGuard (no executable code: DEX files carry only string/type tables).

Samples are synthetic fixtures for parser and policy tests. None of them can run, and none contain real malware.
The 'normal' sample is our own debug APK when it exists.

usage: python tools/linkguard/make_apk_corpus.py --out tests_data/apk_corpus
"""
from __future__ import annotations
import argparse, hashlib, io, json, struct, sys, zipfile, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.release_metadata import load_distribution
NS = 'http://schemas.android.com/apk/res/android'
IDS = {'name': 0x01010003, 'exported': 0x01010010, 'permission': 0x01010006, 'versionCode': 0x0101021b, 'versionName': 0x0101021c,
       'minSdkVersion': 0x0101020c, 'targetSdkVersion': 0x01010270, 'debuggable': 0x0101000f}
T_STR, T_DEC, T_BOOL = 0x03, 0x10, 0x12


def _pool(strings):
    offs, body = [], bytearray()
    for s in strings:
        offs.append(len(body)); b = s.encode('utf-8'); u = len(s.encode('utf-16-le')) // 2
        for n in (u, len(b)):
            body += bytes([0x80 | (n >> 8), n & 0xFF]) if n > 0x7F else bytes([n])
        body += b + b'\0'
    while len(body) % 4: body += b'\0'
    hdr = 28; start = hdr + 4 * len(offs)
    return struct.pack('<HHIIIIII', 0x0001, hdr, start + len(body), len(strings), 0, 0x100, start, 0) + b''.join(struct.pack('<I', o) for o in offs) + bytes(body)


def axml(tree):
    """tree = (tag, [(android_ns:bool, name, type, value)], [children])"""
    names = []
    def walk(n):
        for ns, nm, *_ in n[1]:
            if ns and nm not in names: names.append(nm)
        for c in n[2]: walk(c)
    walk(tree); names.sort(key=lambda a: IDS[a])
    pool = list(names)
    def add(s):
        if s not in pool: pool.append(s)
        return pool.index(s)
    add('android'); add(NS)
    def collect(n):
        add(n[0])
        for ns, nm, t, v in n[1]:
            add(nm)
            if t == T_STR: add(v)
        for c in n[2]: collect(c)
    collect(tree)
    body = bytearray(struct.pack('<HHIIIII', 0x0100, 16, 24, 1, 0xFFFFFFFF, pool.index('android'), pool.index(NS)))
    def emit(n):
        raw = bytearray()
        for ns, nm, t, v in n[1]:
            if t == T_STR: rv, d = pool.index(v), pool.index(v)
            elif t == T_BOOL: rv, d = 0xFFFFFFFF, 0xFFFFFFFF if v else 0
            else: rv, d = 0xFFFFFFFF, v
            raw += struct.pack('<IIIHBBI', pool.index(NS) if ns else 0xFFFFFFFF, pool.index(nm), rv, 8, 0, t, d)
        body.extend(struct.pack('<HHIII', 0x0102, 16, 36 + len(raw), 1, 0xFFFFFFFF) +
                    struct.pack('<IIHHHHHH', 0xFFFFFFFF, pool.index(n[0]), 20, 20, len(n[1]), 0, 0, 0) + raw)
        for c in n[2]: emit(c)
        body.extend(struct.pack('<HHIIIII', 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, pool.index(n[0])))
    emit(tree)
    body += struct.pack('<HHIIIII', 0x0101, 16, 24, 1, 0xFFFFFFFF, pool.index('android'), pool.index(NS))
    sp = _pool(pool)
    rmap = struct.pack('<HHI', 0x0180, 8, 8 + 4 * len(names)) + b''.join(struct.pack('<I', IDS[a]) for a in names)
    return struct.pack('<HHI', 0x0003, 8, 8 + len(sp) + len(rmap) + len(body)) + sp + rmap + bytes(body)


def _uleb(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n: return bytes(out)


def strings_dex(strings, types):
    """A DEX header + string_ids + type_ids only. Not loadable by ART; enough for string-table scanning."""
    allstr = sorted(set(strings) | set(types), key=lambda s: s.encode('utf-16-be'))
    si = {s: i for i, s in enumerate(allstr)}
    tlist = sorted(set(types), key=lambda t: si[t])
    off_s = 0x70; off_t = off_s + 4 * len(allstr); data_off = off_t + 4 * len(tlist)
    data = bytearray(); offs = []
    for s in allstr:
        offs.append(data_off + len(data)); data += _uleb(len(s.encode('utf-16-le')) // 2) + s.encode('utf-8') + b'\0'
    size = data_off + len(data)
    hdr = bytearray(b'dex\n035\0' + b'\0' * 24)
    hdr += struct.pack('<IIIIIIIIIIIIIIIIIIII', size, 0x70, 0x12345678, 0, 0, 0, len(allstr), off_s, len(tlist), off_t,
                       0, 0, 0, 0, 0, 0, 0, 0, len(data), data_off)
    out = hdr + b''.join(struct.pack('<I', o) for o in offs) + b''.join(struct.pack('<I', si[t]) for t in tlist) + data
    out[12:32] = hashlib.sha1(bytes(out[32:])).digest(); out[8:12] = struct.pack('<I', zlib.adler32(bytes(out[12:])))
    return bytes(out)


def zipbytes(entries):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, d in entries:
            zi = zipfile.ZipInfo(n, date_time=(2026, 11, 2, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, d)
    return b.getvalue()


def manifest(pkg, perms=(), comps=(), debuggable=False):
    app_children = []
    for typ, name, exported, permission, actions in comps:
        attrs = [(True, 'name', T_STR, name)]
        if exported is not None: attrs.append((True, 'exported', T_BOOL, exported))
        if permission: attrs.append((True, 'permission', T_STR, permission))
        kids = [('intent-filter', [], [('action', [(True, 'name', T_STR, a)], []) for a in actions])] if actions else []
        app_children.append((typ, sorted(attrs, key=lambda a: IDS[a[1]]), kids))
    return axml(('manifest', [(False, 'package', T_STR, pkg), (True, 'versionCode', T_DEC, 1), (True, 'versionName', T_STR, '1.0')], [
        ('uses-sdk', [(True, 'minSdkVersion', T_DEC, 24), (True, 'targetSdkVersion', T_DEC, 34)], []),
        *[('uses-permission', [(True, 'name', T_STR, p)], []) for p in perms],
        ('application', [(True, 'debuggable', T_BOOL, debuggable)], app_children)]))


def build(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    samples = {}
    def put(name, data, expect):
        (out / name).write_bytes(data); samples[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'expect': expect}
    # 1. normal: benign utility, internet only
    put('normal_utility.apk', zipbytes([('AndroidManifest.xml', manifest('com.example.notes', ['android.permission.INTERNET'],
        [('activity', 'com.example.notes.Main', True, None, ['android.intent.action.MAIN'])])),
        ('classes.dex', strings_dex(['https://api.example.com/v1', 'Notes'], ['Lcom/example/notes/Main;', 'Landroid/app/Activity;', 'Ljava/lang/String;'])),
        ('META-INF/CERT.RSA', b'0')]), {'state': 'NO_KNOWN_THREAT_FOUND'})
    # 2. over-permissioned "delivery tracker": SMS + accessibility + overlay + SMS receiver + dynamic code (capability pattern only)
    put('overperm_tracker.apk', zipbytes([('AndroidManifest.xml', manifest('com.parcel.track.kr', [
        'android.permission.INTERNET', 'android.permission.READ_SMS', 'android.permission.RECEIVE_SMS', 'android.permission.SEND_SMS',
        'android.permission.READ_CONTACTS', 'android.permission.SYSTEM_ALERT_WINDOW', 'android.permission.READ_PHONE_STATE',
        'android.permission.REQUEST_INSTALL_PACKAGES'],
        [('activity', 'com.parcel.track.kr.Main', True, None, ['android.intent.action.MAIN']),
         ('receiver', 'com.parcel.track.kr.R', None, None, ['android.provider.Telephony.SMS_RECEIVED']),
         ('service', 'com.parcel.track.kr.A', True, 'android.permission.BIND_ACCESSIBILITY_SERVICE', ['android.accessibilityservice.AccessibilityService'])])),
        ('classes.dex', strings_dex(['sendTextMessage', 'content://sms/inbox', 'http://203.0.113.77:8080/up', 'performGlobalAction', 'TYPE_APPLICATION_OVERLAY'],
            ['Lcom/parcel/track/kr/Main;', 'Landroid/telephony/SmsManager;', 'Ldalvik/system/DexClassLoader;',
             'Landroid/accessibilityservice/AccessibilityService;', 'Ljava/lang/String;'])),
        ('assets/payload.dex', b'dex\n035\0'), ('META-INF/CERT.RSA', b'0')]), {'state': 'SUSPICIOUS'})
    # 3. obfuscated (R8-style short names) but low-risk permissions
    obf_types = ['L%s/%s;' % (p, c) for p in ('a', 'b', 'o') for c in 'abcdefghijklmnopqrstuv'] + ['Lcom/game/puzzle/App;']
    put('obfuscated_game.apk', zipbytes([('AndroidManifest.xml', manifest('com.game.puzzle', ['android.permission.INTERNET'],
        [('activity', 'com.game.puzzle.App', True, None, ['android.intent.action.MAIN'])])),
        ('classes.dex', strings_dex(['https://cdn.example.net/levels'], obf_types)), ('lib/arm64-v8a/libgame.so', b'\x7fELF' + b'\0' * 60),
        ('META-INF/CERT.RSA', b'0')]), {'state': 'NO_KNOWN_THREAT_FOUND', 'obfuscation_likely': True})
    # 4. extension mismatch: PDF bytes named .apk
    put('mismatch_pdf.apk', b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n', {'state': 'SCAN_FAILED', 'finding': 'NOT_AN_APK_CONTAINER_EXTENSION_MISMATCH'})
    # 5. zip without manifest
    put('no_manifest.apk', zipbytes([('readme.txt', b'hello')]), {'state': 'SCAN_FAILED', 'finding': 'NO_ANDROID_MANIFEST'})
    # 6. zip-slip path traversal
    put('zipslip.apk', zipbytes([('AndroidManifest.xml', manifest('com.x.y')), ('../../data/evil.so', b'x')]), {'state': 'SUSPICIOUS', 'finding': 'PATH_TRAVERSAL'})
    # 7. corrupt manifest
    put('corrupt_manifest.apk', zipbytes([('AndroidManifest.xml', b'\x03\x00\x08\x00\xff\xff\xff\x7f' + b'\x01' * 40)]), {'state': 'SCAN_FAILED', 'finding': 'MANIFEST_PARSE_FAILED'})
    # 8. unsigned benign
    put('unsigned_benign.apk', zipbytes([('AndroidManifest.xml', manifest('com.example.unsigned')),
        ('classes.dex', strings_dex([], ['Lcom/example/unsigned/A;']))]), {'state': 'NO_KNOWN_THREAT_FOUND', 'finding': 'UNSIGNED'})
    dist = load_distribution(ROOT)
    own = ROOT / dist['apk']
    if hashlib.sha256(own.read_bytes()).hexdigest() != dist['sha256']:
        raise ValueError('CURRENT_APK_HASH_MISMATCH')
    # Avoid copying the release APK; tests resolve its path/hash from build metadata.
    samples['own_iteraguard_debug.apk'] = {'source': 'release_distribution_metadata',
        'path': dist['apk'], 'sha256': dist['sha256'], 'bytes': own.stat().st_size,
        'expect': {'state': 'NO_KNOWN_THREAT_FOUND', 'finding': 'DEBUGGABLE'}}
    (out / 'CORPUS.json').write_text(json.dumps(samples, indent=1, ensure_ascii=False))
    return samples


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=str(ROOT / 'tests_data/apk_corpus'))
    print(json.dumps(build(Path(ap.parse_args().out)), indent=1))
