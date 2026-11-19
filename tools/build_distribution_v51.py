"""Build only v5.1 artifacts from frozen sources; no inference or v5.0 rebuild."""
from pathlib import Path
import argparse
import base64
import datetime
import hashlib
import json
import mimetypes
import re
import shutil
import subprocess
import sys

if __package__:
    from . import build_apps, build_apk
    from .release_metadata import shared_assets, validate_distribution
    from .verify_release import copied_web_sources, validate_v51_execution_contract, verify_v51_app_freshness
else:
    import build_apps, build_apk
    from release_metadata import shared_assets, validate_distribution
    from verify_release import copied_web_sources, validate_v51_execution_contract, verify_v51_app_freshness

ROOT = Path(__file__).resolve().parents[1]
VERSION, VERSION_CODE = '5.1', 51


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_assets(root=ROOT):
    return copied_web_sources(Path(root), VERSION)


def preflight(root=ROOT):
    """All read-only checks happen before generated output is replaced."""
    root = Path(root).resolve()
    files = source_assets(root)
    for name, path in files.items():
        if not path.is_file():
            raise ValueError('MISSING_SOURCE_ASSET:' + name)
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('SOURCE_ASSET_OUTSIDE_TREE:' + name)
    sw = (root / 'apps/web/sw.js').read_text('utf8')
    if sw.count('__BUILD__') != 1:
        raise ValueError('INVALID_SW_BUILD_PLACEHOLDER')
    shell = re.search(r'\bconst\s+SHELL\s*=\s*\[([^\]]*)\]', sw, re.S)
    if not shell:
        raise ValueError('SW_SHELL_LIST_MISSING')
    listed = set(re.findall(r'[\'"]([^\'"]+)[\'"]', shell.group(1)))
    if not set(shared_assets(VERSION)) <= listed:
        raise ValueError('SW_MISSING_REQUIRED_ASSETS:' + ','.join(sorted(set(shared_assets(VERSION)) - listed)))
    index = files['index.html'].read_text('utf8')
    scripts = set(re.findall(r'<script\b[^>]*\bsrc\s*=\s*[\'"]([^\'"]+)[\'"]', index, re.I))
    if not set(shared_assets(VERSION)) <= scripts:
        raise ValueError('HTML_MISSING_REQUIRED_ASSETS:' + ','.join(sorted(set(shared_assets(VERSION)) - scripts)))
    for rel in ('configs/v51_contract.json', 'configs/v51_profiles.json', 'tools/export_v51_contract.py'):
        if not (root / rel).is_file():
            raise ValueError('MISSING_EXECUTION_CONTRACT:' + rel)
    run = subprocess.run([sys.executable, '-X', 'utf8', str(root / 'tools/export_v51_contract.py'), '--check'],
                         cwd=root, text=True, capture_output=True, timeout=120)
    if run.returncode:
        raise ValueError('EXECUTION_CONTRACT_CHECK_FAILED')
    return files, validate_v51_execution_contract(root)


def build(root=ROOT):
    root = Path(root).resolve()
    files, selected = preflight(root)
    source_hashes = {name: sha(path) for name, path in sorted(files.items())}
    source_id = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    web = root / 'apps/dist/web'
    if web.is_symlink():
        raise ValueError('UNSAFE_GENERATED_STAGING')
    # Rebuild declared assets in place; never recursively delete the output tree.
    if web.exists():
        expected = set(files) | {'build-info.js', 'sw.js'}
        extra = [x.relative_to(web).as_posix() for x in web.rglob('*') if x.is_file() and x.relative_to(web).as_posix() not in expected]
        if extra: raise ValueError('UNEXPECTED_STAGING_ASSETS:' + ','.join(sorted(extra)))
        if any(x.is_symlink() for x in web.rglob('*')): raise ValueError('UNSAFE_GENERATED_STAGING')
    web.mkdir(parents=True, exist_ok=True)
    for name, path in files.items():
        dest = web / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    info = {'version': VERSION, 'release_stage': 'DEVELOPMENT_CANDIDATE',
            'built': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat(),
            'source': source_id, 'copied_source_sha256': source_hashes,
            'default_policy': selected['default_policy'], 'default_profile_id': selected['default_profile_id'],
            'comparison_policy': 'dra', 'typed_validation': 'SEE_SEPARATE_RUNTIME_EVIDENCE',
            'contract_validation': 'SOURCE_CHECK_ONLY_NOT_MODEL_PERFORMANCE',
            'independent_evaluation': 'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY',
            'domain_calibration': 'NOT_ESTABLISHED', 'provider_temperature': 1.52,
            'model_attested': False, 'android_device': 'NOT_RUN', 'transport_scope': 'LOOPBACK_ONLY'}
    (web / 'build-info.js').write_text('window.DMSG_BUILD = ' + json.dumps(info, ensure_ascii=False) + ';\n', 'utf8', newline='\n')
    shell_id = hashlib.sha256(b''.join(name.encode() + p.read_bytes() for name, p in sorted(
        (p.relative_to(web).as_posix(), p) for p in web.rglob('*') if p.is_file() and p.relative_to(web).as_posix() != 'sw.js'))).hexdigest()[:16]
    sw_template = root / 'apps/web/sw.js'
    (web / 'sw.js').write_text(sw_template.read_text('utf8').replace('__BUILD__', shell_id), 'utf8', newline='\n')
    pwa = root / 'apps/dist/IteraGuard_DoubtMeter_v5_1_web_pwa.zip'
    build_apps.zip_dir(web, pwa, 'dmsg-web')
    apk = root / 'apps/dist/IteraGuard_DoubtMeter_v5_1_android_debug.apk'
    saved = {key: getattr(build_apk, key) for key in ('ROOT', 'WEB', 'KEY_DIR', 'VERSION_CODE', 'VERSION_NAME', 'debug_key')}
    try:
        build_apk.ROOT, build_apk.WEB = root, web
        # Ephemeral debug signing: never read, replace, or generate source-tree private keys.
        build_apk.debug_key = build_apk._new_debug_key
        build_apk.VERSION_CODE, build_apk.VERSION_NAME = VERSION_CODE, VERSION
        result = build_apk.build(apk)
    finally:
        for key, value in saved.items():
            setattr(build_apk, key, value)
    root_apk = root / 'IteraGuard_DoubtMeter_v5.1.apk'
    shutil.copy2(apk, root_apk)
    assets = {}
    types = {'.js': 'text/javascript; charset=utf-8', '.html': 'text/html; charset=utf-8',
             '.css': 'text/css; charset=utf-8', '.webmanifest': 'application/manifest+json'}
    for path in sorted(p for p in web.rglob('*') if p.is_file()):
        assets['/' + path.relative_to(web).as_posix()] = {
            'type': types.get(path.suffix, mimetypes.guess_type(path.name)[0] or 'application/octet-stream'),
            'b64': base64.b64encode(path.read_bytes()).decode()}
    desktop = root / 'apps/desktop/assets.gen.js'
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text('/* GENERATED v5.1 web assets */\nmodule.exports = ' + json.dumps(assets) + ';\n', 'utf8', newline='\n')
    result.update(version=VERSION, version_code=VERSION_CODE, version_name=VERSION,
                  build_type='DEBUG', release_stage='DEVELOPMENT_CANDIDATE', device_install='NOT_RUN',
                  independent_evaluation='NOT_RUN_AI_DEVELOPMENT_DATA_ONLY', domain_calibration='NOT_ESTABLISHED',
                  model_attested=False, contract_validation='SOURCE_CHECK_ONLY_NOT_MODEL_PERFORMANCE',
                  default_profile_id=selected['default_profile_id'], default_policy=selected['default_policy'],
                  pwa=pwa.relative_to(root).as_posix(), pwa_sha256=sha(pwa),
                  root_apk=root_apk.relative_to(root).as_posix(), root_apk_sha256=sha(root_apk),
                  copied_source_sha256=source_hashes, source_assets_fingerprint=source_id,
                  source_sw_template_sha256=sha(sw_template), desktop_assets_sha256=sha(desktop),
                  execution_contract_sha256=sha(root / 'configs/v51_contract.json'),
                  generated_assets_sha256={name: sha(web / name) for name in ('build-info.js', 'sw.js')},
                  asset_count=len(assets), desktop='BUN_SOURCE_HOST_EMBEDDED_ASSETS_NOT_CROSS_COMPILED',
                  signature_validation='NOT_RUN_IN_BUILD_REQUIRES_SEPARATE_VERIFIER',
                  reproducibility='Current source hashes; ephemeral in-memory debug signing key, so APK bytes vary across builds. No store-signing/device claim')
    validate_distribution(result, VERSION)
    freshness = verify_v51_app_freshness(root, result)
    if freshness['status'] != 'PASS':
        raise ValueError('BUILT_ASSET_VERIFICATION_FAILED:' + json.dumps(freshness, ensure_ascii=True))
    result['asset_verification'] = freshness
    out = root / 'internal/evidence/v51/distribution_build.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(json.dumps({'version': VERSION, 'apk': result['apk'], 'pwa': result['pwa'],
                      'asset_count': len(assets), 'asset_verification': freshness['status'],
                      'device_install': 'NOT_RUN', 'independent_evaluation': result['independent_evaluation']}))
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
