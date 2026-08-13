"""Purpose: the attention correspondence, run rather than argued. A stored
key is the pattern side and its value the reduction; a query is the ! side;
the KV cache is a space that each step rewrites with add-atom, which is the
fast-weight-programmer reading of a decoder; softmax weighting is a measure
over the match set whose hard limit is symbolic retrieval. A single-head
causal attention layer is written here as MeTTa equations over the space and
held to torch's answer exactly, gradients included, and the knn operation is
shown to be its temperature-to-infinity limit.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

torch = pytest.importorskip("torch")

import pettorch  # noqa: E402
from petta import S, decode, expr, val  # noqa: E402
from petta.arrays import EmbeddingStore  # noqa: E402

D = 4  # head dimension; sqrt is inlined in the MeTTa source below


ATTENTION_PROGRAM = """
(= (kv-keys) (stack (collapse (match (context-space) (kv $t $k $v) $k))))
(= (kv-vals) (stack (collapse (match (context-space) (kv $t $k $v) $v))))

(= (attend $q)
   (let* (($K (kv-keys))
          ($V (kv-vals))
          ($scores (t/ (matmul $K $q) (sqrt-math 4.0)))
          ($w (softmax $scores))
          ($out (matmul (t-transpose $V 0 1) $w)))
         $out))

(= (proj-of $name)
   (match (context-space) (proj $name $w) $w))

(= (step! $t $x)
   (let* (($k (matmul (proj-of k) $x))
          ($v (matmul (proj-of v) $x))
          ($written (add-atom (context-space) (kv $t $k $v)))
          ($q (matmul (proj-of q) $x)))
         (attend $q)))
"""


@pytest.fixture(scope="module")
def tm(metta):
    pettorch.install(metta)
    return metta


def _reference(wq, wk, wv, tokens):
    """Pure torch causal single-head attention over the same weights."""
    outs = []
    ks, vs = [], []
    for x in tokens:
        ks.append(wk @ x)
        vs.append(wv @ x)
        q = wq @ x
        K = torch.stack(ks)
        V = torch.stack(vs)
        w = torch.softmax((K @ q) / (D**0.5), dim=-1)
        outs.append(V.T @ w)
    return outs


def _fresh_attention_space(tm, requires_grad=False):
    torch.manual_seed(7)
    space = tm.fresh_space()
    wq = torch.randn(D, D, requires_grad=requires_grad)
    wk = torch.randn(D, D, requires_grad=requires_grad)
    wv = torch.randn(D, D, requires_grad=requires_grad)
    space.add(S.proj(S.q, val(wq)), S.proj(S.k, val(wk)), S.proj(S.v, val(wv)))
    space.run(ATTENTION_PROGRAM)
    return space, (wq, wk, wv)


def test_the_kv_cache_is_a_space_and_attention_is_equations(tm):
    """Decoder steps through the engine equal torch's causal attention.

    Causal masking is not implemented anywhere: at step t the space only
    holds what was written, so the mask is the state of the knowledge base,
    which is the point of the formulation.
    """
    space, (wq, wk, wv) = _fresh_attention_space(tm)
    tokens = [torch.randn(D) for _ in range(5)]
    reference = _reference(wq, wk, wv, tokens)
    for t, (x, expected) in enumerate(zip(tokens, reference), start=1):
        (answer,) = space.eval(expr(S["step!"], t, val(x)))
        got = decode(answer)
        assert torch.allclose(got, expected, atol=1e-5), f"step {t} diverged"
    # The cache grew one association per step: the fast-weight reading.
    assert len(space.query("(kv $t $k $v)")) == len(tokens)


def test_gradients_flow_through_the_symbolic_attention(tm):
    """The layer is trainable while being a symbolic program: backward
    through five engine-evaluated steps matches torch's gradients."""
    space, (wq, wk, wv) = _fresh_attention_space(tm, requires_grad=True)
    tokens = [torch.randn(D) for _ in range(5)]
    loss = sum(
        decode(space.eval(expr(S["step!"], t, val(x)))[0]).sum()
        for t, x in enumerate(tokens, start=1)
    )
    loss.backward()
    grads = (wq.grad.clone(), wk.grad.clone(), wv.grad.clone())
    assert all(g is not None and g.abs().sum() > 0 for g in grads)

    # The same computation in pure torch, from the same weights.
    wq2 = wq.detach().clone().requires_grad_(True)
    wk2 = wk.detach().clone().requires_grad_(True)
    wv2 = wv.detach().clone().requires_grad_(True)
    reference_loss = sum(o.sum() for o in _reference(wq2, wk2, wv2, tokens))
    reference_loss.backward()
    for got, expected in zip(grads, (wq2.grad, wk2.grad, wv2.grad)):
        assert torch.allclose(got, expected, atol=1e-4)


def test_hard_attention_is_the_symbolic_limit(tm):
    """Sharpening the softmax converges on what knn retrieves: the
    temperature-to-infinity limit of attention is symbolic match.

    Keys are unit vectors, so cosine (knn's metric) and dot (attention's)
    order identically, and the comparison is exact rather than lucky.
    """
    space = tm.fresh_space()
    store = EmbeddingStore(space, name="hard")
    keys = {
        "north": torch.tensor([1.0, 0.0, 0.0, 0.0]),
        "east": torch.tensor([0.0, 1.0, 0.0, 0.0]),
        "up": torch.tensor([0.0, 0.0, 1.0, 0.0]),
    }
    values = {"north": 10.0, "east": 20.0, "up": 30.0}
    for name, k in keys.items():
        store.add(S[name], k)
        space.add(S.stored(S[name], values[name]))

    query = torch.tensor([0.9, 0.3, 0.1, 0.0])

    # Soft attention over the same keys and scalar values, sharpened:
    K = torch.stack(list(keys.values()))
    v = torch.tensor([values[n] for n in keys])
    sharp = torch.softmax(50.0 * (K @ query), dim=-1) @ v

    # The symbolic limit: retrieve the best key, reduce to its value.
    (group,) = space.run(
        "!(let ($who $score) (hard-knn (tensor (0.9 0.3 0.1 0.0)) 1)"
        " (match (context-space) (stored $who $v) $v))"
    )
    hard = float(group[0].value if hasattr(group[0], "value") else group[0])
    assert hard == values["north"]
    assert abs(float(sharp) - hard) < 1e-3  # sharpened soft == hard
