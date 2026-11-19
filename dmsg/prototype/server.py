"""Local-only stdlib browser demo. Run: python -m prototype.server

Bind to loopback only. No cookies, network APIs, raw transcript logs, bank
integration, telephony interception, or hidden inference. Synthetic fixtures.
"""
from __future__ import annotations
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from .session import Store, Conflict
from .fixtures import CASES
from .paylock import PaylockStore, PaylockError, public_examples

STORE = Store()
PAYLOCK_STORE = PaylockStore()
WEB = Path(__file__).resolve().parents[1] / 'web'

class Handler(BaseHTTPRequestHandler):
    server_version='dmsg-local/4.4'
    sys_version=''
    def log_message(self, fmt, *args):
        # Avoid logging raw request paths, payloads or participant text.
        return

    def headers_safe(self, type_='application/json; charset=utf-8'):
        self.send_header('Content-Type',type_)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

    def out(self, code, data):
        raw=json.dumps(data,ensure_ascii=False,sort_keys=True).encode('utf8')
        self.send_response(code)
        self.headers_safe()
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _origin_safe(self):
        # DNS-rebinding defense for a local demonstration server.
        # Multiple Host values create ambiguous routing/security checks.
        if len(self.headers.get_all('Host', [])) != 1:
            return False
        host=self.headers.get('Host','').lower().strip()
        port=getattr(getattr(self,'server',None),'server_port',8765)
        return host in (f'127.0.0.1:{port}',f'localhost:{port}',f'[::1]:{port}')

    def do_GET(self):
        if not self._origin_safe():
            return self.out(403,{'error':'LOCAL_HOST_ONLY'})
        path=urlsplit(self.path).path
        if path=='/api/paylock/fixtures':
            return self.out(200,public_examples())
        if path=='/api/model-status':
            from .model_bridge import ModelClient
            return self.out(200,ModelClient().status())
        if path=='/api/fixtures':
            return self.out(200,{'mode':'FIXTURE / SIMULATED','fixtures':[{'id':x.id,'title':x.title,'family':x.family,'text':x.transcript,'story':x.story} for x in CASES]})
        name= 'index.html' if path in ('/','/index.html') else 'paylock.html' if path=='/paylock.html' else 'paylock.js' if path=='/paylock.js' else 'main.js' if path == '/main.js' else 'style.css' if path == '/style.css' else None
        if name is None:
            return self.out(404,{'error':'NOT_FOUND'})
        data=(WEB/name).read_bytes()
        self.send_response(200)
        self.headers_safe('text/javascript; charset=utf-8' if name in ('main.js','paylock.js') else 'text/css; charset=utf-8' if name=='style.css' else 'text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)

    def _request_context_safe(self):
        # Ambiguous client provenance headers are rejected, not first-value trusted.
        if len(self.headers.get_all('Origin', [])) > 1 or len(self.headers.get_all('Sec-Fetch-Site', [])) > 1:
            return False
        origin=self.headers.get('Origin')
        port=getattr(getattr(self,'server',None),'server_port',8765)
        if origin is not None and origin not in (
            f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
            return False
        if self.headers.get('Sec-Fetch-Site','same-origin') not in ('same-origin','none'):
            return False
        # Reject ambiguous content framing. No chunked request parser exists.
        if len(self.headers.get_all('Content-Length',[]))!=1:
            return False
        if self.headers.get('Transfer-Encoding') is not None:
            return False
        return True

    def do_POST(self):
        if not self._origin_safe():
            return self.out(403,{'error':'LOCAL_HOST_ONLY'})
        if not self._request_context_safe():
            return self.out(403,{'error':'UNTRUSTED_REQUEST_CONTEXT'})
        path=urlsplit(self.path).path
        if path not in ('/api/start','/api/turn','/api/ack','/api/model-turn','/api/paylock/evaluate','/api/paylock/verify'):
            return self.out(404,{'error':'NOT_FOUND'})
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
            return self.out(415,{'error':'JSON_ONLY'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=5000:
                return self.out(413,{'error':'INVALID_PAYLOAD_SIZE'})
            def unique_keys(pairs):
                obj={}
                for key,value in pairs:
                    if key in obj: raise ValueError('DUPLICATE_JSON_KEY')
                    obj[key]=value
                return obj
            body=json.loads(self.rfile.read(length), object_pairs_hook=unique_keys)
            if not isinstance(body,dict):return self.out(400,{'error':'OBJECT_REQUIRED'})
            if path=='/api/paylock/evaluate':
                if set(body)-{'request_id','requester_id','invoice_id','vendor_id',
                             'sender_email','requested_bank','requested_account','amount_krw',
                             'message','use_model'}:
                    return self.out(400,{'error':'UNKNOWN_FIELD'})
                use_model=body.pop('use_model',False)
                if type(use_model) is not bool:return self.out(400,{'error':'INVALID_MODEL_FLAG'})
                signals=()
                if use_model:
                    from .paylock_model import optional_advisory
                    signals=optional_advisory(body)
                return self.out(200,PAYLOCK_STORE.evaluate(body,model_signals=signals))
            if path=='/api/paylock/verify':
                return self.out(200,PAYLOCK_STORE.record_verification(body))
            if path=='/api/start':
                if body:return self.out(400,{'error':'START_TAKES_NO_ARGS'})
                return self.out(200,STORE.start())
            if path=='/api/model-turn':
                if set(body)-{'session_id','turn_id','version','text'}:return self.out(400,{'error':'UNKNOWN_FIELD'})
                return self.out(200,STORE.process_model(**body))
            if path=='/api/ack':
                if set(body)-{'session_id','event_id','version','choice'}:return self.out(400,{'error':'UNKNOWN_FIELD'})
                return self.out(200,STORE.acknowledge(**body))
            allowed={'session_id','turn_id','version','fixture_id','text','user_asks_review','simulate_failure'}
            if any(k not in allowed for k in body):return self.out(400,{'error':'UNKNOWN_FIELD'})
            data=STORE.process(**body)
            return self.out(200,data)
        except (UnicodeError, json.JSONDecodeError):
            return self.out(400,{'error':'INVALID_JSON'})
        except (Conflict,PaylockError) as exc:
            return self.out(409,{'error':str(exc)[:80]})
        except (TypeError, ValueError):
            return self.out(400,{'error':'INVALID_REQUEST'})


def main():
    host='127.0.0.1';port=8765
    with ThreadingHTTPServer((host,port),Handler) as server:
        print(f'IteraGuard / 의심계 simulated demo: http://{host}:{port}  [NOT LIVE ZORO]',flush=True)
        server.serve_forever()
if __name__=='__main__':main()
