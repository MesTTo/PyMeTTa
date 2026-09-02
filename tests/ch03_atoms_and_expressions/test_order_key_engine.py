"""Purpose: hold Python order_key to the engine's msort order across atom kinds.
Guarantees:
  - mixed variables, numbers, strings, opaque values, symbols, empty lists,
    and nonempty expressions sort exactly as msort sorts their shared wire
    image [tested: test_order_key_matches_msort_across_kinds;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - generated nested expression shapes retain that same differential [tested:
    test_flat_order_key_matches_msort_on_nested_shapes;
    commit=c8dace7a057afeb9db6acec2a1f4e952b954927e]
  - the engine oracle sorts decoded wire terms directly, so call-shaped data
    is compared rather than evaluated [tested:
    test_flat_order_key_matches_msort_on_nested_shapes; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205 -- the contract is one continuous invariant

import pytest

from metta import Expression, Grounded, Symbol, Variable, wire
from metta.atoms import _alpha_eq, order_key

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
st = hypothesis.strategies


_OPAQUE = object()
_ATOMS = (
    Variable("x"),
    Grounded(-3),
    Grounded(1.0),
    Grounded(1),
    Grounded(2.5),
    Grounded("kiwi"),
    Grounded(_OPAQUE),
    Expression(),
    Symbol("Apple"),
    Symbol("zebra"),
    Expression([Symbol("f")]),
    Expression([Symbol("f"), Grounded(1)]),
)
_TREE_ATOMS = st.recursive(
    st.sampled_from(_ATOMS),
    lambda children: st.lists(children, min_size=0, max_size=4).map(Expression),
    max_leaves=20,
)


def _engine_msort(metta, atoms):
    """Sort atoms after decoding their shared wire image, without evaluation."""
    row = metta.runtime.must(
        "metta_py_decode_shared(W, _Terms, _), "
        "msort(_Terms, _Sorted), metta_py_encode(_Sorted, Out)",
        W=Expression(atoms).to_wire(),
    )
    return wire.atom_from_wire(row["Out"])


@given(st.permutations(_ATOMS))
def test_order_key_matches_msort_across_kinds(metta, permutation):
    """Sorting any permutation agrees with engine msort after alpha-renaming."""
    expected = Expression(sorted(permutation, key=order_key))
    plain = Expression(sorted(permutation))
    actual = _engine_msort(metta, permutation)
    assert isinstance(actual, Expression)
    assert _alpha_eq(expected, actual)
    assert _alpha_eq(plain, actual)


@given(st.lists(_TREE_ATOMS, min_size=0, max_size=8))
def test_flat_order_key_matches_msort_on_nested_shapes(metta, atoms):
    """Generated expression trees sort exactly like the engine wire image."""
    expected = Expression(sorted(atoms, key=order_key))
    actual = _engine_msort(metta, atoms)

    assert isinstance(actual, Expression)
    assert _alpha_eq(expected, actual)
