import json,threading,tempfile,unittest,urllib.request,urllib.error
from unittest.mock import patch
from pathlib import Path
from http.server import ThreadingHTTPServer
from arena.server import Handler
from arena.store import Arena
from test_arena import Client

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.arena=Arena(Path(self.temp.name)/'audit.db',Client())
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def call(self,path,body=None,headers=None):
        h={'Content-Type':'application/json',**(headers or {})}
        req=urllib.request.Request(self.url+path,data=body,headers=h)
        try:
            with urllib.request.urlopen(req) as r:return r.status,r.headers,r.read()
        except urllib.error.HTTPError as e:return e.code,e.headers,e.read()
    def test_workflow_roundtrip_and_reload(self):
        code,_,data=self.call('/api/start',b'{}');self.assertEqual(code,200);s=json.loads(data)
        payload={**s,'request_id':'http1','text':'송금하세요.','synthetic_only':True};payload.pop('mode')
        code,_,data=self.call('/api/evaluate',json.dumps(payload).encode());self.assertEqual(code,200)
        result=json.loads(data);self.assertEqual(result['action'],'PAUSE_AND_VERIFY')
        code,_,data=self.call('/api/state?session_id='+s['session_id'])
        self.assertEqual(json.loads(data)['version'],1);self.assertEqual(len(json.loads(data)['tasks']),1)
    def test_origin_host_duplicate_keys_and_unknown_fields(self):
        for path,data,headers,expected in [('/api/start',b'{}',{'Origin':'https://evil.example'},403),
            ('/api/start',b'{}',{'Host':'evil.example'},403),
            ('/api/start',b'{"x":1,"x":2}',{},400),('/api/start',b'{"x":1}',{},400),
            ('/api/start',b'[]',{},400),('/api/evaluate',b'{"tool":"transfer"}',{},400)]:
            with self.subTest(path=path,data=data):self.assertEqual(self.call(path,data,headers)[0],expected)
    def test_ui_external_assets_and_no_inline_script(self):
        code,headers,data=self.call('/');self.assertEqual(code,200)
        self.assertIn('frame-ancestors',headers['Content-Security-Policy'])
        self.assertIn(b'src="/signal.js"',data)
        self.assertEqual(self.call('/signal.js')[0],200)
        self.assertIn(b'src="/main.js"',self.call('/arena')[2])
        self.assertNotIn(b'<script>',data)
        self.assertEqual(self.call('/main.js')[0],200)
        self.assertEqual(self.call('/../store.py')[0],404)
    def test_bad_generation_backend_is_502_not_a_valid_label(self):
        with patch('arena.server.compare',side_effect=ValueError('MALFORMED')):
            code,_,raw=self.call('/api/generation-compare',b'{"text":"x","synthetic_only":true}')
        self.assertEqual(code,502);self.assertEqual(json.loads(raw)['mode'],'GENERATION_UNAVAILABLE')

if __name__=='__main__':unittest.main()
