"""Build deterministic v5.2 SOURCE candidate; no provider, Android or NPU test here.

Use from source root: python tools/v52_release.py /mnt/data
"""
from pathlib import Path
from hashlib import sha256
import json,os,sys,zipfile,stat,shutil
ROOT=Path(__file__).resolve().parents[1]
PRODUCT='IteraGuard_DoubtMeter_v5_2_EXPERIMENTAL_SOURCE_CANDIDATE'
BANNED=('Decision_Agent_v3.1_표지포함.pdf','Decision_Agent_v3.1_', 'decision_agents_v3.1')

def path_list():
    return [p for p in ROOT.rglob('*') if p.is_file()
            and not any(x in p.parts for x in ('__pycache__','.git','.pytest_cache'))
            and p.suffix not in ('.pyc','.pyo')
            and not any(x.casefold() in p.name.casefold() for x in BANNED)
            and not (p.name=='MANIFEST_V52_SHA256.json')]

def zwrite(output:Path, files:list[Path], prefix:str, relative_to:Path):
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for p in sorted(files,key=lambda p:p.relative_to(relative_to).as_posix()):
            name=(prefix.rstrip('/')+'/'+p.relative_to(relative_to).as_posix()).lstrip('/')
            if '..' in Path(name).parts or any(x.casefold() in name.casefold() for x in BANNED):raise ValueError('UNSAFE_PATH:'+name)
            info=zipfile.ZipInfo(name,date_time=(2026,11,10,0,0,0));info.create_system=3
            info.external_attr=(0o100644<<16);info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('ZIP_CRC_FAILED')
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('DUPLICATE_PATH')
        if any(any(t.casefold() in name.casefold() for t in BANNED) for name in names):raise ValueError('FORBIDDEN_PDF')
        return len(names),sha256(output.read_bytes()).hexdigest()

def main():
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent
    out.mkdir(parents=True,exist_ok=True)
    # canonical skill zip, and same-byte legacy aliases for v5.2; prior v5.1 archive retained.
    dmsg_root=ROOT/'dmsg'
    skill_files=[p for p in dmsg_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')]
    dmsg_archive=ROOT/'dmsg_v5.2.skill'
    skill_count,skill_hash=zwrite(dmsg_archive,skill_files,'dmsg',dmsg_root)
    for fname in ('dmsg_v5.2.zip','dmsg.skill','dmsg.zip'):
        shutil.copyfile(dmsg_archive,ROOT/fname)
    for fname in ('dmsg_v5.2.skill','dmsg_v5.2.zip'):
        shutil.copyfile(dmsg_archive,out/fname)
    # Own manifest deliberately excludes itself; previous MANIFEST_SHA256 is historical v5.1.
    files=path_list()
    manifest={p.relative_to(ROOT).as_posix():{'size':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()} for p in files}
    new={'schema_version':'iteraguard-v52-source-manifest/1','product':PRODUCT,
         'original_v51_zip_sha256':'b7aa499b2306203710e94bd77a367de922f1ac5e5b44aec112c5d2d39703bbb1',
         'source_pdf_included':False,'dmsg_skill_files':skill_count,'dmsg_skill_sha256':skill_hash,
         'release_status':'EXPERIMENTAL_SOURCE_CANDIDATE','real_zoro1_run_in_upgrade':False,
         'independent_human_evaluation':'NOT_RUN','npu_run':'NOT_RUN','android_rebuild':'NOT_RUN',
         'files':manifest}
    (ROOT/'MANIFEST_V52_SHA256.json').write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    allfiles=files+[ROOT/'MANIFEST_V52_SHA256.json']
    full=out/(PRODUCT+'.zip')
    full_count,full_hash=zwrite(full,allfiles,PRODUCT,ROOT)
    # Source-only alternative: no APK, JS NLP weights, data-vectors or full historical evidence.
    def keep_core(p):
        rel=p.relative_to(ROOT);parts=rel.parts
        if p.suffix.lower()=='.apk':return False
        if parts[0] in ('models','data','evidence','수정기록'):return False
        if parts[0]=='apps':return False
        if len(parts)>1 and parts[:2] in (('internal','evidence'),('internal','history'),('internal','organization')):return False
        if parts[0]=='tests_data' and 'apk_corpus' in parts:return False
        if p.stat().st_size>2_000_000:return False
        if parts[0]=='tests_v49' and p.suffix=='.js':return True
        return True
    codeonly=out/'IteraGuard_DoubtMeter_v5_2_CODE_ONLY.zip'
    codefiles=[p for p in allfiles if keep_core(p)]
    code_count,code_hash=zwrite(codeonly,codefiles,PRODUCT,ROOT)
    result={'release_stage':'EXPERIMENTAL_SOURCE_CANDIDATE','full_zip':full.name,'full_count':full_count,
            'full_bytes':full.stat().st_size,'full_sha256':full_hash,'code_zip':codeonly.name,
            'code_count':code_count,'code_bytes':codeonly.stat().st_size,'code_sha256':code_hash,
            'dmsg_count':skill_count,'dmsg_sha256':skill_hash,'model_evaluation':'AI_SYNTHETIC_EXPLORATORY_NO_IMPROVEMENT_PROVEN',
            'android_device':'NOT_RUN','real_zoro1_in_this_upgrade':'NOT_RUN','npu':'NOT_RUN',
            'code_only_is_full_runnable_product':False,
            'forbidden_pdf_included':False,'manifest_entries':len(manifest)}
    (out/'IteraGuard_v5_2_DISTRIBUTION_RECEIPT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':main()
