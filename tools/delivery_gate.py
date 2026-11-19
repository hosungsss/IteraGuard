"""Offline delivery verification using the archive's version and build metadata.

No browser delivery, model execution, or cloud upload is implied by success.
Usage: python tools/delivery_gate.py FULL.zip OUTDIR
"""
from pathlib import Path
import hashlib
import json
import re
import sys
import tempfile
import zipfile

if __package__:
    from .release_metadata import (archive_issues, distribution_path, required_members,
                                   validate_distribution, version_of)
else:  # Direct CLI invocation already puts the script directory on sys.path.
    from release_metadata import (archive_issues, distribution_path, required_members,
                                  validate_distribution, version_of)

ALLOWED_NAME = re.compile(r'[A-Za-z0-9_.-]+\Z')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def archive_contract(z, require_manifest):
    issues = archive_issues(z)
    if issues:
        raise ValueError(','.join(issues))
    names = [i.filename for i in z.infolist() if not i.is_dir()]
    roots = {n.split('/')[0] for n in names}
    if len(roots) != 1:
        raise ValueError('MULTIPLE_ROOT_FOLDERS')
    prefix = next(iter(roots)) + '/'
    files = {n[len(prefix):] for n in names}
    meta_path = 'MANIFEST_SHA256.json' if require_manifest else 'CORE_SCOPE.json'
    if meta_path not in files:
        raise ValueError('MISSING_' + meta_path)
    manifest = json.loads(z.read(prefix + meta_path))
    version = version_of(manifest)
    dist = validate_distribution(json.loads(z.read(prefix + distribution_path(version))), version)
    required = required_members(version, dist)
    # Regression prerequisites are not disposable historical reports.
    if 'tests_linkguard/test_linkguard.py' in files:
        required |= {'internal/evidence/v47/BASELINE_V46.json', 'tests_data/release/skill_path_additions.json'}
    if not required <= files:
        raise ValueError('MISSING_REQUIRED_MEMBERS:' + repr(sorted(required - files)))
    return prefix, files, version, dist, required, manifest


def checked_members(archive, *, require_manifest):
    archive = Path(archive)
    if not archive.is_file() or not ALLOWED_NAME.fullmatch(archive.name):
        raise ValueError('UNSAFE_OR_MISSING_DOWNLOAD_FILENAME')
    with zipfile.ZipFile(archive) as z:
        prefix, files, version, dist, required, manifest = archive_contract(z, require_manifest)
        if z.testzip() is not None:
            raise ValueError('ZIP_CRC_ERROR')
        if require_manifest:
            if set(manifest['files']) != files - {'MANIFEST_SHA256.json'}:
                raise ValueError('MANIFEST_MEMBER_SET_MISMATCH')
            for rel, entry in manifest['files'].items():
                data = z.read(prefix + rel)
                if hashlib.sha256(data).hexdigest() != entry['sha256'] or len(data) != entry['bytes']:
                    raise ValueError('MANIFEST_HASH_MISMATCH:' + rel)
        for key, hash_key in [('apk', 'sha256'), ('pwa', 'pwa_sha256')]:
            if hashlib.sha256(z.read(prefix + dist[key])).hexdigest() != dist[hash_key]:
                raise ValueError('DISTRIBUTION_HASH_MISMATCH:' + dist[key])
        # Every entry, including directory entries, was checked before extraction.
        with tempfile.TemporaryDirectory() as tmp:
            z.extractall(tmp)
            for rel in required:
                if not (Path(tmp) / prefix / rel).is_file():
                    raise ValueError('REEXTRACTION_MISSING:' + rel)
        return {'version': version, 'sha256': sha(archive), 'bytes': archive.stat().st_size,
                'member_count': len(files), 'crc': 'PASS', 'safe_paths': 'PASS',
                'reextraction': 'PASS', 'internal_manifest': 'PASS' if require_manifest else 'SCOPED_CORE',
                'root': prefix.rstrip('/')}


def make_core(full, outdir):
    outdir = Path(outdir)
    with zipfile.ZipFile(full) as src:
        prefix, files, version, dist, required, _ = archive_contract(src, True)
        out = outdir / f'IteraGuard_DoubtMeter_v{version.replace(".", "_")}_CORE.zip'
        kept = {}
        for rel in sorted(files):
            if rel == 'MANIFEST_SHA256.json':
                continue
            if rel not in required and (rel.startswith(('internal/source_material/', 'internal/evidence/'))
                    or re.match(r'apps/dist/.*_desktop_', rel)
                    or re.fullmatch(r'dmsg_v[0-9.]+\.(skill|zip)', rel)):
                continue
            kept[rel] = src.read(prefix + rel)
    kept['CORE_SCOPE.json'] = json.dumps({'version': version, 'scope': 'CORE_NOT_FULL',
        'excluded': 'Optional historical evidence, source-reference attachments and native desktop archives.',
        'preserved': 'Current release metadata, skill aliases and regression prerequisites.'}, indent=2).encode()
    kept['README_CORE_SCOPE.txt'] = b'Core fallback; not equivalent to FULL. No model or device certification. See CORE_SCOPE.json.\n'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
        for rel, data in sorted(kept.items()):
            dst.writestr(prefix + rel, data)
    return out


def run(full, outdir):
    full, outdir = Path(full), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    full_result = checked_members(full, require_manifest=True)
    core = make_core(full, outdir)
    core_result = checked_members(core, require_manifest=False)
    version = full_result['version']
    stem = f'IteraGuard_DoubtMeter_v{version.replace(".", "_")}'
    report = {'status': 'LOCAL_DELIVERY_ARTIFACT_VERIFIED', 'host_browser_download': 'NOT_VERIFIED',
              'full': {'file': full.name, **full_result}, 'core': {'file': core.name, **core_result},
              'note': 'Local archive integrity only; CORE scope differs. No model/device/cloud execution.'}
    (outdir / (stem + '_DOWNLOAD_CHECKS.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    (outdir / (stem + '_SHA256.txt')).write_text(f'{full_result["sha256"]}  {full.name}\n{core_result["sha256"]}  {core.name}\n', 'utf8')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: delivery_gate.py FULL_ZIP OUTDIR')
    try:
        print(json.dumps(run(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}))
        raise SystemExit(1)
