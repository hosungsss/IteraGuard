"""One offline regression entry point. Live model and physical devices are separate evidence."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(report_dir, include_release=False):
    dest = Path(report_dir).resolve()
    if dest == ROOT or dest.is_relative_to(ROOT):
        raise ValueError('REPORT_DIR_MUST_BE_OUTSIDE_SOURCE_TREE')
    dest.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    commands = [
        ('dmsg', [py, '-m', 'unittest', 'discover', '-s', 'dmsg/tests', '-v']),
        ('v49', [py, '-m', 'unittest', 'discover', '-s', 'tests_v49', '-v']),
        ('v50', [py, '-m', 'unittest', 'discover', '-s', 'tests_v50', '-v']),
        ('contract_export', [py, 'tools/export_v50_contract.py', '--check']),
        ('ui', ['node', 'tests_v49/test_ui_binding.js']),
        ('conformance', ['node', 'apps/conformance/run_conformance.js', str(dest / 'conformance.json')]),
        ('linkguard_python', [py, '-m', 'unittest', 'discover', '-s', 'tests_linkguard', '-v']),
        ('linkguard_js', ['node', 'apps/conformance/run_linkguard.js']),
        ('domain', ['node', 'tools/test_domain_v48.js']),
        ('trace', [py, 'tools/test_trace_v48.py']),
        ('nlp_golden', ['node', 'tools/nlp/regress_cases_v46.js']),
        ('nlp_parity', ['node', 'tools/nlp/nlp_parity.js']),
        ('forbidden', [py, 'tools/check_forbidden_phrases.py', '--json', str(dest / 'forbidden.json')]),
        ('syntax_app', ['node', '--check', 'apps/web/app.js']),
        ('syntax_arena', ['node', '--check', 'arena/web/main.js']),
        ('syntax_host', ['node', '--check', 'apps/desktop/server.js']),
    ]
    commands.extend((p.stem, ['node', str(p.relative_to(ROOT))]) for p in sorted((ROOT / 'tests_v50').glob('test_*.js')))
    if include_release:
        commands.append(('release', [py, 'tools/verify_release.py']))
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', DMSG_MODEL_ENABLED='0')
    records = []
    for name, cmd in commands:
        start = datetime.datetime.now(datetime.timezone.utc)
        try:
            p = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
            data, code = p.stdout, p.returncode
        except subprocess.TimeoutExpired as exc:
            data, code = (exc.stdout or b'') + b'\nVALIDATION_TIMEOUT\n', 124
        (dest / (name + '.log')).write_bytes(data)
        row = {'name': name, 'command': cmd, 'exit_code': code,
               'started_utc': start.isoformat(), 'duration_s': (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds(),
               'log_sha256': hashlib.sha256(data).hexdigest()}
        records.append(row)
        print(json.dumps(row), flush=True)
    result = {'status': 'PASS' if all(r['exit_code'] == 0 for r in records) else 'FAIL',
              'checks': records, 'live_model_calls': 0, 'device_execution': 'NOT_RUN',
              'independent_accuracy': 'NOT_MEASURED'}
    (dest / 'validation_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', required=True, type=Path)
    parser.add_argument('--include-release', action='store_true')
    args = parser.parse_args()
    sys.exit(0 if run(args.report_dir, args.include_release)['status'] == 'PASS' else 1)
