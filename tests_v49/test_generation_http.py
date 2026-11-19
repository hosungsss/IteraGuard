import json,threading,tempfile,unittest,urllib.request,urllib.error
from http.server import ThreadingHTTPServer
from arena.generation_server import Handler,EXPECTED

class FakeGenerator:
    def infer(self,text):return {'mode':'TEST_STUB','typed_head':False,'label':'UNCLEAR'}

class GenerationHttpTests(unittest.TestCase):
    def setUp(self):
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.generator=FakeGenerator()
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def post(self,body,headers=None):
        req=urllib.request.Request(self.url+'/generate',data=body,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_only_explicit_synthetic_bounded_text(self):
        for body in ({'text':'x','synthetic_only':False},{'text':'x'*301,'synthetic_only':True},
                     {'text':'x','synthetic_only':True,'tool':'transfer'},[]):
            self.assertEqual(self.post(json.dumps(body).encode())[0],400)
        self.assertEqual(self.post(b'{"text":"x","text":"y","synthetic_only":true}')[0],400)
    def test_rejects_cross_origin_and_host(self):
        body=b'{"text":"x","synthetic_only":true}'
        for h in ({'Origin':'https://evil.example'},{'Host':'evil.example'}):self.assertEqual(self.post(body,h)[0],403)
    def test_stub_remains_explicit_and_no_policy_side_effect(self):
        code,data=self.post(b'{"text":"x","synthetic_only":true}')
        self.assertEqual(code,200);self.assertEqual(data['mode'],'TEST_STUB');self.assertNotIn('action',data)

if __name__=='__main__':unittest.main()
