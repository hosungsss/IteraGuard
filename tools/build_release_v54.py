"""Package current reviewed sources; does not assert live inference or upload."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(root):
 return sorted(p for p in root.rglob('*') if p.is_file() and not any(x in p.relative_to(root).parts for x in ('__pycache__','.git','.venv','node_modules')) and p.suffix not in ('.pyc','.pyo') and p.name!='.env')
def main():
 for script in ('export_v51_semantic.py','export_v51_contract.py'):
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools'/script),'--check'],cwd=ROOT,check=True)
 skill=ROOT/'dmsg_v5.4.skill'
 with zipfile.ZipFile(skill,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files(ROOT/'dmsg'):z.write(p,'dmsg/'+p.relative_to(ROOT/'dmsg').as_posix())
 for name in ('dmsg_v5.4.zip','dmsg.skill','dmsg.zip'):(ROOT/name).write_bytes(skill.read_bytes())
 manifest=ROOT/'MANIFEST_V54_SHA256.json'
 inventory={p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files(ROOT) if p!=manifest}
 manifest.write_text(json.dumps({'package_version':'5.4','contract_version':'5.1','files':inventory},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 archive=ROOT.parent/'[v5.4] IteraGuard_DoubtMeter.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files(ROOT):z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  prefix=ROOT.name+'/'
  assert len(z.namelist())==len(inventory)+1
  for name,record in inventory.items():
   data=z.read(prefix+name)
   assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'],name
  assert z.read(prefix+'dmsg.skill')==z.read(prefix+'dmsg.zip')==z.read(prefix+'dmsg_v5.4.skill')
 result={'archive':archive.name,'package_version':'5.4','bytes':archive.stat().st_size,'sha256':sha(archive),'verified_files':len(inventory)+1,'zip_crc':'PASS','sha256_all_files':'PASS','skill_aliases':'IDENTICAL','actual_model_calls':0,'drive_upload':'NOT_REQUESTED_NOT_DONE'}
 (ROOT.parent/'v54_package_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT.parent/'SHA256SUMS.txt').write_text(result['sha256']+'  '+archive.name+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
