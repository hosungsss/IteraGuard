"""Rerun the pinned Korean test set through the local signal evaluator."""

import csv
import hashlib
import io
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep

from integration.v48 import bridge

from .signal import DEFAULT_PROFILE, evaluate_signal


CSV_SHA256 = '31bed1a63581de43b1c81b84c8714873199ace1f92a4d93830478842df5443bf'
CSV_BYTES = 299076
TOTAL = 551
LABEL_COUNTS = {'0': 501, '1': 50}
CLASSES = {'0': 'normal', '1': 'phishing'}
GRADES = ('green', 'orange', 'red', 'gray')


def load_cases(path):
    """Check the exact input bytes before parsing or passing any rows to Zoro."""
    try:
        path = Path(path)
        if not path.is_file():
            raise ValueError
        with path.open('rb') as source:
            data = source.read(CSV_BYTES + 1)
        if len(data) != CSV_BYTES or hashlib.sha256(data).hexdigest() != CSV_SHA256:
            raise ValueError
        rows = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
        if next(rows, None) != ['LABEL', 'TEXT']:
            raise ValueError
        cases = []
        for label, text in rows:
            if label not in LABEL_COUNTS or not text.strip() or len(text) > 2000:
                raise ValueError
            cases.append((label, text))
        if len(cases) != TOTAL or Counter(label for label, _ in cases) != LABEL_COUNTS:
            raise ValueError
    except (OSError, ValueError, csv.Error):
        raise ValueError('BENCHMARK_CSV_INVALID') from None
    return cases


class SignalBenchmark:
    """One background run per Arena instance. Publish aggregates after completion."""

    def __init__(self, csv_path, client, inference_slot, *, profile=DEFAULT_PROFILE):
        self.csv_path = csv_path
        self.client = client
        self.inference_slot = inference_slot
        self.profile = profile
        self._lock = threading.Lock()
        self.status = 'idle'
        self.completed = 0
        self.error = None
        self.result = None

    def _snapshot(self):
        return {
            'available': bool(self.csv_path),
            'status': self.status,
            'completed': self.completed,
            'total': TOTAL,
            'error': self.error,
            'result': self.result,
        }

    def snapshot(self):
        with self._lock:
            return self._snapshot()

    def start(self):
        with self._lock:
            if self.csv_path and self.status != 'running':
                self.status = 'running'
                self.completed = 0
                self.error = None
                try:
                    threading.Thread(target=self._run, daemon=True).start()
                except RuntimeError:
                    self.status = 'failed'
                    self.error = 'BENCHMARK_RUN_FAILED'
            return self._snapshot()

    def _fail(self, code):
        with self._lock:
            self.status = 'failed'
            self.error = code

    def _run(self):
        start = monotonic()
        try:
            cases = load_cases(self.csv_path)
        except ValueError:
            self._fail('BENCHMARK_CSV_INVALID')
            return
        counts = {name: dict.fromkeys(GRADES, 0) for name in CLASSES.values()}
        try:
            for index, (label, text) in enumerate(cases, 1):
                with self.inference_slot:
                    result = evaluate_signal(self.client, text, profile=self.profile)
                counts[CLASSES[label]][result['grade']] += 1
                with self._lock:
                    self.completed = index
                if index < TOTAL:
                    sleep(0.06)  # Yield the shared model slot to interactive requests.
        except (bridge.ModelUnavailable, bridge.ContractError):
            self._fail('BENCHMARK_MODEL_UNAVAILABLE')
            return
        except Exception:
            # Release the run for retry without logging input-derived exceptions.
            self._fail('BENCHMARK_RUN_FAILED')
            return
        with self._lock:
            self.result = {
                'counts': counts,
                'elapsed_ms': round((monotonic() - start) * 1000),
                'finished_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'profile': self.profile,
            }
            self.status = 'completed'
