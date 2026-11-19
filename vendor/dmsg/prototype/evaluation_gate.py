"""Inspectable annotation evaluation. Never invents model metrics or gold labels."""
from __future__ import annotations
from collections import Counter, defaultdict
from math import sqrt

ACTIONS={"NO_STRONG_SIGNAL","CAUTION","PAUSE_AND_VERIFY","ASK_HUMAN"}
SPLITS={"development","calibration","locked"}
MODES={"FIXTURE","MOCK","MODEL_RESPONSE_UNATTESTED","CHECKPOINT_VERIFIED"}

class EvaluationError(ValueError): pass

def wilson_interval(numerator:int,denominator:int,z:float=1.96):
    """Binomial Wilson interval, not a substitute for representative sampling."""
    if denominator==0: return None
    p=numerator/denominator
    denom=1+z*z/denominator
    center=(p+z*z/(2*denominator))/denom
    half=z*sqrt(p*(1-p)/denominator+z*z/(4*denominator*denominator))/denom
    return [round(max(0,center-half),4),round(min(1,center+half),4)]

def evaluate(rows:list[dict])->dict:
    if type(rows) is not list or not rows:raise EvaluationError('NONEMPTY_ROWS_REQUIRED')
    seen=set();families=defaultdict(set);by_split=defaultdict(list);modes=set()
    for index,row in enumerate(rows):
        if type(row) is not dict:raise EvaluationError('BAD_ROW')
        if set(row)!={'case_id','scenario_family','split','gold_risky','predicted_action','source_mode'}:
            raise EvaluationError('ROW_SCHEMA_MISMATCH')
        if any(type(row[k]) is not str or not row[k].strip() or len(row[k])>120 for k in ('case_id','scenario_family')):
            raise EvaluationError('BAD_ID')
        if row['case_id'] in seen: raise EvaluationError('DUPLICATE_CASE_ID')
        seen.add(row['case_id'])
        if row['split'] not in SPLITS or row['predicted_action'] not in ACTIONS or row['source_mode'] not in MODES or type(row['gold_risky']) is not bool:
            raise EvaluationError('INVALID_LABEL_OR_MODE')
        families[row['scenario_family']].add(row['split'])
        by_split[row['split']].append(row)
        modes.add(row['source_mode'])
    mixed=[f for f,splits in families.items() if len(splits)>1]
    if mixed:raise EvaluationError('SCENARIO_FAMILY_LEAKAGE')
    results={}
    for split,subset in sorted(by_split.items()):
        n=len(subset)
        risky=[r for r in subset if r['gold_risky']]
        normal=[r for r in subset if not r['gold_risky']]
        missed=sum(r['predicted_action']=='NO_STRONG_SIGNAL' for r in risky)
        disrupted=sum(r['predicted_action']=='PAUSE_AND_VERIFY' for r in normal)
        review=sum(r['predicted_action']=='ASK_HUMAN' for r in subset)
        results[split]={
            'n':n,'n_risky':len(risky),'n_normal':len(normal),
            'missed_warning':{'numerator':missed,'denominator':len(risky),'rate':round(missed/len(risky),4) if risky else None,'wilson95':wilson_interval(missed,len(risky))},
            'normal_pause':{'numerator':disrupted,'denominator':len(normal),'rate':round(disrupted/len(normal),4) if normal else None,'wilson95':wilson_interval(disrupted,len(normal))},
            'abstention':{'numerator':review,'denominator':n,'rate':round(review/n,4),'wilson95':wilson_interval(review,n)},
            'action_counts':dict(Counter(r['predicted_action'] for r in subset))}
    return {'evidence_tier':'ANNOTATION_ONLY_NO_REAL_MODEL_ATTESTATION',
            'model_modes':sorted(modes),'n_total':len(rows),'scenario_families':len(families),'splits':results,
            'limits':['label correctness not independently verified','sample representativeness not established','model checkpoint identity not inferred from source_mode']}
