"""Generate the v5.1 execution manifest and matching JS metadata; never promotes a candidate."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration import v50,v51_profiles as P

def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def build():
 base=v50.execution_manifest();reg=P.registry();sel=json.loads((ROOT/'configs/v51_release_selection.json').read_text());rules=json.loads((ROOT/'configs/v51_semantic_rules.json').read_text())
 for policy,ident in sel['default_profile_by_policy'].items():P.profile(ident,policy)
 files=['integration/v51.py','integration/v51_profiles.py','integration/v51_policy.py','integration/v51_evidence.py',
        'configs/v51_release_selection.json','configs/v51_semantic_rules.json','configs/v51_profiles.json',
        'apps/shared/v51-contract.js','apps/shared/v51-base-engine.js','apps/shared/v51-base-contract.js','apps/shared/v51-profile-data.js','apps/shared/v51-semantic.js','apps/shared/v51-semantic-data.js','apps/shared/v51-evidence.js',
        'tools/export_v51_contract.py']
 p=P.profile(sel['default_profile_by_policy']['legacy'],'legacy')
 m={'schema_version':'dmsg-v51-execution-manifest/1','trace_schema_version':'dmsg-v51-execution-trace/1','product_version':sel['product_version'],
    'release_status':sel['release_stage'],'manifest_scope':'ALLOWED_PROFILE_REGISTRY_AND_EXECUTION_SOURCES; CURRENT_REQUEST_BOUND_SEPARATELY',
    'default_policy_id':'legacy','question_signature':p['question_signature'],'question_contract_sha256':p['question_contract_sha256'],
    'base_execution_manifest_fingerprint':base['manifest_fingerprint'],'profile_registry_fingerprint':reg['registry_fingerprint'],
    'profiles':{k:{n:v[n] for n in ['allowed_policy_ids','question_contract_sha256','profile_fingerprint','required_questions','optional_questions']} for k,v in reg['profiles'].items()},
    'release_selection':sel,'semantic_policy_id':rules['version'],'runtime':base['runtime'],'privacy':base['privacy'],
    'team_decisions':base['team_decisions'],'source_hashes':{n:h(ROOT/n) for n in files}}
 m['manifest_fingerprint']=digest(m);return m

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');a=ap.parse_args();m=build()
 contents={ROOT/'configs/v51_contract.json':json.dumps(m,ensure_ascii=False,indent=2)+'\n',ROOT/'apps/shared/v51-contract-data.js':'(function(g){g.DMSG_V51_MANIFEST = '+json.dumps(m,ensure_ascii=False,separators=(',',':'))+';})(typeof globalThis!=="undefined"?globalThis:this);\n'}
 for p,s in contents.items():
  if a.check:
   if not p.exists() or p.read_text()!=s:raise SystemExit('STALE_V51_CONTRACT:'+str(p))
  else:p.write_text(s)
 print(json.dumps({'status':'CHECKED' if a.check else 'GENERATED','manifest_fingerprint':m['manifest_fingerprint']}))
if __name__=='__main__':main()
