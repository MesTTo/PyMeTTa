"""Purpose: verify every joined atom operation and its documented MeTTa image.

Guarantees: the source-derived inventory supplies protocol identities while
operators.py alone supplies MeTTa policy. Method, word, compiler and runtime
projections retain those meanings [source:
extensions/python/metta/_atoms/operators.py:OPERATOR_LOWERINGS;
commit=f866cc992295171a9a9e97417514f31597181e7b].
Owns resources: scratch_space retires the temporary matmul equation.
"""

from __future__ import annotations

import operator
from pathlib import Path

import pytest

from metta import (
    Atom,
    Grounded,
    S,
    V,
)
from metta._atoms.factories import OPERATOR_LOWERINGS, order_key
from metta._atoms.operators import selector

DOC = Path(__file__).resolve().parents[4] / "website" / "guide" / "atoms-terms.md"

def _head(expr) -> str:
    return str(next(iter(expr)))


def test_every_operator_is_documented_including_non_symbolic_comparisons():
    """Build every policy row's term and require its documented MeTTa head."""
    text = DOC.read_text(encoding="utf-8")
    built: dict[str, str] = {}
    for entry in OPERATOR_LOWERINGS:
        name = selector(entry) if entry.kind == "taken" else entry.dunder
        operands = [S.x, *(V.y for _ in range(entry.arity - 1))]
        built[name] = _head(getattr(type(S.x), name)(*operands))

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

    # A refusal names the NEAREST rung. The four ordering methods landed after
    # this message was written, and it went on pointing at the bracket door
    # below them, which is the ladder rule read backwards: every convenience
    # names its longhand, so the message shows both and leads with the method.
    for entry in OPERATOR_LOWERINGS:
        if entry.method != "order_key":
            continue
        symbol, method = entry.form, selector(entry)
        with pytest.raises(TypeError) as refused:
            getattr(type(S.x), f"__{method}__")(S.x, 1)
        message = str(refused.value)
        assert f"left.{method}(right)" in message, message
        assert f"S[{symbol!r}](left, right)" in message, message


def test_the_operator_table_is_generated_from_one_source_with_no_holes(scratch_space):
    """Every atom policy joins a source operation and installs its methods."""
    from metta._atoms._python_protocols import BY_OPERATOR
    from metta._atoms.operators import _POLICIES

    assert {entry.dunder for entry in OPERATOR_LOWERINGS} == set(_POLICIES)
    assert all(entry.source is BY_OPERATOR[("object", entry.dunder)] for entry in OPERATOR_LOWERINGS)
    # Four kinds, not five. "absent" was the vocabulary for an operator with
    # no MeTTa lowering, and `<<` and `>>` were its only two rows; giving MeTTa
    # bit-shift-left and bit-shift-right left it with none, so the kind, its
    # `reason` field and the branch that raised from it are gone. Every Python
    # binary operator lowers now.
    assert {entry.kind for entry in OPERATOR_LOWERINGS} == {
        "provided", "symbol", "taken", "template"
    }
    with pytest.raises(TypeError):
        operator.setitem(OPERATOR_LOWERINGS, 0, OPERATOR_LOWERINGS[0])

    for entry in OPERATOR_LOWERINGS:
        if entry.kind == "taken":
            assert entry.method in {"eq", "ne", "order_key"}
            implementation = order_key if entry.method == "order_key" else getattr(Atom, entry.method)
            assert callable(implementation)
            continue
        method = getattr(Atom, entry.dunder)
        assert method.__metta_lowering__ == entry
        if entry.reflected is not None:
            assert getattr(Atom, entry.reflected).__metta_lowering__ == entry

    assert str(S.x // 2) == "(floor-math (/ x 2))"
    assert str(-S.x) == "(- 0 x)"
    assert str(abs(S.x)) == "(abs-math x)"
    assert str(S.x << 2) == "(bit-shift-left x 2)"
    assert str(S.x >> 2) == "(bit-shift-right x 2)"

    metta = scratch_space
    assert metta.eval(Atom.__floordiv__(Grounded(7), 2)) == [3]
    assert metta.eval(Atom.__neg__(Grounded(7))) == [-7]
    assert metta.eval(Atom.__abs__(Grounded(-7))) == [7]
    provided = Atom.__matmul__(Grounded(6), 7)
    assert metta.eval(provided) == [provided]
    metta.run("(= (matmul $left $right) (* $left $right))")
    assert metta.eval(provided) == [42]

    assert Grounded(7) // 2 == S["floor-math"](S["/"](7, 2))
    assert -Grounded(7) == S["-"](0, 7)
    assert abs(Grounded(-7)) == S["abs-math"](-7)
    assert Grounded(3) << 2 == S["bit-shift-left"](3, 2)
    assert Grounded(12) >> 2 == S["bit-shift-right"](12, 2)
    assert metta.eval(Grounded(3) << 2) == [12]
    assert metta.eval(Grounded(12) >> 2) == [3]
    # Non-negative counts only: SWI answers 0 for `1 << -1`, silently reading
    # a left shift as a right one, and the engine refuses instead.
    refused = metta.eval(Grounded(1) << -1)
    assert "must not be negative" in str(refused[0])
    assert (S.x == S.x) is True
    assert str(S.x.eq(S.y)) == "(== x y)"


def test_every_operator_projection_is_this_table():
    """Every table for "how a Python operator spells in MeTTa" is one table.

    There were eight, keyed four different ways, each holding its own copy of
    the MeTTa heads. Each is derived now, and this is the relation that says
    so: a row's selector, its augmented selector, its `ast` node and its heads
    are what every consumer reads, so a head that moves moves once.
    """
    import ast

    from metta._atoms.mentions import OPERATOR_CALLABLES
    from metta._atoms.names import OPERATOR_WORDS, OperatorRecipe
    from metta._atoms.operators import OPERATOR_LOWERINGS, augmented_selector, selector
    from metta._compile.expressions import (
        _BINOPS,
        _COMPARE,
        _INPLACE_BINOPS,
        _MEMBERSHIP,
        _NATIVE_BINOPS,
        _NATIVE_COMPARE,
        _SOURCE_COMPARE,
    )
    from metta._declare.prelude import _EXTRA_OPERATORS, _PYTHON_OPERATORS

    rows = {selector(entry): entry for entry in OPERATOR_LOWERINGS}

    # The compiler's five tables are the rows with an `ast` node, split by
    # whether the operator has an augmented form.
    binary = {name: entry for name, entry in rows.items() if entry.augmented}
    compared = {
        name: entry
        for name, entry in rows.items()
        if not entry.augmented and entry.kind == "taken"
    }
    assert {getattr(ast, entry.node): name for name, entry in binary.items()} == _BINOPS
    assert {
        getattr(ast, entry.node): entry.native
        for name, entry in binary.items()
        if entry.native
    } == _NATIVE_BINOPS
    assert {
        getattr(ast, entry.node): name for name, entry in compared.items()
    } == _COMPARE
    assert {
        getattr(ast, entry.node): entry.native
        for entry in compared.values()
        if entry.native
    } == _NATIVE_COMPARE
    assert {
        getattr(ast, entry.node): augmented_selector(entry)
        for entry in binary.values()
    } == _INPLACE_BINOPS
    # The two comparison nodes with no operator protocol behind them are the
    # only entries `_SOURCE_COMPARE` adds beyond the table.
    assert set(_SOURCE_COMPARE) - set(_MEMBERSHIP) == {
        getattr(ast, entry.node) for entry in compared.values()
    }

    # The word door is the rows marked `word`, reaching each row's own form.
    assert set(OPERATOR_WORDS) == {name for name, entry in rows.items() if entry.word}
    for name, target in OPERATOR_WORDS.items():
        if isinstance(target, OperatorRecipe):
            continue
        entry = rows[name]
        assert target == (entry.word_head or str(entry.form))

    # Exact runtime callable dispatch is a projection of all source exports,
    # independent of the subset that has a MeTTa atom meaning.
    assert _PYTHON_OPERATORS == dict(OPERATOR_CALLABLES) | _EXTRA_OPERATORS
