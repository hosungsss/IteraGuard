"""Loopback-only integration; neither API nor stub is a live Zoro inference test."""
import json
import os
import sys
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.server import Handler
from prototype.model_bridge import ModelClient
from test_v35_model_bridge import sample

class StubHandler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path!='/v1/systemone' or len(data.get('questions',{}))!=7:  # v4.5: +q_evidence (PRD v3.3)

            self.send_response(400);self.end_headers();return
        value=sample();value['model']='stub-typed-model';raw=json.dumps(value).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

class HTTPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.worker=threading.Thread(target=cls.host.serve_forever,daemon=True);cls.worker.start()
    @classmethod
    def tearDownClass(cls):cls.host.shutdown();cls.host.server_close()
    def call(self,path,body=None,headers=None):
        url=f'http://127.0.0.1:{self.host.server_port}'+path
        h={'Host':f'127.0.0.1:{self.host.server_port}',**(headers or {})}
        if body is None: req=urllib.request.Request(url,headers=h)
        else:
            raw=json.dumps(body,ensure_ascii=False).encode()
            req=urllib.request.Request(url,data=raw,headers={**h,'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=3) as r:return json.loads(r.read())
    def test_model_status_explicit_unattested(self):
        d=self.call('/api/model-status');self.assertFalse(d['verified_model']);self.assertFalse(d['calibrated'])
    def test_model_turn_disabled_abstains(self):
        s=self.call('/api/start',{})
        d=self.call('/api/model-turn',{'session_id':s['session_id'],'turn_id':'HTTPM1','version':0,'text':'지금 송금하세요'})
        self.assertEqual(d['action'],'ASK_HUMAN');self.assertFalse(d['verified_model'])
        self.assertEqual(d['version'],1)
    def test_host_denial(self):
        url=f'http://127.0.0.1:{self.host.server_port}/api/model-status'
        req=urllib.request.Request(url,headers={'Host':'evil.example'})
        with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(req,timeout=3)
        self.assertEqual(cm.exception.code,403)
    def test_local_modelclient_actual_http_exchange_is_stub_only(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),StubHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            c=ModelClient(endpoint=f'http://127.0.0.1:{server.server_port}/v1/systemone',model_id='stub-typed-model',enabled=True)
            body,ms=c.infer('합성: 송금하세요');self.assertEqual(body['model'],'stub-typed-model')
            self.assertEqual(len(body['answers']),6)  # stub omits optional q_evidence;self.assertGreaterEqual(ms,0)
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
