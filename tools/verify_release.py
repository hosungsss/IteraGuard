"""Read-only release verification. Stale source/binaries fail; no implicit rebuild."""
import argparse
import base64
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

if __package__:
    from .release_metadata import (V51_CONTRACT_SOURCES, archive_issues, distribution_path, relative_path,
                                   required_members, shared_assets, skill_names, validate_distribution, version_of)
    from .build_apps import WEB_FILES
    from .verify_apk import packaged_web_assets, compare_packaged_assets
else:  # Direct CLI invocation already puts the script directory on sys.path.
    from release_metadata import (V51_CONTRACT_SOURCES, archive_issues, distribution_path, relative_path,
                                  required_members, shared_assets, skill_names, validate_distribution, version_of)
    from build_apps import WEB_FILES
    from verify_apk import packaged_web_assets, compare_packaged_assets

ROOT = Path(__file__).resolve().parents[1]


def content_files(base):
    # Same release boundary as the current full-project builder.
    base = Path(base)
    for p in sorted(base.rglob('*')):
        rel = p.relative_to(base)
        if (p.is_file() and not set(rel.parts) & {'__pycache__', 'node_modules', '.git', 'runs'}
                and p.name not in {'.env', 'desktop.ini'} and p.suffix not in {'.pyc', '.db', '.sqlite3'}
                and '.sqlite3' not in p.name and not p.name.endswith('.partial')
                and not rel.as_posix().startswith(('apps/dist/web/', 'apps/dist/desktop/'))):
            yield p


def h(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def unsafe_entries(z):
    return archive_issues(z)


def copied_web_sources(root, version=None):
    """The source-copy boundary of build_distribution_v49; generated files are separate."""
    root = Path(root)
    files = {name: root / 'apps/web' / name for name in WEB_FILES if name != 'sw.js'}
    if version is None:
        version = ('5.1' if (root / 'configs/v51_contract.json').is_file() else
                   '5.0' if (root / 'configs/v50_contract.json').is_file() else '4.9')
    for name in shared_assets(version):
        files[name] = root / 'apps/shared' / name
    nlp = root / 'apps/shared/nlp'
    for name in ('dmsg-nlp-vocab.js', 'dmsg-nlp-heads.js', 'dmsg-nlp-weights.js', 'NLP_ASSETS_MANIFEST.json'):
        files['nlp/' + name] = nlp / name
    # The v4.9 builder copies the entire NLP directory with these two exclusions.
    for p in nlp.rglob('*'):
        if p.is_file() and p.name != 'desktop.ini' and '__pycache__' not in p.relative_to(nlp).parts:
            files['nlp/' + p.relative_to(nlp).as_posix()] = p
    return files


def _bounded_zip_payload(path, prefix):
    with zipfile.ZipFile(path) as z:
        issues = archive_issues(z)
        if issues or z.testzip() is not None:
            raise ValueError('INVALID_PACKAGED_ARCHIVE:' + ','.join(issues))
        return {i.filename[len(prefix):]: z.read(i) for i in z.infolist()
                if not i.is_dir() and i.filename.startswith(prefix)}


def _android_version(data):
    """Read the two manifest attributes; no signature/device claim or builder use."""
    if len(data) < 8 or len(data) > 1_000_000 or struct.unpack_from('<HHI', data) != (3, 8, len(data)):
        raise ValueError('INVALID_ANDROID_BINARY_XML')
    strings, offset = [], 8
    def string(index):
        if not 0 <= index < len(strings):
            raise ValueError('INVALID_ANDROID_STRING_INDEX')
        return strings[index]
    while offset + 8 <= len(data):
        kind, header, size = struct.unpack_from('<HHI', data, offset)
        if header < 8 or size < header or offset + size > len(data):
            raise ValueError('INVALID_ANDROID_XML_CHUNK')
        if kind == 1:
            if header < 28:
                raise ValueError('INVALID_ANDROID_STRING_POOL')
            count, _, flags, start = struct.unpack_from('<IIII', data, offset + 8)
            if not flags & 0x100 or count > 10000 or header + count * 4 > size or start >= size:
                raise ValueError('UNSUPPORTED_ANDROID_STRING_POOL')
            strings = []
            for i in range(count):
                pos = offset + start + struct.unpack_from('<I', data, offset + header + 4 * i)[0]
                def length(pos):
                    if pos >= offset + size:
                        raise ValueError('TRUNCATED_ANDROID_STRING')
                    n = data[pos]; pos += 1
                    if n & 0x80:
                        if pos >= offset + size:
                            raise ValueError('TRUNCATED_ANDROID_STRING')
                        n = ((n & 0x7f) << 8) | data[pos]; pos += 1
                    return n, pos
                _, pos = length(pos)
                n, pos = length(pos)
                if pos + n >= offset + size or data[pos + n] != 0:
                    raise ValueError('INVALID_ANDROID_STRING')
                strings.append(data[pos:pos+n].decode('utf8'))
        elif kind == 0x102:
            if header != 16 or size < 36:
                raise ValueError('INVALID_ANDROID_START_TAG')
            _, name, start, stride, count = struct.unpack_from('<IIHHH', data, offset + 16)
            if string(name) == 'manifest':
                if stride < 20 or offset + 16 + start + stride * count > offset + size:
                    raise ValueError('INVALID_ANDROID_ATTRIBUTES')
                found = {}
                for i in range(count):
                    ns, key, _, value_size, _, typ, value = struct.unpack_from('<IIIHBBI', data, offset + 16 + start + stride * i)
                    key = string(key)
                    if key in ('versionCode', 'versionName'):
                        if key in found or value_size != 8 or string(ns) != 'http://schemas.android.com/apk/res/android':
                            raise ValueError('INVALID_ANDROID_VERSION_ATTRIBUTE')
                        found[key] = string(value) if typ == 3 else value if typ == 0x10 else None
                return found
        offset += size
    raise ValueError('ANDROID_MANIFEST_TAG_MISSING')


def validate_v51_execution_contract(root):
    """Verify declared source bindings without importing or executing packaged code."""
    root = Path(root).resolve()
    def read_json(name):
        return json.loads((root / name).read_text('utf8'))
    def digest(value):
        return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                         separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    def bound(manifest, key, required=()):
        if not isinstance(manifest, dict) or manifest.get(key) != digest({k: v for k, v in manifest.items() if k != key}):
            raise ValueError('V51_CONTRACT_FINGERPRINT_MISMATCH:' + key)
        hashes = manifest.get('source_hashes')
        if not isinstance(hashes, dict) or not hashes or not set(required) <= set(hashes):
            raise ValueError('V51_CONTRACT_SOURCE_BINDINGS_MISSING')
        for name, expected in hashes.items():
            path = root / relative_path(name)
            if (not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected)
                    or not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root)
                    or h(path) != expected):
                raise ValueError('V51_CONTRACT_SOURCE_STALE:' + name)
    contract = read_json('configs/v51_contract.json')
    registry = read_json('configs/v51_profiles.json')
    base = read_json('configs/v50_contract.json')
    selection = read_json('configs/v51_release_selection.json')
    bound(contract, 'manifest_fingerprint', V51_CONTRACT_SOURCES)
    bound(registry, 'registry_fingerprint', ('configs/v50_contract.json',))
    bound(base, 'manifest_fingerprint')
    if (contract.get('base_execution_manifest_fingerprint') != base['manifest_fingerprint']
            or contract.get('profile_registry_fingerprint') != registry['registry_fingerprint']
            or registry.get('base_execution_manifest_fingerprint') != base['manifest_fingerprint']):
        raise ValueError('V51_CONTRACT_BASE_BINDING_MISMATCH')
    if contract.get('release_selection') != selection:
        raise ValueError('V51_RELEASE_SELECTION_MISMATCH')
    selected = selection.get('default_profile_by_policy', {})
    if (selection.get('default_policy_id') != 'legacy' or contract.get('default_policy_id') != 'legacy'
            or set(selected) != {'legacy', 'dra'}):
        raise ValueError('V51_UNSUPPORTED_DEFAULT_POLICY')
    for policy, ident in selected.items():
        if not isinstance(ident, str):
            raise ValueError('V51_INVALID_SELECTED_PROFILE')
        for profiles in (registry.get('profiles', {}), contract.get('profiles', {})):
            profile = profiles.get(ident)
            if not isinstance(profile, dict) or policy not in profile.get('allowed_policy_ids', []):
                raise ValueError('V51_PROFILE_POLICY_NOT_ALLOWED:' + policy)
    generated = ('(function(g){g.DMSG_V51_MANIFEST = ' + json.dumps(contract, ensure_ascii=False, separators=(',', ':'))
                 + ';})(typeof globalThis!=="undefined"?globalThis:this);\n')
    if (root / 'apps/shared/v51-contract-data.js').read_text('utf8') != generated:
        raise ValueError('V51_GENERATED_CONTRACT_STALE')
    return {'default_policy': selection['default_policy_id'],
            'default_profile_id': selected[selection['default_policy_id']],
            'default_profile_by_policy': selected, 'manifest_fingerprint': contract['manifest_fingerprint']}


def verify_v51_app_freshness(root, dist):
    """Read explicit v5.1 artifacts, including before the new manifest is written."""
    root = Path(root)
    validate_distribution(dist, '5.1')
    try:
        selected = validate_v51_execution_contract(root)
        contract_error = None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        selected, contract_error = {}, str(exc)
    sources = copied_web_sources(root, '5.1')
    missing_source = sorted(k for k, p in sources.items() if not p.is_file())
    source_hashes = {k: h(p) for k, p in sorted(sources.items()) if p.is_file()}
    pwa = root / dist['pwa']; apk = root / dist['apk']
    if h(pwa) != dist['pwa_sha256'] or h(apk) != dist['sha256']:
        raise ValueError('V51_DISTRIBUTION_HASH_MISMATCH')
    all_web = _bounded_zip_payload(pwa, 'dmsg-web/')
    with zipfile.ZipFile(pwa) as z:
        if any(not i.is_dir() and not i.filename.startswith('dmsg-web/') for i in z.infolist()):
            raise ValueError('INVALID_PWA_ROOT')
    copied = {k: v for k, v in all_web.items() if k not in ('build-info.js', 'sw.js')}
    missing_assets = sorted(set(sources) - set(copied))
    extra_assets = sorted(set(copied) - set(sources))
    changed = sorted(k for k, p in sources.items() if p.is_file() and k in copied and p.read_bytes() != copied[k])
    packaged = _bounded_zip_payload(apk, 'assets/www/')
    expected_apk = {k: v for k, v in all_web.items() if k != 'sw.js'}
    generated = {k: hashlib.sha256(all_web[k]).hexdigest() for k in ('build-info.js', 'sw.js') if k in all_web}
    checks = {
        'copied_source_hashes': dist['copied_source_sha256'] == source_hashes,
        'source_fingerprint': dist['source_assets_fingerprint'] == hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest(),
        'generated_hashes': generated == dist['generated_assets_sha256'] and len(generated) == 2,
        'source_sw_template': h(root / 'apps/web/sw.js') == dist['source_sw_template_sha256'],
        'execution_contract': h(root / 'configs/v51_contract.json') == dist['execution_contract_sha256'],
        'execution_contract_sources': contract_error is None,
        'release_selection': contract_error is None and all(dist.get(k) == selected.get(k)
                            for k in ('default_policy', 'default_profile_id')),
        'root_apk': h(root / dist['root_apk']) == dist['root_apk_sha256'] == dist['sha256'],
        'apk_pwa_assets': packaged == expected_apk,
    }
    shell_id = hashlib.sha256(b''.join(k.encode() + v for k, v in sorted(all_web.items()) if k != 'sw.js')).hexdigest()[:16]
    checks['sw_generation'] = all_web.get('sw.js') == (root / 'apps/web/sw.js').read_text('utf8').replace('__BUILD__', shell_id).encode()
    shell = re.search(r'\bconst\s+SHELL\s*=\s*\[([^\]]*)\]', all_web.get('sw.js', b'').decode('utf8'), re.S)
    cache_members = set(re.findall(r'[\'"]([^\'"]+)[\'"]', shell.group(1))) if shell else set()
    checks['sw_required_assets'] = set(shared_assets('5.1')) <= cache_members
    scripts = set(re.findall(r'<script\b[^>]*\bsrc\s*=\s*[\'"]([^\'"]+)[\'"]', all_web.get('index.html', b'').decode('utf8'), re.I))
    checks['html_required_assets'] = set(shared_assets('5.1')) <= scripts
    info_raw = all_web.get('build-info.js', b'').decode('utf8')
    prefix = 'window.DMSG_BUILD = '
    info = json.loads(info_raw[len(prefix):].rstrip().removesuffix(';')) if info_raw.startswith(prefix) else {}
    checks['build_info'] = (info.get('version') == '5.1' and info.get('source') == dist['source_assets_fingerprint']
                            and info.get('copied_source_sha256') == source_hashes
                            and contract_error is None and all(info.get(k) == selected.get(k)
                                for k in ('default_policy', 'default_profile_id'))
                            and info.get('independent_evaluation') == 'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY'
                            and info.get('domain_calibration') == 'NOT_ESTABLISHED'
                            and info.get('android_device') == 'NOT_RUN')
    desktop = root / 'apps/desktop/assets.gen.js'
    desktop_raw = desktop.read_text('utf8')
    body = desktop_raw.split('module.exports = ', 1)[1].rstrip().removesuffix(';')
    embedded = json.loads(body)
    decoded = {k.removeprefix('/'): base64.b64decode(v['b64'], validate=True) for k, v in embedded.items()}
    checks['desktop_assets'] = h(desktop) == dist['desktop_assets_sha256'] and decoded == all_web
    with zipfile.ZipFile(apk) as z:
        manifest_version = _android_version(z.read('AndroidManifest.xml'))
    checks['android_version'] = manifest_version == {'versionCode': 51, 'versionName': '5.1'}
    passed = not (missing_source or missing_assets or extra_assets or changed) and all(checks.values())
    return {'status': 'PASS' if passed else 'FAIL', 'copied_asset_count': len(sources),
            'missing_source': missing_source, 'missing_assets': missing_assets, 'extra_assets': extra_assets,
            'changed_assets': changed, 'v51_checks': checks, 'android_manifest_version': manifest_version,
            'execution_contract_error': contract_error,
            'apk_pwa_equivalence': {'status': 'PASS_ASSETS_ONLY' if checks['apk_pwa_assets'] else 'FAIL',
                                    'signature_validation': 'NOT_RUN_IN_ASSETS_ONLY_MODE', 'device_install_and_run': 'NOT_RUN'},
            'scope': 'v5.1 source -> PWA -> APK + desktop embedded assets, generated SW/build-info, Android version. No device, signature, model-performance or independent-evaluation claim.'}


def verify_app_freshness(root, dist):
    if dist.get('version') == '5.1':
        return verify_v51_app_freshness(root, dist)
    sources = copied_web_sources(root)
    packaged, _ = packaged_web_assets(root)
    copied = {name: data for name, data in packaged.items() if name != 'build-info.js'}
    missing_source = sorted(name for name, p in sources.items() if not p.is_file())
    missing_assets = sorted(set(sources) - set(copied))
    extra_assets = sorted(set(copied) - set(sources))
    changed = sorted(name for name, p in sources.items()
                     if p.is_file() and name in copied and p.read_bytes() != copied[name])
    apk = compare_packaged_assets(Path(root) / dist['apk'], root=root)
    passed = not (missing_source or missing_assets or extra_assets or changed) and apk['status'] == 'PASS_ASSETS_ONLY'
    return {'status': 'PASS' if passed else 'FAIL', 'copied_asset_count': len(sources),
            'missing_source': missing_source, 'missing_assets': missing_assets,
            'extra_assets': extra_assets, 'changed_assets': changed,
            'apk_pwa_equivalence': apk,
            'scope': 'Current copied source bytes -> PWA -> APK web assets. No binary/device execution claim.',
            'generated_assets_excluded_from_source_comparison': ['build-info.js', 'sw.js']}


def verify(zip_path=None, *, root=ROOT):
    root = Path(root)
    errors = []
    version = None
    app_freshness = {'status': 'NOT_VERIFIED'}
    actual = {p.relative_to(root).as_posix(): p for p in content_files(root)
              if p.name != 'MANIFEST_SHA256.json'}
    try:
        manifest = json.loads((root / 'MANIFEST_SHA256.json').read_text('utf8'))
        version = version_of(manifest)
        expected = manifest['files']
        if not isinstance(expected, dict):
            raise ValueError('INVALID_MANIFEST_FILES')
        for key in expected:
            relative_path(key)
        dist = validate_distribution(json.loads((root / distribution_path(version)).read_text('utf8')), version)
        required = required_members(version, dist)
        if (root / 'tests_linkguard/test_linkguard.py').is_file():
            required |= {'internal/evidence/v47/BASELINE_V46.json', 'tests_data/release/skill_path_additions.json'}
        for name in sorted(required):
            if not (root / name).is_file():
                errors.append('MISSING ' + name)
        if set(expected) != set(actual):
            errors.append('MANIFEST_FILE_SET_MISMATCH')
        for key, p in actual.items():
            if key in expected and (expected[key]['sha256'] != h(p) or expected[key]['bytes'] != p.stat().st_size):
                errors.append('HASH_MISMATCH ' + key)
        for key, hash_key in [('apk', 'sha256'), ('pwa', 'pwa_sha256')]:
            if (root / dist[key]).is_file() and h(root / dist[key]) != dist[hash_key]:
                errors.append('DISTRIBUTION_HASH_MISMATCH ' + dist[key])
        if (root / 'dmsg/SKILL.md').is_file() and 'name: dmsg' not in (root / 'dmsg/SKILL.md').read_text('utf8'):
            errors.append('SKILL_ID')
        source = {'dmsg/' + p.relative_to(root / 'dmsg').as_posix(): h(p)
                  for p in content_files(root / 'dmsg')}
        aliases = []
        for name in skill_names(version):
            p = root / name
            if not p.is_file():
                continue  # Already a MISSING issue, never success or an uncaught exception.
            aliases.append(h(p))
            try:
                with zipfile.ZipFile(p) as z:
                    issues = archive_issues(z)
                    if issues or z.testzip() is not None:
                        errors.append('BAD_SKILL_ARCHIVE ' + name)
                        continue  # Do not decompress/hash members after a bound or CRC failure.
                    members = {i.filename: hashlib.sha256(z.read(i)).hexdigest()
                               for i in z.infolist() if not i.is_dir()}
                    if members != source:
                        errors.append('SKILL_SOURCE_MISMATCH ' + name)
                    if sum(n.endswith('/SKILL.md') for n in members) != 1:
                        errors.append('SKILL_ENTRYPOINT_COUNT ' + name)
            except (OSError, ValueError, zipfile.BadZipFile):
                errors.append('BAD_SKILL_ARCHIVE ' + name)
        if len(aliases) == 4 and len(set(aliases)) != 1:
            errors.append('SKILL_ZIP_DIFFERS')
        app_freshness = verify_app_freshness(root, dist)
        if app_freshness['status'] != 'PASS':
            errors.append('SOURCE_TO_APP_ASSETS_MISMATCH')
        if zip_path:
            with zipfile.ZipFile(zip_path) as z:
                issues = archive_issues(z)
                errors.extend(issues)
                if not issues:
                    if z.testzip() is not None:
                        errors.append('ZIP_CRC_FAIL')
                    files = [n for n in z.namelist() if not n.endswith('/')]
                    roots = {n.split('/')[0] for n in files}
                    if len(roots) != 1:
                        errors.append('MULTIPLE_ROOT_FOLDERS')
                    else:
                        prefix = next(iter(roots)) + '/'
                        tree = {**actual, 'MANIFEST_SHA256.json': root / 'MANIFEST_SHA256.json'}
                        if {n[len(prefix):] for n in files} != set(tree):
                            errors.append('ZIP_TREE_MISMATCH')
                        for rel, p in tree.items():
                            if prefix + rel in files and hashlib.sha256(z.read(prefix + rel)).hexdigest() != h(p):
                                errors.append('ZIP_CONTENT_MISMATCH ' + rel)
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error, zipfile.BadZipFile) as exc:
        errors.append('RELEASE_METADATA_OR_ARCHIVE_ERROR ' + type(exc).__name__ + ': ' + str(exc))
    return {'version': version, 'checks': 'manifest,metadata,skill_source,source_to_app_assets,artifact_hashes,optional_archive',
            'file_count': len(actual) + 1, 'issues': errors, 'pass': not errors,
            'source_to_app_freshness': app_freshness,
            'real_model_verified': False, 'host_install_verified': False,
            'note': 'Source edits require new release packaging; this verifier never blesses stale manifests or rebuilds artifacts.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('archive', nargs='?')
    ap.add_argument('--root', type=Path, default=ROOT)
    args = ap.parse_args()
    result = verify(args.archive, root=args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['pass'] else 1)
