"""Optional persistent public Zoro generation baseline. No typed decisions or action authority."""
import argparse,hashlib,json,threading,time
from http.server import ThreadingHTTPServer
from pathlib import Path
from integration.v48 import SOURCE_ROOT
from prototype.server import Handler as SecureHandler
from .generation_probe import parse_generation_label

EXPECTED='fb015df41f21b290d0103a35a23859144b6add47686190fa4aa75be7ca9c24b1'

class Generator:
    def __init__(self,path):
        import torch,transformers
        self.torch=torch;self.lock=threading.Lock()
        digest=hashlib.sha256()
        with (path/'model.safetensors').open('rb') as f:
            while block:=f.read(1024*1024):digest.update(block)
        if digest.hexdigest()!=EXPECTED:raise ValueError('CHECKPOINT_HASH_MISMATCH')
        self.tokenizer=transformers.AutoTokenizer.from_pretrained(path,local_files_only=True)
        self.model=transformers.AutoModelForCausalLM.from_pretrained(path,local_files_only=True,
            dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda').eval()
    def infer(self,text):
        with self.lock:
            prompt='Classify this synthetic Korean utterance as DIRECT_REQUEST, WARNING, or UNCLEAR. Output one label only.\n'+text
            inputs=self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],add_generation_prompt=True,
                enable_thinking=False,return_dict=True,return_tensors='pt').to('cuda')
            eos=sorted({self.tokenizer.eos_token_id,self.tokenizer.convert_tokens_to_ids('<|endoftext|>')})
            self.torch.cuda.synchronize();t=time.monotonic()
            with self.torch.inference_mode():out=self.model.generate(**inputs,max_new_tokens=32,do_sample=False,use_cache=False,eos_token_id=eos)
            self.torch.cuda.synchronize();ms=1000*(time.monotonic()-t)
            answer=self.tokenizer.decode(out[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True)
            label=parse_generation_label(answer)
            return {'mode':'REAL_ZORO_GENERATION_BASELINE','typed_head':False,'usable_as_typed_result':False,
                    'model_id':'trillionlabs/Zoro','weights_sha256':EXPECTED,'label':label,
                    'output_contract':'VALID' if label else 'INVALID','latency_ms':ms,
                    'notice':'생성 레이블 비교용이며 정책·확인 작업에는 적용하지 않습니다.'}

class Handler(SecureHandler):
    def do_GET(self):
        if not self._origin_safe():return self.out(403,{'error':'LOCAL_HOST_ONLY'})
        if self.path=='/health':return self.out(200,{'mode':'REAL_ZORO_GENERATION_BASELINE','typed_head':False})
        return self.out(404,{'error':'NOT_FOUND'})
    def do_POST(self):
        if not self._origin_safe() or not self._request_context_safe():return self.out(403,{'error':'UNTRUSTED_REQUEST_CONTEXT'})
        if self.path!='/generate':return self.out(404,{'error':'NOT_FOUND'})
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':return self.out(415,{'error':'JSON_ONLY'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=5000:raise ValueError()
            def unique(pairs):
                d={}
                for k,v in pairs:
                    if k in d:raise ValueError()
                    d[k]=v
                return d
            body=json.loads(self.rfile.read(n),object_pairs_hook=unique)
            if type(body) is not dict or set(body)!={'text','synthetic_only'} or body['synthetic_only'] is not True:raise ValueError()
            text=body['text']
            if type(text) is not str or not text.strip() or len(text)>300:raise ValueError()
        except (ValueError,TypeError,UnicodeError):return self.out(400,{'error':'INVALID_SYNTHETIC_INPUT'})
        try:return self.out(200,self.server.generator.infer(text))
        except Exception:return self.out(503,{'error':'GENERATION_FAILED','mode':'GENERATION_UNAVAILABLE'})

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--port',type=int,default=8010);a=p.parse_args()
    generator=Generator(a.model)
    with ThreadingHTTPServer(('127.0.0.1',a.port),Handler) as s:
        s.generator=generator
        print(f'PUBLIC ZORO GENERATION ONLY on 127.0.0.1:{a.port}; SHA256 {EXPECTED}',flush=True)
        s.serve_forever()
if __name__=='__main__':main()
