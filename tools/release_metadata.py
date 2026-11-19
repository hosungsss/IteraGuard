"""Versioned artifact selection and bounded archive checks; no build or network."""
from pathlib import Path, PurePosixPath
import json
import re
import stat

BASE_SHARED_ASSETS = ('engine-data.js', 'dmsg-engine.js', 'dmsg-nlp.js',
                      'linkguard-data.js', 'dmsg-linkguard.js', 'dmsg-apkscan.js',
                      'dmsg-domainintel.js')
V50_SHARED_ASSETS = ('v50-contract-data.js', 'v50-contract.js')
V51_SHARED_ASSETS = ('v51-profile-data.js', 'v51-base-engine.js', 'v51-base-contract.js',
                     'v51-semantic-data.js', 'v51-semantic.js', 'v51-evidence.js',
                     'v51-contract-data.js', 'v51-contract.js')
V51_CONTRACT_SOURCES = (
    'integration/v51.py', 'integration/v51_profiles.py', 'integration/v51_policy.py',
    'integration/v51_evidence.py', 'configs/v51_release_selection.json',
    'configs/v51_semantic_rules.json', 'configs/v51_profiles.json',
    'apps/shared/v51-contract.js', 'apps/shared/v51-base-engine.js',
    'apps/shared/v51-base-contract.js', 'apps/shared/v51-profile-data.js',
    'apps/shared/v51-semantic.js', 'apps/shared/v51-semantic-data.js',
    'apps/shared/v51-evidence.js', 'tools/export_v51_contract.py')


def shared_assets(version):
    """Explicit current-version requirements; missing files never lower the version."""
    return BASE_SHARED_ASSETS + (V50_SHARED_ASSETS if version in ('5.0', '5.1') else ()) + (
        V51_SHARED_ASSETS if version == '5.1' else ())


def relative_path(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/'))
            or ':' in value):
        raise ValueError('UNSAFE_RELATIVE_PATH')
    return PurePosixPath(value).as_posix()


def version_of(meta):
    if not isinstance(meta, dict):
        raise ValueError('INVALID_RELEASE_METADATA')
    version = meta.get('version')
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+', version):
        raise ValueError('INVALID_RELEASE_VERSION')
    return version


def skill_names(version):
    version_of({'version': version})
    return ('dmsg.skill', 'dmsg.zip', f'dmsg_v{version}.skill', f'dmsg_v{version}.zip')


def distribution_path(version):
    version_of({'version': version})
    return f'internal/evidence/v{version.replace(".", "")}/distribution_build.json'


def validate_distribution(meta, version):
    if not isinstance(meta, dict):
        raise ValueError('INVALID_DISTRIBUTION_METADATA')
    if meta.get('version') != version:
        raise ValueError('DISTRIBUTION_VERSION_MISMATCH')
    for key in ('apk', 'pwa'):
        relative_path(meta.get(key))
    for key in ('sha256', 'pwa_sha256'):
        if not isinstance(meta.get(key), str) or not re.fullmatch(r'[a-f0-9]{64}', meta[key]):
            raise ValueError('INVALID_DISTRIBUTION_HASH')
    if version == '5.1':
        expected = {'apk': 'apps/dist/IteraGuard_DoubtMeter_v5_1_android_debug.apk',
                    'pwa': 'apps/dist/IteraGuard_DoubtMeter_v5_1_web_pwa.zip',
                    'root_apk': 'IteraGuard_DoubtMeter_v5.1.apk'}
        if any(meta.get(k) != v for k, v in expected.items()):
            raise ValueError('V51_ARTIFACT_PATH_MISMATCH')
        if type(meta.get('version_code')) is not int or meta['version_code'] != 51 or meta.get('version_name') != '5.1':
            raise ValueError('V51_ANDROID_VERSION_MISMATCH')
        for key in ('root_apk_sha256', 'source_assets_fingerprint', 'source_sw_template_sha256',
                    'desktop_assets_sha256', 'execution_contract_sha256'):
            if not isinstance(meta.get(key), str) or not re.fullmatch(r'[a-f0-9]{64}', meta[key]):
                raise ValueError('INVALID_DISTRIBUTION_HASH:' + key)
        for key in ('copied_source_sha256', 'generated_assets_sha256'):
            if not isinstance(meta.get(key), dict) or not meta[key]:
                raise ValueError('INVALID_ASSET_HASH_MAP:' + key)
            for name, digest in meta[key].items():
                relative_path(name)
                if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
                    raise ValueError('INVALID_ASSET_HASH:' + name)
        if (meta.get('release_stage') != 'DEVELOPMENT_CANDIDATE'
                or meta.get('independent_evaluation') != 'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY'
                or meta.get('domain_calibration') != 'NOT_ESTABLISHED'
                or meta.get('device_install') != 'NOT_RUN'):
            raise ValueError('V51_UNSUPPORTED_VALIDATION_CLAIM')
    return meta


def load_distribution(root):
    root = Path(root)
    version = version_of(json.loads((root / 'MANIFEST_SHA256.json').read_text('utf8')))
    meta = json.loads((root / distribution_path(version)).read_text('utf8'))
    return validate_distribution(meta, version)


def required_members(version, distribution):
    validate_distribution(distribution, version)
    members = {
        'README.md', 'all.md', 'CURRENT_PROJECT_STATE.md', 'CHANGELOG.md',
        'MASTER_HANDOFF_PROMPT.md', 'dmsg/SKILL.md', 'dmsg/prototype/paylock.py',
        'dmsg/prototype/server.py', 'apps/README.md', 'apps/shared/dmsg-engine.js',
        'apps/shared/engine-data.js', 'apps/conformance/vectors.json',
        distribution_path(version), distribution['apk'], distribution['pwa'],
        *skill_names(version),
    }
    if version in ('5.0', '5.1'):
        members |= {'configs/v50_contract.json', 'integration/v50.py',
                    'apps/shared/v50-contract-data.js', 'apps/shared/v50-contract.js',
                    'tools/validate_v50.py', 'tools/build_distribution_v50.py',
                    'tools/build_release_v50.py'}
    if version == '5.1':
        members |= {'configs/v51_contract.json', 'configs/v51_profiles.json',
                    'configs/v51_release_selection.json',
                    'configs/v51_semantic_rules.json', 'integration/v51.py',
                    'integration/v51_profiles.py', 'integration/v51_policy.py',
                    'integration/v51_evidence.py', 'tools/export_v51_contract.py',
                    'tools/build_distribution_v51.py', 'tools/build_release_v51.py',
                    'apps/desktop/assets.gen.js', distribution['root_apk']}
        members |= {'apps/shared/' + name for name in V51_SHARED_ASSETS}
    return members


def archive_issues(z):
    # Include directories too: extractall must never see an unchecked path.
    entries = z.infolist()
    names = [i.filename for i in entries]
    issues = []
    if len(names) != len(set(names)):
        issues.append('DUPLICATE_ARCHIVE_ENTRY')
    if not entries or len(entries) > 1000 or sum(i.file_size for i in entries) > 800_000_000:
        issues.append('BOUNDED_ARCHIVE_POLICY')
    for item in entries:
        try:
            relative_path(item.filename.rstrip('/') if item.is_dir() else item.filename)
        except ValueError:
            issues.append('UNSAFE_ARCHIVE_PATH_OR_LINK')
            break
        if stat.S_ISLNK(item.external_attr >> 16):
            issues.append('UNSAFE_ARCHIVE_PATH_OR_LINK')
            break
        if item.file_size > 80_000_000:
            issues.append('ARCHIVE_OVERSIZED_FILE')
            break
    return issues
