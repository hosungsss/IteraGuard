"""Only the fixed local public-generation comparison endpoint, never a policy adapter."""
import json,math,urllib.request
from .generation_server import EXPECTED

def validate_result(result):
    if type(result) is not dict or result.get('mode')!='REAL_ZORO_GENERATION_BASELINE' or result.get('typed_head') is not False or result.get('usable_as_typed_result') is not False or result.get('weights_sha256')!=EXPECTED:raise ValueError('GENERATION_RESPONSE_CONTRACT')
    label=result.get('label')
    if label is not None and (type(label) is not str or label not in {'DIRECT_REQUEST','WARNING','UNCLEAR'}):raise ValueError('GENERATION_LABEL_CONTRACT')
    if result.get('output_contract') not in {'VALID','INVALID'} or (result['output_contract']=='VALID')!=(label is not None):raise ValueError('GENERATION_LABEL_CONTRACT')
    ms=result.get('latency_ms')
    if type(ms) not in (int,float) or not math.isfinite(ms) or ms<0:raise ValueError('GENERATION_LATENCY_CONTRACT')
    return {k:result[k] for k in ('mode','typed_head','usable_as_typed_result','label','output_contract','latency_ms')}

def compare(text):
    if type(text) is not str or not text.strip() or len(text)>300:raise ValueError('GENERATION_COMPARISON_MAX_300_CHARS')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    data=json.dumps({'text':text,'synthetic_only':True},ensure_ascii=False).encode()
    req=urllib.request.Request('http://127.0.0.1:8010/generate',data=data,headers={'Content-Type':'application/json'})
    with opener.open(req,timeout=30) as r:raw=r.read(16001)
    if len(raw)>16000:raise ValueError('GENERATION_RESPONSE_TOO_LARGE')
    def unique(pairs):
        d={}
        for key,value in pairs:
            if key in d:raise ValueError('DUPLICATE_GENERATION_KEY')
            d[key]=value
        return d
    return validate_result(json.loads(raw,object_pairs_hook=unique))
