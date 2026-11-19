"""Opt-in typed decision adapter. No claim of authenticated Zoro inference.

All network responses are UNATTESTED until an operator verifies the model,
checkpoint and server independently. Schema validity is not calibration.
This component only recommends non-destructive human-facing guidance.
"""
from __future__ import annotations
import ipaddress
import http.client
import json
import os
import re
import socket
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from time import monotonic
from .core import Action, Kind, Directness, Status, Evidence, Origin, decide, MESSAGES
from .typed_contract import ContractError, normalize_response
from .context_guard import context_flags, context_conflict, clause_profile, structural_evidence

ACTION_OPTIONS = ['transfer','otp','remote_install','personal_data','link','secrecy','none','unclear']
# v4.5: 'informational' (states or reports a fact without asking the listener to act) is the
# label an on-device classifier needs for notices such as '급여가 입금되었습니다'.
SPEECH_OPTIONS = ['direct_request','reported_or_quoted','negated_or_warning','unclear','informational']
# v4.2: one ordinal label list is both the request criteria and the accepted
# response keys. v4.1 sent ['low','moderate','high','unknown'] but expected
# keys '0'..'3', so any label-keyed reply rejected the whole decision.
RISK_LEVELS = ['none','low','moderate','high']
SPEC = {
    'q_action': {'type':'choice','options':ACTION_OPTIONS},
    'q_speech': {'type':'choice','options':SPEECH_OPTIONS},
    'q_scam': {'type':'noul'},
    'q_claim': {'type':'noul'},
    'q_pressure': {'type':'noul'},
    'q_risk': {'type':'score','options':RISK_LEVELS},
    # v4.5 (team PRD v3.3 'evidence_sufficient'): optional; can only move toward abstention.
    'q_evidence': {'type':'noul'},
}
# Display-only auxiliaries; their absence or malformation must not erase the
# primary speech-act decision. q_scam / q_pressure stay REQUIRED because they
# gate any clearance.
OPTIONAL_QUESTIONS = frozenset({'q_claim','q_risk','q_evidence'})
# Public documents disagree on the fitted calibration temperature
# (trida decision page: 2.19; Hugging Face model card: 1.52, checked 2026-11-01).
# No temperature is applied here; probabilities are shown as returned.
CALIBRATION_TEMPERATURE_STATUS = 'NOT_APPLIED_PUBLIC_SOURCES_CONFLICT_2.19_VS_1.52'
KIND_MAP={'transfer':Kind.TRANSFER,'otp':Kind.OTP,'remote_install':Kind.REMOTE_INSTALL,
          'personal_data':Kind.PERSONAL_DATA,'link':Kind.UNVERIFIED_LINK,
          'secrecy':Kind.SECRECY, 'none':Kind.OTHER,'unclear':Kind.OTHER}
SPEECH_MAP={'direct_request':Directness.DIRECT_REQUEST,
            'reported_or_quoted':Directness.REPORTED_OR_QUOTED,
            'negated_or_warning':Directness.NEGATED_OR_WARNING,
            'unclear':Directness.UNCLEAR,
            'informational':Directness.UNCLEAR}
# A deterministic grounding precondition. It does not assert the meaning of a sentence.
ANCHORS={
 'transfer':('송금','이체','입금','계좌로 보내','자금 이동','돈을 보내','transfer','wire'),
 'otp':('OTP','인증번호','일회용 비밀번호','verification code'),
 'remote_install':('원격제어','원격 앱','팀뷰어','애니데스크','remote access'),
 'personal_data':('주민등록번호','비밀번호','신분증','개인정보','password'),
 'link':('링크','URL','주소를 클릭','link'),
 'secrecy':('비밀','말하지 마','알리지 마','secret'),
}


def questions(state: str) -> dict:
    """No model identifier in the request until operator supplies exact ID."""
    return {'state':state,'questions':{
        'q_action':{'type':'choice','instructions':'Which action, if any, is the addressee being asked to take in the current utterance? Treat quoted and negated phrases separately.','criteria':{
            'transfer':'transfer money','otp':'disclose one-time credential','remote_install':'install or grant remote access','personal_data':'disclose personal data','link':'open link','secrecy':'conceal from others','none':'no requested action','unclear':'unclear'}},
        'q_speech':{'type':'choice','instructions':'Is the apparent action a direct instruction to the listener, a report/quote, a warning/negation, or unclear?','criteria':{
            'direct_request':'speaker directly asks listener to do it','reported_or_quoted':'someone reports or quotes it','negated_or_warning':'speaker warns not to do it','unclear':'insufficient context',
            'informational':'speaker only states or reports information and asks for no action'}},
        'q_scam':{'type':'noul','instructions':'Does the utterance contain features commonly associated with deceptive coercion? Not a real-world probability of fraud.'},
        'q_claim':{'type':'noul','instructions':'Does the speaker CLAIM an institutional identity, without verifying the identity?'},
        'q_pressure':{'type':'noul','instructions':'Does the speaker pressure urgency or secrecy?'},
        'q_risk':{'type':'score','instructions':'Rate advisory attention level from text alone; do not assume real-world criminality.','criteria':RISK_LEVELS},
        'q_evidence':{'type':'noul','instructions':'Can the requested action, its directness and any pressure cues be classified from explicit words in the supplied text? Answer no when context or meaning is insufficient. Evaluate independently of other answers.'},
    }}


def _choose_anchor(text: str, action: str, within: tuple[int,int] | None = None):
    options=ANCHORS.get(action,())
    lo,hi=within if within else (0,len(text))
    hits=[]
    for a in options:
        for m in re.finditer(re.escape(a),text,re.IGNORECASE):
            if lo<=m.start() and m.end()<=hi:
                hits.append((m.start(),m.end(),text[m.start():m.end()]))
                break
    return sorted(hits)[0] if hits else None


def advisory(text: str, raw: dict, *, source: str='MODEL_RESPONSE_UNATTESTED', threshold:float=0.70,
             model_anchor: tuple | None = None) -> dict:
    """No privilege to act outside the browser. No artificial probability calibration."""
    if type(text) is not str or not text.strip() or len(text)>2000:
        raise ContractError('INVALID_TEXT')
    if type(threshold) is not float or not .5<=threshold<=.99:
        raise ContractError('INVALID_THRESHOLD')
    normalized=normalize_response(raw,SPEC,optional=OPTIONAL_QUESTIONS)
    dropped=normalized.pop('_dropped_optional',())
    flags=context_flags(text)
    profile=clause_profile(text)
    a=normalized['q_action']['choice']; sp=normalized['q_speech']['choice']
    p_a=normalized['q_action']['probabilities'][a]
    p_sp=normalized['q_speech']['probabilities'][sp]
    out={'source':source,'model_attested':False,'calibration_status':'NOT_ESTABLISHED',
         'threshold_type':'UNVALIDATED_DEMO_HEURISTIC',
         'probs':{k:v['probabilities'] for k,v in normalized.items()},
         'dropped_optional_questions':list(dropped),
         'calibration_temperature':CALIBRATION_TEMPERATURE_STATUS,
         'guard_scope':'CLAUSE_LOCAL_LEXICAL_V42',
         'selected_action':a,'selected_speech':sp,'action_probability':p_a,'speech_probability':p_sp,
         'threshold':threshold,'grounding':'NO_ACTION_ANCHOR','evidence':[]}
    # The independent contradiction screen has priority over a model's high
    # probability. A missing/negated/quoted meaning cannot be proved by a span.
    contextual_conflict=context_conflict(a,sp,flags,profile)
    if contextual_conflict:
        action,reason=Action.ASK_HUMAN,contextual_conflict
    elif p_a<threshold or p_sp<threshold or a=='unclear' or sp=='unclear':
        action,reason=Action.ASK_HUMAN,'MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS'
    elif a=='none' and (normalized['q_scam']['probabilities']['yes']>=threshold or
                        normalized['q_pressure']['probabilities']['yes']>=threshold and flags.pressure_cue):
        # A strong auxiliary coercion signal cannot be silently cleared by the
        # q_action=none label. This is an abstention, not a fraud determination.
        action,reason=Action.ASK_HUMAN,'CONFLICTING_MODEL_QUESTIONS'
    elif sp=='informational':
        # A statement about an action is not a request for it. Clause-local imperatives were
        # already screened above; lexical pressure plus a coercive auxiliary still blocks clearance.
        if flags.pressure_cue and (normalized['q_scam']['probabilities']['yes']>=threshold or
                                   normalized['q_pressure']['probabilities']['yes']>=threshold):
            action,reason=Action.ASK_HUMAN,'AUX_COERCION_BLOCKS_INFORMATIONAL_CLEARANCE'
        else:
            action,reason=Action.NO_STRONG_SIGNAL,'MODEL_INFORMATIONAL_NOT_REQUEST'
    elif a=='none':
        # The model's "none" is not a factual clearance.
        action,reason=Action.NO_STRONG_SIGNAL,'NO_ACTION_CANDIDATE_NOT_SAFETY_CLEARANCE'
    else:
        # Ground direct requests in a clean (un-negated, un-quoted) clause when one exists.
        clean=[c for c in profile if c.clean_action]
        anchor=None
        if sp=='direct_request':
            for c in clean:
                anchor=_choose_anchor(text,a,(c.start,c.end))
                if anchor: break
        anchor=anchor or _choose_anchor(text,a)
        anchor_origin='MODEL_SCHEMA_CHECKED'
        if not anchor and model_anchor is not None:
            # v4.5: an attribution span supplied by the on-device model (occlusion of its own
            # action head). Accepted only if it is a real, non-empty substring at that offset.
            try:
                ms,me,mq=model_anchor
                if type(ms) is int and type(me) is int and 0<=ms<me<=len(text) and text[ms:me]==mq and mq.strip():
                    anchor=(ms,me,mq); anchor_origin='MODEL_ATTRIBUTION_SPAN'
            except (TypeError,ValueError):
                anchor=None
        aux_coercion=(flags.pressure_cue and
                      (normalized['q_scam']['probabilities']['yes']>=threshold or
                       normalized['q_pressure']['probabilities']['yes']>=threshold))
        if not anchor:
            action,reason=Action.ASK_HUMAN,'NO_GROUNDED_ACTION_ANCHOR'
        else:
            start,end,quote=anchor
            out['grounding']=('LEXICAL_ANCHOR_NOT_SEMANTIC_VERIFICATION' if anchor_origin=='MODEL_SCHEMA_CHECKED'
                              else 'MODEL_ATTRIBUTION_SPAN_NOT_SEMANTIC_PROOF')
            out['evidence']=[{'start':start,'end':end,'quote':quote,'kind':KIND_MAP[a].value,
                               'directness':SPEECH_MAP[sp].value,'origin':anchor_origin}]
            if sp=='negated_or_warning' and aux_coercion:
                # A warning label cannot clear text that also carries lexical
                # pressure/secrecy cues the model itself rates as coercive.
                action,reason=Action.ASK_HUMAN,'AUX_COERCION_BLOCKS_WARNING_CLEARANCE'
            elif sp=='negated_or_warning':
                action,reason=Action.NO_STRONG_SIGNAL,'MODEL_WARNING_NOT_REQUEST'
            elif sp=='reported_or_quoted':
                action,reason=Action.CAUTION,'MODEL_REPORTED_REQUEST'
            elif a in ('transfer','otp','remote_install','personal_data'):
                action,reason=Action.PAUSE_AND_VERIFY,'MODEL_DIRECT_ACTION_ADVISORY'
            else:
                action,reason=Action.CAUTION,'MODEL_DIRECT_CAUTION_ADVISORY'
    # v4.5 / PRD v3.3 rule 6: a model that says its own evidence is insufficient cannot clear or
    # merely caution. A grounded direct high-risk request (PAUSE_AND_VERIFY) keeps priority (rule 2).
    if ('q_evidence' in normalized and normalized['q_evidence']['probabilities']['no']>=threshold
            and action in (Action.NO_STRONG_SIGNAL, Action.CAUTION)):
        action,reason=Action.ASK_HUMAN,'MODEL_EVIDENCE_INSUFFICIENT'
    out.update(action=action.value,reason=reason,message=MESSAGES[action],
               mode=source+' / NOT_ATTESTED')
    return out


class ModelUnavailable(RuntimeError): pass

class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to an already validated public IP while retaining TLS SNI/host verification.

    This avoids the preflight-DNS/connection-DNS TOCTOU gap in urllib. It is not
    endpoint identity attestation, certificate pinning, or a production security audit.
    """
    def __init__(self, hostname: str, verified_ip: str, port: int, timeout: float=4.0):
        self.verified_ip = verified_ip
        super().__init__(hostname, port, timeout=timeout, context=ssl.create_default_context())

    def connect(self):
        sock = socket.create_connection((self.verified_ip, self.port), self.timeout, self.source_address)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class ModelClient:
    """Operator-only config; no caller-provided endpoints and no redirects."""
    def __init__(self, endpoint=None, model_id=None, enabled=None):
        self.endpoint=endpoint if endpoint is not None else os.environ.get('DMSG_SYSTEMONE_ENDPOINT','')
        self.model_id=model_id if model_id is not None else os.environ.get('DMSG_MODEL_ID','')
        self.enabled=enabled if enabled is not None else os.environ.get('DMSG_MODEL_ENABLED')=='1'
        self.mode=os.environ.get('DMSG_MODEL_SOURCE','REMOTE_UNATTESTED')
        self._pinned_ip = None  # set only after full remote DNS address validation
        self.last_model_echo = 'NOT_CALLED'

    @staticmethod
    def _timeout_or_none():
        raw=os.environ.get('DMSG_MODEL_TIMEOUT_S','4.0')
        try:
            value=float(raw)
        except ValueError:
            return None
        return value if 0.5<=value<=60.0 else None

    def timeout(self) -> float:
        # A 4-5B BF16 prefill on a venue laptop can exceed the v4.1 fixed 4 s.
        value=self._timeout_or_none()
        if value is None:
            raise ModelUnavailable('INVALID_TIMEOUT_CONFIG')
        return value

    def status(self) -> dict:
        host=urllib.parse.urlsplit(self.endpoint).hostname if self.endpoint else None
        remote=bool(host and host not in ('localhost','127.0.0.1'))
        consent_ok=not remote or os.environ.get('DMSG_REMOTE_TEXT_CONSENT')=='1'
        allowlist={name.strip().lower() for name in os.environ.get('DMSG_REMOTE_HOST_ALLOWLIST','').split(',') if name.strip()}
        allowed_host=not remote or host.lower() in allowlist
        return {'configured':bool(self.enabled and self.endpoint and self.model_id and consent_ok and allowed_host),
                'remote_text_transfer':remote,'remote_consent':consent_ok,'remote_host_allowlisted':allowed_host,
                'mode':'REMOTE_RESPONSE_UNATTESTED' if self.enabled else 'DISABLED',
                'verified_model':False,'calibrated':False,'reasoning_available':False,
                'send_model_field':os.environ.get('DMSG_SEND_MODEL_FIELD')=='1',
                'require_model_echo':os.environ.get('DMSG_REQUIRE_MODEL_ECHO')=='1',
                'timeout_s':self._timeout_or_none(),
                'calibration_temperature':CALIBRATION_TEMPERATURE_STATUS,
                'endpoint_host':urllib.parse.urlsplit(self.endpoint).hostname if self.endpoint else None}

    def _check_target(self):
        self._pinned_ip = None
        u=urllib.parse.urlsplit(self.endpoint)
        if not self.enabled or not self.model_id:
            raise ModelUnavailable('MODEL_NOT_CONFIGURED')
        if u.username or u.password or u.query or u.fragment or u.path.rstrip('/')!='/v1/systemone':
            raise ModelUnavailable('INVALID_MODEL_ENDPOINT')
        if u.scheme not in ('http','https') or not u.hostname:
            raise ModelUnavailable('INVALID_MODEL_ENDPOINT')
        if u.scheme=='http' and u.hostname not in ('localhost','127.0.0.1'):
            raise ModelUnavailable('HTTPS_REQUIRED')
        # No outbound requests to arbitrary LAN, metadata, or private endpoints.
        if u.hostname not in ('localhost','127.0.0.1'):
            if os.environ.get('DMSG_REMOTE_TEXT_CONSENT') != '1':
                raise ModelUnavailable('REMOTE_TEXT_TRANSFER_NOT_CONSENTED')
            allowed={name.strip().lower() for name in os.environ.get('DMSG_REMOTE_HOST_ALLOWLIST','').split(',') if name.strip()}
            if u.hostname.lower() not in allowed:
                raise ModelUnavailable('REMOTE_HOST_NOT_ALLOWLISTED')
            try:
                addr=socket.getaddrinfo(u.hostname,u.port or 443,type=socket.SOCK_STREAM)
                if not addr or any(not ipaddress.ip_address(x[4][0]).is_global for x in addr):
                    raise ModelUnavailable('NON_PUBLIC_ENDPOINT_IP')
                self._pinned_ip = addr[0][4][0]
            except OSError:
                raise ModelUnavailable('DNS_FAILURE') from None
        return u

    def infer(self,text: str, *, question_payload:dict|None=None) -> tuple[dict,float]:
        self._check_target()
        if question_payload is None:
            payload=questions(text)
        else:
            if (type(question_payload) is not dict or set(question_payload)!={'state','questions'}
                or question_payload.get('state')!=text or type(question_payload['questions']) is not dict
                or not question_payload['questions']):
                raise ModelUnavailable('INVALID_QUESTION_PAYLOAD')
            payload=dict(question_payload)
        # The public kev request example has no 'model' field; sending one is
        # opt-in so an unknown-field-strict server cannot reject every call.
        if os.environ.get('DMSG_SEND_MODEL_FIELD')=='1':
            payload['model']=self.model_id
        timeout=self.timeout()
        data=json.dumps(payload,ensure_ascii=False).encode('utf8')
        if len(data)>30000:raise ModelUnavailable('REQUEST_TOO_LARGE')
        headers={'Content-Type':'application/json'}
        key=os.environ.get('DMSG_MODEL_API_KEY','')
        if key:headers['Authorization']='Bearer '+key
        request=urllib.request.Request(self.endpoint,data=data,headers=headers,method='POST')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,request,fp,code,msg,headers,newurl):return None
        # No environment proxy; pin all remote TLS traffic to a validated public
        # IP for the *actual connection* so a second DNS resolution cannot redirect
        # to loopback, link-local metadata, or an internal address.
        start=monotonic()
        try:
            if self._pinned_ip is not None:
                u=urllib.parse.urlsplit(self.endpoint)
                conn=_PinnedHTTPSConnection(u.hostname,self._pinned_ip,u.port or 443,timeout)
                try:
                    conn.request('POST',u.path,body=data,headers=headers)
                    response=conn.getresponse()
                    if response.status!=200:raise ModelUnavailable('HTTP_STATUS_NOT_OK')
                    if response.getheader('Content-Type','').split(';')[0].strip().lower()!='application/json':
                        raise ModelUnavailable('UNEXPECTED_MODEL_CONTENT_TYPE')
                    raw=response.read(120001)
                    if len(raw)>120000:raise ModelUnavailable('RESPONSE_TOO_LARGE')
                finally:
                    conn.close()
            else:
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
                with opener.open(request,timeout=timeout) as response:
                    if response.status!=200:raise ModelUnavailable('HTTP_STATUS_NOT_OK')
                    if response.headers.get('Content-Type','').split(';')[0].strip().lower() != 'application/json':
                        raise ModelUnavailable('UNEXPECTED_MODEL_CONTENT_TYPE')
                    raw=response.read(120001)
                    if len(raw)>120000:raise ModelUnavailable('RESPONSE_TOO_LARGE')
        except (OSError,ValueError,TimeoutError,ssl.SSLError) as exc:
            raise ModelUnavailable('MODEL_TRANSPORT_ERROR_'+type(exc).__name__) from None
        try:
            def reject_duplicate_keys(pairs):
                obj={}
                for key,val in pairs:
                    if key in obj: raise ValueError('DUPLICATE_MODEL_RESPONSE_KEY')
                    obj[key]=val
                return obj
            def reject_constant(name):
                # RFC 8259 JSON only; NaN/Infinity literals are rejected exactly like JS JSON.parse.
                raise ValueError('NON_STANDARD_JSON_CONSTANT')
            value=json.loads(raw,object_pairs_hook=reject_duplicate_keys,parse_constant=reject_constant)
            if type(value) is not dict:
                raise ModelUnavailable('INVALID_RESPONSE_JSON')
            # v4.1 required an echoed 'model' equal to the configured ID. kev's
            # documented response shape does not show such a field, so a
            # conforming server failed 100% of calls. An echo was never
            # authentication; now: present+different -> reject, absent -> record.
            if 'model' in value:
                if value['model']!=self.model_id:
                    raise ModelUnavailable('MODEL_ID_MISMATCH')
                self.last_model_echo='MATCH_UNAUTHENTICATED'
            elif os.environ.get('DMSG_REQUIRE_MODEL_ECHO')=='1':
                raise ModelUnavailable('MODEL_ID_ECHO_REQUIRED')
            else:
                self.last_model_echo='ABSENT'
            return value,round((monotonic()-start)*1000,2)
        except (UnicodeError,ValueError):
            raise ModelUnavailable('INVALID_RESPONSE_JSON') from None


# LAYER V4.6 / RISK-INDICATOR POLICY (multi-label semantic signals; never downgrades)
# NO_EXPLICIT_ACTION is not SAFE, INFORMATIONAL is not NON_SUSPICIOUS, a confident label is not TRUE and
# no keyword match is not NO_RISK. A model-raised indicator only moves the advice toward caution, and only
# a grounded one (a structural fact or a validated model attribution span in the original text) can
# produce CAUTION / PAUSE; an ungrounded one produces ASK_HUMAN.
INDICATORS = ('OFF_PLATFORM_CONTACT', 'UNVERIFIED_IDENTITY', 'URGENCY_OR_PRESSURE', 'FINANCIAL_INDUCEMENT', 'CREDENTIAL_REQUEST',
              'ACCOUNT_CHANGE_REQUEST', 'IMPERSONATION_SIGNAL', 'MALICIOUS_LINK_SUSPICION', 'UNWANTED_SOLICITATION')
PRIMARY_INDICATORS = frozenset({'OFF_PLATFORM_CONTACT', 'FINANCIAL_INDUCEMENT', 'IMPERSONATION_SIGNAL', 'MALICIOUS_LINK_SUSPICION', 'UNWANTED_SOLICITATION'})
HIGH_SEVERITY_INDICATORS = frozenset({'CREDENTIAL_REQUEST', 'ACCOUNT_CHANGE_REQUEST'})
STRUCTURAL_GROUNDS = {'OFF_PLATFORM_CONTACT': ('MESSENGER_HANDOFF', 'MESSENGER_HANDLE'), 'MALICIOUS_LINK_SUSPICION': ('URL',),
                      'ACCOUNT_CHANGE_REQUEST': ('ACCOUNT_CHANGE_PHRASE',), 'FINANCIAL_INDUCEMENT': ('MONEY_AMOUNT',),
                      'UNVERIFIED_IDENTITY': ('OVERSEAS_SENDER_TAG',)}
WARNING_CLEARANCES = frozenset({'MODEL_WARNING_NOT_REQUEST'})
# An indicator raised by the model alone (no structural fact) must be this confident to force an abstention.
# Chosen on development data (v4.5 dev set + generated calib), not on a locked set.
UNGROUNDED_MIN_PROBABILITY = 0.8
_ACTIONS = tuple(a.value for a in Action)


def _valid_span(text, sp):
    try:
        s, e, q = sp
    except (TypeError, ValueError):
        return None
    if type(s) is int and type(e) is int and type(q) is str and 0 <= s < e <= len(text) and text[s:e] == q and q.strip():
        return (s, e, q)
    return None


def indicator_advisory(text: str, base: dict, indicator_probs: dict, *, thresholds: dict | None = None,
                       model_spans: dict | None = None) -> dict:
    if type(text) is not str or not text.strip() or len(text) > 2000:
        raise ContractError('INVALID_TEXT')
    if type(base) is not dict or base.get('action') not in _ACTIONS or type(base.get('reason')) is not str:
        raise ContractError('INVALID_BASE_ADVISORY')
    if type(indicator_probs) is not dict or not set(indicator_probs) <= set(INDICATORS):
        raise ContractError('INVALID_INDICATORS')
    for v in indicator_probs.values():
        if type(v) not in (int, float) or type(v) is bool or v != v or not 0.0 <= v <= 1.0:
            raise ContractError('INVALID_INDICATORS')
    thr = {k: 0.5 for k in INDICATORS}
    if thresholds is not None:
        if type(thresholds) is not dict or not set(thresholds) <= set(INDICATORS):
            raise ContractError('INVALID_THRESHOLD')
        for k, v in thresholds.items():
            if type(v) is not float or not 0.05 <= v <= 0.95:
                raise ContractError('INVALID_THRESHOLD')
            thr[k] = v
    spans = {}
    if type(model_spans) is dict:
        for k, sp in model_spans.items():
            if k in INDICATORS:
                v = _valid_span(text, sp)
                if v: spans[k] = v
    structural = structural_evidence(text)
    fired = [k for k in INDICATORS if k in indicator_probs and indicator_probs[k] >= thr[k]]
    report = []
    for k in fired:
        ev = [dict(e, origin='STRUCTURAL') for e in structural if e['kind'] in STRUCTURAL_GROUNDS.get(k, ())]
        by = 'STRUCTURAL' if ev else 'NONE'
        if k in spans:
            s0, e0, q = spans[k]; ev.append({'kind': 'MODEL_ATTRIBUTION', 'start': s0, 'end': e0, 'quote': q, 'origin': 'MODEL_ATTRIBUTION_SPAN'})
            if by == 'NONE': by = 'MODEL_ONLY'
        report.append({'label': k, 'probability': float(indicator_probs[k]), 'threshold': thr[k], 'grounded': by == 'STRUCTURAL',
                       'grounded_by': by, 'evidence': ev})
    # Only a structural fact in the original text grounds an escalation; a model attribution span explains
    # the label but cannot by itself justify CAUTION/PAUSE (it can only produce an abstention).
    structural_ok = {r['label'] for r in report if r['grounded']}
    strong_model_only = {r['label'] for r in report if not r['grounded'] and r['probability'] >= max(r['threshold'], UNGROUNDED_MIN_PROBABILITY)}
    speech = base.get('selected_speech')
    warning = base['reason'] in WARNING_CLEARANCES or speech == 'negated_or_warning'
    action, reason = base['action'], base['reason']
    if action != Action.PAUSE_AND_VERIFY.value and not warning:
        if structural_ok & HIGH_SEVERITY_INDICATORS and speech == 'direct_request':
            action, reason = Action.PAUSE_AND_VERIFY.value, 'GROUNDED_HIGH_SEVERITY_INDICATOR'
        elif action == Action.NO_STRONG_SIGNAL.value:
            if structural_ok & (PRIMARY_INDICATORS | HIGH_SEVERITY_INDICATORS):
                action, reason = Action.CAUTION.value, 'RISK_INDICATORS_WITHOUT_EXPLICIT_ACTION'
            elif strong_model_only & (PRIMARY_INDICATORS | HIGH_SEVERITY_INDICATORS):
                action, reason = Action.ASK_HUMAN.value, 'UNGROUNDED_RISK_INDICATOR'
    out = dict(base)
    out.update(base_action=base['action'], base_reason=base['reason'], action=action, reason=reason,
               message=MESSAGES[Action(action)], indicators=report, structural_evidence=[dict(e) for e in structural],
               sender_identity='UNVERIFIED', indicator_policy='V46_NEVER_DOWNGRADES')
    return out


# LAYER V4.7 — DECISION-RELEVANT ARBITER (DRA)
# Why: team run 2026-11-02 (v4.5 code, real Zoro-1): 43/48 and 19/25 abstentions; every benign item abstained.
# advisory() treats every uncertainty and every lexical disagreement as a veto. DRA keeps advisory() unchanged
# and adds a separate decision rule:
#  1. merge options that lead to the same guidance before judging confidence
#     (q_action=none decides NO_STRONG_SIGNAL whatever q_speech says; 'none + direct_request' is a request for a
#     harmless act, not a contradiction);
#  2. treat lexical cues as evidence that reweights the model distribution, not as a veto;
#  3. pick the guidance with the lowest expected cost, where ASK_HUMAN is an output with its own cost
#     (a human check is not free for a benign message, and is weaker than a pause for a direct high-risk request).
# The cost table is a design choice fixed before evaluation (protocol in internal/evidence/v47/), not a fitted
# or validated quantity. DRA never acts; it only chooses advisory text.
DRA_VERSION = 'dra/1.2'
DRA_ACTION_CLASS = {'transfer': 'HIGH', 'otp': 'HIGH', 'remote_install': 'HIGH', 'personal_data': 'HIGH',
                    'link': 'MID', 'secrecy': 'MID', 'none': 'NONE', 'unclear': 'UNK'}
DRA_SPEECH_CLASS = {'direct_request': 'DIRECT', 'reported_or_quoted': 'REPORT', 'negated_or_warning': 'CLEAR',
                    'informational': 'CLEAR', 'unclear': 'UNK'}
DRA_TRUTHS = ('NO_STRONG_SIGNAL', 'CAUTION', 'PAUSE_AND_VERIFY')
DRA_OUTPUTS = ('NO_STRONG_SIGNAL', 'CAUTION', 'ASK_HUMAN', 'PAUSE_AND_VERIFY')
# cost[output] = (truth NSS, truth CAUTION, truth PAUSE, truth UNKNOWN)
# Fixed 2026-11-02 before any v4.7 evaluation run; rationale in docs/24_V47_ABSTENTION_ANALYSIS_KO.md.
DRA_COSTS = {
    'NO_STRONG_SIGNAL': (0.0, 3.0, 10.0, 5.0),
    'CAUTION':          (1.0, 0.0, 4.0, 3.0),
    'ASK_HUMAN':        (2.0, 1.0, 3.0, 0.5),
    'PAUSE_AND_VERIFY': (3.0, 1.0, 0.0, 3.0),
}
# dra/1.2: the v4.6 structural evidence (independent of the model) also grounds an action
DRA_STRUCTURAL_GROUNDS = {'transfer': ('MONEY_AMOUNT', 'ACCOUNT_CHANGE_PHRASE'), 'link': ('URL',)}
DRA_UNGROUNDED_DISCOUNT = 0.25     # likelihood multiplier for an action with no lexical anchor and no model span
DRA_IMPERATIVE_BOOST = 4.0         # direct-request multiplier when a clean imperative clause carries an action term
DRA_WARNING_BOOST = 2.0            # clearing multiplier when every action clause carries a warning/report cue


def _dra_truth(ac, sc):
    if ac == 'NONE': return 'NO_STRONG_SIGNAL'
    if ac == 'UNK' or sc == 'UNK': return 'UNKNOWN'
    if sc == 'CLEAR': return 'NO_STRONG_SIGNAL'
    if sc == 'REPORT': return 'CAUTION'
    return 'PAUSE_AND_VERIFY' if ac == 'HIGH' else 'CAUTION'


def _dra_norm(d, keys):
    s = 0.0
    for k in keys: s += d[k]
    return {k: (d[k] / s if s > 0 else 0.0) for k in keys}


def decision_relevant_advisory(text: str, raw: dict, *, source: str = 'MODEL_RESPONSE_UNATTESTED',
                               model_anchor: tuple | None = None, costs: dict | None = None) -> dict:
    if type(text) is not str or not text.strip() or len(text) > 2000:
        raise ContractError('INVALID_TEXT')
    C = DRA_COSTS if costs is None else costs
    if type(C) is not dict or set(C) != set(DRA_OUTPUTS) or any(
            type(v) is not tuple or len(v) != 4 or any(type(x) is not float or x < 0 for x in v) for v in C.values()):
        raise ContractError('INVALID_COSTS')
    normalized = normalize_response(raw, SPEC, optional=OPTIONAL_QUESTIONS)
    normalized.pop('_dropped_optional', None)
    flags = context_flags(text); profile = clause_profile(text)
    pa = dict(normalized['q_action']['probabilities']); ps = dict(normalized['q_speech']['probabilities'])
    trace = []
    # (2a) grounding: an action the text never names (no lexical anchor, no model span) is down-weighted
    span_ok = False
    if model_anchor is not None:
        try:
            ms, me, mq = model_anchor
            span_ok = type(ms) is int and type(me) is int and 0 <= ms < me <= len(text) and text[ms:me] == mq and bool(mq.strip())
        except (TypeError, ValueError):
            span_ok = False
    top_action = max(ACTION_OPTIONS, key=lambda k: (pa[k], -ACTION_OPTIONS.index(k)))
    anchors = {}
    structural = structural_evidence(text)
    for a in ACTION_OPTIONS:
        if DRA_ACTION_CLASS[a] in ('HIGH', 'MID'):
            anchors[a] = _choose_anchor(text, a)
            if anchors[a] is None:
                st = [e for e in structural if e['kind'] in DRA_STRUCTURAL_GROUNDS.get(a, ())]
                if st: anchors[a] = (st[0]['start'], st[0]['end'], st[0]['quote'])
            # dra/1.1: the model's own attribution span is not independent evidence, so it no longer
            # exempts an action from the discount (same principle as the v4.6 indicator policy)
            if anchors[a] is None:
                pa[a] = pa[a] * DRA_UNGROUNDED_DISCOUNT; trace.append('UNGROUNDED_' + a.upper())
    pa = _dra_norm(pa, ACTION_OPTIONS)
    # (2b) clause evidence reweights speech; it does not veto
    acts = [c for c in profile if c.flags.action_mentioned]
    imperative = [c for c in acts if c.clean_imperative]
    if imperative:
        ps['direct_request'] = ps['direct_request'] * DRA_IMPERATIVE_BOOST; trace.append('CLEAN_IMPERATIVE_ACTION_CLAUSE')
    elif acts and all(c.flags.warning_cue or c.flags.report_cue for c in acts):
        for k in ('negated_or_warning', 'reported_or_quoted'):
            ps[k] = ps[k] * DRA_WARNING_BOOST
        trace.append('ALL_ACTION_CLAUSES_WARNED_OR_REPORTED')
    ps = _dra_norm(ps, SPEECH_OPTIONS)
    # (1) joint guidance distribution (independence of the two questions is an approximation)
    q = {'NO_STRONG_SIGNAL': 0.0, 'CAUTION': 0.0, 'PAUSE_AND_VERIFY': 0.0, 'UNKNOWN': 0.0}
    for a in ACTION_OPTIONS:
        ac = DRA_ACTION_CLASS[a]
        if ac == 'NONE' or ac == 'UNK':
            q[_dra_truth(ac, 'DIRECT')] += pa[a]
            continue
        for s in SPEECH_OPTIONS:
            q[_dra_truth(ac, DRA_SPEECH_CLASS[s])] += pa[a] * ps[s]
    # auxiliary coercion and self-reported evidence gaps move clearing mass to UNKNOWN (never the other way)
    scam = normalized['q_scam']['probabilities']['yes']; press = normalized['q_pressure']['probabilities']['yes']
    if flags.pressure_cue and max(scam, press) >= 0.7:
        moved = q['NO_STRONG_SIGNAL'] * 0.5; q['NO_STRONG_SIGNAL'] -= moved; q['UNKNOWN'] += moved; trace.append('AUX_COERCION_WITH_PRESSURE_CUE')
    if 'q_evidence' in normalized:
        ev_no = normalized['q_evidence']['probabilities']['no']
        moved = q['NO_STRONG_SIGNAL'] * ev_no * 0.5; q['NO_STRONG_SIGNAL'] -= moved; q['UNKNOWN'] += moved
        if ev_no >= 0.5: trace.append('MODEL_EVIDENCE_DOUBT')
    # (3) expected cost
    order = ('NO_STRONG_SIGNAL', 'CAUTION', 'PAUSE_AND_VERIFY', 'UNKNOWN')
    exp = {}
    for o in DRA_OUTPUTS:
        acc = 0.0
        for i, t in enumerate(order): acc += q[t] * C[o][i]
        exp[o] = acc
    protect = {'NO_STRONG_SIGNAL': 0, 'CAUTION': 1, 'ASK_HUMAN': 2, 'PAUSE_AND_VERIFY': 3}
    def _cmp(x, y):
        d = exp[x] - exp[y]
        if abs(d) > 1e-9: return -1 if d < 0 else 1
        return protect[y] - protect[x]           # near-tie: the more protective output wins
    import functools
    ranked = sorted(DRA_OUTPUTS, key=functools.cmp_to_key(_cmp))
    choice = ranked[0]
    evidence, grounding = [], 'NO_ACTION_ANCHOR'
    if choice in ('PAUSE_AND_VERIFY', 'CAUTION'):
        cand = [a for a in ACTION_OPTIONS if DRA_ACTION_CLASS[a] in (('HIGH',) if choice == 'PAUSE_AND_VERIFY' else ('HIGH', 'MID'))]
        cand.sort(key=lambda a: (-pa[a], ACTION_OPTIONS.index(a)))
        for a in cand:
            anc = anchors.get(a)
            origin = 'MODEL_SCHEMA_CHECKED'
            if anc is None and span_ok and a == top_action and choice == 'CAUTION':
                anc = tuple(model_anchor); origin = 'MODEL_ATTRIBUTION_SPAN'   # a model span may explain a caution, never a pause
            if anc is not None:
                sp_top = max(SPEECH_OPTIONS, key=lambda k: (ps[k], -SPEECH_OPTIONS.index(k)))
                evidence = [{'start': anc[0], 'end': anc[1], 'quote': anc[2], 'kind': KIND_MAP[a].value,
                             'directness': SPEECH_MAP[sp_top].value, 'origin': origin}]
                grounding = 'LEXICAL_ANCHOR_NOT_SEMANTIC_VERIFICATION' if origin == 'MODEL_SCHEMA_CHECKED' else 'MODEL_ATTRIBUTION_SPAN_NOT_SEMANTIC_PROOF'
                break
        if not evidence and choice == 'PAUSE_AND_VERIFY':
            # a pause must point at the text; without an anchor take the next best non-pause output
            choice = [o for o in ranked if o != 'PAUSE_AND_VERIFY'][0]; trace.append('PAUSE_WITHOUT_ANCHOR_DEMOTED')
    reason = {'NO_STRONG_SIGNAL': 'DRA_MIN_EXPECTED_COST_CLEAR', 'CAUTION': 'DRA_MIN_EXPECTED_COST_CAUTION',
              'ASK_HUMAN': 'DRA_DECISION_RELEVANT_UNCERTAINTY', 'PAUSE_AND_VERIFY': 'DRA_MIN_EXPECTED_COST_PAUSE'}[choice]
    return {'source': source, 'model_attested': False, 'arbiter': DRA_VERSION, 'cost_table': 'DESIGN_CHOICE_NOT_VALIDATED',
            'action': choice, 'reason': reason, 'message': MESSAGES[Action(choice)], 'mode': source + ' / NOT_ATTESTED',
            'guidance_distribution': dict(q), 'expected_cost': dict(exp),
            'margin': exp[ranked[1]] - exp[ranked[0]], 'trace': trace, 'evidence': evidence, 'grounding': grounding,
            'selected_action': top_action,
            'selected_speech': max(SPEECH_OPTIONS, key=lambda k: (ps[k], -SPEECH_OPTIONS.index(k)))}


def abstention_cause(text: str, raw: dict, threshold: float = 0.70) -> dict:
    """Explain why advisory() abstained: the model, or the gate. Used by tools/zoro/abstention_audit.py."""
    base = advisory(text, raw, threshold=threshold)
    if base['action'] != Action.ASK_HUMAN.value:
        return {'abstained': False, 'cause': None, 'base_reason': base['reason']}
    n = normalize_response(raw, SPEC, optional=OPTIONAL_QUESTIONS)
    pa = n['q_action']['probabilities']; ps = n['q_speech']['probabilities']
    a = n['q_action']['choice']; r = base['reason']
    cls_mass = {}
    for k, v in pa.items(): cls_mass[DRA_ACTION_CLASS[k]] = cls_mass.get(DRA_ACTION_CLASS[k], 0.0) + v
    if r == 'NONE_DIRECT_REQUEST_CONFLICT': cause = 'GATE_ONTOLOGY_GAP_HARMLESS_REQUEST'
    elif r in ('MODEL_NONE_BUT_ACTION_TERMS_PRESENT', 'DIRECT_REQUEST_CONTRADICTS_CONTEXT', 'UNSUPPORTED_WARNING_LABEL',
               'UNSUPPORTED_QUOTATION_LABEL', 'WARNING_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE',
               'INFORMATIONAL_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE', 'REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE'):
        cause = 'GATE_LEXICAL_VETO'
    elif r == 'MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS':
        if a == 'none' and pa['none'] >= threshold: cause = 'GATE_DECISION_IRRELEVANT_SPEECH_THRESHOLD'
        elif max(cls_mass.get('HIGH', 0.0), cls_mass.get('MID', 0.0), cls_mass.get('NONE', 0.0)) >= threshold and pa[a] < threshold:
            cause = 'GATE_SPLIT_MASS_SAME_DECISION_CLASS'
        elif a == 'unclear' or n['q_speech']['choice'] == 'unclear': cause = 'MODEL_SAYS_UNCLEAR'
        else: cause = 'MODEL_LOW_CONFIDENCE'
    elif r == 'MODEL_EVIDENCE_INSUFFICIENT': cause = 'MODEL_SELF_REPORTED_INSUFFICIENT_EVIDENCE'
    elif r == 'NO_GROUNDED_ACTION_ANCHOR': cause = 'GATE_NO_LEXICAL_ANCHOR'
    elif r in ('CONFLICTING_MODEL_QUESTIONS', 'AUX_COERCION_BLOCKS_INFORMATIONAL_CLEARANCE', 'AUX_COERCION_BLOCKS_WARNING_CLEARANCE'):
        cause = 'MODEL_INTERNAL_DISAGREEMENT'
    else: cause = 'OTHER:' + r
    return {'abstained': True, 'cause': cause, 'cause_side': 'GATE' if cause.startswith('GATE_') else 'MODEL', 'base_reason': r,
            'top_action': a, 'p_action': round(pa[a], 6), 'top_speech': n['q_speech']['choice'],
            'p_speech': round(ps[n['q_speech']['choice']], 6), 'class_mass': {k: round(v, 6) for k, v in sorted(cls_mass.items())}}


def retemper(raw: dict, t_from: float, t_to: float) -> dict:
    """Exact re-tempering of softmax outputs: p' ∝ p^(t_from/t_to). For offline sensitivity analysis only."""
    if not (type(t_from) is float and type(t_to) is float and t_from > 0 and t_to > 0):
        raise ContractError('INVALID_TEMPERATURE')
    out = json.loads(json.dumps(raw)); e = t_from / t_to
    ans = out.get('answers', out)
    for q in ans.values():
        if isinstance(q, dict) and isinstance(q.get('probabilities'), dict):
            p = {k: (float(v) ** e if float(v) > 0 else 0.0) for k, v in q['probabilities'].items()}
            s = sum(p.values()) or 1.0
            q['probabilities'] = {k: v / s for k, v in p.items()}
    return out
