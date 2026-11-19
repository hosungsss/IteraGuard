"""Actual public Zoro generation only. NOT Zoro-1 typed decisions; no invented probabilities."""
import argparse,hashlib,json,time,platform
from pathlib import Path

def parse_generation_label(text):
    """Entire output must match; no first-word extraction or fake probabilities."""
    label=text.strip()
    return label if label in {'DIRECT_REQUEST','WARNING','UNCLEAR'} else None

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-sha256');p.add_argument('--stop-mode',choices=['checkpoint','chat'],default='chat');a=p.parse_args()
    if a.out.exists():p.error('Evidence output already exists')
    import torch,transformers
    result={'mode':'LOCAL_GENERATION_UNATTESTED','typed_head':False,'usable_as_typed_result':False,
            'torch':torch.__version__,'transformers':transformers.__version__,'platform':platform.platform(),
            'dtype':'bfloat16','attention':'eager','decoding':'causal_greedy','use_cache':False,
            'max_new_tokens':32,'rows':[]}
    try:
        digest=hashlib.sha256()
        with (a.model/'model.safetensors').open('rb') as f:
            while block:=f.read(1024*1024):digest.update(block)
        result['weights_sha256']=digest.hexdigest()
        if a.expected_sha256 and digest.hexdigest()!=a.expected_sha256:raise ValueError('CHECKPOINT_HASH_MISMATCH')
        if a.expected_sha256=='fb015df41f21b290d0103a35a23859144b6add47686190fa4aa75be7ca9c24b1':
            result.update(mode='REAL_ZORO_GENERATION_BASELINE',model_id='trillionlabs/Zoro',revision='e8b7dc33b6e30b01ba59c46364fced85342ff4ff')
        tokenizer=transformers.AutoTokenizer.from_pretrained(a.model,local_files_only=True)
        t=time.monotonic()
        model=transformers.AutoModelForCausalLM.from_pretrained(a.model,local_files_only=True,
            dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda').eval()
        result.update(load_seconds=time.monotonic()-t,gpu=torch.cuda.get_device_name(0))
        result.update(stop_mode=a.stop_mode,checkpoint_eos=model.generation_config.eos_token_id,
                      tokenizer_eos=tokenizer.eos_token_id)
        generation_kwargs={}
        if a.stop_mode=='chat':
            generation_kwargs['eos_token_id']=sorted({tokenizer.eos_token_id,tokenizer.convert_tokens_to_ids('<|endoftext|>')})
        result['effective_eos']=generation_kwargs.get('eos_token_id',model.generation_config.eos_token_id)
        for cid,text in [('warning','인증번호를 알려주지 마세요.'),('direct','지금 인증번호를 알려주시겠어요?')]:
            prompt='Classify this synthetic Korean utterance as DIRECT_REQUEST, WARNING, or UNCLEAR. Output one label only.\n'+text
            inputs=tokenizer.apply_chat_template([{'role':'user','content':prompt}],add_generation_prompt=True,
                enable_thinking=False,return_dict=True,return_tensors='pt').to('cuda')
            torch.cuda.synchronize();t=time.monotonic()
            with torch.inference_mode():out=model.generate(**inputs,max_new_tokens=32,do_sample=False,use_cache=False,**generation_kwargs)
            torch.cuda.synchronize();ms=1000*(time.monotonic()-t)
            answer=tokenizer.decode(out[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True)
            result['rows'].append({'case_id':cid,'synthetic_only':True,'input_sha256':hashlib.sha256(text.encode()).hexdigest(),
                                   'generated_text':answer,'latency_ms':ms,'not_a_probability_distribution':True,
                                   'accepted_label':parse_generation_label(answer),
                                   'output_contract':'VALID' if parse_generation_label(answer) else 'INVALID'})
        result['valid_label_outputs']=sum(r['output_contract']=='VALID' for r in result['rows'])
        result['output_contract_status']='PASS' if result['valid_label_outputs']==len(result['rows']) else 'FAIL'
        result['status']='PASS_EXECUTION_ONLY'
    except Exception as e:
        result.update(status='FAILED',error_type=type(e).__name__,error=str(e)[:1000])
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='PASS_EXECUTION_ONLY' else 2
if __name__=='__main__':raise SystemExit(main())
