"""Loopback-only UI/API, synthetic text; python -m arena.server."""
import argparse
import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from integration.v48 import SOURCE_ROOT, bridge
from prototype.server import Handler as SecureHandler
from .store import Arena,Conflict
from .generation_client import compare
from urllib.error import URLError

class Handler(SecureHandler):
    server_version='dmsg-arena/5.6'
    _inference_slot=threading.BoundedSemaphore(1)
    def _infer_once(self, call):
        if not self._inference_slot.acquire(blocking=False):
            return self.out(429,{'error':'MODEL_BUSY_RETRY_LATER'})
        try:return self.out(200,call())
        finally:self._inference_slot.release()
    def do_GET(self):
        if not self._origin_safe():return self.out(403,{'error':'LOCAL_HOST_ONLY'})
        u=urlsplit(self.path)
        if u.path=='/api/manifest':
            try:return self.out(200,self.server.arena.manifest())
            except (bridge.ContractError,OSError,KeyError,ValueError):return self.out(503,{'error':'EXECUTION_CONTRACT_UNAVAILABLE'})
        if u.path=='/api/evidence':
            from arena.evidence import export_session
            try:return self.out(200,export_session(self.server.arena,parse_qs(u.query).get('session_id',[''])[0]))
            except Conflict as e:return self.out(404,{'error':str(e)})
            except bridge.ContractError:return self.out(503,{'error':'EXECUTION_CONTRACT_UNAVAILABLE'})
            except ValueError:return self.out(400,{'error':'INVALID_REQUEST'})
        if u.path=='/api/state':
            try:return self.out(200,self.server.arena.read(parse_qs(u.query).get('session_id',[''])[0]))
            except Conflict as e:return self.out(404,{'error':str(e)})
            except ValueError:return self.out(400,{'error':'INVALID_REQUEST'})
        names={'/':'index.html','/main.js':'main.js','/style.css':'style.css','/visual.js':'visual.js'}
        if u.path not in names:return self.out(404,{'error':'NOT_FOUND'})
        data=(Path(__file__).parent/'web'/names[u.path]).read_bytes()
        self.send_response(200);self.headers_safe('text/javascript; charset=utf-8' if u.path.endswith('.js') else 'text/css; charset=utf-8' if u.path.endswith('.css') else 'text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_POST(self):
        if not self._origin_safe() or not self._request_context_safe():return self.out(403,{'error':'UNTRUSTED_REQUEST_CONTEXT'})
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':return self.out(415,{'error':'JSON_ONLY'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=18000:return self.out(413,{'error':'INVALID_PAYLOAD_SIZE'})
            def unique(pairs):
                d={}
                for k,v in pairs:
                    if k in d:raise ValueError('DUPLICATE_JSON_KEY')
                    d[k]=v
                return d
            body=json.loads(self.rfile.read(length),object_pairs_hook=unique)
            if type(body) is not dict:raise ValueError('OBJECT_REQUIRED')
            if self.path=='/api/start':
                if body:raise ValueError('START_TAKES_NO_ARGS')
                return self.out(200,self.server.arena.start())
            if self.path=='/api/close':return self.out(200,self.server.arena.close(**body))
            if self.path=='/api/reopen':return self.out(200,self.server.arena.reopen(**body))
            if self.path=='/api/generation-compare':
                if set(body)!={'text','synthetic_only'} or body['synthetic_only'] is not True:raise ValueError('SYNTHETIC_ONLY_REQUIRED')
                if type(body['text']) is not str or not body['text'].strip() or len(body['text'])>300:raise ValueError('INVALID_COMPARISON_TEXT')
                try:return self._infer_once(lambda: compare(body['text']))
                except URLError:return self.out(503,{'mode':'GENERATION_UNAVAILABLE','error':'LOCAL_GENERATION_NOT_AVAILABLE'})
                except (ValueError,TypeError,UnicodeError):return self.out(502,{'mode':'GENERATION_UNAVAILABLE','error':'INVALID_GENERATION_RESPONSE'})
            if self.path=='/api/evaluate':return self._infer_once(lambda: self.server.arena.evaluate(**body))
            return self.out(404,{'error':'NOT_FOUND'})
        except Conflict as e:return self.out(409,{'error':str(e)})
        except bridge.ContractError:return self.out(503,{'error':'EXECUTION_CONTRACT_UNAVAILABLE'})
        except (ValueError,TypeError,UnicodeError):return self.out(400,{'error':'INVALID_REQUEST'})

def main():
    # Preserve fingerprint-bound legacy policy sources while making Windows
    # direct module launches use the same UTF-8 mode as run_hackathon.ps1.
    if not sys.flags.utf8_mode:
        os.execv(sys.executable,[sys.executable,'-X','utf8','-m','arena.server',*sys.argv[1:]])
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8769);p.add_argument('--db',default='runs/arena.sqlite3')
    p.add_argument('--policy',choices=['legacy','dra'],default='legacy');a=p.parse_args()
    from integration import v51
    arena=Arena(a.db,policy_id=a.policy,profile_id=v51.selected_profile(a.policy))
    with ThreadingHTTPServer(('127.0.0.1',a.port),Handler) as server:
        server.arena=arena
        print(f'http://127.0.0.1:{a.port} - SYNTHETIC ONLY / model identity UNATTESTED',flush=True)
        server.serve_forever()
if __name__=='__main__':main()
