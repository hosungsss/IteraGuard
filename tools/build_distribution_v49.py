"""Build v4.9 PWA/debug APK from updated sources, not relabeled v4.8 binaries."""
from pathlib import Path
import json,hashlib,shutil,zipfile
import build_apps,build_apk
ROOT=Path(__file__).resolve().parents[1]
def build():
    web=ROOT/'apps/dist/web'
    web.mkdir(parents=True,exist_ok=True)
    for rel in build_apps.WEB_FILES:
        dest=web/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'apps/web'/rel,dest)
    for name in ('engine-data.js','dmsg-engine.js','dmsg-nlp.js','linkguard-data.js','dmsg-linkguard.js','dmsg-apkscan.js','dmsg-domainintel.js'):
        shutil.copyfile(ROOT/'apps/shared'/name,web/name)
    shutil.copytree(ROOT/'apps/shared/nlp',web/'nlp',dirs_exist_ok=True,ignore=shutil.ignore_patterns('desktop.ini','__pycache__'))
    info={'version':'4.9','built':'2026-11-04','source':'V49_SOURCE_BUILD',
          'local_zoro':'PC_SEPARATE_GPU_SERVICE','typed_zoro1':'NOT_VALIDATED','android_device':'NOT_RUN'}
    (web/'build-info.js').write_text('window.DMSG_BUILD = '+json.dumps(info)+';\n',encoding='utf8')
    digest=hashlib.sha256()
    for p in sorted(web.rglob('*')):
        if p.is_file() and p.name!='sw.js':digest.update(p.read_bytes())
    p=web/'sw.js';p.write_text(p.read_text(encoding='utf8').replace('__BUILD__',digest.hexdigest()[:12]),encoding='utf8')
    pwa=ROOT/'apps/dist/IteraGuard_DoubtMeter_v4_9_web_pwa.zip'
    build_apps.zip_dir(web,pwa,'dmsg-web')
    apk=ROOT/'apps/dist/IteraGuard_DoubtMeter_v4_9_android_debug.apk'
    result=build_apk.build(apk)
    shutil.copyfile(apk,ROOT/'IteraGuard_DoubtMeter_v4.9.apk')
    result.update(version='4.9',version_code=49,build_type='DEBUG',device_install='NOT_RUN',
                  pwa=pwa.relative_to(ROOT).as_posix(),pwa_sha256=hashlib.sha256(pwa.read_bytes()).hexdigest())
    out=ROOT/'internal/evidence/v49/distribution_build.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))
if __name__=='__main__':build()
