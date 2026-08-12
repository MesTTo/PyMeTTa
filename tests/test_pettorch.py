"""Purpose: engine-backed tests for the deep torch integration: tensors as
atoms, modules in both directions, architecture reflection, training through
the engine with exact gradient assertions, and knn as nondeterminism. All
synthetic data, CPU only; skipped wholesale without torch.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

torch = pytest.importorskip("torch")

import pettorch  # noqa: E402
from petta import S, V, decode, expr, val  # noqa: E402


@pytest.fixture(scope="session")
def tm(metta):
    """The shared engine with the pettorch op set installed once."""
    pettorch.install(metta)
    return metta


@pytest.fixture()
def fresh(tm):
    return tm.fresh_space()


# ------------------------------------------------------------------ pillar 1


def test_tensor_ops_compose_in_metta(tm):
    r = tm.run("!(t-tolist (matmul (tensor ((1.0 2.0 3.0) (4.0 5.0 6.0))) "
               "(tensor ((7.0 8.0) (9.0 10.0) (11.0 12.0)))))")
    assert r == [[expr(expr(58.0, 64.0), expr(139.0, 154.0))]]


def test_tensor_shape_and_reductions(tm):
    assert tm.run("!(t-shape (zeros 2 3))") == [[expr(2, 3)]]
    assert tm.run("!(t-item (t-sum (tensor (1.0 2.0 3.0))))") == [[6.0]]
    assert tm.run("!(t-argmax (tensor (0.1 0.9 0.2)))") == [[1]]


def test_tensors_print_readably(tm):
    (row,) = tm.run("!(tensor ((1.0 2.0)))")
    assert "<Tensor 1x2 float32 cpu>" in repr(row[0])


def test_tensor_identity_through_space(tm, fresh):
    x = torch.arange(4.0)
    fresh.add(S.holds(val(x)))
    back = decode(fresh.query(S.holds(V.t))[0].t)
    assert back is x


def test_equations_over_tensors(tm):
    r = tm.run(
        "(= (affine $w $b $x) (t+ (matmul $w $x) $b))\n"
        "!(t-tolist (affine (tensor ((2.0 0.0) (0.0 3.0))) "
        "(tensor (1.0 1.0)) (tensor (5.0 7.0))))"
    )
    assert r == [[expr(11.0, 22.0)]]


def test_type_declarations_cover_core_ops(tm):
    # Types are nondeterministic, PeTTa's own rule: an object is typed by its
    # Python classes, most specific first, so Tensor leads its base class.
    (answers,) = tm.run("!(get-type (matmul (zeros 2 2) (zeros 2 2)))")
    assert answers[0] == S.Tensor


# ------------------------------------------------------------------ pillar 2


def test_wrapped_module_is_a_metta_function(tm):
    lin = torch.nn.Linear(3, 2)
    with torch.no_grad():
        lin.weight.copy_(torch.tensor([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]))
        lin.bias.zero_()
    pettorch.wrap(tm, "proj", lin)
    r = tm.run("!(t-tolist (proj (tensor (3.0 5.0 7.0))))")
    assert r == [[expr(3.0, 5.0)]]


def test_rules_route_between_experts(tm, fresh):
    """The mixture-of-experts shape: symbolic routing over neural experts."""
    doubler = torch.nn.Linear(1, 1, bias=False)
    tripler = torch.nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        doubler.weight.fill_(2.0)
        tripler.weight.fill_(3.0)
    pettorch.wrap(tm, "expert-double", doubler)
    pettorch.wrap(tm, "expert-triple", tripler)
    # A match pattern is structural, the engine's own rule: functions inside
    # it stay data, so the routing computes first and matches the value.
    fresh.run(
        "(route small expert-double)\n"
        "(route large expert-triple)\n"
        "(= (size-of $x) (if (< (t-item $x) 10.0) small large))\n"
        "(= (moe $x) (let $size (size-of $x)\n"
        "  (let $expert (match (context-space) (route $size $e) $e)\n"
        "       ($expert $x))))"
    )
    small = fresh.run("!(t-item (moe (tensor (3.0))))")
    large = fresh.run("!(t-item (moe (tensor (30.0))))")
    assert small == [[6.0]]
    assert large == [[90.0]]


# ------------------------------------------------------------------ pillar 3


def test_gradients_flow_through_metta_forward(tm):
    w = torch.tensor([2.0, 3.0], requires_grad=True)
    x = torch.tensor([5.0, 7.0])
    tm.run("(= (dotp $w $x) (t-sum (t* $w $x)))")
    (loss,) = tm.eval(expr(S.dotp, val(w), val(x)))
    loss = decode(loss)
    assert loss.item() == pytest.approx(31.0)
    loss.backward()
    assert w.grad.tolist() == [5.0, 7.0]


def test_metta_module_trains_under_torch_optimizer(tm):
    """A MeTTa program as an nn.Module, fit by an ordinary training loop."""
    space = tm.fresh_space()
    space.run("(= (predict $x) (t-sum (t* (param w) $x)))")
    model = pettorch.MettaModule(space, "predict", params={"w": torch.zeros(2)})
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
    x = torch.tensor([1.0, 2.0])
    target = torch.tensor(8.0)  # reachable: w = [8/5*1, 8/5*2] etc.
    for _ in range(200):
        optimizer.zero_grad()
        loss = torch.nn.functional.mse_loss(model(x), target)
        loss.backward()
        optimizer.step()
    assert float(loss.item()) < 1e-3
    assert model(x).item() == pytest.approx(8.0, abs=0.05)


def test_metta_module_refuses_nondeterministic_forward(tm):
    space = tm.fresh_space()
    space.run("(= (ambig $x) (tensor (1.0)))\n(= (ambig $x) (tensor (2.0)))")
    model = pettorch.MettaModule(space, "ambig", params={})
    with pytest.raises(RuntimeError) as excinfo:
        model(torch.zeros(1))
    assert "2 results" in str(excinfo.value)


def test_train_step_runs_the_forward_in_metta(tm):
    space = tm.fresh_space()
    space.run("(= (tr-loss $w $x $y) (mse-loss (t-sum (t* $w $x)) $y))")
    w = torch.zeros(2, requires_grad=True)
    optimizer = torch.optim.SGD([w], lr=0.1)
    x = torch.tensor([1.0, 1.0])
    y = torch.tensor(4.0)
    losses = [
        pettorch.train_step(space, "tr-loss", optimizer, val(w), val(x), val(y))
        for _ in range(60)
    ]
    assert losses[0] == pytest.approx(16.0)
    assert losses[-1] < 1e-4
    assert w.detach().sum().item() == pytest.approx(4.0, abs=0.01)


def test_training_loop_written_in_metta(tm):
    """The whole update loop as MeTTa source: zero, backward, step."""
    space = tm.fresh_space()
    w = torch.tensor([0.0], requires_grad=True)
    optimizer = torch.optim.SGD([w], lr=0.25)
    pettorch.attach_optimizer(space, optimizer, name="sgd")
    space.add(S.weight(val(w)))
    space.run(
        "(= (step! $x $y)\n"
        "   (let* (($w (match (context-space) (weight $wt) $wt))\n"
        "          ($loss (mse-loss (t* $w $x) $y))\n"
        "          ($z (sgd-zero!))\n"
        "          ($b (t-backward! $loss))\n"
        "          ($s (sgd-step!)))\n"
        "         (t-item $loss)))"
    )
    losses = [
        decode(space.eval(expr(S["step!"], val(torch.tensor([1.0])), val(torch.tensor([2.0]))))[0])
        for _ in range(30)
    ]
    assert losses[0] == pytest.approx(4.0)
    assert losses[-1] < 1e-5
    assert w.item() == pytest.approx(2.0, abs=0.01)


def test_gradient_read_is_semidet(tm):
    w = torch.tensor([1.0], requires_grad=True)
    # No backward yet: t-grad answers nothing rather than None-as-a-value.
    assert tm.eval(expr(S["t-grad"], val(w))) == []
    (w * 3).sum().backward()
    (grad,) = tm.eval(expr(S["t-grad"], val(w)))
    assert decode(grad).tolist() == [3.0]


# ------------------------------------------------------------------ pillar 4


def test_reflection_writes_architecture_facts(tm):
    space = tm.fresh_space()
    model = torch.nn.Sequential(torch.nn.Linear(4, 8), torch.nn.ReLU(), torch.nn.Linear(8, 2))
    count = pettorch.reflect(space, "net", model)
    assert count > 0
    linears = space.query("(nn-linear $layer $in $out)")
    assert {("net.0", 4, 8), ("net.2", 8, 2)} == {
        (str(r.layer), int(r[1]), int(r[2])) for r in linears
    }


def test_rules_reason_over_architecture(tm):
    space = tm.fresh_space()
    model = torch.nn.Sequential(torch.nn.Linear(4, 8), torch.nn.ReLU(), torch.nn.Linear(8, 2))
    pettorch.reflect(space, "net2", model)
    # Two linears chain when the first's out matches the second's in.
    rows = space.query("(nn-linear $a $in $mid)", "(nn-linear $b $mid $out)")
    pairs = {(str(r.a), str(r.b)) for r in rows if str(r.a) != str(r.b)}
    assert ("net2.0", "net2.2") in pairs


def test_reflected_parameters_are_the_live_ones(tm):
    space = tm.fresh_space()
    lin = torch.nn.Linear(2, 2)
    pettorch.reflect(space, "live", lin)
    rows = space.query("(nn-param live $name $tensor)")
    by_name = {str(r.name): decode(r.tensor) for r in rows}
    assert by_name["weight"] is lin.weight
    assert by_name["bias"] is lin.bias


# ------------------------------------------------------------------ pillar 5


def test_knn_is_nondeterministic_retrieval(tm):
    space = tm.fresh_space()
    store = pettorch.EmbeddingStore(space, name="tk")
    store.add(S.dog, torch.tensor([1.0, 0.0, 0.0]))
    store.add(S.cat, torch.tensor([0.9, 0.1, 0.0]))
    store.add(S.car, torch.tensor([0.0, 0.0, 1.0]))
    (group,) = space.run("!(collapse (tk-knn (tensor (1.0 0.0 0.0)) 2))")
    (pairs,) = group
    keys = [p[0] for p in pairs]
    assert keys == [S.dog, S.cat]
    scores = [float(p[1]) for p in pairs]
    assert scores[0] == pytest.approx(1.0)
    assert scores == sorted(scores, reverse=True)


def test_knn_composes_with_rules(tm):
    space = tm.fresh_space()
    store = pettorch.EmbeddingStore(space, name="rk")
    store.add(S.rex, torch.tensor([1.0, 0.0]))
    store.add(S.tabby, torch.tensor([0.0, 1.0]))
    space.run(
        "(species rex Dog)\n(species tabby Cat)\n"
        "(= (nearest-species $v)\n"
        "   (let ($who $score) (rk-knn $v 1)\n"
        "        (match (context-space) (species $who $s) $s)))"
    )
    assert space.run("!(nearest-species (tensor (0.9 0.1)))") == [[S.Dog]]
    assert space.run("!(nearest-species (tensor (0.1 0.9)))") == [[S.Cat]]


def test_embed_lookup_declines_for_unknown_key(tm):
    space = tm.fresh_space()
    store = pettorch.EmbeddingStore(space, name="lk")
    store.add(S.thing, torch.tensor([1.0]))
    assert space.eval(expr(S["lk-embed"], S.thing)) != []
    assert space.eval(expr(S["lk-embed"], S.absent)) == []


def test_mirrored_embedding_facts_are_matchable(tm):
    space = tm.fresh_space()
    store = pettorch.EmbeddingStore(space, name="mk")
    store.add(S.a, torch.tensor([1.0, 2.0]))
    rows = space.query("(embedding $k $v)")
    assert [str(r.k) for r in rows] == ["a"]
    assert decode(rows[0].v).tolist() == [1.0, 2.0]


# ------------------------------------------------------------------ hygiene


def test_install_is_idempotent(tm):
    names = pettorch.install(tm)
    assert "matmul" in names and "tensor" in names
    assert tm.run("!(t-item (t-sum (tensor (1.0 1.0))))") == [[2.0]]


def test_lib_torch_metta_loads_via_py_call(tm):
    space = tm.fresh_space()
    r = space.run('!(import! &self (library lib_torch))\n'
                  '!(torch-tolist (torch-matmul (torch-tensor ((1.0 2.0))) '
                  '(torch-tensor ((3.0) (4.0)))))')
    assert r[-1] == [expr(expr(11.0))]
