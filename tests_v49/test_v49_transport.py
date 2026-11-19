import unittest
from arena.generation_client import validate_result
from arena.generation_server import EXPECTED

class ResultBoundaryTests(unittest.TestCase):
    def base(self):return dict(mode='REAL_ZORO_GENERATION_BASELINE',typed_head=False,usable_as_typed_result=False,
                              weights_sha256=EXPECTED,label='UNCLEAR',output_contract='VALID',latency_ms=1.0)
    def test_valid_does_not_acquire_policy_authority(self):
        out=validate_result(self.base());self.assertFalse(out['usable_as_typed_result']);self.assertNotIn('action',out)
    def test_malformed_labels_modes_identity_and_latencies_fail_closed(self):
        for patch in ({'label':[]},{'label':{}},{'label':'SAFE'},{'latency_ms':True},{'latency_ms':float('nan')},
                      {'typed_head':True},{'weights_sha256':'forged'},{'output_contract':'INVALID'}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):validate_result({**self.base(),**patch})
