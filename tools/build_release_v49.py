"""Build v4.9 full project and instruction/core skill archives; no upload."""
from pathlib import Path
import hashlib,json,zipfile,sys
ROOT=Path(__file__).resolve().parents[1]
def allowed(p):
    rel=p.relative_to(ROOT)
    return (p.is_file() and not set(rel.parts)&{'__pycache__','node_modules','.git','runs'}
            and p.name not in {'.env','desktop.ini','MANIFEST_SHA256.json'} and p.suffix not in {'.pyc','.db','.sqlite3'}
            and '.sqlite3' not in p.name and not p.name.endswith('.partial')
            and not rel.as_posix().startswith(('apps/dist/web/','apps/dist/desktop/')))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out):
    out.mkdir(parents=True,exist_ok=True)
    for ext in ('skill','zip'):
        path=ROOT/f'dmsg_v4.9.{ext}'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted((ROOT/'dmsg').rglob('*')):
                if allowed(p):z.write(p,'dmsg/'+p.relative_to(ROOT/'dmsg').as_posix())
    for ext in ('skill','zip'):
        (ROOT/f'dmsg.{ext}').write_bytes((ROOT/f'dmsg_v4.9.{ext}').read_bytes())
    files={p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)}
           for p in sorted(ROOT.rglob('*')) if allowed(p)}
    meta={'version':'4.9','release_scope':'LOCAL_PROTOTYPE','typed_model_status':'NOT_VALIDATED',
          'public_zoro_mode':'REAL_ZORO_GENERATION_BASELINE','weights_bundled':False,
          'android_v49_built':(ROOT/'IteraGuard_DoubtMeter_v4.9.apk').is_file(),'files':files}
    (ROOT/'MANIFEST_SHA256.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    target=out/'IteraGuard_DoubtMeter_v4_9_FULL.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for rel in files:z.write(ROOT/rel,ROOT.name+'/'+rel)
        z.write(ROOT/'MANIFEST_SHA256.json',ROOT.name+'/MANIFEST_SHA256.json')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for rel,item in files.items():assert hashlib.sha256(z.read(ROOT.name+'/'+rel)).hexdigest()==item['sha256']
    print(json.dumps({'archive':str(target),'sha256':sha(target),'bytes':target.stat().st_size,'files':len(files)+1}))
    return target
if __name__=='__main__':build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent)
