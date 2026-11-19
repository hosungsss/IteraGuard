"""Offline release-boundary regression. Fixtures are inert, not installable APKs."""
import hashlib
import json
import tempfile
import subprocess
import sys
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.delivery_gate import checked_members, make_core
from tools.release_metadata import archive_issues, distribution_path, required_members, skill_names
from tools.verify_apk import compare_packaged_assets
from tools.verify_release import copied_web_sources, verify


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReleaseReproducibility(unittest.TestCase):
    def test_imports_preserve_product_linkguard_and_cli_entrypoints(self):
        root = Path(__file__).resolve().parents[1]
        code = ('import sys; before=list(sys.path); '
                'import tools.verify_release,tools.delivery_gate,tools.verify_apk; '
                'assert sys.path==before; from linkguard.intake import intake; '
                'from pathlib import Path; import linkguard; '
                'assert Path(linkguard.__file__).resolve()==Path("linkguard/__init__.py").resolve()')
        subprocess.run([sys.executable, '-c', code], cwd=root, check=True, capture_output=True)
        for prefix in ([sys.executable, 'tools/verify_release.py'], [sys.executable, '-m', 'tools.verify_release'],
                       [sys.executable, 'tools/verify_apk.py'], [sys.executable, '-m', 'tools.verify_apk']):
            with self.subTest(command=prefix):
                subprocess.run([*prefix, '--help'], cwd=root, check=True, capture_output=True)
        for prefix in ([sys.executable, 'tools/delivery_gate.py'], [sys.executable, '-m', 'tools.delivery_gate']):
            result = subprocess.run(prefix, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Usage: delivery_gate.py FULL_ZIP OUTDIR', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.root = self.parent / 'release-source'
        self.root.mkdir()

    def fixture(self, version='4.9'):
        stem = version.replace('.', '_')
        self.dist = {'version': version, 'apk': f'apps/dist/build_{stem}.apk',
                     'pwa': f'apps/dist/web_{stem}.zip', 'sha256': '0' * 64, 'pwa_sha256': '0' * 64}
        for name in required_members(version, self.dist):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('synthetic release fixture\n')
        (self.root / 'dmsg/SKILL.md').write_text('---\nname: dmsg\n---\n')
        payload = {'build-info.js': b'window.DMSG_BUILD={};'}
        for name, p in copied_web_sources(self.root).items():
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.is_file(): p.write_text('synthetic copied asset: ' + name)
            payload[name] = p.read_bytes()
        with zipfile.ZipFile(self.root / self.dist['pwa'], 'w') as z:
            for name, data in payload.items(): z.writestr('dmsg-web/' + name, data)
            z.writestr('dmsg-web/sw.js', b'/* synthetic */')
        with zipfile.ZipFile(self.root / self.dist['apk'], 'w') as z:
            for name, data in payload.items(): z.writestr('assets/www/' + name, data)
        self.dist['sha256'] = digest((self.root / self.dist['apk']).read_bytes())
        self.dist['pwa_sha256'] = digest((self.root / self.dist['pwa']).read_bytes())
        (self.root / distribution_path(version)).write_text(json.dumps(self.dist))
        skill = self.root / skill_names(version)[0]
        with zipfile.ZipFile(skill, 'w') as z:
            for p in sorted((self.root / 'dmsg').rglob('*')):
                if p.is_file(): z.write(p, 'dmsg/' + p.relative_to(self.root / 'dmsg').as_posix())
        for name in skill_names(version)[1:]: (self.root / name).write_bytes(skill.read_bytes())
        self.version = version
        self.freeze()

    def freeze(self):
        files = {p.relative_to(self.root).as_posix(): {'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())}
                 for p in self.root.rglob('*') if p.is_file() and p.name != 'MANIFEST_SHA256.json'}
        (self.root / 'MANIFEST_SHA256.json').write_text(json.dumps({'version': self.version, 'files': files}))

    def archive(self, name='FULL.zip', override=None):
        p = self.parent / name
        with zipfile.ZipFile(p, 'w') as z:
            for f in sorted(self.root.rglob('*')):
                if f.is_file():
                    rel = f.relative_to(self.root).as_posix()
                    z.writestr('portable-folder/' + rel, (override or {}).get(rel, f.read_bytes()))
        return p

    def test_current_tree_and_archive_verify_without_v47_artifacts(self):
        self.fixture()
        self.assertTrue(verify(root=self.root)['pass'])
        self.assertTrue(verify(self.archive(), root=self.root)['pass'])

    def test_version_and_artifact_names_come_from_metadata(self):
        self.fixture('5.2')  # Synthetic future metadata, not a product version change.
        archive = self.archive()
        self.assertEqual(checked_members(archive, require_manifest=True)['version'], '5.2')
        core = make_core(archive, self.parent)
        self.assertEqual(core.name, 'IteraGuard_DoubtMeter_v5_2_CORE.zip')
        self.assertEqual(checked_members(core, require_manifest=False)['version'], '5.2')

    def test_missing_current_skill_is_reported_not_crash_or_skip(self):
        self.fixture()
        (self.root / 'dmsg_v4.9.skill').unlink()
        result = verify(root=self.root)
        self.assertFalse(result['pass'])
        self.assertIn('MISSING dmsg_v4.9.skill', result['issues'])

    def test_stale_source_manifest_and_skill_fail(self):
        self.fixture()
        (self.root / 'dmsg/prototype/server.py').write_text('changed source')
        result = verify(root=self.root)
        self.assertFalse(result['pass'])
        self.assertIn('HASH_MISMATCH dmsg/prototype/server.py', result['issues'])
        self.assertIn('SKILL_SOURCE_MISMATCH dmsg.skill', result['issues'])

    def test_skill_archive_bounds_skip_crc_and_member_reads(self):
        self.fixture()
        original_info, original_read, original_crc = zipfile.ZipFile.infolist, zipfile.ZipFile.read, zipfile.ZipFile.testzip
        is_skill = lambda z: Path(z.filename).name in skill_names(self.version)
        for label, count, size in [('member_size', 1, 80_000_001),
                                   ('total_size', 11, 80_000_000), ('entry_count', 1001, 0)]:
            with self.subTest(bound=label):
                entries = [zipfile.ZipInfo('dmsg/item' + str(i)) for i in range(count)]
                for entry in entries: entry.file_size = size
                skill_reads, skill_crc = [], []
                def read(z, *args, **kwargs):
                    if is_skill(z):
                        skill_reads.append(z.filename)
                        raise AssertionError('Rejected skill member must not be decompressed')
                    return original_read(z, *args, **kwargs)
                def crc(z):
                    if is_skill(z):
                        skill_crc.append(z.filename)
                        raise AssertionError('Rejected skill must not run CRC decompression')
                    return original_crc(z)
                with patch.object(zipfile.ZipFile, 'infolist', autospec=True,
                                  side_effect=lambda z: entries if is_skill(z) else original_info(z)), \
                     patch.object(zipfile.ZipFile, 'read', autospec=True, side_effect=read), \
                     patch.object(zipfile.ZipFile, 'testzip', autospec=True, side_effect=crc):
                    result = verify(root=self.root)
                self.assertFalse(result['pass'])
                self.assertEqual(sum(x.startswith('BAD_SKILL_ARCHIVE ') for x in result['issues']), 4)
                self.assertEqual(skill_reads, [])
                self.assertEqual(skill_crc, [])

    def test_skill_archive_crc_failure_skips_member_hash_reads(self):
        self.fixture()
        original_read, original_crc = zipfile.ZipFile.read, zipfile.ZipFile.testzip
        is_skill = lambda z: Path(z.filename).name in skill_names(self.version)
        reads, crc_calls = [], []
        def read(z, *args, **kwargs):
            if is_skill(z):
                reads.append(z.filename)
                raise AssertionError('CRC-failed skill must not be read for hashing')
            return original_read(z, *args, **kwargs)
        def crc(z):
            if is_skill(z):
                crc_calls.append(z.filename)
                return 'dmsg/SKILL.md'
            return original_crc(z)
        with patch.object(zipfile.ZipFile, 'read', autospec=True, side_effect=read), \
             patch.object(zipfile.ZipFile, 'testzip', autospec=True, side_effect=crc):
            result = verify(root=self.root)
        self.assertFalse(result['pass'])
        self.assertEqual(sum(x.startswith('BAD_SKILL_ARCHIVE ') for x in result['issues']), 4)
        self.assertEqual(len(crc_calls), 4)
        self.assertEqual(reads, [])

    def test_new_manifest_cannot_bless_stale_app_assets(self):
        self.fixture()
        (self.root / 'apps/web/app.js').write_text('new source without rebuilding apps')
        self.freeze()
        result = verify(root=self.root)
        self.assertFalse(result['pass'])
        self.assertIn('SOURCE_TO_APP_ASSETS_MISMATCH', result['issues'])
        self.assertFalse(any(x.startswith('HASH_MISMATCH ') for x in result['issues']))
        self.assertEqual(result['source_to_app_freshness']['changed_assets'], ['app.js'])

    def test_new_artifact_hash_cannot_bless_apk_pwa_drift(self):
        self.fixture()
        apk = self.root / self.dist['apk']
        with zipfile.ZipFile(apk) as z:
            payload = {i.filename: z.read(i) for i in z.infolist()}
        payload['assets/www/index.html'] = b'APK differs from current source and PWA'
        with zipfile.ZipFile(apk, 'w') as z:
            for name, data in payload.items(): z.writestr(name, data)
        self.dist['sha256'] = digest(apk.read_bytes())
        (self.root / distribution_path(self.version)).write_text(json.dumps(self.dist))
        self.freeze()
        result = verify(root=self.root)
        self.assertFalse(result['pass'])
        self.assertIn('SOURCE_TO_APP_ASSETS_MISMATCH', result['issues'])
        self.assertEqual(result['source_to_app_freshness']['changed_assets'], [])
        self.assertEqual(result['source_to_app_freshness']['apk_pwa_equivalence']['changed_assets'], ['index.html'])

    def test_same_member_set_different_archive_bytes_fail(self):
        self.fixture()
        archive = self.archive(override={'README.md': b'different archive content'})
        self.assertIn('ZIP_CONTENT_MISMATCH README.md', verify(archive, root=self.root)['issues'])
        with self.assertRaisesRegex(ValueError, 'MANIFEST_HASH_MISMATCH'):
            checked_members(archive, require_manifest=True)

    def test_core_preserves_regression_prerequisites(self):
        self.fixture()
        for rel in ['tests_linkguard/test_linkguard.py', 'internal/evidence/v47/BASELINE_V46.json',
                    'tests_data/release/skill_path_additions.json']:
            p = self.root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{}')
        self.freeze()
        archive = self.archive()
        core = make_core(archive, self.parent)
        self.assertEqual(checked_members(core, require_manifest=False)['crc'], 'PASS')
        with zipfile.ZipFile(core) as z:
            self.assertIn('portable-folder/internal/evidence/v47/BASELINE_V46.json', z.namelist())

    def test_missing_regression_prerequisite_rejected(self):
        self.fixture()
        p = self.root / 'tests_linkguard/test_linkguard.py'
        p.parent.mkdir(); p.write_text('synthetic')
        self.freeze()
        with self.assertRaisesRegex(ValueError, 'MISSING_REQUIRED_MEMBERS'):
            checked_members(self.archive(), require_manifest=True)

    def test_apk_assets_use_packaged_pwa_without_staging(self):
        self.fixture()
        self.assertFalse((self.root / 'apps/dist/web').exists())
        result = compare_packaged_assets(self.root / self.dist['apk'], root=self.root)
        self.assertEqual(result['status'], 'PASS_ASSETS_ONLY')
        self.assertEqual(result['signature_validation'], 'NOT_RUN_IN_ASSETS_ONLY_MODE')

    def test_apk_asset_drift_detected(self):
        self.fixture()
        apk = self.root / self.dist['apk']
        with zipfile.ZipFile(apk, 'w') as z:
            z.writestr('assets/www/index.html', b'changed')
            z.writestr('assets/www/build-info.js', b'window.DMSG_BUILD={};')
        result = compare_packaged_assets(apk, root=self.root)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['changed_assets'], ['index.html'])

    def test_unsafe_directory_and_duplicate_names_rejected(self):
        for bad in ['../escape/', '/absolute/', 'C:/escape/']:
            p = self.parent / 'BAD.zip'
            with zipfile.ZipFile(p, 'w') as z: z.writestr(bad, b'')
            with zipfile.ZipFile(p) as z: self.assertIn('UNSAFE_ARCHIVE_PATH_OR_LINK', archive_issues(z))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('same', b'a'); z.writestr('same', b'b')
        with zipfile.ZipFile(p) as z: self.assertIn('DUPLICATE_ARCHIVE_ENTRY', archive_issues(z))

    def test_malformed_manifest_reports_failure(self):
        self.fixture()
        (self.root / 'MANIFEST_SHA256.json').write_text('[]')
        result = verify(root=self.root)
        self.assertFalse(result['pass'])
        self.assertTrue(any('INVALID_RELEASE_METADATA' in x for x in result['issues']))

    def test_distribution_path_cannot_escape_release_root(self):
        self.fixture()
        self.dist['apk'] = '../outside.apk'
        (self.root / distribution_path(self.version)).write_text(json.dumps(self.dist))
        result = verify(root=self.root)
        self.assertFalse(result['pass'])
        self.assertTrue(any('UNSAFE_RELATIVE_PATH' in x for x in result['issues']))


if __name__ == '__main__':
    unittest.main()
