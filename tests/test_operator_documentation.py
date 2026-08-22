"""Purpose: pin Phase 9 item P9.6: every term-building operator on atoms is
documented in one table, derived from the class rather than maintained by
hand, and the one operator that is deliberately NOT symbolic (`==`, whose
term is spelled `.eq()`) is called out. Before this, `S.x + S.y` built a
term and no page in website/ showed the form at all [measured 2026-08-19].
Guarantees:
    - ``Atom.__lt__`` is the standard-order sorting exception and the ``<``
      term remains explicitly buildable [tested:
      test_every_operator_is_documented_including_non_symbolic_comparisons;
      commit=WORKTREE]
    - one immutable 22-entry table generates every symbolic, templated,
      provided, or refusing operator method [tested:
      test_the_operator_table_is_generated_from_one_source_with_no_holes;
      commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Assumes:
    - Python's operator dunders are a closed universe, so enumerating a
      fixed list of them IS deriving the surface: a new overload lands in
      this list or it is not an operator
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import operator
from pathlib import Path

import pytest

from petta import (
    Atom,
    Grounded,
    MeTTa,
    S,
    V,
)
from petta.atoms import OPERATOR_LOWERINGS

DOC = Path(__file__).resolve().parents[3] / "website" / "guide" / "atoms-terms.md"

BINARY_DUNDERS = [
    "__add__", "__sub__", "__mul__", "__truediv__", "__mod__", "__pow__",
    "__matmul__", "__and__", "__or__", "__xor__",
    "__le__", "__gt__", "__ge__",
    "__floordiv__", "__lshift__", "__rshift__",
]


def _head(expr) -> str:
    return str(next(iter(expr)))


def test_every_operator_is_documented_including_non_symbolic_comparisons():
    """Build each operator's term live and require its MeTTa symbol in the
    doc's table, so the table cannot drift from the class: an operator
    added tomorrow is in Python's fixed dunder universe, builds a term
    here, and fails this test until the table names it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    text = DOC.read_text(encoding="utf-8")
    built: dict[str, str] = {}
    entries = {entry.dunder: entry for entry in OPERATOR_LOWERINGS}
    for dunder in BINARY_DUNDERS:
        method = getattr(type(S.x), dunder, None)
        if method is None or getattr(object, dunder, None) is method:
            continue
        if entries[dunder].kind == "absent":
            with pytest.raises(TypeError, match="has no MeTTa lowering"):
                method(S.x, V.y)
            continue
        term = method(S.x, V.y)
        built[dunder] = _head(term)
    # The unary forms and the two spelled methods.
    for dunder in ("__invert__", "__neg__", "__abs__"):
        built[dunder] = _head(getattr(type(S.x), dunder)(S.x))
    built["lt"] = _head(S["<"](S.x, V.y))
    built["eq"] = _head(S.x.eq(V.y))
    built["ne"] = _head(S.x.ne(V.y))

    undocumented = sorted(
        f"{dunder} -> {symbol}"
        for dunder, symbol in built.items()
        if f"`({symbol} " not in text.replace("\\|", "|")
    )
    assert not undocumented, (
        f"term-building operators missing from the table in {DOC.name}: "
        f"{undocumented}"
    )
    # The deliberate exception is stated, not implied: equality's TERM is a
    # method because == itself is structural equality.
    assert ".eq(" in text and "structurally" in text, (
        "the doc no longer says == is structural and the term is .eq()"
    )
    # And == really is the non-operator: it answers a bool, not a term.
    assert (S.x == S.x) is True and (S.x == S.y) is False


def test_the_operator_table_is_generated_from_one_source_with_no_holes():
    """Prove the immutable 22-entry table is the single source from which every operator method is generated."""
    expected = {
        "__abs__", "__add__", "__and__", "__eq__", "__floordiv__",
        "__ge__", "__gt__", "__invert__", "__le__", "__lshift__",
        "__lt__", "__matmul__", "__mod__", "__mul__", "__ne__",
        "__neg__", "__or__", "__pow__", "__rshift__", "__sub__",
        "__truediv__", "__xor__",
    }
    assert len(OPERATOR_LOWERINGS) == 22
    assert {entry.dunder for entry in OPERATOR_LOWERINGS} == expected
    assert {entry.kind for entry in OPERATOR_LOWERINGS} == {
        "absent", "provided", "symbol", "taken", "template"
    }
    with pytest.raises(TypeError):
        operator.setitem(OPERATOR_LOWERINGS, 0, OPERATOR_LOWERINGS[0])

    for entry in OPERATOR_LOWERINGS:
        if entry.kind == "taken":
            assert entry.method in {"eq", "ne"}
            assert callable(getattr(Atom, entry.method))
            continue
        method = getattr(Atom, entry.dunder)
        if entry.dunder == "__lt__":
            assert method(S.a, S.b) is True
            continue
        assert method.__petta_lowering__ == entry
        if entry.reflected is not None:
            assert getattr(Atom, entry.reflected).__petta_lowering__ == entry

    assert str(S.x // 2) == "(floor-math (/ x 2))"
    assert str(-S.x) == "(- 0 x)"
    assert str(abs(S.x)) == "(abs-math x)"
    with pytest.raises(TypeError, match="MeTTa has no integer-left-shift operation"):
        S.x << 2
    with pytest.raises(TypeError, match="MeTTa has no integer-right-shift operation"):
        S.x >> 2

    metta = MeTTa().space()
    assert metta.eval(Atom.__floordiv__(Grounded(7), 2)) == [3]
    assert metta.eval(Atom.__neg__(Grounded(7))) == [-7]
    assert metta.eval(Atom.__abs__(Grounded(-7))) == [7]
    provided = Atom.__matmul__(Grounded(6), 7)
    assert metta.eval(provided) == [provided]
    metta.run("(= (matmul $left $right) (* $left $right))")
    assert metta.eval(provided) == [42]

    assert Grounded(7) // 2 == 3
    assert -Grounded(7) == -7
    assert abs(Grounded(-7)) == 7
    assert Grounded(3) << 2 == 12
    assert Grounded(12) >> 2 == 3
    assert (S.x == S.x) is True
    assert str(S.x.eq(S.y)) == "(== x y)"
