"""Static notice/inventory checks; not a legal clearance or complete SBOM."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def category(path):
    if path.endswith(('.licensing.md', '/LICENSING.md')) or path == 'internal/VERSION_LEDGER.md':
        return None
    if path.endswith(('.zip', '.skill', '.apk')):
        return 'HISTORICAL_PACKAGE_OR_FIXTURE'
    if path.startswith(('models/', 'apps/shared/nlp/', 'apps/dist/web/nlp/')):
        return 'MODEL_MIXED_TERMS_UNVERIFIED_PROVENANCE'
    if path.startswith('tools/nlp/data/'):
        return 'DATA_MIXED_CC_BY_SA_4_0'
    if path.startswith(('internal/', 'vendor/', 'dmsg/', 'data/', 'tests_data/', 'apps/dist/')):
        return 'HISTORICAL_OR_EXTERNAL_REVIEW_REQUIRED'
    return None

def main():
    errors = []
    required = ['LICENSE', 'NOTICE', 'LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md',
                'models/v46/LICENSING.md', 'apps/shared/nlp/LICENSING.md',
                'apps/dist/web/nlp/LICENSING.md', 'tools/nlp/data/LICENSING.md']
    for name in required:
        if not (ROOT / name).is_file(): errors.append('MISSING ' + name)
    for item in json.loads((ROOT / 'LICENSES/SOURCES.json').read_text(encoding='utf-8'))['files']:
        p = ROOT / item['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            errors.append('LICENSE_TEXT_CHANGED ' + item['path'])
    inventory = json.loads((ROOT / 'docs/licensing/ASSET_INVENTORY.json').read_text(encoding='utf-8'))
    if inventory['complete_rights_audit'] is not False: errors.append('UNSUPPORTED_CLEARANCE_CLAIM')
    rows = inventory['assets']; indexed = {x['path']: x for x in rows}
    if len(indexed) != len(rows): errors.append('DUPLICATE_PATH')
    paths = subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(),
                                    'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    expected = {p for p in paths if category(p)}
    if expected != set(indexed): errors.append('INVENTORY_PATH_MISMATCH ' + repr(sorted(expected ^ set(indexed))))
    for name, item in indexed.items():
        p = ROOT / name
        if item['new_apache_grant'] is not False or item['category'] != category(name): errors.append('SCOPE ' + name)
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']: errors.append('ASSET_CHANGED ' + name)
        if name.endswith(('.zip', '.skill', '.apk')):
            notice = ROOT / (name + '.licensing.md')
            if not notice.is_file() or item['sha256'] not in notice.read_text(encoding='utf-8'): errors.append('PACKAGE_NOTICE ' + name)
    if errors: raise SystemExit('\n'.join(errors))
    print(f'NOTICE_AND_INVENTORY_PASS: {len(rows)} exception files; full rights clearance NOT_ASSERTED')

if __name__ == '__main__':
    main()
