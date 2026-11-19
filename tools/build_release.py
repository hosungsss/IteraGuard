"""Create skill archives, deterministic manifest and complete release ZIP.

Run from project root: python tools/build_release.py /mnt/data
This only creates local files. It performs NO Google Drive or remote writes.
"""
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='4.8'

def digest(data):return hashlib.sha256(data).hexdigest()

# Build intermediates that must never ship: raw (uncompressed) desktop runtimes, npm trees,
# Capacitor outputs regenerated from apps/mobile, and generated embed modules. Only the
# compressed bundles in apps/dist/*.zip are released (v4.6: apps/dist/web is the same bytes as the PWA zip and is
# rebuilt by tools/build_apps.py, so it is not shipped twice; FULL must stay under the 400 MiB delivery limit).
RELEASE_EXCLUDE_PREFIXES=('apps/dist/desktop/','apps/dist/web/','apps/dist/_','apps/mobile/node_modules/','apps/mobile/android/',
                          'apps/mobile/ios/','apps/mobile/www/','apps/desktop/assets.gen.js')

def files_in_tree(base,exclude=()):
    def shipped(p):
        rel=p.relative_to(base).as_posix()
        return not (base==ROOT and rel.startswith(RELEASE_EXCLUDE_PREFIXES))
    return sorted([p for p in base.rglob('*') if p.is_file() and not (set(p.parts)&{'__pycache__','.pytest_cache','node_modules'})
                   and p.suffix not in ('.pyc','.pyo') and p not in exclude and shipped(p)],key=lambda p:p.relative_to(base).as_posix())

def add(z,archive_name,data):
    zi=zipfile.ZipInfo(archive_name,date_time=(2026,11,1,0,0,0))
    zi.compress_type=zipfile.ZIP_DEFLATED
    zi.external_attr=(0o100644<<16)
    z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def build(outdir):
    outdir.mkdir(exist_ok=True,parents=True)
    skill=ROOT/'dmsg'
    for name in ('dmsg.skill','dmsg.zip',f'dmsg_v{VERSION}.skill',f'dmsg_v{VERSION}.zip'):
        with zipfile.ZipFile(ROOT/name,'w') as z:
            for p in files_in_tree(skill):add(z,'dmsg/'+p.relative_to(skill).as_posix(),p.read_bytes())
    assert (ROOT/'dmsg.skill').read_bytes()==(ROOT/'dmsg.zip').read_bytes()==(ROOT/f'dmsg_v{VERSION}.skill').read_bytes()==(ROOT/f'dmsg_v{VERSION}.zip').read_bytes()
    manifests={}
    for p in files_in_tree(ROOT,exclude={ROOT/'MANIFEST_SHA256.json'}):
        data=p.read_bytes()
        manifests[p.relative_to(ROOT).as_posix()]={'sha256':digest(data),'bytes':len(data)}
    (ROOT/'MANIFEST_SHA256.json').write_text(json.dumps({'version':VERSION,'files':manifests},ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf8')
    # Download-safe ASCII basename; never percent-encode spaces into filesystem names.
    zip_path=outdir/(f'IteraGuard_DoubtMeter_v{VERSION.replace(chr(46), chr(95))}_FULL.zip')
    with zipfile.ZipFile(zip_path,'w') as z:
        for p in files_in_tree(ROOT):add(z,ROOT.name+'/'+p.relative_to(ROOT).as_posix(),p.read_bytes())
    with zipfile.ZipFile(zip_path) as z:
        assert z.testzip() is None
    return zip_path

if __name__=='__main__':
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent
    zp=build(out)
    print(json.dumps({'zip':str(zp),'sha256':digest(zp.read_bytes()),'bytes':zp.stat().st_size},ensure_ascii=False,indent=2))
