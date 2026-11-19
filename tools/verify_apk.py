"""Independent verification of the debug APK built by tools/build_apk.py.

Uses parsers that did not produce the file:
  * apksigtool  - APK Signature Scheme v2 cryptographic verification
  * androguard  - binary manifest, resources.arsc, DEX parsing/disassembly
plus direct checks of the DEX ordering/alignment rules that Android's runtime verifier
enforces (sorted id tables, map list, checksums), a whitelist of every referenced
method (no network, reflection or class loading), and byte equality of the bundled web
assets with apps/dist/web. A passing result is NOT a device install/run test.
Usage: python tools/verify_apk.py <apk> [--evidence internal/evidence/v46_apk.json]
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, struct, subprocess, sys, zipfile, zlib
from pathlib import Path

if __package__:
    from .release_metadata import archive_issues, load_distribution
else:  # Direct CLI invocation already puts the script directory on sys.path.
    from release_metadata import archive_issues, load_distribution

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_METHODS = {
    'Landroid/app/Activity;-><init>()V', 'Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V',
    'Landroid/app/Activity;->requestWindowFeature(I)Z', 'Landroid/app/Activity;->setContentView(Landroid/view/View;)V',
    'Landroid/app/Activity;->onBackPressed()V', 'Landroid/webkit/WebView;-><init>(Landroid/content/Context;)V',
    'Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;', 'Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V',
    'Landroid/webkit/WebView;->canGoBack()Z', 'Landroid/webkit/WebView;->goBack()V',
    'Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V', 'Landroid/webkit/WebSettings;->setDomStorageEnabled(Z)V',
    'Landroid/webkit/WebView;->setBackgroundColor(I)V',
    'Lkr/iteraguard/doubtmeter/MainActivity;-><init>()V', 'Lkr/iteraguard/doubtmeter/MainActivity;->onCreate(Landroid/os/Bundle;)V',
    'Lkr/iteraguard/doubtmeter/MainActivity;->onBackPressed()V',
    # v4.7 share-sheet text input (local only)
    'Landroid/app/Activity;->getIntent()Landroid/content/Intent;', 'Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;',
    'Ljava/lang/String;->getBytes(Ljava/lang/String;)[B', 'Landroid/util/Base64;->encodeToString([BI)Ljava/lang/String;',
    'Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;'}
FORBIDDEN_TYPE_PREFIXES = ('Ljava/net/', 'Ljavax/net/', 'Landroid/net/', 'Ljava/lang/reflect/', 'Ldalvik/system/', 'Ljava/lang/Runtime;', 'Ljava/lang/ProcessBuilder;')


def packaged_web_assets(root=ROOT):
    """Read the preserved PWA artifact; a missing staging directory is normal."""
    root = Path(root)
    dist = load_distribution(root)
    pwa = root / dist['pwa']
    raw = pwa.read_bytes()
    if hashlib.sha256(raw).hexdigest() != dist['pwa_sha256']:
        raise ValueError('PWA_METADATA_HASH_MISMATCH')
    with zipfile.ZipFile(pwa) as z:
        issues = archive_issues(z)
        if issues or z.testzip() is not None:
            raise ValueError('INVALID_PWA_ARCHIVE:' + ','.join(issues))
        files = [i for i in z.infolist() if not i.is_dir()]
        if not files or any(not i.filename.startswith('dmsg-web/') for i in files):
            raise ValueError('INVALID_PWA_ROOT')
        assets = {i.filename[len('dmsg-web/'):]: z.read(i) for i in files
                  if i.filename != 'dmsg-web/sw.js'}
        if 'index.html' not in assets or 'build-info.js' not in assets:
            raise ValueError('INCOMPLETE_PWA_ASSETS')
    return assets, {'path': dist['pwa'], 'sha256': dist['pwa_sha256'], 'source': 'PACKAGED_PWA_NOT_STAGING'}


def compare_packaged_assets(apk, *, root=ROOT):
    expect, provenance = packaged_web_assets(root)
    with zipfile.ZipFile(apk) as z:
        issues = archive_issues(z)
        if issues:
            raise ValueError('INVALID_APK_ARCHIVE:' + ','.join(issues))
        crc = z.testzip() is None
        assets = {i.filename[len('assets/www/'):]: z.read(i) for i in z.infolist()
                  if not i.is_dir() and i.filename.startswith('assets/www/')}
    equal = assets == expect
    return {'status': 'PASS_ASSETS_ONLY' if equal and crc else 'FAIL',
            'assets_equal_web_bundle': equal, 'zip_crc': crc, 'expected_asset_count': len(expect),
            'actual_asset_count': len(assets), 'bundle': provenance,
            'missing_assets': sorted(set(expect) - set(assets)),
            'extra_assets': sorted(set(assets) - set(expect)),
            'changed_assets': sorted(k for k in set(assets) & set(expect) if assets[k] != expect[k]),
            'signature_validation': 'NOT_RUN_IN_ASSETS_ONLY_MODE', 'device_install_and_run': 'NOT_RUN',
            'note': 'APK/PWA artifact equality only; edited source requires a separate rebuild and release verification.'}


def dex_rules(d: bytes) -> dict:
    r = {}
    u32 = lambda o: struct.unpack('<I', d[o:o + 4])[0]
    r['magic'] = d[:8] == b'dex\n035\0'
    r['checksum'] = u32(8) == zlib.adler32(d[12:])
    r['sha1'] = d[12:32] == hashlib.sha1(d[32:]).digest()
    r['file_size'] = u32(32) == len(d)
    r['header_size'] = u32(36) == 0x70 and u32(40) == 0x12345678
    ns, os_, nt, ot, np_, op, nf, of, nm, om, nc, oc, dsz, doff = [u32(56 + 4 * i) for i in range(14)]
    def mutf8(i):
        o = u32(os_ + 4 * i)
        while d[o] & 0x80: o += 1
        o += 1; e = d.index(b'\0', o); return d[o:e].decode('utf-8')
    strings = [mutf8(i) for i in range(ns)]
    r['strings_sorted_unique'] = all(a.encode('utf-16-be') < b.encode('utf-16-be') for a, b in zip(strings, strings[1:]))
    types = [u32(ot + 4 * i) for i in range(nt)]
    r['types_sorted_unique'] = all(a < b for a, b in zip(types, types[1:]))
    def tl(off): return () if off == 0 else tuple(struct.unpack('<H', d[off + 4 + 2 * k:off + 6 + 2 * k])[0] for k in range(u32(off)))
    protos = [(u32(op + 12 * i + 4), tl(u32(op + 12 * i + 8))) for i in range(np_)]
    r['protos_sorted_unique'] = all(a < b for a, b in zip(protos, protos[1:]))
    fields = [struct.unpack('<HHI', d[of + 8 * i:of + 8 * i + 8]) for i in range(nf)]
    r['fields_sorted_unique'] = all((a[0], a[2], a[1]) < (b[0], b[2], b[1]) for a, b in zip(fields, fields[1:]))
    meths = [struct.unpack('<HHI', d[om + 8 * i:om + 8 * i + 8]) for i in range(nm)]
    r['methods_sorted_unique'] = all((a[0], a[2], a[1]) < (b[0], b[2], b[1]) for a, b in zip(meths, meths[1:]))
    mo = u32(52); n = u32(mo); items = [struct.unpack('<HHII', d[mo + 4 + 12 * i:mo + 16 + 12 * i]) for i in range(n)]
    offs = [x[3] for x in items]
    r['map_offsets_ascending'] = offs == sorted(offs) and len({x[0] for x in items}) == n and items[0][0] == 0
    want = {1: (ns, os_), 2: (nt, ot), 3: (np_, op), 4: (nf, of), 5: (nm, om), 6: (nc, oc)}
    r['map_matches_header'] = all(any(x[0] == t and x[2] == c and x[3] == o for x in items) for t, (c, o) in want.items())
    r['data_section'] = doff + dsz == len(d) and dsz % 4 == 0
    r['aligned_items'] = all(x[3] % 4 == 0 for x in items if x[0] in (0x2001, 0x1001, 0x1000))
    tname = lambda i: strings[types[i]]
    refs = []
    for c, p, nmx in meths:
        ret, params = protos[p]
        refs.append(f'{tname(c)}->{strings[nmx]}({"".join(tname(x) for x in params)}){tname(ret)}')
    r['only_whitelisted_methods'] = set(refs) <= ALLOWED_METHODS
    r['no_forbidden_types'] = not any(strings[t].startswith(FORBIDDEN_TYPE_PREFIXES) for t in types)
    r['single_class'] = nc == 1
    return {'rules': r, 'method_refs': sorted(refs)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('apk'); ap.add_argument('--evidence')
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--assets-only', action='store_true', help='No independent parser or signature claim')
    a = ap.parse_args()
    if a.assets_only:
        out = compare_packaged_assets(a.apk, root=a.root)
        if a.evidence: Path(a.evidence).write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', 'utf8')
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out['status'] == 'PASS_ASSETS_ONLY' else 1
    missing = [name for name in ('apksigtool', 'androguard', 'loguru') if importlib.util.find_spec(name) is None]
    if missing:
        out = {'status': 'NOT_RUN_MISSING_DEPENDENCIES', 'missing': missing, 'device_install_and_run': 'NOT_RUN'}
        if a.evidence: Path(a.evidence).write_text(json.dumps(out, indent=2) + '\n', 'utf8')
        print(json.dumps(out)); return 2
    out = {'apk': a.apk, 'sha256': hashlib.sha256(Path(a.apk).read_bytes()).hexdigest()}
    v = subprocess.run([sys.executable, '-m', 'apksigtool', 'verify', a.apk], text=True, capture_output=True)
    out['signature_v2'] = v.returncode == 0 and 'v2 verified' in v.stdout
    from loguru import logger; logger.remove()
    from androguard.core.apk import APK
    from androguard.core.dex import DEX
    x = APK(a.apk)
    man = x.get_android_manifest_xml()
    act = man.find('application/activity')
    NS = '{http://schemas.android.com/apk/res/android}'
    out['manifest'] = {'package': x.get_package(), 'version': [x.get_androidversion_code(), x.get_androidversion_name()],
                       'min_target': [x.get_min_sdk_version(), x.get_target_sdk_version()], 'label': x.get_app_name(),
                       'icon': x.get_app_icon(), 'permissions': x.get_permissions(), 'activities': x.get_activities(),
                       'main_activity': x.get_main_activity(), 'exported': act.get(NS + 'exported'),
                       'debuggable': man.find('application').get(NS + 'debuggable')}
    # v4.5 launch theme: resolve style/AppTheme through androguard's independent ARSC parser
    rp = x.get_android_resources()
    theme_ref = man.find('application').get(NS + 'theme')
    try:
        sty = rp.get_resolved_res_configs(int(str(theme_ref).lstrip('@'), 16))
        out['launch_theme'] = {'ref': str(theme_ref), 'resolved': [str(v) for _, v in sty]}
    except Exception as e:
        out['launch_theme'] = {'ref': str(theme_ref), 'error': type(e).__name__}
    z = zipfile.ZipFile(a.apk)
    dex = z.read('classes.dex')
    out['dex'] = dex_rules(dex)
    d = DEX(dex)
    out['dex']['androguard_methods'] = sorted(m.get_name() for c in d.get_classes() for m in c.get_methods())
    out['asset_comparison'] = compare_packaged_assets(a.apk, root=a.root)
    out['assets_equal_web_bundle'] = out['asset_comparison']['assets_equal_web_bundle']
    out['zip_crc'] = z.testzip() is None
    misaligned = []
    raw = Path(a.apk).read_bytes()
    for i in z.infolist():
        if i.compress_type == 0:
            nlen, elen = struct.unpack('<HH', raw[i.header_offset + 26:i.header_offset + 30])
            if (i.header_offset + 30 + nlen + elen) % 4: misaligned.append(i.filename)
    out['stored_entries_aligned'] = not misaligned
    m = out['manifest']
    checks = [out['signature_v2'], out['assets_equal_web_bundle'], out['zip_crc'], out['stored_entries_aligned'],
              m['package'] == 'kr.iteraguard.doubtmeter', m['permissions'] == [], m['main_activity'] == 'kr.iteraguard.doubtmeter.MainActivity',
              m['icon'] == 'res/mipmap/ic_launcher.png', m['label'] == '의심계', all(out['dex']['rules'].values())]
    out['status'] = 'STRUCTURE_AND_SIGNATURE_PASS_DEVICE_NOT_RUN' if all(checks) else 'FAIL'
    out['device_install_and_run'] = 'NOT_RUN'
    if a.evidence:
        Path(a.evidence).write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(json.dumps({k: out[k] for k in ('status', 'signature_v2', 'assets_equal_web_bundle', 'stored_entries_aligned', 'manifest')}, ensure_ascii=False, indent=1))
    print(json.dumps(out['dex']['rules']))
    return 0 if all(checks) else 1


if __name__ == '__main__':
    sys.exit(main())
