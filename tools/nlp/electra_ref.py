"""KoELECTRA-small encoder: weight export + NumPy reference forward pass.

Weights come from the ONNX graph (initializers named by role, MatMul weights identified by the
node that consumes them). MatMul weights and the word-embedding table are stored as symmetric
int8 with one float32 scale per output channel (per row for embeddings); everything else is
float32. The NumPy forward below uses exactly those quantized tensors, so it is the oracle for
the JavaScript implementation (apps/shared/dmsg-nlp.js), and is itself compared against the
official ONNX Runtime on the fp32 graph (tools/nlp/check_parity.py).
"""
from __future__ import annotations
import json, math, struct
from pathlib import Path
import numpy as np

H, HEADS, LAYERS, EMB, FF = 256, 4, 12, 128, 1024
EPS = 1e-12


def load_onnx_weights(path: str) -> dict:
    import onnx
    from onnx import numpy_helper
    m = onnx.load(path)
    init = {t.name: numpy_helper.to_array(t).astype(np.float32) for t in m.graph.initializer}
    w = {k: v for k, v in init.items() if not k.startswith('onnx::')}
    role = {'/embeddings_project/MatMul': 'embeddings_project.weight'}
    for i in range(LAYERS):
        p = f'/encoder/layer.{i}/'
        role.update({p + 'attention/self/query/MatMul': f'encoder.layer.{i}.attention.self.query.weight',
                     p + 'attention/self/key/MatMul': f'encoder.layer.{i}.attention.self.key.weight',
                     p + 'attention/self/value/MatMul': f'encoder.layer.{i}.attention.self.value.weight',
                     p + 'attention/output/dense/MatMul': f'encoder.layer.{i}.attention.output.dense.weight',
                     p + 'intermediate/dense/MatMul': f'encoder.layer.{i}.intermediate.dense.weight',
                     p + 'output/dense/MatMul': f'encoder.layer.{i}.output.dense.weight'})
    for nd in m.graph.node:
        if nd.op_type == 'MatMul' and nd.name in role:
            src = [x for x in nd.input if x in init]
            assert len(src) == 1, nd.name
            w[role[nd.name]] = init[src[0]]          # already [in, out]
    missing = [v for v in role.values() if v not in w]
    assert not missing, missing
    return w


def quantize(w: dict) -> dict:
    """int8 symmetric: matmul weights per output column, word embeddings per row."""
    q = {}
    for k, v in w.items():
        if k.endswith('.weight') and v.ndim == 2 and k != 'embeddings.position_embeddings.weight' and k != 'embeddings.token_type_embeddings.weight':
            axis = 1 if k == 'embeddings.word_embeddings.weight' else 0   # reduce over this axis
            amax = np.abs(v).max(axis=axis, keepdims=True)
            scale = np.where(amax > 0, amax / 127.0, 1.0).astype(np.float32)
            q[k] = ('i8', np.clip(np.round(v / scale), -127, 127).astype(np.int8), scale.reshape(-1))
        else:
            q[k] = ('f32', v.astype(np.float32), None)
    return q


def dequant(entry, name):
    kind, arr, scale = entry
    if kind == 'f32':
        return arr
    if name == 'embeddings.word_embeddings.weight':
        return arr.astype(np.float32) * scale[:, None]          # embeddings: per row
    return arr.astype(np.float32) * scale[None, :]              # matmul: per output column


def write_bin(q: dict, out: Path) -> dict:
    """Format: 'DMSGNLP1' | u32 header_len | header JSON | aligned tensor blobs."""
    header, blobs, off = {'tensors': {}}, [], 0
    for k in sorted(q):
        kind, arr, scale = q[k]
        b = arr.tobytes()
        pad = (-off) % 4; blobs.append(b'\0' * pad); off += pad
        e = {'dtype': kind, 'shape': list(arr.shape), 'offset': off, 'bytes': len(b),
             'scale_axis': None if scale is None else ('row' if k == 'embeddings.word_embeddings.weight' else 'col')}
        blobs.append(b); off += len(b)
        if scale is not None:
            pad = (-off) % 4; blobs.append(b'\0' * pad); off += pad
            sb = scale.astype(np.float32).tobytes(); e['scale_offset'] = off; e['scale_len'] = len(scale)
            blobs.append(sb); off += len(sb)
        header['tensors'][k] = e
    hj = json.dumps(header, separators=(',', ':')).encode()
    hj += b' ' * ((-(len(hj) + 12)) % 4)
    data = b'DMSGNLP1' + struct.pack('<I', len(hj)) + hj + b''.join(blobs)
    out.write_bytes(data)
    return {'bytes': len(data), 'tensors': len(q)}


def read_bin(path: Path) -> dict:
    d = path.read_bytes(); assert d[:8] == b'DMSGNLP1'
    hl = struct.unpack('<I', d[8:12])[0]; header = json.loads(d[12:12 + hl]); base = 12 + hl
    q = {}
    for k, e in header['tensors'].items():
        dt = np.int8 if e['dtype'] == 'i8' else np.float32
        arr = np.frombuffer(d, dtype=dt, count=int(np.prod(e['shape'])), offset=base + e['offset']).reshape(e['shape'])
        sc = np.frombuffer(d, dtype=np.float32, count=e['scale_len'], offset=base + e['scale_offset']) if 'scale_offset' in e else None
        q[k] = (e['dtype'], arr, sc)
    return q


def layer_norm(x, g, b):
    mu = x.mean(-1, keepdims=True); var = ((x - mu) ** 2).mean(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + EPS) * g + b


def gelu(x):
    erf = np.vectorize(math.erf)
    return 0.5 * x * (1.0 + erf(x / math.sqrt(2.0)))


def forward(W: dict, ids: list[int]) -> np.ndarray:
    """Single sequence, no padding. Returns last_hidden_state [L, 256]."""
    g = lambda k: W[k]
    L = len(ids)
    x = g('embeddings.word_embeddings.weight')[ids] + g('embeddings.position_embeddings.weight')[:L] + g('embeddings.token_type_embeddings.weight')[0]
    x = layer_norm(x, g('embeddings.LayerNorm.weight'), g('embeddings.LayerNorm.bias'))
    x = x @ g('embeddings_project.weight') + g('embeddings_project.bias')
    dh = H // HEADS
    for i in range(LAYERS):
        p = f'encoder.layer.{i}.'
        qm = x @ g(p + 'attention.self.query.weight') + g(p + 'attention.self.query.bias')
        km = x @ g(p + 'attention.self.key.weight') + g(p + 'attention.self.key.bias')
        vm = x @ g(p + 'attention.self.value.weight') + g(p + 'attention.self.value.bias')
        ctx = np.zeros_like(x)
        for h in range(HEADS):
            s = slice(h * dh, (h + 1) * dh)
            sc = qm[:, s] @ km[:, s].T / math.sqrt(dh)
            sc = np.exp(sc - sc.max(-1, keepdims=True)); sc /= sc.sum(-1, keepdims=True)
            ctx[:, s] = sc @ vm[:, s]
        a = ctx @ g(p + 'attention.output.dense.weight') + g(p + 'attention.output.dense.bias')
        x = layer_norm(a + x, g(p + 'attention.output.LayerNorm.weight'), g(p + 'attention.output.LayerNorm.bias'))
        f = gelu(x @ g(p + 'intermediate.dense.weight') + g(p + 'intermediate.dense.bias'))
        f = f @ g(p + 'output.dense.weight') + g(p + 'output.dense.bias')
        x = layer_norm(f + x, g(p + 'output.LayerNorm.weight'), g(p + 'output.LayerNorm.bias'))
    return x


def pooled(hidden: np.ndarray) -> np.ndarray:
    """Feature vector used by the heads: [CLS ; mean over tokens] (512 dims)."""
    return np.concatenate([hidden[0], hidden.mean(0)]).astype(np.float32)
