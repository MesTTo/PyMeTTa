"""Purpose: the library-agnostic array layer: one operation set over the
array API standard, exercised with NumPy end to end, DLTensor as a protocol
type the engine checks, protocol printing, cross-library conversion through
DLPack, and the embedding store running on NumPy alone.
Runs before test_pettorch alphabetically; the constructor default is
process-global, so this suite installs NumPy as the default and the torch
suite installs torch over it, each self-consistent.
Guarantees:
  - each installed array operation has an arrow and a cache-safe effect rank;
    broadcast-shape works forwards and backwards as a CLP(FD) relation
    [tested: test_every_array_operation_is_typed_and_a_shape_is_a_constraint,
     test_embedding_store_runs_on_numpy;
     commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - the module fixture retires its process-global operation registrations, so
    later suites do not inherit array callables [tested: python -m pytest
    extensions/python/tests/ch08_data/test_arrays.py
    extensions/python/tests/repository/test_operator_documentation.py;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import inspect
import threading

import pytest

from metta import (
    Expression,
    S,
    V,
    arrays,
    ground,
    wire,
)
from metta.ops import registered
from metta.vocabularies import EffectClass

numpy = pytest.importorskip("numpy")
pytest.importorskip("array_api_compat")


@pytest.fixture(scope="module")
def am(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    before = set(registered())
    arrays.install(metta, default=numpy)
    installed = set(registered()) - before
    try:
        yield metta
    finally:
        for name in sorted(installed, reverse=True):
            if name in registered():
                metta.unregister_op(name)


def test_numpy_flows_through_the_same_ops(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    r = am.run(
        "!(t-tolist (matmul (tensor ((1.0 2.0 3.0) (4.0 5.0 6.0))) "
        "(tensor ((7.0 8.0) (9.0 10.0) (11.0 12.0)))))"
    )
    assert r == [[Expression(Expression(58.0, 64.0), Expression(139.0, 154.0))]]
    assert am.run("!(t-shape (zeros 2 3))") == [[Expression(2, 3)]]
    assert am.run("!(t-item (t-sum (tensor (1.0 2.0 3.0))))") == [[6.0]]


def test_every_array_operation_is_typed_and_a_shape_is_a_constraint(am):
    """Every installed array op carries an arrow type, and broadcast-shape solves both ways."""
    assert len(arrays.ARRAY_OPS) == len(set(arrays.ARRAY_OPS)) == 44
    for name in arrays.ARRAY_OPS:
        types = [atom for group in am.run(f"!(get-type {name})") for atom in group]
        assert types, name
        assert all(type_.head == S["->"] for type_ in types), (name, types)

    operations = {
        name: registered()[name]
        for name in arrays.ARRAY_OPS
        if name in registered()
    }
    assert operations
    assert all(operation.effect in EffectClass for operation in operations.values())
    assert registered()["matmul"].effect is EffectClass.writesState
    assert registered()["t-item"].effect is EffectClass.readOnlyLookup
    random_constructor = next(
        name for name in operations if name.startswith("randn--")
    )
    assert registered()[random_constructor].effect is EffectClass.oracleIO

    assert am.run(
        "!(let True (broadcast-shape (4 1) (3) $shape) $shape)"
    ) == [[Expression(4, 3)]]
    assert am.run(
        "!(let True (broadcast-shape ($d 1) (1 3) (4 3)) $d)"
    ) == [[4]]
    assert am.run("!(broadcast-shape (2 3) (4 3) (4 3))") == [[]]

    assert am.run("!(t-shape (reshape (arange-t 4) 2 2))") == [[Expression(2, 2)]]
    tensors = "((tensor ((1 2))) (tensor ((3 4))))"
    assert am.run(f"!(t-tolist (cat {tensors} 0))") == [
        [Expression(Expression(1.0, 2.0), Expression(3.0, 4.0))]
    ]
    assert am.run(f"!(t-tolist (stack {tensors} 0))") == [
        [Expression(Expression(Expression(1.0, 2.0)), Expression(Expression(3.0, 4.0)))]
    ]


def test_the_constructor_builds_numpy_here(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (group,) = am.run("!(tensor (1.0 2.0))")
    assert isinstance(wire.decode(group[0]), numpy.ndarray)


def test_activations_are_standard_not_torch(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert am.run("!(t-tolist (relu (tensor (-1.0 2.0))))") == [[Expression(0.0, 2.0)]]
    (group,) = am.run("!(t-tolist (softmax (tensor (0.0 0.0))))")
    assert [round(float(x), 3) for x in group[0]] == [0.5, 0.5]


def test_ndarray_identity_through_space(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    array = numpy.arange(4.0)
    space = am._new_space()
    space.add(S.holds(ground(array)))
    assert wire.decode(space.match(S.holds(V.a))[0].a) is array


def test_dltensor_is_a_protocol_type_the_engine_checks(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # get-type answers the classes and the protocol of the BUILT tensor, so
    # the tensor is built first. get-type does not evaluate its argument, and
    # the classes are a property of the value rather than of the call that
    # would make it.
    (answers,) = am.run("!(collapse (let $t (tensor (1.0)) (get-type $t)))")
    names = {str(a) for a in answers[0]}
    assert "ndarray" in names and "DLTensor" in names
    # and a declared (-> DLTensor DLTensor DLTensor) holds for NumPy values,
    # which is the whole point of protocol typing:
    assert am.run("!(t-item (t-sum (matmul (eye 2) (eye 2))))") == [[2.0]]


def test_a_protocol_and_a_declaration_are_both_answered_once(am):
    """The two sources of extra types compose instead of hiding each other.

    A protocol name reaches the engine through the shim's bridge, which
    computes it in Python; a `(py-atom f Type)` declaration reaches it
    through seam:grounded_extra_type/2, in Prolog. The engine used to CHOOSE
    between the bridge and the branch the declaration hangs off, so with
    the library loaded the declaration was dropped
    [tested test_ops.py::test_a_declared_type_survives_the_library_being_loaded].
    Answering both raises the opposite question, whether a name can now
    arrive twice, so this pins the whole list rather than a membership:
    the classes, then the protocol, then the declaration, each once.
    """
    source = "\"__import__('numpy').arange(3.0)\""
    (answers,) = am.run(
        f"!(let $a (py-atom {source} (-> Number Number)) (collapse (get-type $a)))"
    )
    names = [str(a) for a in answers[0]]
    assert names == ["ndarray", "DLTensor", "(-> Number Number)"], names


def test_protocol_printing_covers_any_library(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (group,) = am.run("!(tensor ((1.0 2.0)))")
    printed = repr(group[0])
    assert "1x2" in printed and "float32" in printed and "ndarray" in printed


def test_cross_library_conversion_via_dlpack(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    pytest.importorskip("torch")
    space = am._new_space()
    space.add(S.np_vec(ground(numpy.array([1.0, 2.0], dtype=numpy.float32))))
    (group,) = space.run(
        "!(t-dtype (t-as (match (context-space) (np-vec $v) $v) torch))"
    )
    assert "float32" in str(group[0])


def test_mixed_library_binary_op_converts_rightward(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    torch = pytest.importorskip("torch")
    left = numpy.ones((2, 2), dtype=numpy.float32)
    right = torch.ones(2, 2)
    space = am._new_space()
    space.add(S.pairT(ground(left), ground(right)))
    (group,) = space.run(
        "!(t-item (t-sum (match (context-space) (pairT $a $b) (matmul $a $b))))"
    )
    assert float(group[0]) == 8.0


def test_embedding_store_runs_on_numpy(am):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = am._new_space()
    store = arrays.EmbeddingStore(space, name="npk")
    internal_knn, internal_embed = arrays._SPACE_STORES[(space.name, "npk")]
    assert (
        registered()[internal_knn].effect
        is EffectClass.nondeterministicReadOnly
    )
    assert registered()[internal_embed].effect is EffectClass.readOnlyLookup
    store.add(S.dog, numpy.array([1.0, 0.0, 0.0]))
    store.add(S.cat, numpy.array([0.9, 0.1, 0.0]))
    store.add(S.car, numpy.array([0.0, 0.0, 1.0]))
    (group,) = space.run("!(collapse (npk-knn (tensor (1.0 0.0 0.0)) 2))")
    (pairs,) = group
    assert [p[0] for p in pairs] == [S.dog, S.cat]
    scores = [float(p[1]) for p in pairs]
    assert scores == sorted(scores, reverse=True)


def test_top_indices_match_full_order_and_stabilize_ties():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    xp = arrays.namespace_of(numpy.array([0.0]))
    scores = numpy.random.default_rng(7).normal(size=10_000)
    expected = sorted(
        range(len(scores)), key=lambda index: (-float(scores[index]), index)
    )[:25]
    assert arrays._top_indices(xp, scores, 25) == expected

    ties = numpy.array([0.5, 1.0, 1.0, 1.0, 0.1])
    assert arrays._top_indices(xp, ties, 2) == [1, 2]
    assert arrays._top_indices(xp, ties, 0) == []
    assert arrays._top_indices(xp, ties, len(ties)) == [1, 2, 3, 0, 4]


def test_array_protocol_registration_is_idempotent(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    calls = []
    monkeypatch.setattr(arrays, "_PROTOCOLS_REGISTERED", threading.Event())
    monkeypatch.setattr(arrays, "_PROTOCOLS_LOCK", threading.Lock())
    monkeypatch.setattr(
        arrays._integrate,
        "register_object_type",
        lambda *args: calls.append(("type", args)),
    )
    monkeypatch.setattr(
        arrays._integrate,
        "register_repr",
        lambda *args: calls.append(("repr", args)),
    )

    arrays._register_protocols()
    arrays._register_protocols()

    assert [kind for kind, _ in calls] == ["type", "repr"]


def test_same_named_embedding_stores_route_per_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as left, metta._new_space() as right:
        left_store = arrays.EmbeddingStore(left, name="shared-emb")
        right_store = arrays.EmbeddingStore(right, name="shared-emb")
        left_store.add(S.dog, numpy.array([1.0, 0.0]))
        right_store.add(S.cat, numpy.array([0.0, 1.0]))

        assert left.run("!(shared-emb-embed dog)")
        assert left.run("!(shared-emb-embed cat)") == [[]]
        assert right.run("!(shared-emb-embed cat)")
        assert right.run("!(shared-emb-embed dog)") == [[]]


def test_embedding_store_replaces_duplicate_keys_and_owns_vectors(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        store = arrays.EmbeddingStore(space, name="replace-emb")
        original = numpy.array([1.0, 0.0])
        store.add(S.same, original)
        original[:] = [0.0, 1.0]
        assert store.vector_for(S.same).tolist() == [1.0, 0.0]

        replacement = numpy.array([0.0, 1.0])
        store.add(S.same, replacement)
        assert len(store) == 1
        assert store.keys() == [S.same]
        assert store.vector_for(S.same).tolist() == [0.0, 1.0]
        assert len(space.match(S.embedding(S.same, V.vector))) == 1


@pytest.mark.parametrize(
    ("vector", "message"),
    [
        (numpy.array([[1.0, 0.0]]), "one-dimensional"),
        (numpy.array([numpy.nan, 1.0]), "finite"),
        (numpy.array([numpy.inf, 1.0]), "finite"),
        (numpy.array([0.0, 0.0]), "nonzero"),
    ],
)
def test_embedding_store_validates_added_vectors(metta, vector, message):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        store = arrays.EmbeddingStore(space, name="validated-emb")
        with pytest.raises(ValueError, match=message):
            store.add(S.bad, vector)


def test_embedding_store_requires_one_width_and_positive_integer_k(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        store = arrays.EmbeddingStore(space, name="bounded-emb")
        store.add(S.good, numpy.array([1.0, 0.0]))
        with pytest.raises(ValueError, match="width must be 2"):
            store.add(S.wide, numpy.array([1.0, 0.0, 0.0]))
        for invalid in (0, -1):
            with pytest.raises(ValueError, match="positive integer"):
                list(store.ranked([1.0, 0.0], invalid))
        for invalid in (True, 1.5, "1"):
            with pytest.raises(TypeError, match="positive integer"):
                list(store.ranked([1.0, 0.0], invalid))
        with pytest.raises(ValueError, match="width must be 2"):
            list(store.ranked([1.0, 0.0, 0.0], 1))


def test_arrays_layer_is_torch_free():
    """The module must not import torch anywhere, even lazily by name."""
    source = inspect.getsource(arrays)
    assert "import torch" not in source
