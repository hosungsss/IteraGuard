"""Synthetic-only durable workflow; closing a session never clears its risk.

SQLite stores derived decisions, keyed fingerprints and user reports, never input
text, model raw output or quoted evidence. Local records are not independent
institutional verification or tamper-proof audit storage.
"""
from datetime import datetime, timezone
from time import perf_counter
from arena.evidence import digest as evidence_digest
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import math
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
from uuid import uuid4
from urllib.parse import urlsplit

from integration.v48 import bridge
from integration import v50, v51

SCHEMA_VERSION = 1
MAX_OPEN_TASKS = 64
TASK_ORDER = "CASE trigger_action WHEN 'PAUSE_AND_VERIFY' THEN 0 WHEN 'ASK_HUMAN' THEN 1 ELSE 2 END,created_version,id"
POLICY_IDS = {'legacy', 'dra'}
OBSERVATIONS = {'NOT_CHECKED', 'USER_REPORTS_CONFIRMED', 'USER_REPORTS_DENIED', 'UNRESOLVED'}
MESSAGES = {
    'NO_STRONG_SIGNAL': '현재 텍스트에서 강한 요청 신호를 확인하지 못했습니다. 안전 보증은 아닙니다.',
    'CAUTION': '요청 내용과 상대를 독립적인 경로로 확인하세요.',
    'PAUSE_AND_VERIFY': '민감한 행동을 멈추고 독립적으로 알고 있던 공식 경로에서 확인하세요.',
    'ASK_HUMAN': '현재 판단을 확정할 수 없습니다. 사람의 검토와 추가 확인이 필요합니다.',
}
TASK_INSTRUCTION = '독립적으로 알고 있던 공식 경로에서 확인하세요. 실제 연락은 수행되지 않습니다.'


class Conflict(ValueError):
    pass


def check_loopback_endpoint(endpoint):
    """v5 runtime scope cannot be broadened by remote-consent environment flags."""
    if not endpoint:
        return  # Unconfigured clients follow the explicit unavailable path.
    try:
        if type(endpoint) is not str or any(ord(ch) <= 32 for ch in endpoint):
            raise ValueError
        u = urlsplit(endpoint)
        if (u.username is not None or u.password is not None or u.query or u.fragment
                or u.path.rstrip('/') != '/v1/systemone' or u.scheme not in {'http', 'https'}
                or not u.hostname or (u.port is not None and not 1 <= u.port <= 65535)):
            raise ValueError
    except (ValueError, TypeError):
        raise bridge.ModelUnavailable('INVALID_MODEL_ENDPOINT') from None
    if u.hostname not in {'127.0.0.1', 'localhost'}:
        raise bridge.ModelUnavailable('V50_LOOPBACK_ONLY')


class Arena:
    def __init__(self, db='runs/arena.sqlite3', client=None, *, policy_id='legacy', profile_id='v50-baseline'):
        if policy_id not in POLICY_IDS:
            raise ValueError('UNKNOWN_POLICY_ID')
        Path(db).parent.mkdir(parents=True, exist_ok=True)
        self.db = str(db)
        self.client = client if client is not None else bridge.ModelClient()
        if isinstance(self.client, bridge.ModelClient):
            check_loopback_endpoint(self.client.endpoint)
        self.policy_id = policy_id
        v51.P.profile(profile_id, policy_id)
        self.profile_id = profile_id
        # Atomic additive migration from v4.9 (user_version=0); never downgrade.
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            version = c.execute('PRAGMA user_version').fetchone()[0]
            if version > SCHEMA_VERSION:
                raise ValueError('UNSUPPORTED_DATABASE_SCHEMA')
            for statement in (
                'CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY,version INTEGER NOT NULL,prior_pause INTEGER NOT NULL)',
                'CREATE TABLE IF NOT EXISTS events (sid TEXT,request_id TEXT,digest TEXT,result TEXT NOT NULL,PRIMARY KEY(sid,request_id))',
                'CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY,sid TEXT NOT NULL,created_version INTEGER NOT NULL,status TEXT NOT NULL,observation TEXT NOT NULL)',
            ):
                c.execute(statement)
            columns = {r['name'] for r in c.execute('PRAGMA table_info(sessions)')}
            if 'lifecycle' not in columns:
                c.execute("ALTER TABLE sessions ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'OPEN'")
            columns = {r['name'] for r in c.execute('PRAGMA table_info(tasks)')}
            if 'trigger_fingerprint' not in columns:
                c.execute('ALTER TABLE tasks ADD COLUMN trigger_fingerprint TEXT')
            if 'trigger_action' not in columns:
                c.execute('ALTER TABLE tasks ADD COLUMN trigger_action TEXT')
            if 'trigger_reason' not in columns:
                c.execute('ALTER TABLE tasks ADD COLUMN trigger_reason TEXT')
            c.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('digest_key', secrets.token_hex(32)))
            self.key = bytes.fromhex(c.execute('SELECT value FROM meta WHERE key=?', ('digest_key',)).fetchone()[0])
            c.execute('PRAGMA user_version = 1')

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def manifest(self):
        manifest = self._execution_manifest()
        try:
            binding = v51.P.binding(self.profile_id, self.policy_id)
        except (OSError, ValueError, KeyError, TypeError):
            raise bridge.ContractError('EXECUTION_CONTRACT_UNAVAILABLE') from None
        return {'app': 'dmsg-arena', 'version': '5.6', 'contract_version': '5.1', 'schema_version': SCHEMA_VERSION,
                'active_policy_id': self.policy_id, 'active_question_profile': self.profile_id,
                'question_binding': binding, 'execution_manifest': manifest,
                'context_scope': 'CURRENT_TEXT_ONLY', 'observation_authority': 'USER_REPORTED',
                'lifecycle_states': ['OPEN', 'CLOSED_UNRESOLVED'], 'risk_release_implemented': False,
                'arena_sources': {name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ('store.py','evidence.py','server.py','web/main.js')}}

    @staticmethod
    def _execution_manifest():
        try:
            return v51.execution_manifest()
        except (OSError, ValueError, KeyError, TypeError):
            raise bridge.ContractError('EXECUTION_CONTRACT_UNAVAILABLE') from None

    @staticmethod
    def _id(value, kind):
        if type(value) is not str or len(value) != 32 or any(x not in '0123456789abcdef' for x in value):
            raise ValueError('INVALID_' + kind + '_ID')

    def _controls(self, session_id, version, request_id, synthetic_only):
        if synthetic_only is not True:
            raise ValueError('SYNTHETIC_ONLY_REQUIRED')
        self._id(session_id, 'SESSION')
        if type(version) is not int or not 0 <= version <= 100000:
            raise ValueError('INVALID_VERSION')
        if (type(request_id) is not str or not 1 <= len(request_id) <= 64 or not request_id.isascii()
                or not all(x.isalnum() or x in '_-' for x in request_id)):
            raise ValueError('INVALID_REQUEST_ID')

    def _digest(self, value):
        return hmac.new(self.key, json.dumps(value, ensure_ascii=False).encode(), 'sha256').hexdigest()

    @staticmethod
    def _check(c, session_id, version, request_id, digest):
        old = c.execute('SELECT digest,result FROM events WHERE sid=? AND request_id=?', (session_id, request_id)).fetchone()
        if old:
            if not hmac.compare_digest(old['digest'], digest):
                raise Conflict('CONFLICTING_RETRY')
            # A retry describes its recorded event, not the session's latest state.
            return json.loads(old['result']), None
        session = c.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
        if session is None:
            raise Conflict('UNKNOWN_SESSION')
        if session['version'] != version:
            raise Conflict('STALE_VERSION')
        return None, session

    @staticmethod
    def _save_event(c, session_id, request_id, digest, result):
        c.execute('INSERT INTO events VALUES (?,?,?,?)',
                  (session_id, request_id, digest, json.dumps(result, ensure_ascii=False, allow_nan=False)))

    def start(self):
        sid = uuid4().hex
        with self.connect() as c:
            c.execute("INSERT INTO sessions (id,version,prior_pause,lifecycle) VALUES (?,0,0,'OPEN')", (sid,))
        # Preserve the v4.9 start envelope. Lifecycle/profile are in state/manifest.
        return {'session_id': sid, 'version': 0, 'mode': 'NOT_EVALUATED'}

    def read(self, sid):
        self._id(sid, 'SESSION')
        with self.connect() as c:
            # The envelope, tasks and event list must describe one DB snapshot.
            c.execute('BEGIN')
            s = c.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
            if s is None:
                raise Conflict('UNKNOWN_SESSION')
            tasks = [dict(r) for r in c.execute('SELECT * FROM tasks WHERE sid=? ORDER BY created_version,id', (sid,))]
            events = [json.loads(r[0]) for r in c.execute('SELECT result FROM events WHERE sid=? ORDER BY rowid', (sid,))]
        for task in tasks:
            task.update(self._task_result(task))
            task.pop('trigger_fingerprint', None)
            task.pop('trigger_action', None)
            task.pop('trigger_reason', None)
        tasks.sort(key=lambda t: (0 if t.get('type') == 'PAUSE_AND_INDEPENDENT_CHECK' else 1 if t.get('type') in {'CLARIFY_REQUEST','MODEL_RETRY'} else 2,t['created_version'],t['id']))
        return {**dict(s), 'open_task_count':sum(t['status']=='OPEN' for t in tasks), 'schema_version': SCHEMA_VERSION, 'tasks': tasks, 'events': events,
                'active_policy_id': self.policy_id, 'risk_release_implemented': False}

    def close(self, *, session_id, version, request_id, synthetic_only):
        return self._transition('CLOSE_UNRESOLVED', session_id, version, request_id, synthetic_only)

    def reopen(self, *, session_id, version, request_id, synthetic_only):
        return self._transition('REOPEN', session_id, version, request_id, synthetic_only)

    def _transition(self, operation, session_id, version, request_id, synthetic_only):
        self._controls(session_id, version, request_id, synthetic_only)
        digest = self._digest([operation, version])
        target = 'CLOSED_UNRESOLVED' if operation == 'CLOSE_UNRESOLVED' else 'OPEN'
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            cached, session = self._check(c, session_id, version, request_id, digest)
            if cached is not None:
                return cached
            if session['lifecycle'] == target:
                raise Conflict('SESSION_ALREADY_CLOSED' if target == 'CLOSED_UNRESOLVED' else 'SESSION_ALREADY_OPEN')
            result = {'event_type': operation, 'mode': 'LIFECYCLE_ONLY', 'session_id': session_id,
                      'version': version + 1, 'request_id': request_id, 'lifecycle': target,
                      'prior_pause': bool(session['prior_pause']), 'risk_cleared': False,
                      'model_called': False, 'schema_version': SCHEMA_VERSION,
                      'message': ('미해결 상태로 보관했습니다. 위험이 해제되거나 확인된 것은 아닙니다.'
                                  if target == 'CLOSED_UNRESOLVED' else '이전 위험과 확인 이력을 유지한 채 재개했습니다.'),
                      'execution_trace': {'schema_version': 'arena-lifecycle/1', 'event_type': operation,
                                          'session_id': session_id, 'request_id': request_id,
                                          'version_before': version, 'version_after': version + 1,
                                          'lifecycle_before': session['lifecycle'], 'lifecycle_after': target,
                                          'prior_pause_before': bool(session['prior_pause']),
                                          'prior_pause_after': bool(session['prior_pause']),
                                          'model_called': False, 'risk_cleared': False}}
            c.execute('UPDATE sessions SET version=?,lifecycle=? WHERE id=?', (version + 1, target, session_id))
            self._save_event(c, session_id, request_id, digest, result)
        return result

    @staticmethod
    def _task_result(row):
        reason = row['trigger_reason'] or ''
        action = row['trigger_action'] or ''
        kind, instruction = 'INDEPENDENT_CHANNEL_CHECK', TASK_INSTRUCTION
        if reason in {'MODEL_UNAVAILABLE', 'MODEL_RESPONSE_INVALID', 'MODEL_NOT_CONFIGURED',
                      'INVALID_TIMEOUT_CONFIG', 'INVALID_MODEL_ENDPOINT', 'HTTP_STATUS_NOT_OK',
                      'UNEXPECTED_MODEL_CONTENT_TYPE', 'RESPONSE_TOO_LARGE', 'INVALID_RESPONSE_JSON',
                      'MODEL_ID_MISMATCH', 'MODEL_ID_ECHO_REQUIRED', 'DNS_FAILURE', 'LOCAL_APP_UNREACHABLE',
                      'HTTPS_REQUIRED', 'REMOTE_TEXT_TRANSFER_NOT_CONSENTED', 'REMOTE_HOST_NOT_ALLOWLISTED',
                      'NON_PUBLIC_ENDPOINT_IP', 'REQUEST_TOO_LARGE', 'V50_LOOPBACK_ONLY', 'REMOTE_RELAY_DISABLED_V50'} or any(x in reason for x in ('UNAVAILABLE', 'CONTRACT', 'TRANSPORT')):
            kind, instruction = 'MODEL_RETRY', '모델 연결과 응답 계약을 확인한 뒤 같은 입력을 다시 평가하세요. 연결 실패는 안전 판정이 아닙니다.'
        elif action == 'ASK_HUMAN':
            kind, instruction = 'CLARIFY_REQUEST', '누가 무엇을 어디로 요청했는지 확인하세요. 코드·비밀번호 등 비밀정보를 추가 입력하지 말고, 알려진 독립 연락 경로로 요청을 확인하세요.'
        elif action == 'PAUSE_AND_VERIFY':
            kind, instruction = 'PAUSE_AND_INDEPENDENT_CHECK', '송금·코드 전달·원격접속을 멈추고, 메시지 속 연락처가 아닌 기존 공식 경로로 요청을 확인하세요. 완료 보고만으로 위험이 해제되지 않습니다.'
        return {'id': row['id'], 'type': kind, 'status': row['status'],
                'observation': row['observation'], 'observation_provenance': 'USER_REPORTED',
                'instruction': instruction}

    def evaluate(self, *, session_id, version, request_id, text, synthetic_only,
                 task_id=None, observation='NOT_CHECKED', user_review=False, consent=None):
        started = perf_counter()
        received_utc = datetime.now(timezone.utc).isoformat()
        raw_digest = None
        self._controls(session_id, version, request_id, synthetic_only)
        if task_id is not None:
            self._id(task_id, 'TASK')
        if type(text) is not str or not text.strip() or len(text) > 2000:
            raise ValueError('INVALID_TEXT')
        if type(observation) is not str or observation not in OBSERVATIONS:
            raise ValueError('INVALID_OBSERVATION')
        if observation != 'NOT_CHECKED' and not task_id:
            raise ValueError('TASK_REQUIRED')
        if type(user_review) is not bool:
            raise ValueError('INVALID_USER_REVIEW')
        if consent is None:
            consent = {}
        if (type(consent) is not dict or set(consent) - {'external_reputation', 'web_analysis'}
                or any(type(v) is not bool for v in consent.values())):
            raise ValueError('INVALID_CONSENT')
        consent = {k: consent.get(k, False) for k in ('external_reputation', 'web_analysis')}
        # Preserve default v4.9 digests so identical retries survive migration.
        # Explicit new local options are bound into v5 retry identity.
        identity = [version, text, task_id, observation]
        if user_review or any(consent.values()):
            identity += ['local-options-v1', user_review, consent]
        if self.profile_id != 'v50-baseline' or self.policy_id != 'legacy':
            identity += ['v51-profile-policy', self.profile_id, self.policy_id, v51.P.binding(self.profile_id, self.policy_id)['profile_fingerprint']]
        digest = self._digest(identity)
        text_fingerprint = self._digest(['task-input-v1', text])

        def check(c):
            cached, session = self._check(c, session_id, version, request_id, digest)
            if cached is not None:
                return cached, session
            if session['lifecycle'] != 'OPEN':
                raise Conflict('SESSION_CLOSED_UNRESOLVED')
            if task_id and not c.execute('SELECT 1 FROM tasks WHERE id=? AND sid=? AND status=?',
                                        (task_id, session_id, 'OPEN')).fetchone():
                raise Conflict('UNKNOWN_OR_CLOSED_TASK')
            return None, session

        with self.connect() as c:
            cached, _ = check(c)
            if cached is not None:
                return cached
        # Reject a broken question/policy contract before sending any model input.
        # A manifest failure has no valid trace and is handled as static HTTP 503.
        self._execution_manifest()
        # Only current text goes to the model; history/observations add no hidden facts.
        # Network outside SQLite's write lock, then lifecycle/version checked again.
        try:
            if isinstance(self.client, bridge.ModelClient):
                check_loopback_endpoint(self.client.endpoint)
            bound_profile, bound_policy = self.profile_id, self.policy_id
            bound_request = v51.request_binding(bound_profile, bound_policy)
            if bound_profile == 'v50-baseline':
                raw, ms = self.client.infer(text)
            else:
                raw, ms = self.client.infer(text, question_payload=v51.question_payload(text, bound_profile, bound_policy))
            outcome = v51.evaluate_current(text, raw, policy_id=bound_policy, profile_id=bound_profile, binding=bound_request)
            if type(ms) not in (int,float) or not math.isfinite(ms) or ms < 0:
                raise bridge.ContractError('INVALID_LATENCY')
            raw_digest = evidence_digest(raw)
        except (bridge.ModelUnavailable, bridge.ContractError, ValueError, TypeError) as exc:
            outcome = v51.unavailable_current(str(exc), policy_id=self.policy_id, profile_id=self.profile_id)
            ms = None
        outcome = v51.apply_local_layers(text, outcome, user_review=user_review, consent=consent)
        result = {k: deepcopy(outcome[k]) for k in ('action', 'reason', 'policy_id', 'manifest_fingerprint',
                  'model_status', 'execution_trace', 'abstention', 'error_code', 'link_summary',
                  'question_profile_id', 'question_binding', 'semantic_policy_id', 'evidence_display_trace') if k in outcome}
        result.update(mode='MODEL_RESPONSE_UNATTESTED' if ms is not None else 'MODEL_UNAVAILABLE',
                      model_status='VALID' if ms is not None else 'FAILED', latency_ms=ms,
                      probabilities=deepcopy(outcome.get('probs', {})),
                      evidence=[{k: e[k] for k in ('start', 'end', 'kind', 'directness') if k in e}
                                for e in outcome.get('evidence', [])])
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            cached, session = check(c)
            if cached is not None:
                return cached
            paused = bool(session['prior_pause'])
            current_action = result['action']
            result['current_turn_action'] = current_action
            result['current_turn_reason'] = result['reason']
            if paused and current_action != 'PAUSE_AND_VERIFY':
                result['action'] = 'ASK_HUMAN'
                result['reason'] = 'PRIOR_RISK_UNRESOLVED'
            prior_pause_after = paused or current_action == 'PAUSE_AND_VERIFY'
            result.update(event_type='EVALUATE', message=MESSAGES[result['action']],
                          session_id=session_id, version=version + 1, request_id=request_id,
                          lifecycle='OPEN', prior_pause=prior_pause_after,
                          observation=observation, observation_provenance='USER_REPORTED',
                          schema_version=SCHEMA_VERSION, model_attested=False,
                          policy_id=self.policy_id, policy_version='v51/' + self.policy_id + '/' + self.profile_id + '/session-1')
            if task_id:
                # No new report must not erase UNRESOLVED.
                if observation != 'NOT_CHECKED':
                    status = 'OPEN' if observation == 'UNRESOLVED' else 'REPORTED_COMPLETE'
                    c.execute('UPDATE tasks SET observation=?,status=? WHERE id=?', (observation, status, task_id))
                result['observed_task_id'] = task_id
            open_task = c.execute('SELECT * FROM tasks WHERE sid=? AND status=? ORDER BY created_version,id LIMIT 1',
                                  (session_id, 'OPEN')).fetchone()
            latest_task = c.execute('SELECT * FROM tasks WHERE sid=? ORDER BY created_version DESC,id DESC LIMIT 1',
                                    (session_id,)).fetchone()
            # Key each current actionable request by input, action and reason. Past
            # session risk alone cannot create new work. Completed identical work
            # remains a report, not safety clearance.
            requires_current_task = current_action in {'ASK_HUMAN', 'PAUSE_AND_VERIFY', 'CAUTION'}
            matching_task = c.execute(
                'SELECT * FROM tasks WHERE sid=? AND trigger_fingerprint=? AND trigger_action=? AND trigger_reason=? ORDER BY created_version DESC LIMIT 1',
                (session_id,text_fingerprint,current_action,result['current_turn_reason'])).fetchone()
            if requires_current_task and matching_task is None:
                count = c.execute("SELECT COUNT(*) FROM tasks WHERE sid=? AND status='OPEN'",(session_id,)).fetchone()[0]
                if count >= MAX_OPEN_TASKS:
                    raise Conflict('TASK_CAPACITY_REACHED')
                tid = uuid4().hex
                c.execute('INSERT INTO tasks (id,sid,created_version,status,observation,trigger_fingerprint,trigger_action,trigger_reason) VALUES (?,?,?,?,?,?,?,?)',
                          (tid,session_id,version+1,'OPEN','NOT_CHECKED',text_fingerprint,current_action,result['current_turn_reason']))
            open_rows = c.execute("SELECT * FROM tasks WHERE sid=? AND status='OPEN' ORDER BY " + TASK_ORDER,(session_id,)).fetchall()
            open_task = open_rows[0] if open_rows else None
            result['open_task_count'] = len(open_rows)
            result['open_tasks'] = [self._task_result(row) for row in open_rows]
            if open_task:
                result['next_task'] = self._task_result(open_task)
                result['task_disposition'] = 'OPEN_TASK_AVAILABLE'
            elif latest_task:
                result['related_task'] = self._task_result(latest_task)
                result['task_disposition'] = 'REPORTED_TASK_RETAINED_NOT_VERIFIED'
            else:
                result['task_disposition'] = 'NO_TASK'
            result['provenance'] = {
                'schema': 'iteraguard-provenance/1', 'received_utc': received_utc,
                'execution_source': 'LOCAL_HTTP_MODEL_UNATTESTED' if type(self.client) is bridge.ModelClient else 'CONTROLLED_CLIENT',
                'model_identity_verified': False, 'response_sha256': raw_digest,
                'pipeline_ms': round((perf_counter() - started) * 1000, 3),
                'profile_id': self.profile_id, 'policy_id': self.policy_id,
                'execution_manifest': result.get('manifest_fingerprint'),
                'arena_sources': self.manifest()['arena_sources'],
                'input_source': 'USER_SUPPLIED_SYNTHETIC', 'npu_execution_verified': False}
            trace = result.setdefault('execution_trace', {})
            trace['session'] = {'session_id': session_id, 'request_id': request_id,
                                'version_before': version, 'version_after': version + 1,
                                'input_fingerprint': digest, 'context_scope': 'CURRENT_TEXT_ONLY',
                                'lifecycle_before': 'OPEN', 'lifecycle_after': 'OPEN',
                                'current_turn_action': current_action, 'session_action': result['action'],
                                'prior_pause_before': paused, 'prior_pause_after': prior_pause_after,
                                'applied_rule': 'PRIOR_RISK_UNRESOLVED' if paused and current_action != 'PAUSE_AND_VERIFY' else 'CURRENT_TURN_RETAINED',
                                'observation': observation, 'observation_provenance': 'USER_REPORTED',
                                'observed_task_id': task_id, 'task_disposition': result['task_disposition'],
                                'risk_cleared': False}
            c.execute('UPDATE sessions SET version=?,prior_pause=? WHERE id=?',
                      (version + 1, int(prior_pause_after), session_id))
            self._save_event(c, session_id, request_id, digest, result)
        return result
