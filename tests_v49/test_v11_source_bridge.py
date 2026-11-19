import copy
import unittest
from experiments.contracts import ContractError
from experiments.run import load_cases, execute
from integration.v48 import bridge, convert, source_contract
from integration.v48_replay import stub_raw
from pathlib import Path


class SourceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.case=load_cases(Path(__file__).resolve().parents[1]/'data/development.jsonl')[2]

    def test_seven_questions_extracted_not_invented(self):
        contract=source_contract()
        self.assertEqual(len(contract['spec']),7)
        self.assertEqual(set(contract['wire_questions']),set(contract['spec']))

    def test_probability_mapping_preserves_actual_mass(self):
        raw=stub_raw(self.case);trace=convert(self.case['text'],raw,12.5)
        self.assertEqual(trace['answers']['q_action']['probabilities']['money_transfer'],raw['answers']['q_action']['probabilities']['transfer'])
        self.assertEqual(trace['inference_mode'],'MODEL_RESPONSE_UNATTESTED')

    def test_original_policy_exactly_recomputed(self):
        raw=stub_raw(self.case);trace=convert(self.case['text'],raw,12.5)
        self.assertEqual(trace['reference_outcome'],bridge.advisory(self.case['text'],raw)['action'])
        self.assertEqual(trace['source_diagnostics']['source_threshold'],.70)

    def test_model_anchor_not_promoted_to_independent_proof(self):
        trace=convert(self.case['text'],stub_raw(self.case),1)
        self.assertTrue(trace['evidence'])
        self.assertTrue(all(e['origin']=='MODEL_PROPOSED' for e in trace['evidence']))

    def test_missing_optional_is_preserved(self):
        raw=stub_raw(self.case);del raw['answers']['q_evidence']
        trace=convert(self.case['text'],raw,1)
        self.assertIn('q_evidence',trace['source_diagnostics']['dropped_optional'])

    def test_missing_required_and_nan_rejected(self):
        raw=stub_raw(self.case);del raw['answers']['q_action']
        with self.assertRaises(ValueError):convert(self.case['text'],raw,1)
        raw=stub_raw(self.case);raw['answers']['q_scam']['noul']=float('nan')
        with self.assertRaises(ValueError):convert(self.case['text'],raw,1)

    def test_source_cannot_attest_live_identity(self):
        with self.assertRaises(ContractError):convert(self.case['text'],stub_raw(self.case),1,'REAL_ZORO')

    def test_source_input_is_not_mutated(self):
        raw=stub_raw(self.case);before=copy.deepcopy(raw)
        convert(self.case['text'],raw,1)
        self.assertEqual(raw,before)


if __name__=='__main__':unittest.main()
