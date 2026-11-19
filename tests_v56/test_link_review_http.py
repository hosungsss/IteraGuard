import json
import os
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from arena.server import Handler
from arena.link_review import LinkReviewer


class ReviewHTTP(TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.link_reviewer=LinkReviewer()
        self.server.arena=SimpleNamespace(client=Mock())
        thread=Thread(target=self.server.serve_forever,daemon=True);thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(thread.join,3);self.addCleanup(self.server.shutdown)
        self.body=dict(text="합성 https://example.org/a",share_host="example.org",synthetic_only=True,local_zoro=True)

    def request(self,body):
        conn=HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        try:
            conn.request('POST','/api/link-review',json.dumps(body),{'Content-Type':'application/json'})
            r=conn.getresponse();return r.status,json.loads(r.read())
        finally:
            conn.close()

    def test_read_only_and_explicit_contract(self):
        with patch.dict(os.environ,{'DMSG_LINK_REVIEW_EXTERNAL':'0'}):
            self.assertEqual(self.request(self.body)[1]['observation']['status'],'OPERATOR_DISABLED')
            self.assertEqual(self.request(dict(self.body,synthetic_only=False))[0],400)
            self.assertEqual(self.request(dict(self.body,share_host=[]))[0],400)
            self.server.arena.client.infer.assert_not_called()

    def test_limit_does_not_make_provider_call(self):
        self.server.link_reviewer.remaining=0
        with patch.dict(os.environ,{'DMSG_LINK_REVIEW_EXTERNAL':'1','SCAMADVISER_API_KEY':'fixture'}), patch('arena.link_review.request_cache') as send:
            self.assertEqual(self.request(self.body)[1]['observation']['status'],'RATE_LIMIT')
            send.assert_not_called()
            self.server.arena.client.infer.assert_not_called()

    def test_offline_evidence_and_shadow_read_through_http(self):
        from datetime import datetime, timezone
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            feed=Path(temp)/"synthetic.csv"
            feed.write_text("url,verified,online\nhttps://example.org/a,yes,yes\n")
            client=self.server.arena.client
            client.infer.return_value=({"answers":{"q_review":{"type":"choice","choice":"verify_first",
                "probabilities":{"verify_first":1,"ask_context":0,"no_sensitive_request":0}}}},0)
            with patch.dict(os.environ,{"DMSG_PHISHTANK_CSV":str(feed),"DMSG_PHISHTANK_AS_OF":datetime.now(timezone.utc).isoformat()}):
                code,out=self.request(dict(self.body,share_host=""))
            self.assertEqual(code,200)
            self.assertEqual(out['observation']['status'],'LISTED_EXACT')
            self.assertEqual(out['shadow_model'],{'status':'TEST_DOUBLE','proposal':'verify_first'})
            self.assertFalse(out['authorized_action'])
            self.assertEqual(json.loads(client.infer.call_args.args[0])['link_observation'],out['observation'])
