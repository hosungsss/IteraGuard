"""SNM time-axis regressions: delayed model answer cannot overwrite newer turns."""
import sys,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.session import Store,Conflict
from test_v35_model_bridge import sample

class HeldModel:
    def __init__(self):
        self.started=threading.Event();self.release=threading.Event()
    def infer(self,text):
        self.started.set()
        if not self.release.wait(2): raise RuntimeError('TEST_TIMEOUT')
        return sample(),5.0

class TemporalSafety(unittest.TestCase):
    def test_delayed_high_confidence_does_not_override_new_turn(self):
        st=Store();sid=st.start()['session_id'];fake=HeldModel();errors=[];results=[]
        def old_call():
            try:results.append(st.process_model(session_id=sid,turn_id='old',version=0,text='송금하세요',client=fake))
            except Exception as e:errors.append(e)
        t=threading.Thread(target=old_call);t.start()
        try:
            self.assertTrue(fake.started.wait(2))
            new=st.process(session_id=sid,turn_id='new',version=0,text='송금하지 마세요')
            self.assertEqual(new['action'],'ASK_HUMAN')
        finally:
            fake.release.set();t.join(3)
        self.assertFalse(t.is_alive())
        self.assertFalse(results)
        self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],Conflict)
        self.assertEqual(str(errors[0]),'STALE_VERSION')
        self.assertTrue(st.verify_audit(sid))
    def test_duplicated_result_mutation_does_not_corrupt_audit(self):
        st=Store();sid=st.start()['session_id'];fake=type('Local',(),{'infer':lambda self,text:(sample(),3.)})()
        a=st.process_model(session_id=sid,turn_id='t0',version=0,text='송금하세요',client=fake)
        a['history'][0]['action']='FORGED';a['probs']['q_scam']['yes']=999
        b=st.process_model(session_id=sid,turn_id='t0',version=0,text='송금하세요',client=fake)
        self.assertNotEqual(b['history'][0]['action'],'FORGED')
        self.assertNotEqual(b['probs']['q_scam']['yes'],999)
        self.assertTrue(st.verify_audit(sid))

if __name__=='__main__':unittest.main()
