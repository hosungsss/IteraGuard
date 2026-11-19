"""Strict internal validator of a proposed /v1/systemone response envelope.

NOT a claim that the current hosted Zoro server has been smoke-tested.
We reject unknown/malformed response schemas instead of silently coercing them.
"""
import math

class ContractError(ValueError):
    pass

def _prob(p):
    if type(p) not in (float,int) or not math.isfinite(p) or not 0<=p<=1:
        raise ContractError('INVALID_PROBABILITY')
    return float(p)

def _score_probabilities(probs, options):
    """LAYER KEV-ADAPTER (v4.2). The public kev page shows score criteria as an
    array of labels but does not document the response keys. Accept exactly the
    label keys, or exactly the positional index keys '0'..'n-1', and map indices
    back to labels. Any other key set is rejected; the chosen format is recorded."""
    if type(probs) is not dict:
        raise ContractError('INVALID_OPTIONS')
    if set(probs)==set(options):
        return probs,'LABEL_KEYS'
    index_keys=[str(i) for i in range(len(options))]
    if set(probs)==set(index_keys):
        return {options[i]:probs[str(i)] for i in range(len(options))},'INDEX_KEYS'
    raise ContractError('INVALID_OPTIONS')


def normalize_response(body:dict, spec:dict, *, optional:frozenset|set|tuple=()) -> dict:
    """Map per-question choice/noul probabilities to typed objects.

    spec: {question_id: {type:'choice',options:[...] } or {type:'noul'}}.
    ``optional`` (v4.2) names auxiliary questions that may be absent or
    malformed; they are dropped and listed under the reserved key
    ``'_dropped_optional'`` instead of invalidating the required answers.
    Unknown answer keys are still rejected. A real backend schema must first be
    confirmed by an actual response capture.
    """
    if type(body) is not dict or type(spec) is not dict or not spec:
        raise ContractError('INVALID_ENVELOPE')
    optional=frozenset(optional)
    if not optional<=set(spec):
        raise ContractError('INVALID_OPTIONAL_SPEC')
    answers=body.get('answers')
    required=set(spec)-optional
    if type(answers) is not dict or not required<=set(answers) or not set(answers)<=set(spec):
        raise ContractError('ANSWER_KEYS_MISMATCH')
    if not optional:
        return _normalize_strict(answers,spec)
    out={};dropped=[]
    for name in spec:
        if name not in answers:
            if name in optional: dropped.append(name)
            continue
        try:
            out.update(_normalize_strict({name:answers[name]},{name:spec[name]}))
        except ContractError:
            if name not in optional: raise
            dropped.append(name)
    out['_dropped_optional']=tuple(sorted(dropped))
    return out


def _normalize_strict(answers:dict, spec:dict) -> dict:
    out={}
    for name,requirement in spec.items():
        a=answers[name]
        if type(a) is not dict or type(requirement) is not dict:
            raise ContractError('INVALID_ANSWER_OBJECT')
        typ=requirement.get('type')
        # kev responses carry answer["type"]; when present it must agree.
        if 'type' in a and a['type']!=typ:
            raise ContractError('ANSWER_TYPE_MISMATCH')
        if typ=='noul':
            p=_prob(a.get('noul'))
            out[name]={'type':'noul','probabilities':{'yes':p,'no':1-p}}
        elif typ in ('choice','score'):
            options=requirement.get('options')
            if type(options) is not list or len(options)<2 or any(type(o) is not str for o in options) or len(set(options))!=len(options):
                raise ContractError('INVALID_CHOICE_SPEC')
            probs=a.get('probabilities')
            winner=a.get('choice') if typ=='choice' else a.get('score')
            key_format='LABEL_KEYS'
            if typ=='score':
                probs,key_format=_score_probabilities(probs,options)
            if type(probs) is not dict or set(probs)!=set(options):
                raise ContractError('INVALID_OPTIONS')
            parsed={o:_prob(probs[o]) for o in options}
            if abs(sum(parsed.values())-1)>0.002:
                raise ContractError('PROBABILITIES_NOT_NORMALIZED')
            if typ=='choice':
                if winner is None:
                    top=max(parsed.values())
                    winners=[k for k,v in parsed.items() if abs(v-top)<=1e-8]
                    if len(winners)!=1: raise ContractError('TIED_ARGMAX')
                    winner=winners[0]
                if winner not in options or parsed[winner]+1e-8<max(parsed.values()):
                    raise ContractError('INCONSISTENT_CHOICE')
                out[name]={'type':typ,'choice':winner,'probabilities':parsed}
            else:
                # System One score may be a fractional weighted rubric number.
                # Legacy string rubric labels are supported for historical tests.
                # v4.2: a missing score is derived as the argmax label (ties rejected).
                if winner is None:
                    top=max(parsed.values())
                    winners=[k for k,v in parsed.items() if abs(v-top)<=1e-8]
                    if len(winners)!=1: raise ContractError('TIED_ARGMAX')
                    winner=winners[0]
                if type(winner) is bool:
                    raise ContractError('INVALID_SCORE')
                if key_format=='INDEX_KEYS' and type(winner) is str and winner.isascii() and winner.isdigit() and int(winner)<len(options):
                    winner=options[int(winner)]
                if type(winner) not in (float,int,str) or (type(winner) is str and winner not in options) or (type(winner) is not str and (not math.isfinite(winner) or not 0<=winner<=len(options)-1)):
                    raise ContractError('INVALID_SCORE')
                if type(winner) is str and parsed[winner]+1e-8<max(parsed.values()):
                    raise ContractError('INCONSISTENT_SCORE')
                out[name]={'type':typ,'score':winner,'probabilities':parsed,'key_format':key_format}
        else:
            raise ContractError('UNKNOWN_QUESTION_TYPE')
    return out

QUESTION_SPEC={'request_action':{'type':'choice','options':['transfer','otp','remote_install','link','none','unclear']},
               'direct_instruction':{'type':'noul'}}

def request_for_synthetic_state(state: str) -> dict:
    if type(state) is not str or not 1 <= len(state) <= 2000:
        raise ValueError('INVALID_STATE')
    return {
     'state':state,
     'questions':{
       'request_action':{'type':'choice','instructions':'Which explicit action is the addressee being directly asked to do? Select unclear for insufficient context. Do not infer criminal identity.',
                         'criteria':{'transfer':'send money','otp':'disclose authentication code','remote_install':'install remote-control software','link':'open an unverified URL','none':'no direct action requested','unclear':'insufficient context'}},
       'direct_instruction':{'type':'noul','instructions':'Does the speaker DIRECTLY instruct the addressee to take this action now, rather than quote, warn against, negate, or report a past instruction?'}
     }
    }
