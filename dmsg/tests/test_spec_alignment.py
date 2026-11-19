"""Cross-check current PRD and prompt obligations. Content checks are not model tests."""
from pathlib import Path
import re
import unittest

SKILL=Path(__file__).resolve().parents[1]
ROOT=SKILL.parent
PRD=(SKILL/'references/PRD.md').read_text(encoding='utf8')
SYSTEM=(SKILL/'references/SYSTEM_PROMPT.md').read_text(encoding='utf8')
TRACE=(SKILL/'references/TRACEABILITY.md').read_text(encoding='utf8')

class DocumentContractTests(unittest.TestCase):
    def test_prd_has_40_unique_requirement_definitions(self):
        # Legacy test ID preserved; current upper bound expanded with new contracts.
        ids=re.findall(r'^\|\s*(PRD-\d\d)\s*\|',PRD,re.M)
        self.assertEqual(ids,[f'PRD-{i:02d}' for i in range(1,63)])

    def test_prompt_has_38_unique_guard_rules(self):
        ids=re.findall(r'^\[GUARD-(\d\d) ',SYSTEM,re.M)
        self.assertEqual(ids,[f'{i:02d}' for i in range(1,61)])

    def test_trace_mentions_every_prd_id_once_in_rows(self):
        self.assertTrue(TRACE,'the packaged trace matrix is required')
        ids=re.findall(r'^\|\s*(PRD-\d\d)\s*\|',TRACE,re.M)
        self.assertEqual(ids,[f'PRD-{i:02d}' for i in range(1,63)])

    def test_trace_links_every_prompt_guard(self):
        for i in range(1,61):
            self.assertIn(f'GUARD-{i:02d}',TRACE)

    def test_approved_policy_states_present_in_both(self):
        for action in ('NO_STRONG_SIGNAL','CAUTION','PAUSE_AND_VERIFY','ASK_HUMAN'):
            self.assertIn(action,PRD)
            self.assertIn(action,SYSTEM)

    def test_system_prompt_never_self_attests_model_evidence(self):
        self.assertIn('MODEL_PROPOSED',SYSTEM)
        self.assertIn('REAL_ZORO',SYSTEM)
        self.assertIn('실제',SYSTEM)
        self.assertIn('독립',SYSTEM)

    def test_skill_and_product_docs_are_identical(self):
        if (ROOT/'docs/01_PRODUCT_REQUIREMENTS_PRD_KO.md').is_file():
            self.assertEqual(PRD,(ROOT/'docs/01_PRODUCT_REQUIREMENTS_PRD_KO.md').read_text(encoding='utf8'))
            self.assertEqual(SYSTEM,(ROOT/'docs/02_SYSTEM_PROMPT_AGENT_KO.md').read_text(encoding='utf8'))
            self.assertEqual(TRACE,(ROOT/'docs/03_TRACEABILITY_MATRIX_KO.md').read_text(encoding='utf8'))
        else:
            self.assertTrue(PRD and SYSTEM and TRACE)

    def test_current_runtime_not_mislabeled_real(self):
        config=(SKILL/'config.example.json').read_text(encoding='utf8')
        self.assertIn('"engine_mode": "FIXTURE"',config)
        self.assertIn('"model_attested": false',config)
        self.assertIn('"live_endpoint_verified": false',config)

if __name__=='__main__':unittest.main()
