"""Source-backed bridge to the bundled, unmodified dmsg v4.8 code."""
import sys
from pathlib import Path

from experiments.contracts import ContractError, fingerprint, validate_trace

SOURCE_ROOT = Path(__file__).resolve().parents[1] / 'vendor' / 'dmsg'
sys.path.insert(0, str(SOURCE_ROOT))
from prototype import model_bridge as bridge
from prototype.typed_contract import normalize_response

if not Path(bridge.__file__).resolve().is_relative_to(SOURCE_ROOT.resolve()):
    raise RuntimeError('A different prototype package is already imported')

ACTION_MAP = {'transfer':'money_transfer','otp':'credential_or_otp','remote_install':'remote_app_install',
              'personal_data':'personal_data','link':'verification_link','secrecy':'secrecy',
              'none':'none','unclear':'other_unclear'}
SPEECH_MAP = {'direct_request':'direct_request','reported_or_quoted':'quoted_or_reported',
              'negated_or_warning':'negated_or_warning','informational':'information','unclear':'unclear'}
KIND_MAP = {'TRANSFER':'money_transfer','OTP':'credential_or_otp','REMOTE_INSTALL':'remote_app_install',
            'PERSONAL_DATA':'personal_data','UNVERIFIED_LINK':'verification_link','SECRECY':'secrecy','OTHER':'none'}
DIRECTNESS_MAP = {'DIRECT_REQUEST':'DIRECT','REPORTED_OR_QUOTED':'QUOTED',
                  'NEGATED_OR_WARNING':'WARNING','UNCLEAR':'UNCLEAR'}


def convert(text, raw, latency_ms, mode='MODEL_RESPONSE_UNATTESTED'):
    """Map actual v4.8 normalized probabilities, preserving original policy separately.

    The source's lexical/model-attribution anchor is NOT independent human-confirmed
    semantic evidence. Keep MODEL_PROPOSED so the kit probe cannot promote it.
    """
    if mode not in {'FIXTURE','SURROGATE','MODEL_RESPONSE_UNATTESTED'}:
        raise ContractError('This bridge never attests REAL_ZORO identity')
    norm = normalize_response(raw, bridge.SPEC, optional=bridge.OPTIONAL_QUESTIONS)
    original = bridge.advisory(text, raw, threshold=0.70)
    cause = bridge.abstention_cause(text, raw, threshold=0.70)
    answers = {}
    for name, value in norm.items():
        if name.startswith('_'): continue
        mapping = ACTION_MAP if name == 'q_action' else SPEECH_MAP if name == 'q_speech' else None
        probs = {(mapping[k] if mapping else k):v for k,v in value['probabilities'].items()}
        answers[name] = {'selected':max(probs,key=probs.get), 'probabilities':probs}
    evidence = []
    for item in original['evidence']:
        evidence.append({'start_cp':item['start'],'end_cp':item['end'],'quote':item['quote'],
                         'action':KIND_MAP[item['kind']], 'directness':DIRECTNESS_MAP[item['directness']],
                         'origin':'MODEL_PROPOSED'})
    flags = bridge.context_flags(text)
    profile = bridge.clause_profile(text)
    conflict = bridge.context_conflict(norm['q_action']['choice'],norm['q_speech']['choice'],flags,profile)
    trace = {'schema_version':'dmsg-kit-trace-v1','input_sha256':fingerprint(text),
             'session_version':1,'inference_mode':mode,'model_status':'VALID','latency_ms':latency_ms,
             'answers':answers,'evidence':evidence,'context_conflict':bool(conflict),
             'reference_outcome':original['action'], 'reference_reason':original['reason'],
             'source_diagnostics':{'abstention':cause, 'dropped_optional':list(norm.get('_dropped_optional',())),
                                   'context_guard_reason':conflict or None,
                                   'source_threshold':0.70,'source_policy_modified':False}}
    validate_trace(trace,text)
    return trace


def evaluate(request):
    if request.get('session_version') != 1 or request.get('latest_turn_id') != 1 or len(request.get('turns',[])) != 1:
        raise ContractError('The v1.1 adapter supports single caller turns only')
    turn=request['turns'][0]
    if turn.get('speaker')!='caller':raise ContractError('Caller turn required')
    # Existing endpoint allowlist, timeout and explicit DMSG_MODEL_ENABLED are enforced by source.
    raw, latency = bridge.ModelClient().infer(turn['text'])
    return convert(turn['text'],raw,latency)


def source_contract():
    return {'source_product_version':'4.8','wire_questions':bridge.questions('Synthetic contract inspection')['questions'],
            'spec':bridge.SPEC,'optional':sorted(bridge.OPTIONAL_QUESTIONS),
            'action_mapping':ACTION_MAP,'speech_mapping':SPEECH_MAP,'threshold':0.70,
            'notice':'Extracted from bundled source; not a live server handshake or model attestation.'}
