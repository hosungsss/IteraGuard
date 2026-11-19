"""In-memory, bounded demonstration sessions with optimistic concurrency.

No raw transcript is stored in event history. Sessions are ephemeral. Requests
are idempotent for identical turn/payload; conflicting retries are rejected.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from time import monotonic
from threading import RLock
import re
import json
from copy import deepcopy
from hashlib import sha256
from hmac import new as hmac_new
from secrets import token_bytes
from uuid import uuid4
from .core import Action, Status, decide
from .fixtures import FIXTURES
from .model_bridge import ModelClient, ModelUnavailable, advisory
from .typed_contract import ContractError

class Conflict(ValueError):
    pass


def _failure_reason(exc: BaseException) -> str:
    code=str(exc)
    if re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}',code):
        return type(exc).__name__+':'+code
    return type(exc).__name__

@dataclass
class Session:
    id: str
    version: int = 0
    history: list[dict] = field(default_factory=list)
    idempotency: dict[str,tuple[str,dict]] = field(default_factory=dict)
    updated: float = field(default_factory=monotonic)
    audit_head: str = 'GENESIS'

class Store:
    def __init__(self, capacity=100, ttl_seconds=1800):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._sessions:dict[str,Session] = {}
        self._lock = RLock()
        # Ephemeral secret prevents offline dictionary attacks against short utterance hashes.
        self._privacy_key = token_bytes(32)
        # v4.2: the audit chain is keyed. v4.1 used bare SHA-256, so anyone able to
        # edit history could recompute every link and verify_audit() returned True.
        # Still ephemeral and in-process: not a signature, not persistence.
        self._audit_key = token_bytes(32)

    def _private_digest(self, text: str) -> str:
        """Per-process HMAC. No raw text or globally reversible content hash in audit logs."""
        return hmac_new(self._privacy_key, text.encode('utf8'), 'sha256').hexdigest()

    def _audit_digest(self, prev: str, record: dict) -> str:
        payload=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        return hmac_new(self._audit_key,(prev+'\n'+payload).encode('utf-8'),'sha256').hexdigest()

    def _append_audit(self, session: Session, record: dict) -> None:
        clean=deepcopy(record)
        prev=session.audit_head
        clean['audit_prev']=prev
        clean['audit_hash']=self._audit_digest(prev,record)
        session.audit_head=clean['audit_hash']
        session.history.append(clean)

    def verify_audit(self, session_id: str) -> bool:
        with self._lock:
            self._prune()
            s=self._sessions.get(session_id)
            if s is None: raise Conflict('UNKNOWN_SESSION')
            return self._integrity_ok(s)

    def _integrity_ok(self, s: Session) -> bool:
        prev='GENESIS'
        for item in s.history:
            clean={k:v for k,v in item.items() if k not in ('audit_prev','audit_hash')}
            if item.get('audit_prev')!=prev or item.get('audit_hash')!=self._audit_digest(prev,clean):
                return False
            prev=item['audit_hash']
        return prev==s.audit_head

    def _prune(self):
        now=monotonic()
        for sid,s in list(self._sessions.items()):
            if now-s.updated > self.ttl_seconds: del self._sessions[sid]
        # Capacity eviction belongs only to session creation, not reads/turns.

    def start(self) -> dict:
        with self._lock:
            return self._start_unlocked()

    def _start_unlocked(self) -> dict:
        self._prune()
        if len(self._sessions)>=self.capacity:
            oldest=min(self._sessions.values(),key=lambda x:x.updated)
            del self._sessions[oldest.id]
        s=Session(uuid4().hex)
        self._sessions[s.id]=s
        return {'session_id':s.id,'version':0,'mode':'FIXTURE / SIMULATED'}

    def process(self, *, session_id: str, turn_id: str, version: int,
                fixture_id: str | None = None, text: str | None = None,
                user_asks_review: bool = False, simulate_failure: bool = False) -> dict:
        with self._lock:
            return self._process_unlocked(session_id=session_id,turn_id=turn_id,version=version,
                        fixture_id=fixture_id,text=text,user_asks_review=user_asks_review,simulate_failure=simulate_failure)

    def _process_unlocked(self, *, session_id,turn_id,version,fixture_id,text,user_asks_review,simulate_failure) -> dict:
        self._prune()
        if type(session_id) is not str or session_id not in self._sessions:
            raise Conflict('UNKNOWN_SESSION')
        s=self._sessions[session_id]
        if not self._integrity_ok(s): raise Conflict('AUDIT_INTEGRITY_FAILED')
        if type(turn_id) is not str or re.fullmatch(r'[A-Za-z0-9_-]{1,64}',turn_id) is None or type(version) is not int:
            raise Conflict('INVALID_TURN_OR_VERSION')
        if type(user_asks_review) is not bool or type(simulate_failure) is not bool:
            raise Conflict('INVALID_CONTROL_FLAGS')
        if (fixture_id is None) == (text is None):
            raise Conflict('EXACTLY_ONE_INPUT_REQUIRED')
        if fixture_id is not None:
            if type(fixture_id) is not str or fixture_id not in FIXTURES:
                raise Conflict('UNKNOWN_FIXTURE')
            fixture=FIXTURES[fixture_id]
            transcript,spans=fixture.transcript,fixture.evidence
        else:
            if type(text) is not str or len(text)>2000:
                raise Conflict('INVALID_TEXT')
            transcript,spans=text,()
        # v4.2: the expected version is part of the retry identity (same class of
        # defect fixed for PAYLOCK in v4.1; the main session path was not swept).
        digest=self._private_digest(repr((version,fixture_id,transcript,user_asks_review,simulate_failure)))
        if turn_id in s.idempotency:
            prior_digest,prior_result=s.idempotency[turn_id]
            if prior_digest != digest: raise Conflict('CONFLICTING_RETRY')
            return deepcopy(prior_result)
        if s.version != version: raise Conflict('STALE_VERSION')
        if fixture_id=='AMBIGUOUS': user_asks_review=True
        status = Status.UNAVAILABLE if simulate_failure else (
            Status.OK if fixture_id is not None else Status.NOT_CONNECTED)
        # User-entered text has no human annotations and no model. It must abstain.
        outcome=decide(transcript,spans,status=status,user_asks_review=user_asks_review)
        s.version+=1
        s.updated=monotonic()
        record={'turn_id':turn_id,'version':s.version,'scenario_id':fixture_id or 'MANUAL_REDACTED',
                'action':outcome.action.value,'reason':outcome.reason,
                'evidence':[{'start':x.start,'end':x.end,'kind':x.kind.value} for x in outcome.evidence],
                'mode':outcome.mode}
        self._append_audit(s,record)
        result={'session_id':s.id,'version':s.version,'turn_id':turn_id,
                'action':outcome.action.value,'message':outcome.message,'reason':outcome.reason,
                'evidence':[{'quote':x.quote,'start':x.start,'end':x.end,'kind':x.kind.value} for x in outcome.evidence],
                'mode':outcome.mode,'verified_model':False,
                'history':deepcopy(s.history),'audit_integrity':'UNSIGNED_LOCAL_HASH_CHAIN',
                'audit_chain_keying':'EPHEMERAL_PROCESS_HMAC_SHA256'}
        s.idempotency[turn_id]=(digest,result)
        return deepcopy(result)
    def process_model(self, *, session_id: str, turn_id: str, version: int, text: str,
                      client: ModelClient | None = None) -> dict:
        """Only operator-configured endpoint; caller cannot forge a model response.

        Network call occurs outside the lock. A stale session rejects the response.
        No raw transcript or full probability vector enters the audit history.
        """
        if type(text) is not str or not text.strip() or len(text)>2000:
            raise Conflict('INVALID_MODEL_TEXT')
        if type(version) is not int or type(turn_id) is not str or re.fullmatch(r'[A-Za-z0-9_-]{1,64}',turn_id) is None:
            raise Conflict('INVALID_TURN_OR_VERSION')
        digest=self._private_digest('MODEL:'+repr((version,text)))
        with self._lock:
            self._prune()
            s=self._sessions.get(session_id)
            if s is None: raise Conflict('UNKNOWN_SESSION')
            if not self._integrity_ok(s): raise Conflict('AUDIT_INTEGRITY_FAILED')
            if turn_id in s.idempotency:
                old,result=s.idempotency[turn_id]
                if old!=digest:raise Conflict('CONFLICTING_RETRY')
                return deepcopy(result)
            if s.version!=version:raise Conflict('STALE_VERSION')
        client=client or ModelClient()
        t=monotonic()
        try:
            raw,latency=client.infer(text)
            outcome=advisory(text,raw)
            outcome['latency_ms']=latency
            outcome['model_id_echo']=getattr(client,'last_model_echo','UNKNOWN')
        except (ModelUnavailable,ContractError,ValueError) as exc:
            outcome={'action':Action.ASK_HUMAN.value,
                     'message':'모델의 검증 가능한 판단이 없습니다. 중요 행동을 멈추고 공식 경로에서 확인하세요.',
                     # v4.2: keep the bounded machine code (e.g. MODEL_ID_MISMATCH);
                     # v4.1 kept only the class name, hiding the real failure cause.
                     'reason':_failure_reason(exc),'evidence':[],
                     'mode':'MODEL_UNAVAILABLE_OR_INVALID / NOT_ATTESTED',
                     'source':'MODEL_UNAVAILABLE_OR_INVALID', 'model_attested':False,
                     'calibration_status':'NOT_ESTABLISHED', 'probs':{},
                     'grounding':'NONE','latency_ms':round((monotonic()-t)*1000,2)}
        with self._lock:
            self._prune()
            s=self._sessions.get(session_id)
            if s is None or not self._integrity_ok(s):raise Conflict('UNKNOWN_OR_INVALID_SESSION')
            if s.version!=version:raise Conflict('STALE_VERSION')
            if turn_id in s.idempotency:raise Conflict('CONCURRENT_RETRY_REQUIRES_REFRESH')
            s.version+=1;s.updated=monotonic()
            record={'turn_id':turn_id,'version':s.version,'scenario_id':'SYNTHETIC_FREE_TEXT',
                    'action':outcome['action'],'reason':outcome['reason'],
                    'mode':outcome['mode'],'model_attested':False,
                    'transcript_hmac_sha256':self._private_digest(text)}
            self._append_audit(s,record)
            result={'session_id':s.id,'version':s.version,'turn_id':turn_id,
                    'history':deepcopy(s.history),'verified_model':False,
                    'audit_integrity':'UNSIGNED_LOCAL_HASH_CHAIN',
                    'audit_chain_keying':'EPHEMERAL_PROCESS_HMAC_SHA256',**outcome}
            s.idempotency[turn_id]=(digest,result)
            return deepcopy(result)

    def acknowledge(self, *, session_id: str, event_id: str, version: int,
                    choice: str = 'PLAN_INDEPENDENT_VERIFICATION') -> dict:
        """Record only an intent in synthetic demo; no real verification performed."""
        with self._lock:
            self._prune()
            if type(session_id) is not str or session_id not in self._sessions:
                raise Conflict('UNKNOWN_SESSION')
            if type(event_id) is not str or re.fullmatch(r'[A-Za-z0-9_-]{1,64}',event_id) is None or type(version) is not int:
                raise Conflict('INVALID_EVENT_OR_VERSION')
            if type(choice) is not str or choice not in ('PLAN_INDEPENDENT_VERIFICATION', 'REQUEST_TRUSTED_HUMAN_HELP'):
                raise Conflict('INVALID_CHOICE')
            s=self._sessions[session_id]
            if not self._integrity_ok(s): raise Conflict('AUDIT_INTEGRITY_FAILED')
            if not s.history: raise Conflict('NO_DECISION_TO_REVIEW')
            key='ACK:'+event_id
            digest=self._private_digest(repr((version,choice)))
            if key in s.idempotency:
                old_hash,old_result=s.idempotency[key]
                if old_hash!=digest:raise Conflict('CONFLICTING_RETRY')
                return deepcopy(old_result)
            if s.version!=version:raise Conflict('STALE_VERSION')
            # The acknowledgement is a plan about the latest evaluated turn,
            # never a free-floating event or an unverified claim of real action.
            if s.history[-1].get('turn_id') != event_id:
                raise Conflict('ACK_NOT_LINKED_TO_LATEST_TURN')
            s.version+=1;s.updated=monotonic()
            record={'event_id':event_id,'version':s.version,'event':'INTENT_ONLY_NOT_VERIFIED',
                    'choice':choice,'linked_turn_id':event_id,'mode':'FIXTURE / SIMULATED'}
            self._append_audit(s,record)
            result={'session_id':s.id,'version':s.version,'recorded_intent':choice,
                    'real_verification_completed':False,'linked_turn_id':event_id,'history':deepcopy(s.history),
                    'mode':'FIXTURE / SIMULATED'}
            s.idempotency[key]=(digest,result)
            return deepcopy(result)

