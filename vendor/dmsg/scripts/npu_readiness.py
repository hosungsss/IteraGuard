"""Hardware readiness inventory, not a Zoro-1 NPU inference benchmark.

No hardware or trained model compatibility is asserted without a real execution trace.
"""
from __future__ import annotations
import argparse,json,platform,importlib.util,sys
from pathlib import Path

# LAYER NPU-FEASIBILITY (v4.2). Arithmetic only, from public model-card facts checked
# 2026-11-01: trillionlabs/Zoro-1 is a Qwen3.5-4B derivative, BF16 safetensors, card
# metadata ~5B parameters, benchmarked on one H100 per server; no ONNX/quantized/NPU
# artifact is published. These numbers are lower bounds for weights only (no KV cache,
# activations, runtime or OS), not measurements.
BYTES_PER_PARAM={'bf16':2.0,'int8':1.0,'int4':0.5}


def weight_memory_gib(params_b: float) -> dict:
    if type(params_b) not in (int,float) or not 0.1<=params_b<=1000:
        raise ValueError('INVALID_PARAMS_B')
    return {k:round(params_b*1e9*v/2**30,2) for k,v in BYTES_PER_PARAM.items()}


def prefill_budget(prompt_tokens: int, questions: int, timeout_s: float) -> dict:
    """A typed decision costs one prefill per evaluated state (public trida page). If the
    server scores questions separately, prefills scale with the question count. Report the
    tokens/second a host must sustain to meet the client timeout; this is a requirement,
    not a measured throughput."""
    if any(type(x) is not int or x<1 for x in (prompt_tokens,questions)) or not 0.5<=timeout_s<=60:
        raise ValueError('INVALID_BUDGET_INPUT')
    return {'prompt_tokens':prompt_tokens,'timeout_s':timeout_s,
            'required_tokens_per_s_if_one_prefill':round(prompt_tokens/timeout_s,1),
            'required_tokens_per_s_if_prefill_per_question':round(prompt_tokens*questions/timeout_s,1),
            'status':'REQUIREMENT_NOT_MEASUREMENT'}


def inventory(model_path:str|None=None, claimed_backend:str|None=None)->dict:
    providers=[]
    if importlib.util.find_spec('onnxruntime') is not None:
        try:
            import onnxruntime as ort
            providers=list(ort.get_available_providers())
        except (ImportError,RuntimeError,OSError):providers=[]
    artifact=Path(model_path).is_file() if model_path else False
    backend=(claimed_backend or '').strip()
    installed=backend in providers if backend else False
    return {
        'status':'NOT_VERIFIED', 'model_identity':'NOT_ATTESTED',
        'model_artifact_present':artifact, 'requested_execution_provider':backend or None,
        'execution_provider_detected':installed, 'available_providers':providers,
        'host_platform':platform.system(), 'host_architecture':platform.machine(),
        'zoro_typed_head_compatible':'UNKNOWN','operator_support':'UNKNOWN',
        'quantization_and_accuracy':'NOT_TESTED','actual_npu_inference':'NOT_RUN',
        'p50_latency_ms':None,'p95_latency_ms':None,'energy_joules':None,
        'note':'Backend listed or model file existing is not evidence that Zoro-1 typed decisions execute on NPU.'}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--model-path',default=None)
    parser.add_argument('--execution-provider',default=None)
    parser.add_argument('--params-b',type=float,default=5.0)
    parser.add_argument('--prompt-tokens',type=int,default=900)
    parser.add_argument('--questions',type=int,default=6)
    parser.add_argument('--timeout-s',type=float,default=4.0)
    args=parser.parse_args(argv)
    out=inventory(args.model_path,args.execution_provider)
    out['weight_memory_gib_lower_bound']=weight_memory_gib(args.params_b)
    out['prefill_requirement']=prefill_budget(args.prompt_tokens,args.questions,args.timeout_s)
    out['published_npu_artifact']='NONE_FOUND_ON_MODEL_CARD_2026-11-01'
    print(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True))

if __name__=='__main__':main()
