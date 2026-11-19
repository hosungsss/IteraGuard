"""Inert temporary archives only: no product build, model, or dataset reads."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools import build_apk
from tools import build_distribution_v51 as distribution
from tools import build_release_v51 as release
from tools.release_metadata import (V51_CONTRACT_SOURCES, V51_SHARED_ASSETS, distribution_path, required_members,
                                    shared_assets, skill_names, validate_distribution)
from tools.verify_release import copied_web_sources, verify, verify_v51_app_freshness


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_digest(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


class V51PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.root = self.parent / '[v5.1] Fixture'
        self.root.mkdir()
        self.meta = {'version': '5.1', 'version_code': 51, 'version_name': '5.1',
                     'apk': 'apps/dist/IteraGuard_DoubtMeter_v5_1_android_debug.apk',
                     'pwa': 'apps/dist/IteraGuard_DoubtMeter_v5_1_web_pwa.zip',
                     'root_apk': 'IteraGuard_DoubtMeter_v5.1.apk',
                     'release_stage': 'DEVELOPMENT_CANDIDATE', 'device_install': 'NOT_RUN',
                     'independent_evaluation': 'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY',
                     'domain_calibration': 'NOT_ESTABLISHED',
                     'copied_source_sha256': {'index.html': '0'*64},
                     'generated_assets_sha256': {'build-info.js': '0'*64, 'sw.js': '0'*64}}
        for k in ('sha256', 'pwa_sha256', 'root_apk_sha256', 'source_assets_fingerprint',
                  'source_sw_template_sha256', 'desktop_assets_sha256', 'execution_contract_sha256'):
            self.meta[k] = '0'*64
        for rel in required_members('5.1', self.meta):
            self.write(rel, 'fixture\n')
        for name, p in copied_web_sources(self.root, '5.1').items():
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True); p.write_text('inert ' + name)
        names = shared_assets('5.1')
        self.write('apps/web/index.html', ''.join('<script src="'+n+'"></script>' for n in names))
        self.write('apps/web/sw.js', "const CACHE='__BUILD__'; const SHELL=" + json.dumps(list(names)) + ';\n')
        self.selection = {'default_policy_id':'legacy',
                          'default_profile_by_policy':{'legacy':'v50-baseline','dra':'v50-baseline'}}
        self.registry = {'default_policy_id':'legacy', 'default_profile_id':'v50-baseline',
                         'profiles':{'v50-baseline':{'allowed_policy_ids':['legacy','dra']},
                                     'v51-specific-candidate':{'allowed_policy_ids':['legacy']}}}
        self.write('tools/export_v51_contract.py', 'import sys\nassert sys.argv[1:]==["--check"]\n')
        for rel in V51_CONTRACT_SOURCES:
            if not (self.root / rel).exists():self.write(rel,'inert source\n')
        self.freeze_contract()
        self.write('dmsg/SKILL.md', '---\nname: dmsg\n---\n')
        # Existing stamped artifacts/evidence must never be touched by a v5.1 build.
        self.old = {}
        for rel in ('internal/evidence/v50/distribution_build.json', 'dmsg_v5.0.skill',
                    'dmsg_v5.0.zip', 'IteraGuard_DoubtMeter_v5.0.apk',
                    'apps/dist/IteraGuard_DoubtMeter_v5_0_web_pwa.zip',
                    'apps/dist/IteraGuard_DoubtMeter_v5_0_android_debug.apk'):
            data=('historical '+rel).encode();self.write(rel,data);self.old[rel]=data
        self.write('MANIFEST_SHA256.json', '{"version":"5.0","files":{}}')

    def write(self, rel, data):
        p = self.root / rel;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data if isinstance(data,bytes) else data.encode())

    def write_contract(self, contract):
        contract.pop('manifest_fingerprint',None)
        contract['manifest_fingerprint']=object_digest(contract)
        self.write('configs/v51_contract.json',json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
        self.write('apps/shared/v51-contract-data.js','(function(g){g.DMSG_V51_MANIFEST = '+
                   json.dumps(contract,ensure_ascii=False,separators=(',',':'))+
                   ';})(typeof globalThis!=="undefined"?globalThis:this);\n')

    def freeze_contract(self):
        base={'source_hashes':{'integration/v50.py':digest((self.root/'integration/v50.py').read_bytes())}}
        base['manifest_fingerprint']=object_digest(base)
        self.write('configs/v50_contract.json',json.dumps(base))
        reg=dict(self.registry,base_execution_manifest_fingerprint=base['manifest_fingerprint'],
                 source_hashes={name:digest((self.root/name).read_bytes()) for name in
                                ('configs/v50_contract.json','integration/v51_profiles.py')})
        reg['registry_fingerprint']=object_digest(reg)
        self.write('configs/v51_profiles.json',json.dumps(reg))
        self.write('configs/v51_release_selection.json',json.dumps(self.selection))
        contract={'default_policy_id':'legacy', 'release_selection':self.selection,
                  'profiles':self.registry['profiles'], 'profile_registry_fingerprint':reg['registry_fingerprint'],
                  'base_execution_manifest_fingerprint':base['manifest_fingerprint'],
                  'source_hashes':{name:digest((self.root/name).read_bytes()) for name in V51_CONTRACT_SOURCES}}
        self.write_contract(contract)

    def fake_apk(self, out):
        # Read only the synthetic temp web tree; use a binary manifest in memory.
        self.assertEqual(build_apk.debug_key(),('in-memory key',b'in-memory certificate'))
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('AndroidManifest.xml',build_apk.manifest_xml(1,2))
            for p in build_apk.WEB.rglob('*'):
                if p.is_file() and p.name!='sw.js':
                    z.write(p,'assets/www/'+p.relative_to(build_apk.WEB).as_posix())
        return {'apk':out.relative_to(self.root).as_posix(),'sha256':digest(out.read_bytes()),'bytes':out.stat().st_size}

    def build_fixture(self):
        with patch.object(build_apk,'build',side_effect=self.fake_apk), \
             patch.object(build_apk,'_new_debug_key',return_value=('in-memory key',b'in-memory certificate')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.dist=distribution.build(root=self.root)
        return self.dist

    def save_dist(self):
        self.write(distribution_path('5.1'),json.dumps(self.dist))

    def test_v51_build_preserves_old_artifacts_and_sets_actual_android_version(self):
        saved=(build_apk.ROOT,build_apk.WEB,build_apk.KEY_DIR,build_apk.VERSION_CODE,build_apk.VERSION_NAME)
        dist=self.build_fixture()
        self.assertEqual(saved,(build_apk.ROOT,build_apk.WEB,build_apk.KEY_DIR,build_apk.VERSION_CODE,build_apk.VERSION_NAME))
        self.assertEqual(dist['asset_verification']['android_manifest_version'],{'versionCode':51,'versionName':'5.1'})
        self.assertEqual(dist['asset_verification']['status'],'PASS')
        self.assertEqual(dist['independent_evaluation'],'NOT_RUN_AI_DEVELOPMENT_DATA_ONLY')
        for rel,data in self.old.items():self.assertEqual((self.root/rel).read_bytes(),data)

    def test_active_selection_overrides_registry_compatibility_default(self):
        self.selection['default_profile_by_policy']['legacy']='v51-specific-candidate'
        self.freeze_contract();dist=self.build_fixture()
        self.assertEqual(self.registry['default_profile_id'],'v50-baseline')
        self.assertEqual(dist['default_profile_id'],'v51-specific-candidate')
        self.assertEqual(dist['default_policy'],'legacy')
        with zipfile.ZipFile(self.root/dist['pwa']) as z:
            info=json.loads(z.read('dmsg-web/build-info.js').decode().removeprefix('window.DMSG_BUILD = ').strip().removesuffix(';'))
        self.assertEqual(info['default_profile_id'],'v51-specific-candidate')
        self.assertTrue(dist['asset_verification']['v51_checks']['release_selection'])
        dist['default_profile_id']='v50-baseline'
        self.assertFalse(verify_v51_app_freshness(self.root,dist)['v51_checks']['release_selection'])

    def test_selection_requires_allowed_policy_and_matching_contract(self):
        self.selection['default_profile_by_policy']['dra']='v51-specific-candidate'
        self.freeze_contract()
        with self.assertRaisesRegex(ValueError,'PROFILE_POLICY_NOT_ALLOWED:dra'):distribution.preflight(self.root)
        self.selection['default_profile_by_policy']['dra']='v50-baseline';self.freeze_contract()
        c=json.loads((self.root/'configs/v51_contract.json').read_text())
        c['release_selection']['default_profile_by_policy']['legacy']='v51-specific-candidate'
        self.write_contract(c)
        with self.assertRaisesRegex(ValueError,'RELEASE_SELECTION_MISMATCH'):distribution.preflight(self.root)
        self.assertFalse((self.root/'apps/dist/web').exists())

    def test_ephemeral_debug_key_preserves_existing_files_and_restores_function(self):
        names=('apps/mobile/debug-key/debug_key_DO_NOT_USE_FOR_RELEASE.pem',
               'apps/mobile/debug-key/debug_cert.der')
        for name in names:self.write(name,'historical public debug fixture')
        before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*')
                if p.is_file() and p.suffix in ('.pem','.der')}
        original=build_apk.debug_key
        self.build_fixture()
        after={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*')
               if p.is_file() and p.suffix in ('.pem','.der')}
        self.assertEqual(before,after);self.assertIs(build_apk.debug_key,original)

    def test_ephemeral_key_function_restored_after_signing_failure(self):
        original=build_apk.debug_key
        def fail(_):
            self.assertEqual(build_apk.debug_key(),('memory',b'cert'))
            raise RuntimeError('synthetic signing failure')
        with patch.object(build_apk,'_new_debug_key',return_value=('memory',b'cert')), \
             patch.object(build_apk,'build',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'synthetic signing failure'):distribution.build(self.root)
        self.assertIs(build_apk.debug_key,original)
        self.assertFalse(list(self.root.rglob('*.pem')));self.assertFalse(list(self.root.rglob('*.der')))

    def test_every_new_asset_is_required_even_if_v51_config_missing(self):
        (self.root/'configs/v51_contract.json').unlink()
        self.assertTrue(set(V51_SHARED_ASSETS)<=set(copied_web_sources(self.root,'5.1')))
        for name in V51_SHARED_ASSETS:
            p=self.root/'apps/shared'/name;original=p.read_bytes();p.unlink()
            with self.assertRaisesRegex(ValueError,'MISSING_SOURCE_ASSET:'+name):distribution.preflight(self.root)
            p.write_bytes(original)
        self.assertFalse((self.root/'apps/dist/web').exists())

    def test_missing_cache_member_or_contract_check_fails_before_artifact_writes(self):
        p=self.root/'apps/web/sw.js';original=p.read_text();p.write_text(original.replace('v51-semantic.js','missing.js'))
        with self.assertRaisesRegex(ValueError,'SW_MISSING_REQUIRED_ASSETS'):distribution.build(self.root)
        p.write_text(original)
        self.write('tools/export_v51_contract.py','raise SystemExit(1)')
        with self.assertRaisesRegex(ValueError,'EXECUTION_CONTRACT_CHECK_FAILED'):distribution.build(self.root)
        self.assertFalse((self.root/'apps/dist/web').exists())

    def test_release_rejects_stale_sources_before_manifest_or_skills_are_changed(self):
        self.build_fixture();old_manifest=(self.root/'MANIFEST_SHA256.json').read_bytes()
        skill=(self.root/'dmsg.skill').read_bytes()
        self.write('apps/shared/v51-semantic.js','changed source')
        with self.assertRaisesRegex(ValueError,'BUILD_DISTRIBUTION_FIRST'):release.build(self.parent/'delivery',root=self.root)
        self.assertEqual((self.root/'MANIFEST_SHA256.json').read_bytes(),old_manifest)
        self.assertEqual((self.root/'dmsg.skill').read_bytes(),skill)

    def test_nonweb_contract_source_drift_rejected_without_executing_exporter(self):
        self.build_fixture();old_manifest=(self.root/'MANIFEST_SHA256.json').read_bytes()
        skill=(self.root/'dmsg.skill').read_bytes()
        for rel in ('integration/v51_policy.py','configs/v51_semantic_rules.json','integration/v50.py'):
            with self.subTest(source=rel):
                p=self.root/rel;before=p.read_bytes();p.write_bytes(before+b'\nchanged')
                with patch('subprocess.run',side_effect=AssertionError('read-only verifier must not execute source')):
                    r=verify_v51_app_freshness(self.root,self.dist)
                    self.assertEqual(r['status'],'FAIL')
                    self.assertFalse(r['v51_checks']['execution_contract_sources'])
                    self.assertIn('CONTRACT_SOURCE_STALE:'+rel,r['execution_contract_error'])
                    with self.assertRaisesRegex(ValueError,'BUILD_DISTRIBUTION_FIRST'):
                        release.build(self.parent/'delivery',root=self.root)
                self.assertEqual((self.root/'MANIFEST_SHA256.json').read_bytes(),old_manifest)
                self.assertEqual((self.root/'dmsg.skill').read_bytes(),skill)
                p.write_bytes(before)

    def test_rehashed_pwa_with_missing_new_js_fails(self):
        self.build_fixture();p=self.root/self.dist['pwa']
        with zipfile.ZipFile(p) as z:payload={i.filename:z.read(i) for i in z.infolist()}
        del payload['dmsg-web/v51-base-contract.js']
        with zipfile.ZipFile(p,'w') as z:
            for k,v in payload.items():z.writestr(k,v)
        self.dist['pwa_sha256']=digest(p.read_bytes())
        result=verify_v51_app_freshness(self.root,self.dist)
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('v51-base-contract.js',result['missing_assets'])

    def test_actual_android_version_mismatch_fails_despite_refreshed_hashes(self):
        self.build_fixture();p=self.root/self.dist['apk']
        with zipfile.ZipFile(p) as z:payload={i.filename:z.read(i) for i in z.infolist()}
        with patch.object(build_apk,'VERSION_CODE',52),patch.object(build_apk,'VERSION_NAME','5.2'):
            payload['AndroidManifest.xml']=build_apk.manifest_xml(1,2)
        with zipfile.ZipFile(p,'w') as z:
            for k,v in payload.items():z.writestr(k,v)
        (self.root/self.dist['root_apk']).write_bytes(p.read_bytes())
        self.dist['sha256']=self.dist['root_apk_sha256']=digest(p.read_bytes())
        r=verify_v51_app_freshness(self.root,self.dist)
        self.assertFalse(r['v51_checks']['android_version']);self.assertEqual(r['status'],'FAIL')

    def test_source_service_worker_change_cannot_be_blessed_by_hash_only(self):
        self.build_fixture();p=self.root/'apps/web/sw.js';p.write_text(p.read_text()+'// changed\n')
        self.dist['source_sw_template_sha256']=digest(p.read_bytes())
        r=verify_v51_app_freshness(self.root,self.dist)
        self.assertTrue(r['v51_checks']['source_sw_template'])
        self.assertFalse(r['v51_checks']['sw_generation']);self.assertEqual(r['status'],'FAIL')

    def test_complete_release_and_four_skill_aliases_verify_from_outside_tree(self):
        self.build_fixture()
        with contextlib.redirect_stdout(io.StringIO()):archive=release.build(self.parent/'delivery',root=self.root)
        self.assertEqual(archive.name,'IteraGuard_DoubtMeter_v5_1_FULL_CANDIDATE.zip')
        self.assertTrue(verify(archive,root=self.root)['pass'])
        self.assertEqual(len({digest((self.root/n).read_bytes()) for n in skill_names('5.1')}),1)
        for rel,data in self.old.items():self.assertEqual((self.root/rel).read_bytes(),data)
        with self.assertRaisesRegex(ValueError,'OUTPUT_MUST_BE_OUTSIDE_SOURCE_TREE'):
            release.build(self.root/'nested',root=self.root)

    def test_unsupported_performance_or_device_claims_fail_metadata_validation(self):
        for key in ('independent_evaluation','domain_calibration','device_install'):
            d=dict(self.meta);d[key]='PASS'
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_VALIDATION_CLAIM'):validate_distribution(d,'5.1')
        # Existing releases keep their earlier, less specific metadata contract.
        for version in ('4.9','5.0'):
            minimal={'version':version,'apk':'old.apk','pwa':'old.zip','sha256':'0'*64,'pwa_sha256':'0'*64}
            self.assertEqual(validate_distribution(minimal,version),minimal)

    def test_existing_v50_full_release_remains_compatible(self):
        from tests_v49 import test_release_reproducibility as old_tests
        old = old_tests.ReleaseReproducibility()
        old.setUp()
        try:
            old.fixture('5.0')
            self.assertTrue(verify(old.archive(), root=old.root)['pass'])
            self.assertFalse(set(V51_SHARED_ASSETS) & set(copied_web_sources(old.root)))
        finally:
            old.doCleanups()


if __name__=='__main__':unittest.main()
