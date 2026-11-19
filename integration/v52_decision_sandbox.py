"""v5.2 experimental post-model decision sandbox; NEVER a payment/URL/SMS action authority.

Authoritative v5.1 request/response profile and production policy are unchanged.
No Zoro-1 invocation, attestation, hidden reasoning, or real-world risk calibration
is performed by this module. Analytic output is audit-only until independently
labelled, calibrated, externally authorized, and release-gated.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from math import exp, isfinite, log
import json
import random
from typing import Mapping, Sequence

FEATURE_KEYS = (
    "q_scam_yes", "q_pressure_yes", "q_current_exposure_yes",
    "q_payment_anomaly_yes", "q_request_scope_sensitive_request",
)
T_REASONING_DEFAULT = 0.70  # Uncertainty of typed selection, NOT action threshold.
STATUS = "EXPERIMENT_ONLY_NOT_PRODUCTION_VALIDATED"

class SandboxError(ValueError):
    pass


def _prob(value: object) -> float:
    if type(value) not in (float, int) or not isfinite(value) or not 0.0 <= value <= 1.0:
        raise SandboxError("INVALID_PROBABILITY")
    return float(value)


def _read_noul(answers: Mapping, key: str) -> float:
    item = answers.get(key)
    if not isinstance(item, dict) or item.get("type") != "noul":
        raise SandboxError("MISSING_OR_WRONG_TYPED_QUESTION:" + key)
    if "noul" not in item:
        raise SandboxError("MISSING_NOUL:" + key)
    return _prob(item["noul"])


def _read_choice(answers: Mapping, key: str, option: str) -> float:
    item = answers.get(key)
    if not isinstance(item, dict) or item.get("type") != "choice":
        raise SandboxError("MISSING_OR_WRONG_TYPED_QUESTION:" + key)
    dist = item.get("probabilities")
    if not isinstance(dist, dict) or option not in dist or not dist:
        raise SandboxError("MISSING_OPTION:" + option)
    values = [_prob(x) for x in dist.values()]
    if abs(sum(values) - 1.0) > 0.002:
        raise SandboxError("PROBABILITY_SUM_MISMATCH")
    if item.get("choice") not in dist or dist[item["choice"]] < max(values) - 0.002:
        raise SandboxError("SELECTED_OPTION_MISMATCH")
    return _prob(dist[option])


def extract_features(raw: Mapping) -> tuple[float, ...]:
    """Strict extractor; raw typed envelope should also pass v5.1 contract first.

    A noul probability is a *model answer to a question*, not P(real-world fraud).
    """
    if not isinstance(raw, dict) or not isinstance(raw.get("answers"), dict):
        raise SandboxError("INVALID_TYPED_ENVELOPE")
    a = raw["answers"]
    return (
        _read_noul(a, "q_scam"),
        _read_noul(a, "q_pressure"),
        _read_noul(a, "q_current_exposure"),
        _read_noul(a, "q_payment_anomaly"),
        _read_choice(a, "q_request_scope", "sensitive_request"),
    )


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1 / (1 + exp(-min(z, 700)))
    e = exp(max(z, -700)); return e / (1 + e)


@dataclass(frozen=True)
class FitRow:
    case_id: str
    family_id: str
    split: str
    origin: str
    features: tuple[float, ...]
    label: int

    def validate(self) -> None:
        if not self.case_id or not self.family_id or self.split not in ("development", "calibration", "locked"):
            raise SandboxError("INVALID_ROW_ID_OR_SPLIT")
        if self.origin not in ("AI_AUTHORED_SYNTHETIC", "HUMAN_ANNOTATED_UNVERIFIED", "HUMAN_INDEPENDENT_ATTESTED"):
            raise SandboxError("INVALID_LABEL_ORIGIN")
        if len(self.features) != len(FEATURE_KEYS) or any(not 0 <= _prob(v) <= 1 for v in self.features):
            raise SandboxError("INVALID_FEATURE_VECTOR")
        if type(self.label) is not int or self.label not in (0, 1):
            raise SandboxError("INVALID_BINARY_LABEL")


@dataclass(frozen=True)
class LogisticModel:
    intercept: float
    weights: tuple[float, ...]
    source_cases_sha256: str
    training_label_origin: str
    sample_size: int
    status: str = STATUS

    def score(self, features: Sequence[float]) -> float:
        if len(features) != len(FEATURE_KEYS):
            raise SandboxError("FEATURE_SCHEMA_MISMATCH")
        return _sigmoid(self.intercept + sum(w * _prob(f) for w, f in zip(self.weights, features)))

    def as_dict(self) -> dict:
        return {"schema_version":"iteraguard-v52-lab-logistic/1", "feature_order":list(FEATURE_KEYS),
                "intercept":self.intercept, "weights":list(self.weights),
                "training_source_hash":self.source_cases_sha256,"training_label_origin":self.training_label_origin,
                "n_train":self.sample_size,"status":self.status,
                "independent_domain_calibration":"NOT_ESTABLISHED", "production_authority":False}


def _audit_rows(rows: Sequence[FitRow], *, permitted_split: str) -> None:
    if not rows: raise SandboxError("EMPTY_DATA")
    cases = set();fam = set(); positive = set()
    for row in rows:
        row.validate()
        if row.split != permitted_split: raise SandboxError("FORBIDDEN_SPLIT_IN_FIT")
        if row.case_id in cases: raise SandboxError("DUPLICATE_CASE_ID")
        cases.add(row.case_id);fam.add(row.family_id);positive.add(row.label)
    if len(positive) < 2: raise SandboxError("SINGLE_CLASS_TRAINING")


def fit_exploratory_logistic(rows: Sequence[FitRow], *, steps: int = 2000, l2: float = 0.1) -> LogisticModel:
    """Train for experiment ONLY. Cannot grant model production approval."""
    _audit_rows(rows, permitted_split="development")
    if not (1 <= steps <= 30000) or type(l2) is not float or not 0 <= l2 <= 10:
        raise SandboxError("INVALID_HYPERPARAMETERS")
    n = len(rows); w = [0.0] * len(FEATURE_KEYS);b = 0.0
    # Deterministic projected gradient, scale normalized to [0,1]; no dependency on sklearn.
    for i in range(steps):
        gb = 0.; gw = [0.]*len(w)
        for r in rows:
            e = _sigmoid(b + sum(a*x for a,x in zip(w,r.features))) - r.label
            gb += e
            for j,x in enumerate(r.features): gw[j] += e*x
        rate = .15/(1+i/750)
        b -= rate*(gb/n)
        for j in range(len(w)): w[j] -= rate*(gw[j]/n + l2*w[j])
    source = [{"id":r.case_id,"family":r.family_id,"label":r.label,"x":list(r.features),"origin":r.origin} for r in sorted(rows,key=lambda r:r.case_id)]
    digest=sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return LogisticModel(b,tuple(w),digest, "MIXED" if len({r.origin for r in rows})>1 else rows[0].origin,len(rows))


def validate_split_isolation(*groups: Sequence[FitRow]) -> None:
    used={}
    for g in groups:
        for row in g:
            row.validate()
            if row.family_id in used and used[row.family_id] != row.split:
                raise SandboxError("FAMILY_LEAKAGE_BETWEEN_SPLITS")
            used[row.family_id]=row.split


def decision_threshold(c_false_positive: float, c_false_negative: float) -> float:
    """p*=CFP/(CFP+CFN); requires *validated event probability* and comparable utility units."""
    if any(type(v) not in (int,float) or not isfinite(v) or v<=0 for v in (c_false_positive,c_false_negative)):
        raise SandboxError("INVALID_ACTION_COSTS")
    return c_false_positive/(c_false_positive+c_false_negative)


def request_reasoning(top_option_probability: float, *, threshold: float=T_REASONING_DEFAULT,
                      question_has_checkable_answer: bool=True, budget_available: bool=True) -> bool:
    _prob(top_option_probability); _prob(threshold)
    return question_has_checkable_answer and budget_available and top_option_probability < threshold


def decision_utility(action: str, label: int, *, c_fp: float,c_fn: float) -> float:
    decision_threshold(c_fp,c_fn)
    if action not in ("warn","pass") or type(label) is not int or label not in (0,1):
        raise SandboxError("INVALID_ACTION_OR_LABEL")
    return -c_fp if action=="warn" and label==0 else (-c_fn if action=="pass" and label==1 else 0.0)


def empirical_delta(cases: Sequence[Mapping], *, c_fp:float,c_fn:float,c_reason:float=0.0,
                    seed:int=51, bootstrap_rounds:int=400)->dict:
    """Paired comparison; same observed cases, cost in common utility units.

    `p_direct`/`p_reasoned` MUST be independently calibrated probabilities of
    the target event, not raw q_scam noul values. Enforced by caller provenance.
    """
    p_star=decision_threshold(c_fp,c_fn)
    if type(c_reason) not in (int,float) or not isfinite(c_reason) or c_reason<0:
        raise SandboxError("INVALID_REASONING_COST")
    if not cases:raise SandboxError("EMPTY_COMPARISON")
    gains=[]; changes=0; families={};seen=set()
    for row in cases:
        if row.get("probability_kind") != "INDEPENDENTLY_CALIBRATED_EVENT_PROBABILITY":
            raise SandboxError("UNVERIFIED_PROBABILITY_SEMANTICS")
        if row.get("case_id") in seen or not row.get("case_id") or not row.get("family_id"):
            raise SandboxError("DUPLICATE_OR_MISSING_CASE_ID")
        seen.add(row['case_id'])
        p0,p1=_prob(row['p_direct']),_prob(row['p_reasoned']);label=row['label']
        a0='warn' if p0>=p_star else 'pass';a1='warn' if p1>=p_star else 'pass'
        diff=decision_utility(a1,label,c_fp=c_fp,c_fn=c_fn)-decision_utility(a0,label,c_fp=c_fp,c_fn=c_fn)-c_reason
        gains.append(diff);changes+=a0!=a1;families.setdefault(row['family_id'],[]).append(diff)
    rng=random.Random(seed); fam=list(families);boot=[]
    for _ in range(bootstrap_rounds):
        obs=[]
        for f in (rng.choice(fam) for _ in fam):obs.extend(families[f])
        boot.append(sum(obs)/len(obs))
    boot.sort(); lo=boot[int(.025*(len(boot)-1))] if boot else None;hi=boot[int(.975*(len(boot)-1))] if boot else None
    return {"n":len(gains),"families":len(fam),"action_change_rate":changes/len(gains),
            "net_gain_per_case":sum(gains)/len(gains),"paired_family_bootstrap_95pct":[lo,hi],
            "assumed_costs":{"false_positive":c_fp,"false_negative":c_fn,"reasoning":c_reason},
            "p_action":p_star,"p_reasoning":T_REASONING_DEFAULT,
            "production_gain_certified":False,"data_provenance_verified_by_module":False}


def inverse_odds_check(probability: float, *, prior: float) -> dict:
    """Algebraic inverse only. NOT an independent corroboration or Bayesian truth test."""
    p=_prob(probability); prior=_prob(prior)
    if not 0<p<1 or not 0<prior<1:raise SandboxError("ODDS_REQUIRE_INTERIOR_PROBABILITIES")
    posterior_log_odds=log(p/(1-p));prior_log_odds=log(prior/(1-prior))
    return {"log_likelihood_ratio_if_priors_valid":posterior_log_odds-prior_log_odds,
            "round_trip_probability":_sigmoid(posterior_log_odds),
            "independent_verification":False,"assumes_valid_posterior_and_known_prior":True}


def review_only_signal(raw: Mapping, model: LogisticModel) -> dict:
    features=extract_features(raw)
    return {"schema_version":"iteraguard-v52-sandbox-observation/1", "features":dict(zip(FEATURE_KEYS,features)),
            "exploratory_model_score":model.score(features),"score_is_verified_fraud_probability":False,
            "model_identity_attested":False,"action_permission":"NONE", "may_override_v51_policy":False,
            "status":STATUS,"candidate_model_hash":sha256(json.dumps(model.as_dict(),sort_keys=True).encode()).hexdigest()}
