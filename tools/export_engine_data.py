"""Export the dmsg Python reference data to the shared JS engine (single source of truth).

The JavaScript engine in apps/shared/dmsg-engine.js implements the same algorithms but
never hand-copies patterns, fixtures, messages or records. This tool regenerates
apps/shared/engine-data.js from the Python modules and stamps the SHA-256 of every
source file, so the conformance gate can detect drift.

Python regex -> JS regex translation (documented, mechanical):
  * a leading global '(?i)' is removed and the 'i' flag is set instead;
  * '\\b' (Unicode word boundary in Python str patterns) becomes an explicit
    lookaround over [\\p{L}\\p{N}_], compiled with the 'u' flag;
  * re.S becomes the 's' flag. Any other construct is passed through unchanged and
    must compile in JS; the conformance gate proves behavioural equality on vectors.
Usage: python tools/export_engine_data.py
"""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'dmsg'
sys.path.insert(0, str(SKILL))

from prototype import core, fixtures, context_guard as cg, model_bridge as mb, paylock as pl  # noqa: E402

WORD = r'[\p{L}\p{N}_]'
JS_BOUNDARY = rf'(?:(?<!{WORD})(?={WORD})|(?<={WORD})(?!{WORD}))'


def js(pattern: str, *, ignorecase: bool = False, dotall: bool = False) -> dict:
    src = pattern
    flags = 'u'
    if src.startswith('(?i)'):
        src = src[4:]
        ignorecase = True
    if '(?i' in src or '(?s' in src or '(?x' in src:
        raise SystemExit('NON_PORTABLE_INLINE_FLAG: ' + pattern)
    full = False
    if src.endswith('\\Z'):
        # Python fullmatch patterns end in \Z; JS gets an explicit ^(?:...)$ anchor.
        src, full = src[:-2], True
    src = re.sub(r'(?<!\\)\\b', lambda _m: JS_BOUNDARY, src)
    if full:
        src = '^(?:' + src + ')$'
    if ignorecase:
        flags += 'i'
    if dotall:
        flags += 's'
    return {'source': src, 'flags': flags}


def evidence(e):
    return {'kind': e.kind.value, 'start': e.start, 'end': e.end, 'quote': e.quote,
            'directness': e.directness.value, 'origin': e.origin.value}


def build() -> dict:
    sources = {}
    for rel in ('prototype/core.py', 'prototype/fixtures.py', 'prototype/context_guard.py',
                'prototype/model_bridge.py', 'prototype/typed_contract.py', 'prototype/ontology.py',
                'prototype/paylock.py'):
        sources[rel] = hashlib.sha256((SKILL / rel).read_bytes()).hexdigest()
    return {
        'schema': 'dmsg-engine-data/1',
        'reference_implementation': 'Python dmsg/prototype',
        'source_sha256': sources,
        'core': {
            'actions': [a.value for a in core.Action],
            'kinds': [k.value for k in core.Kind],
            'directness': [d.value for d in core.Directness],
            'origins': [o.value for o in core.Origin],
            'statuses': [s.value for s in core.Status],
            'messages': {a.value: m for a, m in core.MESSAGES.items()},
            'dangerous': sorted(k.value for k in core.DANGEROUS),
            'cautionary': sorted(k.value for k in core.CAUTIONARY),
            'max_text': 2000, 'max_spans': 20,
            'default_mode': 'FIXTURE / SIMULATED',
        },
        'fixtures': [{'id': c.id, 'family': c.family, 'title': c.title, 'transcript': c.transcript,
                      'story': c.story, 'evidence': [evidence(e) for e in c.evidence]} for c in fixtures.CASES],
        'guard': {
            'action_tokens': list(cg.ACTION_TOKENS),
            'warning': [js(p, ignorecase=True) for p in cg.WARNING_PATTERNS],
            'report': [js(p, ignorecase=True) for p in cg.REPORT_PATTERNS],
            'pressure': [js(p, ignorecase=True) for p in cg.PRESSURE_PATTERNS],
            'request': [js(p, ignorecase=True) for p in cg.REQUEST_CUES],
            'secrecy': [js(p) for p in cg.SECRECY_IMPERATIVES],
            'credential_topic': js(cg.CREDENTIAL_TOPIC, ignorecase=True),
            'clause_split': js(cg.CLAUSE_SPLIT.pattern, ignorecase=bool(cg.CLAUSE_SPLIT.flags & re.IGNORECASE)),
            'external_directive': [js(p, ignorecase=True, dotall=True) for p in cg.EXTERNAL_DIRECTIVE_PATTERNS],
            'external_max': 1500,
            'structural': [{'kind': k, **js(p)} for k, p in cg.STRUCTURAL_PATTERNS],
        },
        'model': {
            'spec': mb.SPEC, 'spec_order': list(mb.SPEC), 'optional': sorted(mb.OPTIONAL_QUESTIONS),
            'risk_levels': mb.RISK_LEVELS,
            'kind_map': {k: v.value for k, v in mb.KIND_MAP.items()},
            'speech_map': {k: v.value for k, v in mb.SPEECH_MAP.items()},
            'anchors': {k: list(v) for k, v in mb.ANCHORS.items()},
            'questions': mb.questions('')['questions'],
            'calibration_temperature': mb.CALIBRATION_TEMPERATURE_STATUS,
            'default_threshold': 0.70,
            'indicators': list(mb.INDICATORS), 'primary_indicators': sorted(mb.PRIMARY_INDICATORS),
            'high_severity_indicators': sorted(mb.HIGH_SEVERITY_INDICATORS),
            'structural_grounds': {k: list(v) for k, v in mb.STRUCTURAL_GROUNDS.items()},
            'warning_clearances': sorted(mb.WARNING_CLEARANCES), 'ungrounded_min_probability': mb.UNGROUNDED_MIN_PROBABILITY,
            'dra': {'version': mb.DRA_VERSION, 'action_options': mb.ACTION_OPTIONS, 'speech_options': mb.SPEECH_OPTIONS,
                    'action_class': mb.DRA_ACTION_CLASS, 'speech_class': mb.DRA_SPEECH_CLASS, 'outputs': list(mb.DRA_OUTPUTS),
                    'costs': {k: list(v) for k, v in mb.DRA_COSTS.items()}, 'ungrounded_discount': mb.DRA_UNGROUNDED_DISCOUNT,
                    'imperative_boost': mb.DRA_IMPERATIVE_BOOST, 'structural_grounds': {k: list(v) for k, v in mb.DRA_STRUCTURAL_GROUNDS.items()}, 'warning_boost': mb.DRA_WARNING_BOOST},
            'unavailable_message': '모델의 검증 가능한 판단이 없습니다. 중요 행동을 멈추고 공식 경로에서 확인하세요.',
        },
        'paylock': {
            'banks': sorted(pl.BANKS),
            'id_pattern': js(pl.ID_PATTERN.pattern), 'email_pattern': js(pl.EMAIL_PATTERN.pattern),
            'account_pattern': js(pl.ACCOUNT_PATTERN.pattern),
            'urgency_tokens': list(pl.URGENCY_TOKENS),
            'vendor_list': [{'vendor_id': v.vendor_id, 'name': v.name, 'known_email': v.known_email,
                             'bank': v.bank, 'account': v.account, 'reference_contact': v.reference_contact}
                            for v in pl.VENDORS.values()],
            'invoice_list': [{'invoice_id': i.invoice_id, 'vendor_id': i.vendor_id, 'amount_krw': i.amount_krw}
                             for i in pl.INVOICES.values()],
            'examples': [dict(e) for e in pl.EXAMPLES],
        },
    }


def main() -> int:
    data = build()
    out = ROOT / 'apps' / 'shared' / 'engine-data.js'
    out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    out.write_text('/* GENERATED by tools/export_engine_data.py from the Python dmsg reference. Do not edit. */\n'
                   '(function (g) { g.DMSG_DATA = ' + body + '; })(typeof globalThis !== "undefined" ? globalThis : this);\n',
                   encoding='utf8')
    print(json.dumps({'written': str(out.relative_to(ROOT)), 'bytes': out.stat().st_size,
                      'fixtures': len(data['fixtures']), 'sources': len(data['source_sha256'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
