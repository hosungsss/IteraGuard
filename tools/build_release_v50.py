"""Package a verified-source v5 candidate; independent evaluation and device status stay explicit."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

from verify_release import content_files

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out):
    out = Path(out).resolve()
    if out == ROOT or out.is_relative_to(ROOT):
        raise ValueError('OUTPUT_MUST_BE_OUTSIDE_SOURCE_TREE')
    out.mkdir(parents=True, exist_ok=True)
    dist = json.loads((ROOT / 'internal/evidence/v50/distribution_build.json').read_text())
    if dist['version'] != '5.0':
        raise ValueError('BUILD_DISTRIBUTION_FIRST')
    skill = ROOT / 'dmsg_v5.0.skill'
    with zipfile.ZipFile(skill, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in content_files(ROOT / 'dmsg'):
            z.write(path, 'dmsg/' + path.relative_to(ROOT / 'dmsg').as_posix())
    for name in ('dmsg_v5.0.zip', 'dmsg.skill', 'dmsg.zip'):
        (ROOT / name).write_bytes(skill.read_bytes())
    files = {p.relative_to(ROOT).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in content_files(ROOT) if p.name != 'MANIFEST_SHA256.json'}
    manifest = {'version': '5.0', 'release_scope': 'DEVELOPMENT_CANDIDATE',
                'typed_model_status': 'LOCAL_RUNTIME_EVIDENCE_SEPARATE_NOT_ATTESTED',
                'independent_evaluation': 'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY',
                'android_device': 'NOT_RUN', 'weights_bundled': False,
                'source_baseline': 'verified v4.9 iteration, 2026-11-04', 'files': files}
    (ROOT / 'MANIFEST_SHA256.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    target = out / 'IteraGuard_DoubtMeter_v5_0_FULL_CANDIDATE.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel in [*files, 'MANIFEST_SHA256.json']:
            z.write(ROOT / rel, ROOT.name + '/' + rel)
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP_CRC_FAIL')
        for rel, item in files.items():
            if hashlib.sha256(z.read(ROOT.name + '/' + rel)).hexdigest() != item['sha256']:
                raise ValueError('ZIP_CONTENT_MISMATCH:' + rel)
    print(json.dumps({'archive': str(target), 'sha256': sha(target), 'bytes': target.stat().st_size,
                      'file_count': len(files) + 1, 'release_stage': manifest['release_scope']}))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    build(parser.parse_args().out)
