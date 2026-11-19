"""Package v5.1 only. Preserve older artifacts; refuse output inside the source tree."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

if __package__:
    from .release_metadata import archive_issues, required_members, skill_names, validate_distribution
    from .verify_release import content_files, verify_v51_app_freshness, verify
else:
    from release_metadata import archive_issues, required_members, skill_names, validate_distribution
    from verify_release import content_files, verify_v51_app_freshness, verify

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out, *, root=ROOT):
    root, out = Path(root).resolve(), Path(out).resolve()
    if out == root or out.is_relative_to(root):
        raise ValueError('OUTPUT_MUST_BE_OUTSIDE_SOURCE_TREE')
    dist = validate_distribution(json.loads((root / 'internal/evidence/v51/distribution_build.json').read_text('utf8')), '5.1')
    if verify_v51_app_freshness(root, dist)['status'] != 'PASS':
        raise ValueError('BUILD_DISTRIBUTION_FIRST_SOURCE_OR_ASSETS_STALE')
    for name in required_members('5.1', dist) - set(skill_names('5.1')):
        if not (root / name).is_file():
            raise ValueError('MISSING_REQUIRED_MEMBER:' + name)
    for p in content_files(root):
        if p.is_symlink() or not p.resolve().is_relative_to(root):
            raise ValueError('RELEASE_SOURCE_LINK_OUTSIDE_TREE')
    skill = root / 'dmsg_v5.1.skill'
    with zipfile.ZipFile(skill, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in content_files(root / 'dmsg'):
            z.write(path, 'dmsg/' + path.relative_to(root / 'dmsg').as_posix())
    for name in ('dmsg_v5.1.zip', 'dmsg.skill', 'dmsg.zip'):
        (root / name).write_bytes(skill.read_bytes())
    files = {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in content_files(root) if p.name != 'MANIFEST_SHA256.json'}
    manifest = {'version': '5.1', 'release_scope': 'DEVELOPMENT_CANDIDATE',
                'typed_model_status': 'LOCAL_RUNTIME_EVIDENCE_SEPARATE_NOT_ATTESTED',
                'independent_evaluation': 'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY',
                'domain_calibration': 'NOT_ESTABLISHED', 'android_device': 'NOT_RUN',
                'zoro_weights_bundled': False, 'existing_on_device_nlp_assets_bundled': True,
                'source_baseline': 'verified v5.0 organized development candidate, 2026-11-04',
                'distribution_evidence': 'internal/evidence/v51/distribution_build.json', 'files': files}
    (root / 'MANIFEST_SHA256.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf8')
    local = verify(root=root)
    if not local['pass']:
        raise ValueError('SOURCE_RELEASE_VERIFICATION_FAILED:' + ','.join(local['issues']))
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'IteraGuard_DoubtMeter_v5_1_FULL_CANDIDATE.zip'
    partial = out / (target.name + '.partial')
    try:
        with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for rel in [*files, 'MANIFEST_SHA256.json']:
                z.write(root / rel, root.name + '/' + rel)
        with zipfile.ZipFile(partial) as z:
            issues = archive_issues(z)
            if issues:
                raise ValueError('UNSAFE_FULL_ARCHIVE:' + ','.join(issues))
        result = verify(partial, root=root)
        if not result['pass']:
            raise ValueError('FULL_RELEASE_VERIFICATION_FAILED:' + ','.join(result['issues']))
        partial.replace(target)
    finally:
        if partial.exists():
            partial.unlink()
    print(json.dumps({'archive': str(target), 'sha256': sha(target), 'bytes': target.stat().st_size,
                      'file_count': len(files) + 1, 'release_stage': 'DEVELOPMENT_CANDIDATE',
                      'independent_evaluation': manifest['independent_evaluation'], 'android_device': 'NOT_RUN'}))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    build(parser.parse_args().out)
