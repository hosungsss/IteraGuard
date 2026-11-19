"""Build every runnable v4.7 app from one source tree.

  1. export Python reference data -> apps/shared/engine-data.js
  2. regenerate conformance vectors and require Python == JS (gate)
  3. assemble the offline web app (PWA) -> apps/dist/web
  4. embed it in the desktop host and cross-compile with Bun for
     linux-x64, windows-x64, darwin-arm64, darwin-x64
  5. package the Capacitor Android/iOS projects with the same web bundle
Writes internal/evidence/v47_build.json. Local files only; no uploads.
Usage: python tools/build_apps.py [--skip-desktop] [--skip-mobile]
"""
from __future__ import annotations
import argparse, base64, datetime, hashlib, json, mimetypes, os, shutil, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / 'apps'
DIST = APPS / 'dist'
EVD = ROOT / 'internal' / 'evidence'
VERSION = '4.8'
TARGETS = {
    'linux-x64': ('bun-linux-x64', 'dmsg-desktop'),
    'windows-x64': ('bun-windows-x64', 'dmsg-desktop.exe'),
    'macos-arm64': ('bun-darwin-arm64', 'dmsg-desktop'),
    'macos-x64': ('bun-darwin-x64', 'dmsg-desktop'),
}
WEB_FILES = ['index.html', 'styles.css', 'app.js', 'sw.js', 'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-180.png',
             'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png']
FIXED_TIME = (2026, 11, 1, 0, 0, 0)


def sh(cmd, cwd=ROOT, env=None):
    r = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=900)
    if r.returncode:
        print(r.stdout[-3000:]); raise SystemExit(f'FAILED: {cmd}')
    return r.stdout


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def zip_dir(src: Path, out: Path, root_name: str, exec_names=()):
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(x for x in src.rglob('*') if x.is_file()):
            rel = p.relative_to(src).as_posix()
            zi = zipfile.ZipInfo(f'{root_name}/{rel}', date_time=FIXED_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if (p.name in exec_names or p.suffix in ('.command', '.sh')) else 0o644
            zi.external_attr = (0o100000 | mode) << 16
            z.writestr(zi, p.read_bytes())
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None


def build_web(conf: dict) -> Path:
    web = DIST / 'web'
    if web.exists(): shutil.rmtree(web)
    (web / 'icons').mkdir(parents=True)
    for f in WEB_FILES:
        shutil.copy2(APPS / 'web' / f, web / f)
    for f in ('engine-data.js', 'dmsg-engine.js', 'dmsg-nlp.js', 'linkguard-data.js', 'dmsg-linkguard.js', 'dmsg-apkscan.js', 'dmsg-domainintel.js'):
        shutil.copy2(APPS / 'shared' / f, web / f)
    (web / 'nlp').mkdir()
    for f in ('dmsg-nlp-vocab.js', 'dmsg-nlp-heads.js', 'dmsg-nlp-weights.js', 'NLP_ASSETS_MANIFEST.json'):
        shutil.copy2(APPS / 'shared' / 'nlp' / f, web / 'nlp' / f)
    data = json.loads((APPS / 'shared' / 'engine-data.js').read_text('utf8').split('g.DMSG_DATA = ', 1)[1].rsplit('; })(', 1)[0])
    src_id = hashlib.sha256(json.dumps(data['source_sha256'], sort_keys=True).encode()).hexdigest()[:12]
    info = {'version': VERSION, 'built': datetime.date.today().isoformat(), 'source': src_id,
            'conformance': {'total': conf['total'], 'pass': conf['pass'], 'status': conf['status']}}
    par = EVD / 'v47_nlp_parity.json'
    if par.is_file():
        pj = json.loads(par.read_text('utf8')); info['nlp_parity'] = {k: pj[k] for k in ('status', 'n', 'action_match', 'tokenizer_exact')}
    ev = ROOT / 'tools' / 'nlp' / 'eval' / 'v46_vs_v45_locked_report.json'
    if ev.is_file():
        sy = json.loads(ev.read_text('utf8'))['systems']
        b = sy['V46_b8n_int8']['W']['policy']; a0 = sy['A_v45']['W']['policy']
        info['nlp_eval'] = {'expected': b['expected_action_rate'], 'recall': b['risky_intervention_recall'], 'fa': b['benign_false_alarm_rate'], 'n': b['n'],
                            'v45': {'expected': a0['expected_action_rate'], 'recall': a0['risky_intervention_recall'], 'fa': a0['benign_false_alarm_rate']}}
    (web / 'build-info.js').write_text('window.DMSG_BUILD = ' + json.dumps(info, ensure_ascii=False) + ';\n', 'utf8')
    shell_hash = hashlib.sha256(b''.join((web / f).read_bytes() for f in sorted(WEB_FILES + ['engine-data.js', 'dmsg-engine.js', 'dmsg-nlp.js', 'linkguard-data.js', 'dmsg-linkguard.js', 'dmsg-apkscan.js', 'dmsg-domainintel.js', 'build-info.js',
                                'nlp/dmsg-nlp-heads.js', 'nlp/dmsg-nlp-vocab.js', 'nlp/dmsg-nlp-weights.js']) if f != 'sw.js')).hexdigest()[:12]
    (web / 'sw.js').write_text((web / 'sw.js').read_text('utf8').replace('__BUILD__', shell_hash), 'utf8')
    return web


def build_desktop(web: Path) -> dict:
    assets = {}
    for p in sorted(x for x in web.rglob('*') if x.is_file()):
        rel = '/' + p.relative_to(web).as_posix()
        typ = {'.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.html': 'text/html; charset=utf-8',
               '.webmanifest': 'application/manifest+json', '.svg': 'image/svg+xml', '.png': 'image/png'}.get(p.suffix, mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
        assets[rel] = {'type': typ, 'b64': base64.b64encode(p.read_bytes()).decode()}
    (APPS / 'desktop' / 'assets.gen.js').write_text('/* GENERATED by tools/build_apps.py */\nmodule.exports = ' + json.dumps(assets) + ';\n', 'utf8')
    out = {}
    for name, (target, exe) in TARGETS.items():
        stage = DIST / 'desktop' / name
        if stage.exists(): shutil.rmtree(stage)
        stage.mkdir(parents=True)
        sh(['bun', 'build', '--compile', '--minify', f'--target={target}', 'apps/desktop/server.js', '--outfile', str(stage / exe)])
        sig = None
        if name.startswith('macos'):
            # Bun keeps its own signature on some Mach-O targets; appending the app invalidates it.
            # Re-sign ad-hoc (rcodesign, no Apple tools) and require every page hash to verify.
            rc = shutil.which('rcodesign') or str(Path.home() / '.cargo/bin/rcodesign')
            if Path(rc).is_file():
                sh([rc, 'sign', str(stage / exe)])
            v = subprocess.run([sys.executable, 'tools/verify_macho_signature.py', str(stage / exe)], cwd=str(ROOT), text=True, stdout=subprocess.PIPE)
            sig = json.loads(v.stdout)[0]
            if sig['status'] != 'PAGE_HASHES_VALID':
                raise SystemExit(f'MACOS_SIGNATURE_INVALID: {name} (install rcodesign: cargo install apple-codesign)')
        readme = (APPS / 'desktop' / 'launchers' / f'README_{name.split("-")[0]}.txt').read_text('utf8')
        (stage / 'README.txt').write_text(readme, 'utf8')
        if name.startswith('macos'):
            shutil.copy2(APPS / 'desktop' / 'launchers' / 'open-dmsg.command', stage / '의심계 실행.command')
        elif name.startswith('linux'):
            shutil.copy2(APPS / 'desktop' / 'launchers' / 'run-dmsg.sh', stage / 'run-dmsg.sh')
        else:
            shutil.copy2(APPS / 'desktop' / 'launchers' / 'run-dmsg.bat', stage / 'run-dmsg.bat')
        z = DIST / f'IteraGuard_DoubtMeter_v4_8_desktop_{name}.zip'
        zip_dir(stage, z, f'dmsg-desktop-{name}', exec_names=(exe,))
        out[name] = {'zip': z.name, 'zip_sha256': sha(z), 'zip_bytes': z.stat().st_size, 'executable': exe,
                     'executable_sha256': sha(stage / exe), 'executable_bytes': (stage / exe).stat().st_size,
                     'macho_signature': None if sig is None else {'status': sig['status'], 'adhoc': [c['adhoc'] for c in sig['code_directories']]}}
    return out


def build_mobile(web: Path) -> dict:
    mob = APPS / 'mobile'
    www = mob / 'www'
    if www.exists(): shutil.rmtree(www)
    shutil.copytree(web, www)
    res = {}
    if (mob / 'node_modules').is_dir():
        sh(['npx', '--no-install', 'cap', 'sync'], cwd=mob)
        res['capacitor_sync'] = 'PASS'
    out = {}
    for plat in ('android', 'ios'):
        if not (mob / plat).is_dir():
            out[plat] = {'status': 'PROJECT_NOT_GENERATED'}; continue
        z = DIST / f'IteraGuard_DoubtMeter_v4_8_{plat}_project.zip'
        stage = DIST / f'_{plat}'
        if stage.exists(): shutil.rmtree(stage)
        stage.mkdir(parents=True)
        shutil.copytree(mob / plat, stage / plat, ignore=shutil.ignore_patterns('build', '.gradle', 'Pods', 'DerivedData', 'node_modules'))
        for f in ('capacitor.config.json', 'package.json', 'package-lock.json', 'BUILD_' + plat.upper() + '.md'):
            if (mob / f).is_file(): shutil.copy2(mob / f, stage / f)
        shutil.copytree(www, stage / 'www')
        zip_dir(stage, z, f'dmsg-{plat}', exec_names=('gradlew',))
        shutil.rmtree(stage)
        out[plat] = {'zip': z.name, 'zip_sha256': sha(z), 'zip_bytes': z.stat().st_size, 'status': 'SOURCE_PROJECT_NOT_COMPILED'}
    pwa = DIST / 'IteraGuard_DoubtMeter_v4_8_web_pwa.zip'
    zip_dir(web, pwa, 'dmsg-web')
    out['pwa'] = {'zip': pwa.name, 'zip_sha256': sha(pwa), 'zip_bytes': pwa.stat().st_size, 'status': 'BUILT_OFFLINE_WEB_APP'}
    out.update(res)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--skip-desktop', action='store_true'); ap.add_argument('--skip-mobile', action='store_true')
    a = ap.parse_args(argv)
    DIST.mkdir(parents=True, exist_ok=True); EVD.mkdir(parents=True, exist_ok=True)
    sh([sys.executable, 'tools/export_engine_data.py'])
    sh([sys.executable, 'tools/make_conformance_vectors.py'])
    sh(['node', 'apps/conformance/run_conformance.js', str(EVD / 'v47_conformance.json')])
    sh([sys.executable, 'tools/check_contrast.py'])
    # on-device NLP: JS must reproduce the Python reference (tokens, features, labels, attribution, advisory)
    r = subprocess.run(['node', 'tools/nlp/nlp_parity.js'], cwd=str(ROOT), text=True, stdout=subprocess.PIPE, timeout=1800)
    (EVD / 'v47_nlp_parity.json').write_text(r.stdout, 'utf8')
    if r.returncode: raise SystemExit('NLP_PARITY_FAILED')
    conf = json.loads((EVD / 'v47_conformance.json').read_text('utf8'))
    web = build_web(conf)
    report = {'version': VERSION, 'date_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'conformance': {k: conf[k] for k in ('status', 'total', 'pass', 'sections')},
              'bun': sh(['bun', '--version']).strip(), 'web': sorted(p.relative_to(web).as_posix() for p in web.rglob('*') if p.is_file())}
    if not a.skip_desktop: report['desktop'] = build_desktop(web)
    if not a.skip_mobile:
        report['mobile'] = build_mobile(web)
        # Debug APK built from format specs (no SDK binaries), then verified by independent parsers.
        apk = DIST / 'IteraGuard_DoubtMeter_v4_8_android_debug.apk'
        report['mobile']['apk_build'] = json.loads(sh([sys.executable, 'tools/build_apk.py', '--out', str(apk)]))
        sh([sys.executable, 'tools/verify_apk.py', str(apk), '--evidence', str(EVD / 'v47_apk.json')])
        report['mobile']['apk_verify'] = json.loads((EVD / 'v47_apk.json').read_text('utf8'))['status']
    (EVD / 'v47_build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(json.dumps({k: (v if k != 'web' else len(v)) for k, v in report.items()}, ensure_ascii=False, indent=1)[:3000])


if __name__ == '__main__':
    main()
