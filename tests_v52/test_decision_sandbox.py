"""Deterministic offline tests; no REAL_ZORO1 or independent human data claims."""
import copy, json, math, unittest
from pathlib import Path
from integration.v52_decision_sandbox import (
 SandboxError,FitRow,fit_exploratory_logistic,validate_split_isolation,decision_threshold,
 request_reasoning,empirical_delta,inverse_odds_check,extract_features,review_only_signal)

ROOT=Path(__file__).resolve().parents[1]
RAW_PATH=ROOT/'internal/evidence/v51/experiments/stage5_specified_candidate/specified_raw.jsonl'

def rows(n=48):
 return [FitRow(f'ex{i}',f'fam{i}', 'development','AI_AUTHORED_SYNTHETIC',
     (i%7/6,i%5/4,i%3/2,i%11/10,(i%9)/8), int(i%3==0)) for i in range(n)]

class MiddlewareTests(unittest.TestCase):
 def test_baseline_version_remains_untouched(self):
  self.assertEqual(json.loads((ROOT/'configs/v51_release_selection.json').read_text())['default_profile_by_policy']['legacy'],'v51-specific-candidate')
 def test_five_features(self):
  raw=json.loads(RAW_PATH.read_text().splitlines()[0])['raw'];f=extract_features(raw)
  self.assertEqual(len(f),5);self.assertTrue(all(0<=p<=1 for p in f))
 def test_unsupported_incomplete_profile_fails(self):
  raw=json.loads(RAW_PATH.read_text().splitlines()[0])['raw'];del raw['answers']['q_current_exposure']
  with self.assertRaisesRegex(SandboxError,'MISSING'):extract_features(raw)
 def test_not_probabilities_of_fraud(self):
  model=fit_exploratory_logistic(rows(36),steps=200)
  raw=json.loads(RAW_PATH.read_text().splitlines()[0])['raw'];o=review_only_signal(raw,model)
  self.assertFalse(o['score_is_verified_fraud_probability']);self.assertFalse(o['may_override_v51_policy'])
  self.assertEqual(o['action_permission'],'NONE')
 def test_noul_nan_rejected(self):
  raw=json.loads(RAW_PATH.read_text().splitlines()[0])['raw'];raw['answers']['q_scam']['noul']=float('nan')
  with self.assertRaises(SandboxError):extract_features(raw)
 def test_noul_bool_rejected(self):
  raw=json.loads(RAW_PATH.read_text().splitlines()[0])['raw'];raw['answers']['q_scam']['noul']=True
  with self.assertRaises(SandboxError):extract_features(raw)
 def test_choice_sum_rejected(self):
  raw=json.loads(RAW_PATH.read_text().splitlines()[0])['raw'];raw['answers']['q_request_scope']['probabilities']['sensitive_request']=.99
  with self.assertRaises(SandboxError):extract_features(raw)
 def test_development_only_training(self):
  x=rows(20);x[0]=FitRow('oops','fnew','locked','AI_AUTHORED_SYNTHETIC',x[0].features,1)
  with self.assertRaisesRegex(SandboxError,'FORBIDDEN_SPLIT'):fit_exploratory_logistic(x,steps=100)
 def test_training_deterministic(self):
  a=fit_exploratory_logistic(rows(),steps=120);b=fit_exploratory_logistic(rows(),steps=120)
  self.assertEqual(a.as_dict(),b.as_dict());self.assertTrue(0<a.score([.2]*5)<1)
 def test_no_production_promotion(self):
  self.assertFalse(fit_exploratory_logistic(rows(),steps=100).as_dict()['production_authority'])
 def test_single_class_invalid(self):
  xs=rows(5);xs=[FitRow(x.case_id,x.family_id,x.split,x.origin,x.features,1) for x in xs]
  with self.assertRaises(SandboxError):fit_exploratory_logistic(xs,steps=20)
 def test_family_leakage(self):
  a=rows(2);b=[FitRow('next',a[0].family_id,'calibration',a[0].origin,a[0].features,1)]
  with self.assertRaisesRegex(SandboxError,'FAMILY_LEAKAGE'):validate_split_isolation(a,b)
 def test_threshold_cost_asymmetry(self):
  self.assertAlmostEqual(decision_threshold(1,4),.2)
  self.assertAlmostEqual(decision_threshold(1,1),.5)
 def test_threshold_not_reasoning_threshold(self):
  self.assertTrue(request_reasoning(.69))
  self.assertFalse(request_reasoning(.7))
  self.assertFalse(request_reasoning(.69,question_has_checkable_answer=False))
  self.assertFalse(request_reasoning(.69,budget_available=False))
 def test_reasoning_cost_nonzero(self):
  rows_=[dict(case_id='1',family_id='a',p_direct=.1,p_reasoned=.9,label=1,
             probability_kind='INDEPENDENTLY_CALIBRATED_EVENT_PROBABILITY')]
  out=empirical_delta(rows_,c_fp=1,c_fn=4,c_reason=.4,bootstrap_rounds=40)
  self.assertAlmostEqual(out['net_gain_per_case'],3.6);self.assertFalse(out['production_gain_certified'])
 def test_no_action_change_with_cost(self):
  rows_=[dict(case_id='1',family_id='a',p_direct=.8,p_reasoned=.9,label=1,
             probability_kind='INDEPENDENTLY_CALIBRATED_EVENT_PROBABILITY')]
  out=empirical_delta(rows_,c_fp=1,c_fn=4,c_reason=.2,bootstrap_rounds=50)
  self.assertAlmostEqual(out['net_gain_per_case'],-.2)
 def test_uncalibrated_fails_meu(self):
  x=[dict(case_id='1',family_id='a',p_direct=.5,p_reasoned=.6,label=1,
          probability_kind='RAW_NOUL_Q_SCAM')]
  with self.assertRaisesRegex(SandboxError,'UNVERIFIED_PROBABILITY'):empirical_delta(x,c_fp=1,c_fn=4)
 def test_odds_inverse_not_independent(self):
  out=inverse_odds_check(.7,prior=.1)
  self.assertAlmostEqual(out['round_trip_probability'],.7)
  self.assertFalse(out['independent_verification'])
 def test_bad_probability_rejected(self):
  with self.assertRaises(SandboxError):decision_threshold(float('nan'),1)
  with self.assertRaises(SandboxError):inverse_odds_check(0,prior=.1)
 def test_paired_output_has_denominator(self):
  examples=[dict(case_id=str(i),family_id=str(i//2),p_direct=.4,p_reasoned=.1,label=i%2,
              probability_kind='INDEPENDENTLY_CALIBRATED_EVENT_PROBABILITY') for i in range(8)]
  out=empirical_delta(examples,c_fp=1,c_fn=4,c_reason=.02,bootstrap_rounds=100)
  self.assertEqual(out['n'],8);self.assertEqual(out['families'],4)
 def test_locked_not_used_as_train(self):
  # Defensive test against inadvertently treating source holdout as training data.
  obj=rows(3)[0]
  with self.assertRaises(SandboxError):fit_exploratory_logistic([FitRow(obj.case_id,obj.family_id,'locked',obj.origin,obj.features,1)],steps=5)

if __name__=='__main__': unittest.main()
