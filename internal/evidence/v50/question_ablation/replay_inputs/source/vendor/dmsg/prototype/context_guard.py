"""Conservative speech-act counterexample guard for untrusted model responses.

This is a lexical contradiction detector, NOT a Korean language parser or a
fraud classifier. If a model label conflicts with an overt counterexample,
ABSTAIN rather than treating either text or model as semantically verified.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

# Prevent a high model probability from silently converting explicit requests
# into a declaration of safety, or a quotation into a direct instruction.
ACTION_TOKENS = (
    '송금', '이체', '입금', '계좌', '인증번호', 'otp', '비밀번호', '주민등록번호',
    '신분증', '원격제어', '원격 앱', '팀뷰어', '애니데스크', '링크', 'url',
    '돈을 보내', '자금 이동', 'transfer', 'wire', 'password', 'verification code',
    'remote access', 'link',
)
WARNING_PATTERNS = (
    r'(?:하지|주지|보내지|누르지|알려주지|설치하지|전송하지|입금하지|이체하지)\s*마',
    r'(?:해서는|하면|해선)\s*안\s*(?:됩니다|돼|된다)',
    r'(?:절대\s+)?(?:송금|이체|입금|인증번호|원격제어).*?(?:금지|하지\s*마|안\s*됩니다)',
    r'\b(?:never|do not|don\x27t|must not|should not)\b',
    r'금지|경고|주의하세요|피싱\s*예방',
)
REPORT_PATTERNS = (
    r'라고\s*(?:했|말했|들었|하더|전했)',
    r'라는\s*(?:말|문자|지시|요청|메시지|표현)',
    r'라고\s*하면|말하(?:는|라고|면서)|인용|교육\s*자료|예시|신고',
    r'\b(?:quoted|reported|said to|told me|example|training|warning)\b',
)
# These verbs are ambiguous and only supply a weak counterexample to the
# model's "warning" claim, never a reliable direct-request classification.
PRESSURE_PATTERNS = (
    r'지금\s*(?:바로|당장)|즉시|오늘\s*중|시간이\s*없|긴급|서둘러|알리면\s*안\s*돼|남에게\s*말하지|\b(?:urgent|immediately|right now|keep it secret)\b',
)
REQUEST_CUES = (
    r'(?:하세요|해\s*주세요|해줘|보내세요|알려주세요|입력하세요|설치하세요|클릭하세요)',
    r'\b(?:please|send|install|enter|click|wire|transfer)\b',
)

@dataclass(frozen=True)
class ContextFlags:
    action_mentioned: bool
    warning_cue: bool
    report_cue: bool
    request_cue: bool
    pressure_cue: bool


# LAYER CLAUSE-SCOPE (v4.2)
# Secrecy imperatives ("가족에게 말하지 마세요") are coercion cues, not warnings.
# The v4.1 regex '(?:하지...)\s*마' matched the tail of '말하지 마', so the most
# common scam secrecy demand was counted as a safety warning. They are masked
# out of warning detection unless the same clause names a credential as the
# thing not to disclose ("인증번호는 누구에게도 말하지 마세요" stays a warning).
SECRECY_IMPERATIVES = (
    r'(?:말하지|알리지|얘기하지|이야기하지|신고하지|연락하지|전화하지|끊지)\s*(?:마|말)',
)
CREDENTIAL_TOPIC = r'(?:인증번호|otp|비밀번호|패스워드|주민등록번호|계좌번호|카드번호|password|verification code)'
PRESSURE_PATTERNS = PRESSURE_PATTERNS + SECRECY_IMPERATIVES
# Clause boundaries: sentence punctuation, newline, semicolon and a few
# contrastive connectives. Colons and commas are NOT boundaries, so
# "예시: 송금하세요" keeps its report cue in the same clause.
# Portable subset: no inline flag groups, so the same source compiles in JS engines.
CLAUSE_SPLIT = re.compile(r'[.!?\u3002\n;]+|\s(?:하지만|그런데|그러나|그리고|그러니까|그러니)\s|말고\s+|\s(?:but|however)\s', re.IGNORECASE)
REQUEST_CUES = REQUEST_CUES + (
    r'(?:하십시오|바랍니다|보내\s*(?:줘|라|주세요)|넘겨\s*(?:줘|주세요)|알려\s*(?:줘|주세요)|입력해|설치해|눌러\s*(?:줘|주세요))',
)


def _warning_cue(text: str) -> bool:
    masked = text
    if not re.search(CREDENTIAL_TOPIC, text, re.IGNORECASE):
        for p in SECRECY_IMPERATIVES:
            masked = re.sub(p, ' ', masked)
    return any(re.search(p, masked, re.IGNORECASE) for p in WARNING_PATTERNS)


def context_flags(text: str) -> ContextFlags:
    if type(text) is not str:
        raise TypeError('TEXT_REQUIRED')
    folded=text.casefold()
    return ContextFlags(
        action_mentioned=any(token.casefold() in folded for token in ACTION_TOKENS),
        warning_cue=_warning_cue(text),
        report_cue=any(re.search(p, text, re.IGNORECASE) for p in REPORT_PATTERNS),
        request_cue=any(re.search(p, text, re.IGNORECASE) for p in REQUEST_CUES),
        pressure_cue=any(re.search(p, text, re.IGNORECASE) for p in PRESSURE_PATTERNS),
    )


@dataclass(frozen=True)
class Clause:
    start: int
    end: int
    flags: ContextFlags

    @property
    def clean_action(self) -> bool:
        return self.flags.action_mentioned and not self.flags.warning_cue and not self.flags.report_cue

    @property
    def clean_imperative(self) -> bool:
        return self.clean_action and self.flags.request_cue


def clause_profile(text: str) -> tuple[Clause, ...]:
    """Lexical clause segmentation. Not a parser; boundaries are documented heuristics."""
    if type(text) is not str:
        raise TypeError('TEXT_REQUIRED')
    out=[]; pos=0
    for m in list(CLAUSE_SPLIT.finditer(text))+[None]:
        end=m.start() if m else len(text)
        piece=text[pos:end]
        if piece.strip():
            out.append(Clause(pos,end,context_flags(piece)))
        if m: pos=m.end()
    return tuple(out)


def context_conflict(action: str, speech: str, flags: ContextFlags,
                     profile: tuple[Clause, ...] | None = None) -> str | None:
    """One-way contradiction screen. No cues can *prove* a model label.

    With ``profile`` (v4.2) the speech-act checks are clause-local: a warning,
    report or "신고" word in one sentence can no longer contradict a clean
    imperative in another sentence, and a clean imperative clause contradicts
    any model claim that the text is merely a warning or a quotation.
    """
    if action == 'none' and flags.action_mentioned and speech != 'informational':
        return 'MODEL_NONE_BUT_ACTION_TERMS_PRESENT'
    if action == 'none' and speech == 'direct_request':
        return 'NONE_DIRECT_REQUEST_CONFLICT'
    if profile is not None:
        acts=[c for c in profile if c.flags.action_mentioned]
        clean=[c for c in acts if c.clean_action]
        imperative=[c for c in acts if c.clean_imperative]
        if speech == 'direct_request' and acts and not clean:
            return 'DIRECT_REQUEST_CONTRADICTS_CONTEXT'
        if speech == 'negated_or_warning':
            if imperative:
                return 'WARNING_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE'
            if acts and not any(c.flags.warning_cue for c in acts):
                return 'UNSUPPORTED_WARNING_LABEL'
        if speech == 'informational' and imperative:
            return 'INFORMATIONAL_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE'
        if speech == 'reported_or_quoted':
            if imperative:
                return 'REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE'
            if acts and not any(c.flags.report_cue for c in acts):
                return 'UNSUPPORTED_QUOTATION_LABEL'
        return None
    if speech == 'direct_request' and (flags.warning_cue or flags.report_cue):
        return 'DIRECT_REQUEST_CONTRADICTS_CONTEXT'
    if speech == 'negated_or_warning' and flags.action_mentioned and not flags.warning_cue:
        return 'UNSUPPORTED_WARNING_LABEL'
    if speech == 'reported_or_quoted' and flags.action_mentioned and not flags.report_cue:
        return 'UNSUPPORTED_QUOTATION_LABEL'
    return None


# LAYER MEMORY-PREWRITE / SOURCE-TRUST (preview only, no persistence)
# Method adapted from the team's memory-gate scope, not the standalone product.
# Caller-owned source assertions are not authenticated evidence. Integration
# MUST pass metadata obtained by the trusted harness, never text from a document.
MEMORY_ORIGINS = frozenset(('USER_DIRECT', 'FORWARDED_DOCUMENT', 'WEB_RESULT', 'TOOL_RESULT'))
EXTERNAL_DIRECTIVE_PATTERNS = (
    r'(?i)\b(?:system|developer|assistant)\s*:',
    r'(?i)\b(?:ignore\s+(?:all|previous)|override\s+(?:the\s+)?(?:policy|security)|bypass\s+(?:the\s+)?(?:approval|security))\b',
    r'(?:보안|승인|검증)\s*(?:절차|단계|규칙)?\s*(?:를|은|는)?\s*(?:생략|무시|우회)',
    r'(?:앞으로|다음부터|이후에는).*?(?:자동\s*승인|확인\s*없이|사본을?\s*(?:전송|보내)|외부\s*주소)',
    r'(?:향후|다음).*?(?:파일|문서|청구서).*?(?:무조건|자동으로).*?(?:전송|보내|승인)',
    r'(?i)\b(?:from\s+now\s+on|for\s+all\s+future).*?(?:send|approve|transfer|ignore)',
)
SENSITIVE_MEMORY_PATTERNS = (
    r'(?:비밀번호|패스워드|인증번호|주민등록번호|신분증|계좌번호|otp|password|api[ _-]?key)',
    r'(?:송금|이체|돈을\s*보내|wire\s+transfer|자동\s*승인)',
)


def external_directive_flags(text: str) -> tuple[str, ...]:
    """Narrow heuristic; returns a REVIEW cue, never a semantic fraud verdict."""
    if type(text) is not str or len(text) > 1500:
        raise ValueError('UNSUPPORTED_EXTERNAL_TEXT')
    if any(re.search(p, text, re.I | re.S) for p in EXTERNAL_DIRECTIVE_PATTERNS):
        return ('UNTRUSTED_TEXT_INSTRUCTION_CUE',)
    return ()


def preview_memory_prewrite(*, candidate: str, origin: str,
                            provenance_verified: bool = False,
                            user_authenticated: bool = False,
                            explicit_consent: bool = False,
                            model_flags: tuple[str, ...] = ()) -> dict:
    """Review-only proposal, never a memory write or identity authentication.

    Host must obtain provenance/authentication outside the candidate content.
    A malicious tool result must not be able to declare itself USER_DIRECT.
    """
    if type(candidate) is not str or not (1 <= len(candidate) <= 1500):
        raise ValueError('INVALID_MEMORY_CANDIDATE')
    if type(origin) is not str or origin not in MEMORY_ORIGINS:
        raise ValueError('INVALID_MEMORY_ORIGIN')
    if any(type(x) is not bool for x in (provenance_verified, user_authenticated, explicit_consent)):
        raise ValueError('INVALID_MEMORY_TRUST_FLAGS')
    allowed = ('POSSIBLE_ACTION_INSTRUCTION', 'POSSIBLE_SENSITIVE_DATA', 'MODEL_UNAVAILABLE')
    if type(model_flags) is not tuple or any(type(x) is not str or x not in allowed for x in model_flags):
        raise ValueError('INVALID_MEMORY_MODEL_FLAGS')
    reasons = []
    if not provenance_verified:
        reasons.append('PROVENANCE_NOT_ATTESTED')
    if origin != 'USER_DIRECT':
        reasons.append('NON_USER_SOURCE_NOT_MEMORY_AUTHORITY')
    if external_directive_flags(candidate):
        reasons.append('INSTRUCTION_PATTERN_NEEDS_REVIEW')
    if any(re.search(p, candidate, re.I) for p in SENSITIVE_MEMORY_PATTERNS):
        reasons.append('SENSITIVE_OR_ACTION_TERMS_NEED_REVIEW')
    if model_flags:
        reasons.extend(model_flags)
    if origin == 'USER_DIRECT' and not user_authenticated:
        reasons.append('USER_IDENTITY_NOT_ATTESTED')
    if origin == 'USER_DIRECT' and not explicit_consent:
        reasons.append('EXPLICIT_WRITE_CONSENT_MISSING')
    if not reasons:
        # Still NEVER write: an independent persistence adapter and permission
        # are required; this only grants a review-ready *proposal*.
        disposition = 'REVIEW_READY_NO_WRITE'
    elif not provenance_verified or origin != 'USER_DIRECT':
        disposition = 'QUARANTINE_NO_WRITE'
    else:
        disposition = 'HUMAN_REVIEW_NO_WRITE'
    return {
        'disposition': disposition,
        'reason_codes': list(dict.fromkeys(reasons)),
        'origin': origin,
        'actual_memory_written': False,
        'source_metadata_attested': provenance_verified,
        'identity_authenticated_by_this_function': False,
        'model_attested': False,
        'scope': 'SYNTHETIC_PREWRITE_POLICY_ONLY',
    }


# LAYER V4.6 / STRUCTURAL EVIDENCE (deterministic, separate from any model interpretation)
# Finds checkable surface facts in the original text: a hand-off to an external messenger with an
# ID, a URL, a phone number, a money amount, an overseas-sender tag, an account-change phrase.
# A match is a located fact, never a judgement that the message is fraudulent; an absence of
# matches is never evidence of safety. Offsets are Unicode code points (Python str indices).
STRUCTURAL_PATTERNS = (
    ('MESSENGER_HANDOFF', r'(?:라인|LINE|Line|line|텔레그램|텔레|[Tt]elegram|위챗|[Ww]e[Cc]hat|왓츠앱|[Ww]hats[Aa]pp|카톡|카카오톡|오픈채팅|오픈톡|인스타\s*DM|스냅챗|[Ss]napchat)\s*(?:아이디|ID|Id|id|아디|계정)?\s*(?:는|은|:|：|ㅡ|-|=|is)?\s*@?(?:(?=[A-Za-z0-9._-]*[0-9._])[A-Za-z][A-Za-z0-9._-]{2,30}|[A-Za-z][A-Za-z0-9._-]{4,30})'),
    ('MESSENGER_HANDLE', r'(?<![A-Za-z0-9._%+-])@[A-Za-z][A-Za-z0-9._]{2,30}'),
    ('URL', r'(?<![A-Za-z0-9@._-])(?:https?://)?(?:[A-Za-z0-9-]+\.)+(?:com|net|org|co|kr|top|xyz|ly|me|io|info|site|shop|link|click|app)(?![A-Za-z0-9])(?:/[^\s]*)?'),
    ('PHONE', r'(?<![0-9])0[0-9]{1,2}[- ]?[0-9]{3,4}[- ]?[0-9]{4}(?![0-9])'),
    ('MONEY_AMOUNT', r'(?<![0-9])[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:만\s*원|만원|천\s*원|억\s*원|억|원)|(?:USD|\$)\s*[0-9][0-9,]*(?:\.[0-9]+)?|(?<![0-9])[0-9]+\s*만(?=\s*(?:원|가능|이상|까지|드|지급|(?![\s\S])))'),
    ('OVERSEAS_SENDER_TAG', r'\[(?:국제발신|해외발신|국외발신)\]'),
    ('ACCOUNT_CHANGE_PHRASE', r'(?:결제|입금|대금|수취|송금)?\s*계좌(?:가|를|는)?\s*(?:변경|바뀌|바꿨)|새\s*계좌'),
)
STRUCTURAL_RX = tuple((k, re.compile(p)) for k, p in STRUCTURAL_PATTERNS)


def structural_evidence(text: str) -> tuple[dict, ...]:
    """Located surface facts, sorted by position. Overlapping spans of the same kind are merged away."""
    if type(text) is not str:
        raise TypeError('TEXT_REQUIRED')
    out = []
    for kind, rx in STRUCTURAL_RX:
        last_end = -1
        for m in rx.finditer(text):
            if m.end() <= m.start() or m.start() < last_end:
                continue
            q = m.group(0).strip()
            if not q:
                continue
            s = m.start() + (len(m.group(0)) - len(m.group(0).lstrip()))
            out.append({'kind': kind, 'start': s, 'end': s + len(q), 'quote': q})
            last_end = m.end()
    out.sort(key=lambda e: (e['start'], e['end'], e['kind']))
    return tuple(out[:20])
