"""Independent read-only v5.1 APK inspection. Tamper only an external scratch copy."""
from pathlib import Path
import datetime, hashlib, importlib.metadata, json, os, struct, subprocess, sys, zipfile

W=Path(sys.argv[1]).resolve()
O=Path(__file__).resolve().parent
sys.path.insert(0,str(W))
from tools.release_metadata import archive_issues
from tools.verify_apk import dex_rules
from tools.verify_release import verify_v51_app_freshness
from loguru import logger
logger.remove()
from androguard.core.apk import APK
from androguard.core.dex import DEX
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization

sha=lambda x:hashlib.sha256(x).hexdigest()
dist=json.loads((W/'internal/evidence/v51/distribution_build.json').read_text())
apk=W/dist['apk'];raw=apk.read_bytes();before=sha(raw)
assert before==dist['sha256']==sha((W/dist['root_apk']).read_bytes())
with zipfile.ZipFile(apk) as z:
    assert not archive_issues(z) and z.testzip() is None
    dex=z.read('classes.dex');i=z.getinfo('classes.dex')
    n,e=struct.unpack_from('<HH',raw,i.header_offset+26)
    # Changes authenticated ZIP entry data, preserving the APK signing block.
    tamper_offset=i.header_offset+30+n+e+16
    assert tamper_offset < i.header_offset+30+n+e+i.compress_size
    misaligned=[]
    for item in z.infolist():
        if item.compress_type==0:
            n,e=struct.unpack_from('<HH',raw,item.header_offset+26)
            if (item.header_offset+30+n+e)%4:misaligned.append(item.filename)

def signature(path,label):
    args=[sys.executable,'-m','apksigtool','verify',str(path)]
    p=subprocess.run(args,capture_output=True,text=True,timeout=60,
                     env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    log=O/(label+'.log');log.write_text(p.stdout+p.stderr)
    return {'command':args,'exit_code':p.returncode,'v2_verified':p.returncode==0 and 'v2 verified' in p.stdout,
            'log':str(log),'log_sha256':sha(log.read_bytes())}

sig=signature(apk,'signature_original')
damaged=bytearray(raw);damaged[tamper_offset]^=1
tamper=O/'tampered_copy_DO_NOT_INSTALL.apk';tamper.write_bytes(damaged)
bad=signature(tamper,'signature_tampered')
x=APK(str(apk));m=x.get_android_manifest_xml();NS='{http://schemas.android.com/apk/res/android}'
manifest={'package':x.get_package(),'version_code':x.get_androidversion_code(),
          'version_name':x.get_androidversion_name(),'min_sdk':x.get_min_sdk_version(),
          'target_sdk':x.get_target_sdk_version(),'permissions':x.get_permissions(),
          'label':x.get_app_name(),'main_activity':x.get_main_activity(),
          'debuggable':m.find('application').get(NS+'debuggable')}
certificates=[]
for der in x.get_certificates_der_v2():
    c=x509.load_der_x509_certificate(der)
    public=c.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    certificates.append({'certificate_sha256':c.fingerprint(hashes.SHA256()).hex(),
                         'subject':c.subject.rfc4514_string(),'issuer':c.issuer.rfc4514_string(),
                         'public_key_spki_sha256':sha(public),'serial_number':str(c.serial_number),
                         'not_before':c.not_valid_before_utc.isoformat(),'not_after':c.not_valid_after_utc.isoformat(),
                         'identity_scope':'DEBUG_CERTIFICATE_NOT_EXTERNAL_IDENTITY_ATTESTATION'})
d=dex_rules(dex);parsed=DEX(dex)
d['androguard_methods']=sorted(method.get_name() for cls in parsed.get_classes() for method in cls.get_methods())
freshness=verify_v51_app_freshness(W,dist)
checks={'signature_v2':sig['v2_verified'],
        'tampered_copy_rejected':not bad['v2_verified'] and bad['exit_code']!=0,
        'one_v2_certificate':len(certificates)==1,
        'manifest_version':manifest['version_code']=='51' and manifest['version_name']=='5.1',
        'manifest_sdk':manifest['min_sdk']=='24' and manifest['target_sdk']=='34',
        'manifest_permissions_empty':manifest['permissions']==[],
        'manifest_package_activity':manifest['package']=='kr.iteraguard.doubtmeter' and manifest['main_activity']=='kr.iteraguard.doubtmeter.MainActivity',
        'debug_flag_declared':manifest['debuggable']=='true',
        'dex_structure':all(d['rules'].values()),'stored_entries_aligned':not misaligned,
        'source_pwa_apk_desktop_freshness':freshness['status']=='PASS',
        'original_apk_unchanged':sha(apk.read_bytes())==before,
        'root_apk_matches':sha((W/dist['root_apk']).read_bytes())==before}
result={'status':'STRUCTURE_SIGNATURE_AND_TAMPER_PASS_DEVICE_NOT_RUN' if all(checks.values()) else 'FAIL',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'apk':str(apk),'sha256':before,'bytes':len(raw),'checks':checks,'signature':sig,
        'tamper_test':{'scratch_copy':str(tamper),'sha256':sha(damaged),'changed_byte_offset':tamper_offset,
                       'changed_entry':'classes.dex','signature_result':bad,'original_file_modified':False},
        'certificates':certificates,'manifest':manifest,'dex':d,'asset_verification':freshness,
        'tool_versions':{n:importlib.metadata.version(n) for n in ('apksigtool','androguard','cryptography')},
        'device_install_and_run':'NOT_RUN','new_signing_keys_created':False,'signing_key_read_or_used':False,
        'model_calls':0,'validation24_accessed':False,
        'limitations':['Static parsing, signature/content integrity, and packaged asset correspondence only.',
                      'No Android installation, launch, runtime behavior, upgrade-signature compatibility or independent model-quality claim.']}
out=O/'apk_independent_verification.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','sha256','checks','manifest','device_install_and_run')},ensure_ascii=False))
raise SystemExit(0 if all(checks.values()) else 1)
