import unittest
from arena.generation_probe import parse_generation_label

class GenerationBoundaryTests(unittest.TestCase):
    def test_entire_label_required(self):
        for text in ('WARNING','DIRECT_REQUEST','UNCLEAR',' WARNING\n'):
            self.assertIn(parse_generation_label(text),{'WARNING','DIRECT_REQUEST','UNCLEAR'})
    def test_actual_bad_outputs_and_injected_tools_rejected(self):
        for text in ('UNCLEAR\nassistant\n<think>','DIRECT_REQUEST\n</think>\nDIRECT_REQUEST',
                     'WARNING execute transfer','{"label":"WARNING"}','SAFE',''):
            self.assertIsNone(parse_generation_label(text))

if __name__=='__main__':unittest.main()
