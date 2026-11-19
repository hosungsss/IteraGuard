"""Display-only, bounded lexical context for v5.1 evidence.

This module performs no model, policy, I/O, or storage operations. Its word lists
locate text, NOT fraud, required-pause, or semantic truth. A clause is displayed
only with a supported topic/action pair and an explicit speech-context cue.
``original_evidence`` and ``evidence[*].quote`` are MEMORY/DISPLAY ONLY.
Persist only ``evidence_display_trace`` (fixed enums, counts and CP offsets).
Coverage is lexical-candidate coverage, never human semantic accuracy.
"""
from copy import deepcopy
import re

SCHEMA_VERSION = "dmsg-v51-evidence-display/1"
MAX_TEXT = 2000
MAX_CLAUSE = 240
# Explicit cross-runtime whitespace: U+0085 included, U+FEFF/C0 separators not.
SPACE_PATTERN = r"[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]"
# Delimiters keep punctuation in quotes in the same quote scope. Commas/colons
# are not boundaries: '예시: ...' must not become a direct request.
CONFIG = {
    "boundary": r"[.!?。;]+(?=\s|$)|[\r\n]+|\s+(?:하지만|그런데|그러나|그리고|대신|but|however)\s+",
    "request": r"(?:주세요|주시겠어요|주시겠습니까|주실래요|줄래요|줘요|해줘|해라|하라|하세요|하십시오|하셔야|바랍니다|해야\s*(?:해|합)|보내세요|넘겨주세요|알려줘|설치해|눌러|클릭해|가져오세요|방문해)|(?:please|could you|would you)\s",
    "negation": r"지\s*(?:마|말)|(?:해서는|하면|해선)\s*안|금지|(?:do not|never|don.t)\s",
    "warning": r"경고|주의하세요|피싱\s*예방",
    "report": r"라고\s*(?:말했습니다|말했어요|말했다|했습니다|했어요|했다|들었습니다|들었어요|들었다|하더군요|하더라|전했습니다|전했어요|전했다)\s*$|^(?:인용|교육\s*자료|예시|신고\s*(?:내용|문구))\s*:|^(?:quoted|reported|example|training)\s*:",
    "uncertain_report": r"예시|인용|라고|라는",
    "context_heading": r"^(?:(?:교육\s*)?예시|인용|교육\s*자료|경고|주의|신고\s*(?:내용|문구)|example|training|quoted|reported)\s*:",
    "context_end": r"^(?:예시|인용|교육\s*자료)\s*(?:끝|종료)(?:$|\s|:)|^(?:예시|인용)는\s*여기까지|^end of (?:example|quote)(?:$|\s|:)",
    "pairs": [
        ["CREDENTIAL_TOPIC", r"인증\s*번호|일회용\s*(?:번호|비밀번호)|otp|비밀번호|패스워드|verification code|password", r"알려|보내|공유|전달|제공|입력|말하|말하지|주세요|주시겠|주실래|주지|send|share|enter|disclose"],
        ["MONEY_TOPIC", r"송금|이체|입금|돈(?=$|\s|[을이은])|금액|대금|계좌|[0-9]+\s*(?:만\s*원|천\s*원|원)|money|payment", r"송금|이체|입금|보내|전송|주세요|주시겠|주지|transfer|send|wire"],
        ["APPLICATION_TOPIC", r"원격|앱|프로그램|팀뷰어|애니데스크|remote|app", r"설치|실행|허용|접속|연결|install|allow|run"],
        ["PERSONAL_DATA_TOPIC", r"주민등록번호|신분증|개인정보|카드번호|사진|personal data|identity document", r"알려|보내|공유|전달|제공|입력|주세요|주시겠|주실래|주지|send|share|enter|disclose"],
        ["LINK_TOPIC", r"링크|url|https?://(?:(?!\s|[<>]).)+|link", r"열|누르|눌러|클릭|접속|방문|open|click|visit"],
        ["DISCLOSURE_TOPIC", r"가족|경찰|주변|다른\s*사람|누구|family|police", r"말하|말하지|알리|신고|연락|이야기|tell|contact|report"],
        ["ORDINARY_OBJECT_TOPIC", r"서류|자료|준비물|신발|우산|안내문|documents|umbrella", r"가져|준비|읽|착용|보내|주세요|주시겠|주지|bring|prepare|read|wear|send"],
    ],
}


def _matches(pattern, text):
    return list(re.finditer(pattern.replace(r"\s", SPACE_PATTERN), text, re.IGNORECASE))


def _space(char):
    return bool(re.fullmatch(SPACE_PATTERN, char))


def _nonblank(text):
    return any(not _space(c) for c in text)


def _quote_ranges(text):
    pairs = {"\"": "\"", "'": "'", "“": "”", "‘": "’", "«": "»"}
    stack, ranges = [], []
    for i, char in enumerate(text):
        # Apostrophes in don't/John's are not opening quotation marks.
        if char == "'" and i and i + 1 < len(text) and text[i - 1].isascii() and text[i - 1].isalnum() and text[i + 1].isascii() and text[i + 1].isalnum():
            continue
        if stack and char == stack[-1][1]:
            start, _ = stack.pop()
            ranges.append((start, i + 1, True))
        elif char in pairs:
            stack.append((i, pairs[char]))
    ranges += [(start, len(text), False) for start, _ in stack]
    return ranges


def _clauses(text):
    spans, start = [], 0
    for match in _matches(CONFIG["boundary"], text) + [None]:
        end = match.start() if match else len(text)
        while start < end and _space(text[start]):
            start += 1
        while end > start and _space(text[end - 1]):
            end -= 1
        if start < end:
            spans.append((start, end))
        if match:
            start = match.end()
    return spans


def _inside(start, end, ranges):
    return any(lo <= start and end <= hi for lo, hi, closed in ranges if closed)


def _inspect(text, lo, hi, quote_ranges, has_anchor):
    piece = text[lo:hi]
    topics, pairs, acts = [], [], []
    for name, topic_pattern, action_pattern in CONFIG["pairs"]:
        ts, verbs = _matches(topic_pattern, piece), _matches(action_pattern, piece)
        if ts:
            topics.append(name)
        if ts and verbs:
            pairs.append(name)
            acts += [(lo + m.start(), lo + m.end()) for m in ts + verbs]
    request = bool(_matches(CONFIG["request"], piece))
    negative = bool(_matches(CONFIG["negation"], piece))
    warning = bool(_matches(CONFIG["warning"], piece))
    reported = bool(_matches(CONFIG["report"], piece))
    uncertain_report = bool(_matches(CONFIG["uncertain_report"], piece))
    eligible = bool(topics or request or has_anchor)
    mode, reason = "UNRESOLVED", None
    if not eligible:
        return False, mode, "NO_ACTION_CONTEXT_CANDIDATE", []
    if hi - lo > MAX_CLAUSE:
        reason = "CLAUSE_TOO_LONG_FOR_LOCAL_DISPLAY"
    elif any(not closed and start < hi and lo < end for start, end, closed in quote_ranges):
        reason = "UNBALANCED_QUOTATION"
    elif not pairs:
        reason = "NO_SUPPORTED_TOPIC_ACTION_PAIR"
    else:
        quoted = [_inside(start, end, quote_ranges) for start, end in acts]
        if any(quoted) and not all(quoted):
            reason = "MIXED_QUOTED_AND_UNQUOTED_ACTION_CUES"
        elif all(quoted) or reported:
            mode = "QUOTED_OR_REPORTED"
        elif uncertain_report:
            reason = "REPORT_SCOPE_UNRESOLVED"
        elif negative and request:
            reason = "MIXED_NEGATED_AND_REQUEST_CUES"
        elif negative:
            mode = "NEGATED_OR_WARNING_CUE"
        elif warning and request:
            reason = "WARNING_SCOPE_UNRESOLVED"
        elif warning:
            mode = "NEGATED_OR_WARNING_CUE"
        elif request:
            mode = "DIRECT_REQUEST_CUE"
        else:
            reason = "SPEECH_CONTEXT_UNRESOLVED"
    return eligible, mode, reason, pairs


def enrich_evidence(text, result):
    """Return a copy with display evidence; never alter action/guidance/trace.

    Unicode offsets are Python ``str``/JS ``Array.from`` code points. Repeated
    calls preserve the original anchor list. A well-formed upstream anchor is
    not semantic proof; unmatched/invalid anchors are counted, never relocated.
    """
    if type(text) is not str or len(text) > MAX_TEXT or type(result) is not dict:
        raise ValueError("INVALID_EVIDENCE_INPUT")
    out = deepcopy(result)
    previous = result.get("evidence_display")
    original = result.get("original_evidence") if isinstance(previous, dict) and previous.get("schema_version") == SCHEMA_VERSION else result.get("evidence", [])
    reasons = []
    if type(original) is not list:
        original, reasons = [], ["INVALID_UPSTREAM_EVIDENCE_LIST"]
    out["original_evidence"] = deepcopy(original)
    clauses, quotes = _clauses(text), _quote_ranges(text)
    anchors = [[] for _ in clauses]
    invalid = []
    for index, e in enumerate(original):
        valid = (type(e) is dict and type(e.get("start")) is int and type(e.get("end")) is int
                 and 0 <= e["start"] < e["end"] <= len(text)
                 and type(e.get("quote")) is str and text[e["start"]:e["end"]] == e["quote"] and _nonblank(e["quote"]))
        match = next((i for i, (lo, hi) in enumerate(clauses) if valid and lo <= e["start"] < e["end"] <= hi), None)
        if match is None:
            invalid.append(index)
        else:
            anchors[match].append(index)
    if invalid:
        reasons.append("INVALID_OR_CROSS_CLAUSE_UPSTREAM_SPAN")
    evidence, reviews, shown_anchors = [], [], []
    context_open = False
    for index, (lo, hi) in enumerate(clauses):
        eligible, mode, reason, pairs = _inspect(text, lo, hi, quotes, bool(anchors[index]))
        # Example/warning headings do not end merely because punctuation or a
        # newline appears. Only an explicit scope-end marker reopens display.
        if _matches(CONFIG["context_end"], text[lo:hi]):
            context_open = False
        if eligible and context_open:
            mode, reason = "UNRESOLVED", "PRECEDING_CONTEXT_HEADING_SCOPE_UNRESOLVED"
        if _matches(CONFIG["context_heading"], text[lo:hi]):
            context_open = True
        if not eligible:
            continue
        method = "UPSTREAM_ANCHOR_CLAUSE_CONTEXT" if anchors[index] else "LOCAL_TOPIC_ACTION_CLAUSE_CONTEXT"
        review = {"start": lo, "end": hi, "clause_mode": mode, "status": "UNAVAILABLE" if reason else "DISPLAYED",
                  "reason_code": reason, "method": method, "original_anchor_indexes": anchors[index]}
        reviews.append(review)
        if reason:
            reasons.append(reason)
            continue
        span = {"start": lo, "end": hi, "quote": text[lo:hi], "kind": "TEXT_ACTION_CONTEXT",
                "directness": mode, "clause_mode": mode, "origin": "LOCAL_DISPLAY_HEURISTIC",
                "method": method, "topic_cues": pairs, "semantic_verified": False,
                "original_anchor_indexes": anchors[index]}
        evidence.append(span)
        shown_anchors += anchors[index]
    unavailable = sum(r["status"] == "UNAVAILABLE" for r in reviews)
    n = len(reviews)
    if not _nonblank(text):
        reasons.append("EMPTY_TEXT")
    if not evidence:
        reasons.append("NO_DISPLAYABLE_ACTION_CONTEXT")
    status = "PARTIAL" if evidence and (unavailable or invalid) else "AVAILABLE" if evidence else "UNAVAILABLE" if n or original or reasons[0:1] == ["INVALID_UPSTREAM_EVIDENCE_LIST"] else "NOT_APPLICABLE"
    meta = {"schema_version": SCHEMA_VERSION, "status": status,
            "source": "LOCAL_DISPLAY_HEURISTIC", "extraction_method": "BOUNDED_TOPIC_ACTION_AND_SPEECH_CUES",
            "offset_unit": "UNICODE_CODE_POINT", "whitespace_contract": "EXPLICIT_UNICODE_WHITE_SPACE_NO_BOM", "policy_changed": False,
            "role": "DISPLAY_CONTEXT_NOT_DECISION_GROUNDING",
            "semantic_verified": False, "semantic_quality": "NOT_INDEPENDENTLY_EVALUATED",
            "risk_classification": "NOT_PERFORMED", "model_calls": 0,
            "reason_codes": list(dict.fromkeys(reasons)),
            "candidate_clause_count": n, "displayed_clause_count": len(evidence),
            "unavailable_clause_count": unavailable,
            "candidate_clause_coverage": len(evidence) / n if n else None,
            "unavailable_clause_rate": unavailable / n if n else None,
            "coverage_denominator": "CLAUSES_WITH_TOPIC_OR_REQUEST_CUE_OR_VALID_UPSTREAM_ANCHOR",
            "upstream_span_count": len(original), "upstream_span_displayed_count": len(shown_anchors),
            "upstream_span_unavailable_count": len(original) - len(shown_anchors),
            "upstream_span_unavailable_rate": (len(original) - len(shown_anchors)) / len(original) if original else None,
            "invalid_upstream_span_count": len(invalid),
            "raw_text_persistence": "FORBIDDEN_DISPLAY_AND_ORIGINAL_EVIDENCE_MEMORY_ONLY"}
    out["evidence"] = evidence
    out["evidence_display"] = meta
    # This independently constructed allowlist never copies user/original fields.
    out["evidence_display_trace"] = {**deepcopy(meta), "clauses": reviews,
        "spans": [{k: deepcopy(e[k]) for k in ("start", "end", "kind", "clause_mode", "origin", "method", "topic_cues", "original_anchor_indexes")} for e in evidence],
        "raw_text_stored": False}
    return out
