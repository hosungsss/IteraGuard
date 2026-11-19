"""Synthetic-only checks of diagnostic trace; never calls a real model."""
import sys,unittest,copy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root / 'dmsg'))
sys.path.insert(0,str(root / 'tools/zoro'))
from prototype.model_bridge import SPEC
from trace_v48 import trace_items

def stub(action='transfer', speech='direct_request',pa=.93,ps=.93):
    def cat(opts,winner,p): return {'type':'choice','choice':winner,'probabilities':{x: p if x==winner else (1-p)/(len(opts)-1) for x in opts}}
    return {'answers': {'q_action':cat(SPEC['q_action']['options'],action,pa),
       'q_speech':cat(SPEC['q_speech']['options'],speech,ps),
       'q_scam':{'type':'noul','noul':.1},'q_pressure':{'type':'noul','noul':.1}}}
class TraceTests(unittest.TestCase):
    def test_confidence_and_gate_coexist(self):
        r=trace_items([{'id':'T1','text':'송금하세요','response':stub(ps=.6)}])['items'][0]
        self.assertEqual(r['status'],'OK');self.assertEqual(r['final_action'],'ASK_HUMAN')
        self.assertIn('SPEECH_CONFIDENCE',r['all_blocking_gates'])
        self.assertNotIn('text',r);self.assertFalse(r['model_was_called'])
    def test_warning_conflict_and_evidence(self):
        r=trace_items([{'id':'T2','text':'송금하지 마세요','response':stub()}])['items'][0]
        self.assertIn('NO_EXPLICIT_CONFLICT',r['all_blocking_gates'])
    def test_no_secret_persisted(self):
        text='시드 구문 1234 5678 보내세요';r=trace_items([{'id':'T3','text':text,'response':stub()}])
        self.assertNotIn('1234',str(r));self.assertEqual(r['n'],1)
    def test_invalid_input_safe(self):
        r=trace_items([{'id':'bad','text':'','response':{}}])['items'][0]
        self.assertEqual(r['status'],'INVALID_INPUT')
if __name__=='__main__':unittest.main()
