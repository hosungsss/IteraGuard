import copy
import unittest
from pathlib import Path

from experiments.contracts import ContractError, strict_json, validate_trace
from experiments.fixtures import trace_for
from experiments.metrics import summarize
from experiments.policy_probe import evaluate
from experiments.run import execute, load_cases, model_input

ROOT=Path(__file__).resolve().parents[1]


class KitTests(unittest.TestCase):
    def setUp(self):
        self.cases=load_cases(ROOT/'data/development.jsonl')

    def test_direct_risk_beats_missing_model(self):
        t=trace_for(self.cases[8]);validate_trace(t,self.cases[8]['text'])
        self.assertEqual(evaluate(t)['outcome'],'PAUSE_AND_VERIFY')

    def test_warning_not_direct_otp(self):
        self.assertEqual(evaluate(trace_for(self.cases[1]))['outcome'],'NO_STRONG_SIGNAL')

    def test_nonfinite_and_duplicate_json_rejected(self):
        for s in ('{"x":NaN}','{"x":1,"x":2}'):
            with self.assertRaises(ContractError):strict_json(s)

    def test_wrong_input_hash_rejected(self):
        with self.assertRaises(ContractError):validate_trace(trace_for(self.cases[0]),'changed')

    def test_span_change_rejected(self):
        t=trace_for(self.cases[2]);t['evidence'][0]['quote']='invented'
        with self.assertRaises(ContractError):validate_trace(t,self.cases[2]['text'])

    def test_low_confidence_is_measurable_not_silently_passed(self):
        t=trace_for(self.cases[9])
        self.assertEqual(evaluate(t,.7)['outcome'],'ASK_HUMAN')
        self.assertEqual(evaluate(t,.6)['outcome'],'NO_STRONG_SIGNAL')

    def test_fixture_cannot_be_live(self):
        t=trace_for(self.cases[2]);t['inference_mode']='REAL_ZORO';t['provenance_ref']='operator-file'
        with self.assertRaises(ContractError):validate_trace(t,self.cases[2]['text'])

    def test_model_proposed_evidence_does_not_authorize(self):
        t=trace_for(self.cases[2]);t['evidence'][0]['origin']='MODEL_PROPOSED'
        self.assertEqual(evaluate(t)['outcome'],'ASK_HUMAN')

    def test_gold_and_fixture_data_not_given_to_adapter(self):
        request=model_input(self.cases[0])
        self.assertEqual(set(request),{'request_id','session_version','latest_turn_id','turns'})

    def test_failures_not_hidden_in_latency(self):
        rows,_=execute(self.cases,'fixture');s=summarize(rows)
        self.assertEqual(s['invalid_or_unavailable']['numerator'],2)
        self.assertEqual(s['latency_ms']['count'],10)

    def test_logs_no_raw_text_or_quote(self):
        _,logs=execute(self.cases,'fixture')
        def check_keys(value):
            if isinstance(value,dict):
                self.assertNotIn('quote',value)
                for item in value.values():check_keys(item)
            elif isinstance(value,list):
                for item in value:check_keys(item)
        check_keys(logs)
        self.assertNotIn(self.cases[0]['text'],str(logs))

    def test_zero_denominator_is_null(self):
        self.assertIsNone(summarize([])['coverage']['rate'])

    def test_missing_required_question_rejected(self):
        t=trace_for(self.cases[0]);del t['answers']['q_speech']
        with self.assertRaises(ContractError):validate_trace(t,self.cases[0]['text'])

    def test_inconsistent_argmax_rejected(self):
        t=trace_for(self.cases[0]);t['answers']['q_action']['selected']='money_transfer'
        with self.assertRaises(ContractError):validate_trace(t,self.cases[0]['text'])

    def test_session_version_rejected(self):
        t=trace_for(self.cases[0]);t['session_version']=0
        with self.assertRaises(ContractError):validate_trace(t,self.cases[0]['text'])


if __name__=='__main__':unittest.main()
