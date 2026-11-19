"""Evaluation split gate and NPU evidence gate; all input synthetic."""
import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.evaluation_gate import evaluate,EvaluationError,wilson_interval
from scripts.npu_readiness import inventory

def row(name,family,split,gold,action,mode='MOCK'):
    return dict(case_id=name,scenario_family=family,split=split,gold_risky=gold,predicted_action=action,source_mode=mode)

class EvaluationTests(unittest.TestCase):
    def test_metrics_both_error_types_and_abstention(self):
        data=[row('a','a','development',True,'NO_STRONG_SIGNAL'),row('b','b','development',True,'PAUSE_AND_VERIFY'),
              row('c','c','development',False,'PAUSE_AND_VERIFY'),row('d','d','development',False,'ASK_HUMAN')]
        r=evaluate(data);m=r['splits']['development'];self.assertEqual(r['n_total'],4)
        self.assertEqual(m['missed_warning']['rate'],.5);self.assertEqual(m['normal_pause']['rate'],.5)
        self.assertEqual(m['abstention']['rate'],.25)
    def test_family_leakage_rejected(self):
        data=[row('a','same','development',True,'CAUTION'),row('b','same','locked',False,'CAUTION')]
        with self.assertRaisesRegex(EvaluationError,'SCENARIO_FAMILY_LEAKAGE'):evaluate(data)
    def test_duplicate_case_id_rejected(self):
        data=[row('a','x','development',True,'CAUTION'),row('a','y','development',False,'CAUTION')]
        with self.assertRaisesRegex(EvaluationError,'DUPLICATE_CASE_ID'):evaluate(data)
    def test_bad_gold_type_bool_only(self):
        bad=row('a','x','development',True,'CAUTION');bad['gold_risky']=1
        with self.assertRaisesRegex(EvaluationError,'INVALID_LABEL'):evaluate([bad])
    def test_misleading_source_mode_blocked(self):
        bad=row('a','x','development',True,'CAUTION');bad['source_mode']='REAL_ZORO_VERIFIED'
        with self.assertRaisesRegex(EvaluationError,'INVALID_LABEL'):evaluate([bad])
    def test_no_denominator_does_not_report_zero_rate(self):
        r=evaluate([row('a','a','locked',False,'CAUTION')]);self.assertIsNone(r['splits']['locked']['missed_warning']['rate'])
    def test_empty_rejected(self):
        with self.assertRaisesRegex(EvaluationError,'NONEMPTY'):evaluate([])
    def test_wilson_bound(self):
        interval=wilson_interval(0,4);self.assertEqual(interval[0],0);self.assertLessEqual(interval[1],1)
    def test_report_disclaims_real_model(self):
        r=evaluate([row('a','a','locked',True,'PAUSE_AND_VERIFY')])
        self.assertEqual(r['evidence_tier'],'ANNOTATION_ONLY_NO_REAL_MODEL_ATTESTATION')
    def test_annotated_n_can_not_claim_independence(self):
        r=evaluate([row('a','a','locked',True,'PAUSE_AND_VERIFY','CHECKPOINT_VERIFIED')])
        self.assertIn('label correctness not independently verified',r['limits'])

class NPUReadinessTests(unittest.TestCase):
    def test_no_model_means_not_verified(self):
        x=inventory();self.assertFalse(x['actual_npu_inference']=='RUN')
        self.assertEqual(x['status'],'NOT_VERIFIED')
        self.assertIsNone(x['p95_latency_ms'])
    def test_unrecognized_provider_not_claimed(self):
        x=inventory(claimed_backend='GhostNPUExecutionProvider')
        self.assertFalse(x['execution_provider_detected'])
    def test_file_does_not_prove_npu(self):
        x=inventory(model_path=__file__)
        self.assertTrue(x['model_artifact_present'])
        self.assertEqual(x['zoro_typed_head_compatible'],'UNKNOWN')

if __name__=='__main__':unittest.main()


# LAYER V4.2 — NPU feasibility arithmetic and contract-capture tool.
class V42NpuFeasibility(unittest.TestCase):
    def test_weight_memory_arithmetic(self):
        from scripts.npu_readiness import weight_memory_gib
        m=weight_memory_gib(5.0)
        self.assertAlmostEqual(m['bf16'],9.31,places=2);self.assertAlmostEqual(m['int4'],2.33,places=2)
        with self.assertRaises(ValueError):weight_memory_gib(0)
    def test_prefill_budget_is_requirement_not_measurement(self):
        from scripts.npu_readiness import prefill_budget
        b=prefill_budget(900,6,4.0)
        self.assertEqual(b['required_tokens_per_s_if_prefill_per_question'],1350.0)
        self.assertEqual(b['status'],'REQUIREMENT_NOT_MEASUREMENT')
    def test_smoke_probe_uses_product_question_set(self):
        import scripts.smoke_zoro as sz
        from prototype.model_bridge import SPEC
        self.assertEqual(set(sz.questions('x')['questions']),set(SPEC))
        self.assertEqual(sz.shape({'a':[{'b':1.0}]}),{'a':[{'b':'float'}]})
