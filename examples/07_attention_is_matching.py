"""Purpose: the attention correspondence: the KV cache is a space each step
rewrites, attend is four let* lines, causal masking is just state, and the
whole layer equals torch's answer while staying a symbolic program.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done, skip

try:
    import torch
except ImportError:
    skip("torch is not installed")

import pettorch
from petta import MeTTa, S, decode, expr, val

m = MeTTa().fresh_space()
pettorch.install(m)

torch.manual_seed(0)
wq, wk, wv = (torch.randn(4, 4) for _ in range(3))
m.add(S.proj(S.q, val(wq)), S.proj(S.k, val(wk)), S.proj(S.v, val(wv)))
m.run("""
(= (proj-of $n) (match (context-space) (proj $n $w) $w))
(= (kv-keys) (stack (collapse (match (context-space) (kv $t $k $v) $k))))
(= (kv-vals) (stack (collapse (match (context-space) (kv $t $k $v) $v))))
(= (attend $q)
   (let* (($K (kv-keys)) ($V (kv-vals))
          ($w (softmax (t/ (matmul $K $q) (sqrt-math 4.0)))))
         (matmul (t-transpose $V 0 1) $w)))
(= (step! $t $x)
   (let* (($k (matmul (proj-of k) $x))
          ($v (matmul (proj-of v) $x))
          ($written (add-atom (context-space) (kv $t $k $v))))
         (attend (matmul (proj-of q) $x))))
""")

tokens = [torch.randn(4) for _ in range(4)]
ks, vs = [], []
for t, x in enumerate(tokens, start=1):
    (answer,) = m.eval(expr(S["step!"], t, val(x)))
    ks.append(wk @ x)
    vs.append(wv @ x)
    K, V = torch.stack(ks), torch.stack(vs)
    reference = V.T @ torch.softmax((K @ (wq @ x)) / 2.0, dim=-1)
    assert torch.allclose(decode(answer), reference, atol=1e-5)
check("four decoder steps equal torch", True)
check("the cache is atoms", len(m.query("(kv $t $k $v)")), 4)
done("07_attention_is_matching")
