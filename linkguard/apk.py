"""Static APK inspection for a file the user hands us. Never installs, never executes, never uploads.

Everything is parsed from bytes with our own readers (ZIP central directory, binary XML, DEX string table,
APK Signing Block v2/v3) so the same logic can run on the phone in JS (apps/shared/dmsg-apkscan.js).
Androguard is used only as an independent oracle in tests (tools/linkguard/apk_oracle.py), not here.

What this is NOT: a malware verdict. Permissions and API strings are capabilities, not intent; a clean static
report does not prove the app is harmless, and the source code of the developer is not visible to us.
"""
from __future__ import annotations
import hashlib, re, struct, zlib

MAX_APK_BYTES = 150 * 1024 * 1024
MAX_ENTRIES = 20000
MAX_ENTRY_UNCOMPRESSED = 256 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 1024 * 1024 * 1024
MAX_RATIO = 200
MAX_DEX_SCAN = 64 * 1024 * 1024

ANDROID_NS = 'http://schemas.android.com/apk/res/android'
# Attribute resource ids (stable framework ids) — used when the attribute name string is stripped/obfuscated
ATTR_IDS = {0x01010003: 'name', 0x01010010: 'exported', 0x0101021b: 'versionCode', 0x0101021c: 'versionName',
            0x0101020c: 'minSdkVersion', 0x01010270: 'targetSdkVersion', 0x01010006: 'permission', 0x0101000f: 'debuggable',
            0x01010280: 'allowBackup', 0x010104ec: 'usesCleartextTraffic', 0x0101000e: 'enabled'}

DANGEROUS_PERMS = {
    'android.permission.READ_SMS': 'SMS', 'android.permission.RECEIVE_SMS': 'SMS', 'android.permission.SEND_SMS': 'SMS',
    'android.permission.RECEIVE_MMS': 'SMS', 'android.permission.RECEIVE_WAP_PUSH': 'SMS',
    'android.permission.READ_CALL_LOG': 'CALL_LOG', 'android.permission.WRITE_CALL_LOG': 'CALL_LOG',
    'android.permission.PROCESS_OUTGOING_CALLS': 'CALL_LOG', 'android.permission.CALL_PHONE': 'PHONE',
    'android.permission.READ_PHONE_STATE': 'PHONE', 'android.permission.READ_PHONE_NUMBERS': 'PHONE',
    'android.permission.ANSWER_PHONE_CALLS': 'PHONE', 'android.permission.READ_CONTACTS': 'CONTACTS',
    'android.permission.WRITE_CONTACTS': 'CONTACTS', 'android.permission.GET_ACCOUNTS': 'CONTACTS',
    'android.permission.RECORD_AUDIO': 'MICROPHONE', 'android.permission.CAMERA': 'CAMERA',
    'android.permission.ACCESS_FINE_LOCATION': 'LOCATION', 'android.permission.ACCESS_BACKGROUND_LOCATION': 'LOCATION',
    'android.permission.READ_EXTERNAL_STORAGE': 'STORAGE', 'android.permission.MANAGE_EXTERNAL_STORAGE': 'STORAGE',
}
SPECIAL_PERMS = {
    'android.permission.SYSTEM_ALERT_WINDOW': 'OVERLAY', 'android.permission.BIND_ACCESSIBILITY_SERVICE': 'ACCESSIBILITY',
    'android.permission.REQUEST_INSTALL_PACKAGES': 'INSTALL_PACKAGES', 'android.permission.BIND_DEVICE_ADMIN': 'DEVICE_ADMIN',
    'android.permission.BIND_NOTIFICATION_LISTENER_SERVICE': 'NOTIFICATION_LISTENER', 'android.permission.QUERY_ALL_PACKAGES': 'PACKAGE_VISIBILITY',
    'android.permission.PACKAGE_USAGE_STATS': 'USAGE_STATS', 'android.permission.BIND_VPN_SERVICE': 'VPN',
    'android.permission.WRITE_SETTINGS': 'WRITE_SETTINGS', 'android.permission.FOREGROUND_SERVICE': 'FOREGROUND_SERVICE',
    'android.permission.RECEIVE_BOOT_COMPLETED': 'BOOT', 'android.permission.USE_FULL_SCREEN_INTENT': 'FULL_SCREEN_INTENT',
    'android.permission.BIND_SCREENING_SERVICE': 'CALL_SCREENING', 'android.permission.BIND_INCALL_SERVICE': 'INCALL',
}
# substring in DEX string table -> capability label
API_MARKERS = [
    ('Landroid/telephony/SmsManager;', 'SMS_SEND_API'), ('sendTextMessage', 'SMS_SEND_API'),
    ('Landroid/provider/Telephony$Sms', 'SMS_PROVIDER_READ'), ('content://sms', 'SMS_PROVIDER_READ'),
    ('Landroid/accessibilityservice/AccessibilityService;', 'ACCESSIBILITY_SERVICE'),
    ('performGlobalAction', 'ACCESSIBILITY_AUTOMATION'), ('dispatchGesture', 'ACCESSIBILITY_AUTOMATION'),
    ('TYPE_APPLICATION_OVERLAY', 'OVERLAY_WINDOW'), ('Landroid/view/WindowManager$LayoutParams;', 'WINDOW_PARAMS'),
    ('Ldalvik/system/DexClassLoader;', 'DYNAMIC_CODE_LOADING'), ('Ldalvik/system/InMemoryDexClassLoader;', 'DYNAMIC_CODE_LOADING'),
    ('Ldalvik/system/PathClassLoader;', 'CLASS_LOADER'), ('loadLibrary', 'NATIVE_LOAD'), ('Ljava/lang/System;->load', 'NATIVE_LOAD'),
    ('Ljava/lang/reflect/Method;', 'REFLECTION'), ('Ljava/lang/Runtime;', 'RUNTIME_EXEC'), ('Ljava/lang/ProcessBuilder;', 'RUNTIME_EXEC'),
    ('addJavascriptInterface', 'WEBVIEW_JS_BRIDGE'), ('setJavaScriptEnabled', 'WEBVIEW_JS'),
    ('setAllowFileAccess', 'WEBVIEW_FILE_ACCESS'), ('setAllowUniversalAccessFromFileURLs', 'WEBVIEW_UNIVERSAL_FILE_ACCESS'),
    ('Landroid/app/admin/DevicePolicyManager;', 'DEVICE_ADMIN_API'), ('Landroid/content/pm/PackageInstaller;', 'PACKAGE_INSTALLER'),
    ('Landroid/media/projection/MediaProjection', 'SCREEN_CAPTURE'), ('Landroid/telecom/TelecomManager;', 'TELECOM'),
    ('Landroid/service/notification/NotificationListenerService;', 'NOTIFICATION_READ'),
    ('Ljavax/crypto/Cipher;', 'CRYPTO'), ('Landroid/util/Base64;', 'BASE64'),
    ('Ljava/net/HttpURLConnection;', 'NETWORK_HTTP'), ('Lokhttp3/', 'NETWORK_HTTP'), ('Ljava/net/Socket;', 'NETWORK_SOCKET'),
    ('Landroid/hardware/camera2/', 'CAMERA_API'), ('Landroid/media/AudioRecord;', 'AUDIO_RECORD'),
    ('Landroid/location/LocationManager;', 'LOCATION_API'), ('getDeviceId', 'DEVICE_ID'), ('getSubscriberId', 'DEVICE_ID'),
]
URL_IN_DEX = re.compile(r'(?:https?|wss?)://[A-Za-z0-9.\-]{3,253}(?::[0-9]{1,5})?(?:/[^\s"\'<>]{0,120})?')
IPV4_IN_DEX = re.compile(r'(?<![0-9.])(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(?:\.(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}(?![0-9.])')


class ApkError(Exception):
    pass


# ------------------------------------------------------------------ ZIP
def zip_entries(buf: bytes):
    """Parse the central directory. Returns (entries, problems). Never trusts local headers for sizes."""
    problems = []
    eocd = buf.rfind(b'PK\x05\x06', max(0, len(buf) - 65557))
    if eocd < 0: raise ApkError('NO_ZIP_EOCD')
    (_, disk, cd_disk, n_disk, n_total, cd_size, cd_off, clen) = struct.unpack_from('<IHHHHIIH', buf, eocd)
    if disk or cd_disk or n_disk != n_total: problems.append('MULTI_DISK')
    if n_total == 0xFFFF or cd_off == 0xFFFFFFFF: problems.append('ZIP64_UNSUPPORTED')
    if n_total > MAX_ENTRIES: raise ApkError('TOO_MANY_ENTRIES')
    if cd_off + cd_size > eocd: raise ApkError('BAD_CENTRAL_DIRECTORY')
    out, p, seen = [], cd_off, set()
    for _ in range(n_total):
        if buf[p:p + 4] != b'PK\x01\x02': raise ApkError('BAD_CENTRAL_DIRECTORY')
        (flags, method, crc, csize, usize, nlen, xlen, cmlen, lho) = (
            struct.unpack_from('<H', buf, p + 8)[0], struct.unpack_from('<H', buf, p + 10)[0], struct.unpack_from('<I', buf, p + 16)[0],
            struct.unpack_from('<I', buf, p + 20)[0], struct.unpack_from('<I', buf, p + 24)[0], struct.unpack_from('<H', buf, p + 28)[0],
            struct.unpack_from('<H', buf, p + 30)[0], struct.unpack_from('<H', buf, p + 32)[0], struct.unpack_from('<I', buf, p + 42)[0])
        name = buf[p + 46:p + 46 + nlen].decode('utf-8', 'replace')
        p += 46 + nlen + xlen + cmlen
        e = {'name': name, 'method': method, 'crc': crc, 'csize': csize, 'usize': usize, 'flags': flags, 'lho': lho}
        if name in seen: problems.append('DUPLICATE_ENTRY')
        seen.add(name)
        if name.startswith('/') or name.startswith('\\') or '..' in re.split(r'[\\/]', name) or re.match(r'^[A-Za-z]:', name):
            problems.append('PATH_TRAVERSAL')
        if flags & 1: problems.append('ENCRYPTED_ENTRY_FLAG')
        if method not in (0, 8): problems.append('UNSUPPORTED_COMPRESSION')
        if usize > MAX_ENTRY_UNCOMPRESSED: problems.append('ENTRY_TOO_LARGE')
        if csize and usize / max(csize, 1) > MAX_RATIO and usize > 10 * 1024 * 1024: problems.append('HIGH_COMPRESSION_RATIO')
        out.append(e)
    if sum(e['usize'] for e in out) > MAX_TOTAL_UNCOMPRESSED: problems.append('TOTAL_UNCOMPRESSED_TOO_LARGE')
    return out, cd_off, eocd, sorted(set(problems))


def zip_read(buf, e, limit=MAX_ENTRY_UNCOMPRESSED):
    p = e['lho']
    if buf[p:p + 4] != b'PK\x03\x04': raise ApkError('BAD_LOCAL_HEADER')
    nlen, xlen = struct.unpack_from('<HH', buf, p + 26)
    start = p + 30 + nlen + xlen
    data = buf[start:start + e['csize']]
    if e['usize'] > limit: raise ApkError('ENTRY_TOO_LARGE')
    if e['method'] == 0: raw = data
    elif e['method'] == 8:
        try:
            d = zlib.decompressobj(-15); raw = d.decompress(data, limit + 1)
        except zlib.error:
            raise ApkError('INFLATE_FAILED')
        if len(raw) > limit: raise ApkError('ENTRY_TOO_LARGE')
    else: raise ApkError('UNSUPPORTED_COMPRESSION')
    if len(raw) != e['usize'] or (zlib.crc32(raw) & 0xFFFFFFFF) != e['crc']: raise ApkError('CRC_MISMATCH')
    return raw


# ------------------------------------------------------------------ binary XML (AndroidManifest.xml)
def _sp_strings(b, off):
    typ, hsz, size, count, scount, flags, sstart, ssstart = struct.unpack_from('<HHIIIIII', b, off)
    utf8 = bool(flags & 0x100)
    offs = struct.unpack_from('<%dI' % count, b, off + hsz)
    base = off + sstart; res = []
    for o in offs:
        q = base + o
        if utf8:
            n = b[q]; q += 2 if n & 0x80 else 1
            n = b[q]; m = n
            if n & 0x80: m = ((n & 0x7F) << 8) | b[q + 1]; q += 2
            else: q += 1
            res.append(b[q:q + m].decode('utf-8', 'replace'))
        else:
            n = struct.unpack_from('<H', b, q)[0]; q += 2
            if n & 0x8000: n = ((n & 0x7FFF) << 16) | struct.unpack_from('<H', b, q)[0]; q += 2
            res.append(b[q:q + 2 * n].decode('utf-16-le', 'replace'))
    return res, off + size


def parse_axml(b: bytes):
    """Return list of (depth, tag, {attr: value}) for start elements."""
    if len(b) < 8 or struct.unpack_from('<H', b, 0)[0] != 0x0003: raise ApkError('MANIFEST_NOT_BINARY_XML')
    strings, res_ids, out, depth = [], [], [], 0
    p = struct.unpack_from('<H', b, 2)[0]
    end = min(len(b), struct.unpack_from('<I', b, 4)[0])
    while p + 8 <= end:
        typ, hsz, size = struct.unpack_from('<HHI', b, p)
        if size < 8 or p + size > end: raise ApkError('MANIFEST_CORRUPT')
        if typ == 0x0001: strings, _ = _sp_strings(b, p)
        elif typ == 0x0180: res_ids = list(struct.unpack_from('<%dI' % ((size - hsz) // 4), b, p + hsz))
        elif typ == 0x0102:
            ns, name, a_start, a_size, a_count = struct.unpack_from('<iiHHH', b, p + 16)
            tag = strings[name] if 0 <= name < len(strings) else '?'
            attrs = {}
            q = p + 16 + a_start
            for i in range(a_count):
                ans, aname, araw, vsize, _r, vtype, vdata = struct.unpack_from('<iiiHBBI', b, q + i * a_size)
                key = strings[aname] if 0 <= aname < len(strings) else ''
                if 0 <= aname < len(res_ids) and res_ids[aname] in ATTR_IDS: key = ATTR_IDS[res_ids[aname]]
                if vtype == 0x03 and 0 <= vdata < len(strings): val = strings[vdata]
                elif araw >= 0 and araw < len(strings): val = strings[araw]
                elif vtype == 0x12: val = vdata != 0
                elif vtype in (0x10, 0x11): val = vdata if vdata < 0x80000000 else vdata - 0x100000000
                elif vtype == 0x01: val = '@0x%08x' % vdata
                else: val = vdata
                attrs[key] = val
            out.append((depth, tag, attrs)); depth += 1
        elif typ == 0x0103: depth -= 1
        p += size
    return out


def manifest_summary(nodes):
    m = {'package': None, 'version_code': None, 'version_name': None, 'min_sdk': None, 'target_sdk': None, 'permissions': [],
         'declared_permissions': [], 'components': [], 'debuggable': False, 'allow_backup': None, 'cleartext': None}
    stack = []
    for depth, tag, a in nodes:
        stack = stack[:depth] + [(tag, a)]
        if tag == 'manifest':
            m['package'] = a.get('package'); m['version_code'] = a.get('versionCode'); m['version_name'] = a.get('versionName')
        elif tag == 'uses-sdk':
            m['min_sdk'] = a.get('minSdkVersion'); m['target_sdk'] = a.get('targetSdkVersion')
        elif tag in ('uses-permission', 'uses-permission-sdk-23') and a.get('name'): m['permissions'].append(a['name'])
        elif tag == 'permission' and a.get('name'): m['declared_permissions'].append(a['name'])
        elif tag == 'application':
            m['debuggable'] = a.get('debuggable') is True; m['allow_backup'] = a.get('allowBackup'); m['cleartext'] = a.get('usesCleartextTraffic')
        elif tag in ('activity', 'activity-alias', 'service', 'receiver', 'provider'):
            m['components'].append({'type': tag, 'name': a.get('name'), 'exported': a.get('exported'), 'permission': a.get('permission'),
                                    'intent_filters': [], 'actions': []})
        elif tag == 'action' and len(stack) >= 3 and stack[-2][0] == 'intent-filter' and m['components']:
            m['components'][-1]['actions'].append(a.get('name'))
    for c in m['components']:
        has_filter = bool(c['actions'])
        if c['exported'] is None: c['exported_effective'] = has_filter if c['type'] != 'provider' else False
        else: c['exported_effective'] = bool(c['exported'])
        c['binds'] = c['permission']
        del c['intent_filters']
    m['permissions'] = sorted(set(m['permissions']))
    return m


# ------------------------------------------------------------------ DEX
def _uleb(b, p):
    r, s = 0, 0
    while True:
        x = b[p]; p += 1; r |= (x & 0x7F) << s; s += 7
        if not x & 0x80: return r, p


def dex_strings(b: bytes):
    if len(b) < 0x70 or b[:4] != b'dex\n': raise ApkError('NOT_DEX')
    version = b[4:7].decode('ascii', 'replace')
    n, off = struct.unpack_from('<II', b, 0x38)
    tn, toff = struct.unpack_from('<II', b, 0x40)
    if off + 4 * n > len(b): raise ApkError('DEX_CORRUPT')
    out = []
    for i in range(n):
        so = struct.unpack_from('<I', b, off + 4 * i)[0]
        if so >= len(b): raise ApkError('DEX_CORRUPT')
        ln, q = _uleb(b, so)
        e = b.find(b'\x00', q)
        out.append(b[q:e].decode('utf-8', 'replace'))   # MUTF-8 ≈ UTF-8 for scanning purposes
    types = []
    for i in range(min(tn, 200000)):
        idx = struct.unpack_from('<I', b, toff + 4 * i)[0]
        if idx < len(out): types.append(out[idx])
    return version, out, types


def obfuscation_score(types):
    """Fraction of app classes whose simple name is 1–2 lowercase letters (ProGuard/R8 style). Heuristic only."""
    app = [t for t in types if t.startswith('L') and t.endswith(';') and not t.startswith(('Landroid/', 'Ljava/', 'Ljavax/', 'Lkotlin/',
                                                                                         'Landroidx/', 'Ldalvik/', 'Lorg/'))]
    if not app: return 0.0, 0
    short = sum(1 for t in app if re.fullmatch(r'[a-z]{1,2}(?:\$[A-Za-z0-9]+)?', t[1:-1].rsplit('/', 1)[-1]))
    return round(short / len(app), 4), len(app)


# ------------------------------------------------------------------ signatures
def _der_len(b, p):
    l = b[p]; p += 1
    if l < 0x80: return l, p
    n = l & 0x7F
    return int.from_bytes(b[p:p + n], 'big'), p + n


def _x509_fields(cert):
    """Very small DER walker: return subject/issuer common names and validity strings when present."""
    res = {}
    try:
        def tlv(p):
            t = cert[p]; l, q = _der_len(cert, p + 1); return t, q, q + l
        _, a, _ = tlv(0)                     # Certificate SEQUENCE
        _, tb, tbe = tlv(a)                  # TBSCertificate
        p = tb
        if cert[p] == 0xA0: _, _, p = tlv(p)  # version
        _, _, p = tlv(p)                     # serial
        _, _, p = tlv(p)                     # sigalg
        names = []
        for key in ('issuer', 'validity', 'subject'):
            t, s, e = tlv(p)
            if key == 'validity':
                _, s1, e1 = tlv(s); _, s2, e2 = tlv(e1)
                res['not_before'], res['not_after'] = cert[s1:e1].decode('ascii', 'replace'), cert[s2:e2].decode('ascii', 'replace')
            else:
                blob = cert[s:e]
                cn = blob.find(b'\x06\x03\x55\x04\x03')
                if cn >= 0:
                    q = cn + 5; _t = blob[q]; l, q2 = _der_len(blob, q + 1)
                    res[key + '_cn'] = blob[q2:q2 + l].decode('utf-8', 'replace')
            p = e
    except (IndexError, ValueError):
        res['parse'] = 'PARTIAL'
    return res


def signing_block(buf, cd_off):
    """APK Signature Scheme v2/v3: return list of {scheme, cert_sha256, fields}. Signature validity is NOT verified here."""
    if cd_off < 32 or buf[cd_off - 16:cd_off] != b'APK Sig Block 42': return []
    size = struct.unpack_from('<Q', buf, cd_off - 24)[0]
    start = cd_off - size - 8
    if start < 0 or struct.unpack_from('<Q', buf, start)[0] != size: return []
    p, end, out = start + 8, cd_off - 24, []
    while p + 12 <= end:
        ln = struct.unpack_from('<Q', buf, p)[0]; bid = struct.unpack_from('<I', buf, p + 8)[0]
        val = buf[p + 12:p + 8 + ln]
        scheme = {0x7109871a: 'v2', 0xf05368c0: 'v3', 0x1b93ad61: 'v3.1'}.get(bid)
        if scheme:
            try:
                q = 4  # signers length-prefixed sequence
                signer_len = struct.unpack_from('<I', val, q)[0]; q += 4
                signer = val[q:q + signer_len]
                sd_len = struct.unpack_from('<I', signer, 0)[0]; sd = signer[4:4 + sd_len]
                dl = struct.unpack_from('<I', sd, 0)[0]
                cl = struct.unpack_from('<I', sd, 4 + dl)[0]; certs = sd[8 + dl:8 + dl + cl]
                c1 = struct.unpack_from('<I', certs, 0)[0]; cert = certs[4:4 + c1]
                out.append({'scheme': scheme, 'cert_sha256': hashlib.sha256(cert).hexdigest(), **_x509_fields(cert)})
            except (struct.error, IndexError):
                out.append({'scheme': scheme, 'cert_sha256': None, 'parse': 'FAILED'})
        p += 8 + ln
    return out


# ------------------------------------------------------------------ main entry
def sniff(buf: bytes, filename: str = ''):
    kinds = []
    if buf[:4] == b'PK\x03\x04': kinds.append('ZIP')
    if buf[:4] == b'dex\n': kinds.append('DEX')
    if buf[:4] == b'\x7fELF': kinds.append('ELF')
    if buf[:5] == b'%PDF-': kinds.append('PDF')
    if buf[:2] == b'MZ': kinds.append('PE')
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    return (kinds[0] if kinds else 'UNKNOWN'), ext


def inspect(buf: bytes, filename: str = 'upload.apk', *, max_bytes: int = MAX_APK_BYTES) -> dict:
    rep = {'filename_ext': None, 'size': len(buf), 'sha256': None, 'stages': {}, 'findings': [], 'capabilities': [],
           'scope_note': 'STATIC_ONLY_NOT_EXECUTED', 'verdict_basis': 'NOT_A_MALWARE_VERDICT'}
    st = rep['stages']
    if len(buf) > max_bytes:
        st['size_check'] = 'FAILED'; rep['findings'].append('FILE_TOO_LARGE'); rep['state'] = 'NOT_SCANNED'; return rep
    st['size_check'] = 'PASS'
    rep['sha256'] = hashlib.sha256(buf).hexdigest(); st['hash'] = 'PASS'
    kind, ext = sniff(buf, filename)
    rep['filename_ext'], rep['magic'] = ext, kind
    if kind != 'ZIP':
        st['magic'] = 'FAILED'; rep['findings'].append('NOT_AN_APK_CONTAINER' + ('_EXTENSION_MISMATCH' if ext in ('apk', 'xapk') else ''))
        rep['state'] = 'SCAN_FAILED'; return rep
    if ext not in ('apk', 'apks', 'xapk', 'zip', ''): rep['findings'].append('EXTENSION_MISMATCH')
    st['magic'] = 'PASS'
    try:
        entries, cd_off, eocd, problems = zip_entries(buf)
    except (ApkError, struct.error) as ex:
        st['zip'] = 'FAILED'; rep['findings'].append('ZIP_' + (str(ex) if isinstance(ex, ApkError) else 'CORRUPT')); rep['state'] = 'SCAN_FAILED'; return rep
    rep['findings'] += problems
    st['zip'] = 'PASS' if not problems else 'WARN'
    names = {e['name']: e for e in entries}
    rep['entry_count'] = len(entries)
    if 'PATH_TRAVERSAL' in problems or 'ZIP64_UNSUPPORTED' in problems:
        rep['state'] = 'SUSPICIOUS' if 'PATH_TRAVERSAL' in problems else 'SCAN_FAILED'; return _finish(rep)
    if 'AndroidManifest.xml' not in names:
        st['manifest'] = 'FAILED'; rep['findings'].append('NO_ANDROID_MANIFEST'); rep['state'] = 'SCAN_FAILED'; return _finish(rep)
    try:
        man = manifest_summary(parse_axml(zip_read(buf, names['AndroidManifest.xml'], 8 * 1024 * 1024)))
        st['manifest'] = 'PASS'
    except (ApkError, struct.error, IndexError, UnicodeDecodeError) as ex:
        st['manifest'] = 'FAILED'; rep['findings'].append('MANIFEST_PARSE_FAILED'); rep['state'] = 'SCAN_FAILED'; return _finish(rep)
    rep['manifest'] = man
    perms = man['permissions']
    rep['permission_groups'] = sorted({DANGEROUS_PERMS[p] for p in perms if p in DANGEROUS_PERMS})
    rep['special_access'] = sorted({SPECIAL_PERMS[p] for p in perms if p in SPECIAL_PERMS})
    for c in man['components']:
        if c['binds'] == 'android.permission.BIND_ACCESSIBILITY_SERVICE': rep['special_access'] = sorted(set(rep['special_access']) | {'ACCESSIBILITY'})
        if c['binds'] == 'android.permission.BIND_NOTIFICATION_LISTENER_SERVICE': rep['special_access'] = sorted(set(rep['special_access']) | {'NOTIFICATION_LISTENER'})
        if c['binds'] == 'android.permission.BIND_DEVICE_ADMIN': rep['special_access'] = sorted(set(rep['special_access']) | {'DEVICE_ADMIN'})
    rep['exported'] = [{'type': c['type'], 'name': c['name'], 'protected_by': c['permission']} for c in man['components'] if c['exported_effective']]
    sms_receiver = any('android.provider.Telephony.SMS_RECEIVED' in (c['actions'] or []) for c in man['components'])
    if sms_receiver: rep['capabilities'].append('SMS_RECEIVE_HOOK')
    if man['debuggable']: rep['findings'].append('DEBUGGABLE')
    # signatures
    rep['signing'] = signing_block(buf, cd_off)
    rep['signing_v1_files'] = sorted(n for n in names if re.fullmatch(r'META-INF/[^/]+\.(?:RSA|DSA|EC)', n))
    st['signature'] = 'PASS' if rep['signing'] or rep['signing_v1_files'] else 'WARN'
    if not rep['signing'] and not rep['signing_v1_files']: rep['findings'].append('UNSIGNED')
    rep['signature_note'] = 'CERTIFICATE_EXTRACTED_SIGNATURE_NOT_VERIFIED'
    # DEX
    dex_names = sorted(n for n in names if re.fullmatch(r'classes[0-9]*\.dex', n))
    rep['dex_files'] = dex_names
    caps, urls, ips, all_types, versions = set(rep['capabilities']), set(), set(), [], set()
    scanned = 0
    for dn in dex_names:
        e = names[dn]
        if scanned + e['usize'] > MAX_DEX_SCAN: rep['findings'].append('DEX_SCAN_TRUNCATED'); break
        try:
            v, strs, types = dex_strings(zip_read(buf, e, MAX_DEX_SCAN))
        except (ApkError, struct.error, IndexError):
            rep['findings'].append('DEX_PARSE_FAILED'); continue
        scanned += e['usize']; versions.add(v); all_types += types
        for s in strs:
            for marker, label in API_MARKERS:
                if marker in s: caps.add(label)
            if len(s) < 400:
                for u in URL_IN_DEX.findall(s): urls.add(u[:160])
                for ip in IPV4_IN_DEX.findall(s):
                    if not ip.startswith(('0.', '1.0.', '2.')) and ip.count('.') == 3: ips.add(ip)
    st['dex'] = 'PASS' if dex_names and 'DEX_PARSE_FAILED' not in rep['findings'] else ('FAILED' if dex_names else 'NO_DEX')
    rep['dex_versions'] = sorted(versions)
    rep['capabilities'] = sorted(caps)
    rep['network_indicators'] = {'urls': sorted(urls)[:50], 'ipv4': sorted(ips)[:50], 'url_total': len(urls)}
    score, napp = obfuscation_score(all_types)
    rep['obfuscation'] = {'short_name_ratio': score, 'app_classes': napp, 'likely': score >= 0.5 and napp >= 20}
    rep['native_libs'] = sorted({n.split('/')[1] + ':' + n.rsplit('/', 1)[-1] for n in names if n.startswith('lib/') and n.endswith('.so') and n.count('/') >= 2})[:60]
    rep['nested_packages'] = sorted(n for n in names if re.search(r'\.(?:apk|dex|jar)$', n) and not re.fullmatch(r'classes[0-9]*\.dex', n))[:30]
    if rep['nested_packages']: rep['capabilities'] = sorted(set(rep['capabilities']) | {'EMBEDDED_PACKAGE'})
    rep['state'] = None
    return _finish(rep)


# combinations that are typical of the Korean smishing / fake-app family (capability-level, not a signature)
RISK_COMBOS = [
    ({'SMS'}, {'ACCESSIBILITY'}, 'SMS_PLUS_ACCESSIBILITY'),
    ({'SMS'}, {'OVERLAY'}, 'SMS_PLUS_OVERLAY'),
    ({'CALL_LOG', 'PHONE'}, {'ACCESSIBILITY'}, 'CALL_CONTROL_PLUS_ACCESSIBILITY'),
    (set(), {'ACCESSIBILITY', 'OVERLAY'}, 'ACCESSIBILITY_PLUS_OVERLAY'),
    (set(), {'DEVICE_ADMIN', 'INSTALL_PACKAGES'}, 'DEVICE_ADMIN_PLUS_INSTALLER'),
]


def _finish(rep):
    groups = set(rep.get('permission_groups') or []); special = set(rep.get('special_access') or []); caps = set(rep.get('capabilities') or [])
    combos = []
    for g, s, label in RISK_COMBOS:
        if ((not g) or (g & groups)) and s <= special: combos.append(label)
    if 'SMS_RECEIVE_HOOK' in caps and ('ACCESSIBILITY' in special or 'OVERLAY' in special): combos.append('SMS_HOOK_PLUS_SCREEN_CONTROL')
    if 'DYNAMIC_CODE_LOADING' in caps and (groups & {'SMS', 'CALL_LOG'}): combos.append('DYNAMIC_CODE_PLUS_SENSITIVE_DATA')
    rep['risk_combinations'] = sorted(set(combos))
    if (rep.get('obfuscation') or {}).get('likely') and 'OBFUSCATION_LIKELY' not in rep['findings']: rep['findings'].append('OBFUSCATION_LIKELY')
    if rep.get('state') is None:
        if rep['risk_combinations'] or 'PATH_TRAVERSAL' in rep['findings']: rep['state'] = 'SUSPICIOUS'
        elif any(f in rep['findings'] for f in ('MANIFEST_PARSE_FAILED', 'DEX_PARSE_FAILED')): rep['state'] = 'INCONCLUSIVE'
        else: rep['state'] = 'NO_KNOWN_THREAT_FOUND'
    rep['not_checked'] = ['DYNAMIC_BEHAVIOR', 'SERVER_SIDE_CODE', 'SIGNATURE_CRYPTO_VALIDITY', 'REPUTATION_OF_HASH_UNLESS_CONSENTED',
                          'NATIVE_CODE_CONTENTS', 'ENCRYPTED_OR_DOWNLOADED_PAYLOADS']
    return rep
