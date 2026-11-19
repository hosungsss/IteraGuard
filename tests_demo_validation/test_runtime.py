import tempfile
import threading
import unittest
from pathlib import Path
from arena.server import Handler
from arena.store import Arena
from integration.v48 import bridge

class Runtime(unittest.TestCase):
    def test_configuration_does_not_claim_connectivity(self):
        with tempfile.TemporaryDirectory() as tmp:
            for enabled in (True,False):
                client=bridge.ModelClient(endpoint='http://127.0.0.1:8008/v1/systemone',model_id='trillionlabs/Zoro-1',enabled=enabled)
                arena=Arena(str(Path(tmp)/'test.db'),client=client)
                state=arena.manifest()['runtime_model']
                self.assertEqual(state['configured'],enabled)
                self.assertEqual(state['connection_test'],'NOT_RUN')
                self.assertFalse(state['identity_verified'])

    def test_inference_capacity_and_release_after_failure(self):
        h=object.__new__(Handler); replies=[]
        h.out=lambda code,body:replies.append((code,body))
        started=threading.Event();release=threading.Event()
        def blocked():started.set();release.wait(3);return {'ok':True}
        worker=threading.Thread(target=lambda:h._infer_once(blocked));worker.start()
        try:
            self.assertTrue(started.wait(1))
            h._infer_once(lambda:self.fail('concurrent inference executed'))
            self.assertEqual(replies[0][0],429)
        finally:release.set();worker.join()
        with self.assertRaises(ValueError):h._infer_once(lambda:(_ for _ in ()).throw(ValueError()))
        h._infer_once(lambda:{'ok':True});self.assertEqual(replies[-1][0],200)

if __name__=='__main__':unittest.main()
