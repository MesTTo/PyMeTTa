"""Purpose: the library-agnostic array layer: one operation set over the
array API standard, exercised with NumPy end to end, DLTensor as a protocol
type the engine checks, protocol printing, cross-library conversion through
DLPack, and the embedding store running on NumPy alone.
Runs before test_pettorch alphabetically; the constructor default is
process-global, so this suite installs NumPy as the default and the torch
suite installs torch over it, each self-consistent.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

numpy = pytest.importorskip("numpy")
pytest.importorskip("array_api_compat")

from petta import S, V, decode, expr, val  # noqa: E402
from petta import arrays  # noqa: E402


@pytest.fixture(scope="module")
def am(metta):
    arrays.install(metta, default=numpy)
    return metta


def test_numpy_flows_through_the_same_ops(am):
    r = am.run("!(t-tolist (matmul (tensor ((1.0 2.0 3.0) (4.0 5.0 6.0))) "
               "(tensor ((7.0 8.0) (9.0 10.0) (11.0 12.0)))))")
    assert r == [[expr(expr(58.0, 64.0), expr(139.0, 154.0))]]
    assert am.run("!(t-shape (zeros 2 3))") == [[expr(2, 3)]]
    assert am.run("!(t-item (t-sum (tensor (1.0 2.0 3.0))))") == [[6.0]]


def test_the_constructor_builds_numpy_here(am):
    (group,) = am.run("!(tensor (1.0 2.0))")
    assert isinstance(decode(group[0]), numpy.ndarray)


def test_activations_are_standard_not_torch(am):
    assert am.run("!(t-tolist (relu (tensor (-1.0 2.0))))") == [[expr(0.0, 2.0)]]
    (group,) = am.run("!(t-tolist (softmax (tensor (0.0 0.0))))")
    assert [round(float(x), 3) for x in group[0]] == [0.5, 0.5]


def test_ndarray_identity_through_space(am):
    array = numpy.arange(4.0)
    space = am.fresh_space()
    space.add(S.holds(val(array)))
    assert decode(space.query(S.holds(V.a))[0].a) is array


def test_dltensor_is_a_protocol_type_the_engine_checks(am):
    # get-type answers the classes and the protocol,
    (answers,) = am.run("!(collapse (get-type (tensor (1.0))))")
    names = {str(a) for a in answers[0]}
    assert "ndarray" in names and "DLTensor" in names
    # and a declared (-> DLTensor DLTensor DLTensor) holds for NumPy values,
    # which is the whole point of protocol typing:
    assert am.run("!(t-item (t-sum (matmul (eye 2) (eye 2))))") == [[2.0]]


def test_protocol_printing_covers_any_library(am):
    (group,) = am.run("!(tensor ((1.0 2.0)))")
    printed = repr(group[0])
    assert "1x2" in printed and "float32" in printed and "ndarray" in printed


def test_cross_library_conversion_via_dlpack(am):
    torch = pytest.importorskip("torch")
    space = am.fresh_space()
    space.add(S.np_vec(val(numpy.array([1.0, 2.0], dtype=numpy.float32))))
    (group,) = space.run(
        '!(t-dtype (t-as (match (context-space) (np_vec $v) $v) torch))'
    )
    assert "float32" in str(group[0])


def test_mixed_library_binary_op_converts_rightward(am):
    torch = pytest.importorskip("torch")
    left = numpy.ones((2, 2), dtype=numpy.float32)
    right = torch.ones(2, 2)
    space = am.fresh_space()
    space.add(S.pairT(val(left), val(right)))
    (group,) = space.run(
        "!(t-item (t-sum (match (context-space) (pairT $a $b) (matmul $a $b))))"
    )
    assert float(group[0]) == 8.0


def test_embedding_store_runs_on_numpy(am):
    space = am.fresh_space()
    store = arrays.EmbeddingStore(space, name="npk")
    store.add(S.dog, numpy.array([1.0, 0.0, 0.0]))
    store.add(S.cat, numpy.array([0.9, 0.1, 0.0]))
    store.add(S.car, numpy.array([0.0, 0.0, 1.0]))
    (group,) = space.run("!(collapse (npk-knn (tensor (1.0 0.0 0.0)) 2))")
    (pairs,) = group
    assert [p[0] for p in pairs] == [S.dog, S.cat]
    scores = [float(p[1]) for p in pairs]
    assert scores == sorted(scores, reverse=True)


def test_arrays_layer_is_torch_free():
    """The module must not import torch anywhere, even lazily by name."""
    import inspect

    source = inspect.getsource(arrays)
    assert "import torch" not in source

