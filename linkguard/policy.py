"""LinkGuard policy: six states, scope kept separate from detection, never a default "safe".

States
  KNOWN_MALICIOUS        a checked source lists it (local list, or a consented provider result that is still fresh)
  SUSPICIOUS             structural evidence of deception/risk (lookalike brand, non-public IP, APK download, risky APK combos …)
  NO_KNOWN_THREAT_FOUND  every stage that ran found nothing — this is NOT "safe"
  INCONCLUSIVE           some stages ran, some could not complete
  NOT_SCANNED            nothing beyond intake ran (no consent / not applicable / blocked)
  SCAN_FAILED            the input could not be analysed
"""
from __future__ import annotations

STATES = ['KNOWN_MALICIOUS', 'SUSPICIOUS', 'INCONCLUSIVE', 'NO_KNOWN_THREAT_FOUND', 'NOT_SCANNED', 'SCAN_FAILED']
RANK = {'KNOWN_MALICIOUS': 5, 'SUSPICIOUS': 4, 'SCAN_FAILED': 3, 'INCONCLUSIVE': 2, 'NOT_SCANNED': 1, 'NO_KNOWN_THREAT_FOUND': 0}

SUSPICIOUS_URL_FLAGS = ['HOMOGLYPH_BRAND', 'BRAND_NOT_OFFICIAL_DOMAIN', 'NON_PUBLIC_IP', 'OBFUSCATED_IP', 'USERINFO_AT',
                        'DANGEROUS_SCHEME', 'APK_DOWNLOAD', 'MIXED_SCRIPT']
CAUTION_URL_FLAGS = ['SHORTENER', 'MESSENGER_LINK', 'MESSENGER_OR_APP_DEEPLINK', 'IP_LITERAL', 'PUNYCODE', 'NONSTANDARD_PORT',
                     'DEEP_SUBDOMAIN', 'SENSITIVE_QUERY', 'DEFANGED', 'NON_HTTP_SCHEME']

# Stage status values: DONE / NOT_RUN / BLOCKED / FAILED
WEB_ANALYSIS_STATUS = 'BLOCKED'          # v4.7: isolated fetcher not shipped in this release
WEB_ANALYSIS_REASON = 'WEB_FETCH_MODULE_NOT_INCLUDED_IN_V4_7'


def reputation_local(url: dict, blocklist: dict | None):
    """Offline list check on registrable domain / host. blocklist = {'domains': [...], 'source': str, 'as_of': str}"""
    if not blocklist: return {'provider': 'local_list', 'status': 'NOT_RUN', 'reason': 'NO_LIST_LOADED'}
    doms = set(blocklist.get('domains') or [])
    hit = (url.get('host_ascii') in doms) or (url.get('registrable_domain') in doms)
    return {'provider': 'local_list', 'status': 'DONE', 'listed': bool(hit), 'source': blocklist.get('source'), 'as_of': blocklist.get('as_of')}


def reputation_external(consent: dict, keys_present: bool, provider: str):
    if not consent.get('external_reputation'): return {'provider': provider, 'status': 'NOT_RUN', 'reason': 'NO_CONSENT'}
    if not keys_present: return {'provider': provider, 'status': 'NOT_RUN', 'reason': 'NO_API_KEY_ON_SERVER'}
    return {'provider': provider, 'status': 'NOT_RUN', 'reason': 'NOT_EXECUTED_IN_THIS_ENVIRONMENT'}


def assess_url(url: dict, *, consent: dict, blocklist: dict | None = None, keys_present: bool = False) -> dict:
    flags = url.get('flags') or []
    stages = {'intake': 'DONE', 'local_reputation': None, 'safe_browsing': None, 'virustotal': None, 'web_analysis': None}
    rep_local = reputation_local(url, blocklist)
    stages['local_reputation'] = rep_local['status']
    ext = [reputation_external(consent, keys_present, p) for p in ('google_safe_browsing', 'virustotal')]
    stages['safe_browsing'], stages['virustotal'] = ext[0]['status'], ext[1]['status']
    stages['web_analysis'] = WEB_ANALYSIS_STATUS if consent.get('web_analysis') else 'NOT_RUN'
    reasons = [f for f in flags if f in SUSPICIOUS_URL_FLAGS]
    cautions = [f for f in flags if f in CAUTION_URL_FLAGS]
    if rep_local.get('listed'): state = 'KNOWN_MALICIOUS'
    elif reasons: state = 'SUSPICIOUS'
    elif url.get('scheme_class') in ('DEEPLINK', 'OTHER', 'APP_STORE') and not url.get('host_ascii'): state = 'NOT_SCANNED'
    else:
        ran = [k for k, v in stages.items() if v == 'DONE' and k != 'intake']
        state = 'INCONCLUSIVE' if ran else 'NOT_SCANNED'
        if ran and not cautions and all(stages[k] == 'DONE' for k in ('local_reputation',)) and not any(
                v == 'DONE' for k, v in stages.items() if k in ('safe_browsing', 'virustotal', 'web_analysis')):
            state = 'NO_KNOWN_THREAT_FOUND'   # only the offline list ran, and found nothing
    checked = [k for k, v in stages.items() if v == 'DONE']
    not_checked = [k for k, v in stages.items() if v != 'DONE']
    return {'display_url': url.get('display_url'), 'state': state, 'reasons': reasons, 'cautions': cautions, 'stages': stages,
            'checked': checked, 'not_checked': not_checked, 'reputation': [rep_local] + ext,
            'is_safe_claim': False, 'note': 'NO_DETECTION_IS_NOT_SAFETY'}


def assess_message(intake_result: dict, *, blocklist=None, keys_present=False) -> dict:
    consent = intake_result.get('consent') or {}
    items = [assess_url(u, consent=consent, blocklist=blocklist, keys_present=keys_present) for u in intake_result['urls']]
    if not items: overall = 'NOT_SCANNED'
    else: overall = max((i['state'] for i in items), key=lambda s: RANK[s])
    return {'message_id': intake_result.get('message_id'), 'overall': overall, 'urls': items, 'url_count': len(items),
            'network_used': False}


ACTION_RANK = {'NO_STRONG_SIGNAL': 0, 'CAUTION': 1, 'ASK_HUMAN': 1, 'PAUSE_AND_VERIFY': 2}
LINK_TO_ACTION = {'KNOWN_MALICIOUS': 'PAUSE_AND_VERIFY', 'SUSPICIOUS': 'CAUTION'}


def fuse(message_advisory: dict | None, link: dict | None, apk_state: str | None = None) -> dict:
    """Combine with the v4.6 message advisory (actions from dmsg.prototype.core.Action).
    LinkGuard can only raise the action, never lower it: KNOWN_MALICIOUS -> PAUSE_AND_VERIFY, SUSPICIOUS -> at least CAUTION.
    ASK_HUMAN and CAUTION share a rank (both keep the user from acting alone), so ASK_HUMAN is kept as is."""
    base = (message_advisory or {}).get('policy_action') or 'NO_STRONG_SIGNAL'
    if base not in ACTION_RANK: base = 'ASK_HUMAN'
    target, why = base, []
    for s in [x for x in ((link or {}).get('overall'), apk_state) if x]:
        want = LINK_TO_ACTION.get(s)
        if want and ACTION_RANK[want] > ACTION_RANK[target]: target = want; why.append('LINKGUARD_' + s)
    return {'policy_action': target, 'base_action': base, 'escalated': target != base, 'escalation_reasons': why,
            'link_state': (link or {}).get('overall'), 'apk_state': apk_state, 'downgraded': False}
