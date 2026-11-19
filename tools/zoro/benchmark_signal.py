"""Compare Arena signal profiles on the same pinned Korean examples, locally."""
import argparse
import csv
import hashlib
import io
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from arena.signal import PROFILES, evaluate_signal
from arena.store import check_loopback_endpoint
from integration.v48 import bridge

ROOT = Path(__file__).resolve().parents[2]
SPLITS = {
    'valid': '930f2341fd21b6dd1648328636df1babdb7c7687ef1ff24295656b0caaa5f6b9',
    'test': '31bed1a63581de43b1c81b84c8714873199ace1f92a4d93830478842df5443bf',
}
CASES = ROOT / 'evaluation/signal_review_cases.json'
ALARM = {'red', 'orange'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def panels(directory):
    result = {}
    for name, expected in SPLITS.items():
        data = (directory / (name + '.csv')).read_bytes()
        if digest(data) != expected:
            raise ValueError('DATASET_HASH_MISMATCH: ' + name)
        records = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))
        result[name] = [(int(row['LABEL']), row['TEXT']) for row in records]
    result['challenge'] = [(label, text) for _, label, text in json.loads(CASES.read_text(encoding='utf8'))]
    return result


def grade_metrics(rows):
    matrix = {str(label): dict.fromkeys(('red', 'orange', 'green', 'gray'), 0) for label in (0, 1)}
    for row in rows:
        matrix[str(row['label'])][row['grade']] += 1
    positives, negatives = sum(matrix['1'].values()), sum(matrix['0'].values())
    tp = sum(matrix['1'][g] for g in ALARM)
    fp = sum(matrix['0'][g] for g in ALARM)
    times = sorted(r['ms'] for r in rows)
    return {'n': len(rows), 'matrix': matrix, 'recall': tp / positives, 'fpr': fp / negatives,
            'precision': tp / (tp + fp) if tp + fp else None, 'phishing_green': matrix['1']['green'] / positives,
            'gray_rate': sum(c['gray'] for c in matrix.values()) / len(rows),
            'strict_accuracy': (matrix['0']['green'] + tp) / len(rows),
            'p50_ms': times[math.ceil(.50 * len(times)) - 1], 'p95_ms': times[math.ceil(.95 * len(times)) - 1]}


def risk_score(row):
    return row['scores']['red'] + row['scores']['orange']


def validation_cutoff(rows):
    # Include the empty alert set. Include ties as one indivisible group.
    buckets = {}
    for row in rows:
        buckets.setdefault(risk_score(row), Counter())[row['label']] += 1
    negatives = sum(row['label'] == 0 for row in rows)
    best = (0, 0)
    threshold = None
    tp = fp = 0
    for score, labels in sorted(buckets.items(), reverse=True):
        tp += labels[1]
        fp += labels[0]
        if 20 * fp > negatives:
            break
        if (tp, -fp) > best:
            best = (tp, -fp)
            threshold = score
    return threshold


def score_counts(rows, cutoff):
    chosen = [r for r in rows if cutoff is not None and risk_score(r) >= cutoff]
    return {'n': len(rows), 'phishing': sum(r['label'] for r in rows),
            'tp': sum(r['label'] for r in chosen), 'fp': sum(r['label'] == 0 for r in chosen)}


def paired(before, after):
    counts = {k: 0 for k in ('recovered_phishing', 'lost_phishing', 'resolved_false_alerts', 'new_false_alerts')}
    for left, right in zip(before, after, strict=True):
        if (left['row'], left['input_sha256'], left['label']) != (right['row'], right['input_sha256'], right['label']):
            raise ValueError('PAIR_MISMATCH')
        old, new = left['grade'] in ALARM, right['grade'] in ALARM
        if old != new:
            if left['label']:
                key = 'recovered_phishing' if new else 'lost_phishing'
            else:
                key = 'new_false_alerts' if new else 'resolved_false_alerts'
            counts[key] += 1
    return counts


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    temporary.replace(path)


def run(client, panels_by_name, out, evidence):
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'status': 'INCOMPLETE', 'evidence': evidence, 'model_id': getattr(client, 'model_id', None),
                'checkpoint_verified': False, 'utc': datetime.now(timezone.utc).isoformat(),
                'expected_public_csv_sha256': SPLITS,
                'input_panel_sha256': {name: digest(json.dumps(rows, ensure_ascii=False).encode())
                                       for name, rows in panels_by_name.items()},
                'question_sha256': {k: digest(json.dumps(v, ensure_ascii=False, sort_keys=True).encode())
                                    for k, v in PROFILES.items()}}
    write_json(out / 'manifest.json', manifest)
    history = {}
    thresholds = {}
    profiles = list(PROFILES)
    with (out / 'predictions.jsonl').open('x', encoding='utf8') as log:
        for panel in ('valid', 'test', 'challenge'):
            by_profile = {p: [] for p in profiles}
            for index, (label, text) in enumerate(panels_by_name[panel], 1):
                offset = (index - 1) % len(profiles)
                for profile in profiles[offset:] + profiles[:offset]:
                    start = time.monotonic()
                    result = evaluate_signal(client, text, profile=profile)
                    elapsed = round(1000 * (time.monotonic() - start), 3)
                    ctx = result['context_review']
                    row = {'panel': panel, 'profile': profile, 'row': index, 'input_sha256': digest(text.encode()),
                           'label': label, 'grade': result['grade'], 'scores': result['scores'],
                           'action': result['requested_action']['id'], 'original': ctx['original'],
                           'reasons': ctx['reasons'], 'ms': elapsed}
                    log.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                    by_profile[profile].append(row)
                log.flush()
            if panel == 'valid':
                thresholds = {p: validation_cutoff(by_profile[p]) for p in profiles}
            history[panel] = {p: {'display': grade_metrics(rows),
                                  'score_replay_only': score_counts(rows, thresholds[p]),
                                  'paired_vs_baseline': paired(by_profile['baseline'], rows)}
                              for p, rows in by_profile.items()}
    write_json(out / 'summary.json', {'evidence': evidence, 'valid_cutoffs': thresholds, 'panels': history})
    write_json(out / 'manifest.json', {**manifest, 'status': 'COMPLETE'})
    return history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True, help='original Korean valid.csv and test.csv')
    parser.add_argument('--out', type=Path, required=True, help='new directory for this run')
    args = parser.parse_args()
    data = panels(args.data_dir)
    client = bridge.ModelClient()
    check_loopback_endpoint(client.endpoint)
    if not client.status()['configured']:
        parser.exit(2, 'MODEL_NOT_CONFIGURED: configure the local Zoro used by Arena.\n')
    run(client, data, args.out, 'LOCAL_MODEL_RESPONSE_UNATTESTED')
    print(args.out / 'summary.json')


if __name__ == '__main__':
    main()
