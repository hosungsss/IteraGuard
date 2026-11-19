"""Static checks for the self-contained dmsg skill. Not a host installation test."""
from pathlib import Path
import json, re, sys, zipfile, stat
ROOT=Path(__file__).resolve().parents[1]

def main():
    errors=[]
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')]
    skill_files=[p for p in files if p.name.lower()=='skill.md']
    if skill_files!=[ROOT/'SKILL.md']:
        errors.append('expected one root SKILL.md')
    doc=(ROOT/'SKILL.md').read_text(encoding='utf8')
    m=re.match(r'(?s)^---\n(.*?)\n---\n', doc)
    if not m or not re.search(r'^name: dmsg$',m.group(1),re.M):
        errors.append('skill YAML: name dmsg required')
    if not m or not re.search(r'^description: .+',m.group(1),re.M):
        errors.append('skill YAML: description required')
    config=json.loads((ROOT/'config.example.json').read_text(encoding='utf8'))
    if config.get('skill_id')!='dmsg' or config.get('skill_version')!='5.2':
        errors.append('identity/version mismatch')
    if any(config.get('safety',{}).values()): errors.append('safety defaults may not authorize external actions')
    if len(files)>200:errors.append('R05_TOO_MANY_FILES')
    if not re.fullmatch(r'dmsg', config.get('skill_id','')):errors.append('R03_CANONICAL_ID')
    creator='<!-- Developed by Hankil Choi | M.S., Graduate School of Virtual Convergence, Sogang University | Instagram / LinkedIn: @hank3149 -->'
    if doc.rstrip().splitlines()[-1]!=creator:errors.append('CREATOR_ATTRIBUTION_MISSING')
    if not all(x in doc for x in ('LAYER HARNESS', 'preview_memory_prewrite', 'SNM/4D')):
        errors.append('REQUIRED_CAPABILITY_LAYER_MISSING')
    required=['references/PRD.md','references/SYSTEM_PROMPT.md','references/TRACEABILITY.md','references/PROMPTS.md',
              'references/MODEL_CONTRACT.md','references/EVALUATION.md',
              'references/ELENCHUS_SNM_4D.md','references/PLATFORM_INSTALL.md',
              'tests/test_policy.py','tests/test_prototype.py','tests/test_spec_alignment.py','tests/test_v33_hardening.py','tests/test_v34_release.py','tests/test_v35_model_bridge.py','tests/test_v35_http_integration.py','tests/test_v36_context_and_transport.py','tests/test_v36_async.py','tests/test_v37_privacy_security.py','tests/test_v37_evaluation_npu.py',
              'prototype/paylock.py','prototype/paylock_model.py','tests/test_v38_paylock.py','web/paylock.html','web/paylock.js',
              'prototype/core.py','prototype/session.py','prototype/fixtures.py','prototype/typed_contract.py',
              'prototype/server.py','prototype/context_guard.py','prototype/evaluation_gate.py','prototype/ontology.py','prototype/decision_oracle.py','prototype/model_bridge.py','scripts/evaluate_fixtures.py','scripts/paylock_ablation.py','scripts/evaluate_annotations.py','scripts/npu_readiness.py','scripts/metamorphic_audit.py','scripts/run_adversarial_suite.py','scripts/policy.py','scripts/smoke_zoro.py',
              'web/index.html','web/main.js','web/style.css']
    for path in required:
        if not (ROOT/path).is_file():errors.append('missing: '+path)
    # Optional packaged skill validation is separate from live host testing.
    if len(sys.argv)>1:
        if len(sys.argv)!=3 or sys.argv[1]!='--archive':
            errors.append('INVALID_VALIDATOR_ARGUMENTS')
        else:
            archive=Path(sys.argv[2])
            try:
                with zipfile.ZipFile(archive) as z:
                    entries=[x for x in z.infolist() if not x.is_dir()]
                    names=[x.filename for x in entries]
                    if not (1<=len(entries)<=200):errors.append('ARCHIVE_FILE_COUNT')
                    if len(names)!=len(set(names)):errors.append('ARCHIVE_DUPLICATE_PATH')
                    for item in entries:
                        bits=Path(item.filename).parts
                        if (len(bits)<2 or bits[0]!='dmsg' or '..' in bits or '\\' in item.filename
                                or item.filename.startswith('/') or stat.S_ISLNK(item.external_attr>>16)):
                            errors.append('ARCHIVE_UNSAFE_PATH_OR_LINK')
                        if item.compress_size and item.file_size>50_000_000:
                            errors.append('ARCHIVE_OVERSIZED_ENTRY')
                    if 'dmsg/SKILL.md' not in names:errors.append('ARCHIVE_SKILL_MISSING')
                    if z.testzip() is not None:errors.append('ARCHIVE_BAD_CRC')
                    disk={p.relative_to(ROOT).as_posix() for p in files}
                    package={n.removeprefix('dmsg/') for n in names}
                    if disk!=package:errors.append('ARCHIVE_TREE_DIFFERS_FROM_DISK')
            except (OSError,zipfile.BadZipFile):
                errors.append('UNREADABLE_ARCHIVE')
    if errors:
        print('FAILED:\n'+'\n'.join(errors))
        return 1
    print(f'VALID: dmsg skill; {len(files)} files, config, references, boundary checks PASS')
    return 0

if __name__=='__main__':sys.exit(main())
