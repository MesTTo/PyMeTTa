"""Purpose: hypothesis strategies for property-testing code built on this
library, the pandas.testing reading: the exact generators the library's own
suite fuzzes itself with, exported, so user operations, translators and
spaces get tested against atoms the engine actually reads back. The
filters encode engine truths worth not rediscovering: which characters the
tokeniser reads back whole, that true/false ARE the boolean atoms so their
symbol spellings canonicalize, and that `_` is the anonymous variable,
fresh at every occurrence.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from ._optional import require_module
from .atoms import Expr, Gnd, Sym, Var
from .benchmarking import (
    BenchmarkBaseline,
    benchmark_case,
    benchmark_counter_slope,
    count_atoms,
    measure_instructions,
)

__all__ = [
    "BenchmarkBaseline",
    "atoms",
    "benchmark_case",
    "benchmark_counter_slope",
    "count_atoms",
    "expressions",
    "grounded",
    "measure_instructions",
    "names",
    "numbers",
    "numpy_scalars",
    "symbols",
    "texts",
    "variables",
]


def _st():
    hypothesis = require_module(
        "hypothesis",
        "petta.testing generates atoms with hypothesis, which is not installed; "
        "install petta[test]",
    )
    return hypothesis.strategies


def names():
    """Symbol and variable names PeTTa's tokeniser reads back whole: no
    whitespace, parens or quotes, none of the characters that mean
    something else at the front, and never the boolean spellings (the
    engine holds its booleans as those very atoms, so True and true are
    one term there and a round trip canonicalizes) or the anonymous `_`
    (fresh at every occurrence by contract, so it never shares)."""
    st = _st()
    return st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_?<>=+*"),
        min_size=1,
        max_size=12,
    ).filter(
        lambda s: (
            s[0] not in "$&-<>=+*?0123456789" and s not in ("True", "False", "true", "false", "_")
        )
    )


def symbols():
    """Sym atoms with engine-readable names."""
    return names().map(Sym)


def variables():
    """Var atoms with engine-readable names."""
    return names().map(Var)


def numbers():
    """Numbers the engine's printer round-trips: integers within the
    tagged-integer range, floats without NaN (never compares equal) or
    infinity (prints as a symbol), both printer limits, not carried bugs."""
    st = _st()
    return st.one_of(
        st.integers(min_value=-(2**62), max_value=2**62),
        st.floats(allow_nan=False, allow_infinity=False, width=64),
    )


def numpy_scalars():
    """NumPy integer and real scalar values accepted by PeTTa's Number type.

    NumPy is optional. Install ``petta[arrays,test]`` before requesting this
    strategy.
    """
    st = _st()
    np = require_module(
        "numpy",
        "petta.testing.numpy_scalars requires numpy; install petta[arrays,test]",
    )
    return st.one_of(
        st.integers(-(2**31), 2**31 - 1).map(np.int32),
        st.integers(-(2**62), 2**62).map(np.int64),
        st.floats(allow_nan=False, allow_infinity=False, width=32).map(np.float32),
        st.floats(allow_nan=False, allow_infinity=False, width=64).map(np.float64),
    )


def texts():
    """Strings as the engine stores them; NUL is the one exclusion."""
    st = _st()
    return st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters="\x00"),
        max_size=20,
    )


def grounded():
    """Grounded atoms over numbers, booleans and strings."""
    st = _st()
    return st.one_of(
        numbers().map(Gnd),
        st.booleans().map(Gnd),
        texts().map(Gnd),
    )


def atoms(max_leaves: int = 8, *, ground: bool = False):
    """Whole atoms: symbols, variables (unless ground=True), grounded
    values, and expressions recursively over all of them; max_leaves is
    hypothesis's own size knob for the recursion.

        from hypothesis import given
        from petta import testing

        @given(testing.atoms())
        def test_my_translator_round_trips(atom):
            assert decode(encode(atom)) == atom
    """
    st = _st()
    leaves = [symbols(), grounded()]
    if not ground:
        leaves.insert(1, variables())
    return st.recursive(
        st.one_of(*leaves),
        lambda inner: st.lists(inner, max_size=4).map(Expr),
        max_leaves=max_leaves,
    )


def expressions(max_leaves: int = 8, *, ground: bool = False):
    """Non-empty expression-rooted atoms, the shape spaces store."""
    st = _st()
    return st.lists(atoms(max_leaves, ground=ground), min_size=1, max_size=4).map(Expr)
