"""Assemble the v5 development candidate from current sources; never claim device validation."""
from pathlib import Path
import argparse
import base64
import datetime
import hashlib
import json
import mimetypes
import shutil

import build_apps
import build_apk

ROOT = Path(__file__).resolve().parents[1]
SHARED = ('engine-data.js', 'dmsg-engine.js', 'dmsg-nlp.js', 'linkguard-data.js',
          'dmsg-linkguard.js', 'dmsg-apkscan.js', 'dmsg-domainintel.js',
          'v50-contract-data.js', 'v50-contract.js')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_assets():
    files = {name: ROOT / 'apps/web' / name for name in build_apps.WEB_FILES if name != 'sw.js'}
    files.update({name: ROOT / 'apps/shared' / name for name in SHARED})
    base = ROOT / 'apps/shared/nlp'
    files.update({'nlp/' + p.relative_to(base).as_posix(): p for p in base.rglob('*')
                  if p.is_file() and p.name != 'desktop.ini' and '__pycache__' not in p.parts})
    return files


def build():
    files = source_assets()
    for name, path in files.items():
        if not path.is_file():
            raise ValueError('MISSING_SOURCE_ASSET:' + name)
    source_hashes = {name: sha(path) for name, path in sorted(files.items())}
    source_id = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    web = ROOT / 'apps/dist/web'
    if web.exists():
        shutil.rmtree(web)  # Generated staging only; source files never live here.
    web.mkdir(parents=True)
    for name, path in files.items():
        dest = web / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    info = {'version': '5.0', 'release_stage': 'DEVELOPMENT_CANDIDATE',
            'built': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat(),
            'source': source_id, 'copied_source_sha256': source_hashes,
            'typed_validation': 'SEE_SEPARATE_RUNTIME_EVIDENCE',
            'independent_evaluation': 'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY',
            'android_device': 'NOT_RUN', 'transport_scope': 'LOOPBACK_ONLY',
            'default_policy': 'legacy', 'comparison_policy': 'dra',
            'provider_temperature': 1.52, 'domain_calibration': 'NOT_ESTABLISHED'}
    checks = ROOT / 'internal/evidence/v50/source_validation.json'
    if checks.exists():
        report = json.loads(checks.read_text())
        if report.get('source_assets_sha256') == source_hashes:
            info['source_validation'] = report.get('status', 'NOT_RUN')
            info.update({k: report[k] for k in ('conformance', 'nlp_parity', 'nlp_golden') if k in report})
    (web / 'build-info.js').write_text('window.DMSG_BUILD = ' + json.dumps(info, ensure_ascii=False) + ';\n')
    shell_hash = hashlib.sha256(b''.join(name.encode() + p.read_bytes()
                               for name, p in sorted((p.relative_to(web).as_posix(), p)
                               for p in web.rglob('*') if p.is_file()))).hexdigest()[:16]
    (web / 'sw.js').write_text((ROOT / 'apps/web/sw.js').read_text().replace('__BUILD__', shell_hash))
    pwa = ROOT / 'apps/dist/IteraGuard_DoubtMeter_v5_0_web_pwa.zip'
    build_apps.zip_dir(web, pwa, 'dmsg-web')
    build_apk.VERSION_CODE, build_apk.VERSION_NAME = 50, '5.0'
    apk = ROOT / 'apps/dist/IteraGuard_DoubtMeter_v5_0_android_debug.apk'
    result = build_apk.build(apk)
    shutil.copy2(apk, ROOT / 'IteraGuard_DoubtMeter_v5.0.apk')
    assets = {}
    types = {'.js': 'text/javascript; charset=utf-8', '.html': 'text/html; charset=utf-8',
             '.css': 'text/css; charset=utf-8', '.webmanifest': 'application/manifest+json'}
    for path in sorted(p for p in web.rglob('*') if p.is_file()):
        name = '/' + path.relative_to(web).as_posix()
        assets[name] = {'type': types.get(path.suffix, mimetypes.guess_type(path.name)[0] or 'application/octet-stream'),
                        'b64': base64.b64encode(path.read_bytes()).decode()}
    (ROOT / 'apps/desktop/assets.gen.js').write_text('/* GENERATED v5 web assets */\nmodule.exports = ' + json.dumps(assets) + ';\n')
    result.update(version='5.0', version_code=50, build_type='DEBUG', release_stage='DEVELOPMENT_CANDIDATE',
                  device_install='NOT_RUN', independent_evaluation='NOT_RUN',
                  pwa=pwa.relative_to(ROOT).as_posix(), pwa_sha256=sha(pwa),
                  copied_source_sha256=source_hashes, source_assets_fingerprint=source_id,
                  asset_count=len(assets), desktop='BUN_SOURCE_HOST_EMBEDDED_ASSETS_NOT_CROSS_COMPILED',
                  reproducibility='Source/asset hashes verified; fresh debug signing certificate per build')
    out = ROOT / 'internal/evidence/v50/distribution_build.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'copied_source_sha256'}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
