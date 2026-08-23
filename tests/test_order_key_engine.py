"""Purpose: hold Python order_key to the engine's msort order across atom kinds.
Guarantees:
  - mixed variables, numbers, strings, opaque values, symbols, empty lists,
    and nonempty expressions sort exactly as msort sorts their shared wire
    image [tested: test_order_key_matches_msort_across_kinds;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205 -- the contract is one continuous invariant

import pytest

from petta import Expression, Grounded, S, Symbol, Variable
from petta.atoms import _alpha_eq, order_key

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


@given(st.permutations(_ATOMS))
def test_order_key_matches_msort_across_kinds(metta, permutation):
    """Sorting any permutation agrees with engine msort after alpha-renaming."""
    expected = Expression(sorted(permutation, key=order_key))
    plain = Expression(sorted(permutation))
    (actual,) = metta.eval(S.msort(Expression(permutation)))
    assert isinstance(actual, Expression)
    assert _alpha_eq(expected, actual)
    assert _alpha_eq(plain, actual)
