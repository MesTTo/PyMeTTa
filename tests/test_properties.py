"""Purpose: property-based tests over the atom model and the boundary.
Hypothesis generates random atoms; the laws are wire round trips in Python
and through the live engine, print-then-parse agreement with the engine's own
reader, alpha-equivalence being an equivalence, and unification soundness.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from petta import Expr, Gnd, S, Sym, Var, alpha_eq, expr, unify  # noqa: E402
from petta.atoms import from_wire  # noqa: E402

# Names PeTTa's tokeniser reads back whole: no whitespace, parens, quotes,
# and not starting with the characters that mean something else at the front.
# true and false are excluded alongside True and False: the engine holds its
# booleans as those very atoms, so the symbol spelling and the boolean are one
# term there, and a round trip canonicalizes to the boolean; pinned below.
_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_?<>=+*"),
    min_size=1,
    max_size=12,
).filter(
    lambda s: s[0] not in "$&-<>=+*?0123456789"
    and s not in ("True", "False", "true", "false")
)

_numbers = st.one_of(
    st.integers(min_value=-(2**62), max_value=2**62),
    # inf prints as a symbol under the engine's printer, and NaN never
    # compares equal; both are excluded as printer limits, not carried bugs.
    st.floats(allow_nan=False, allow_infinity=False, width=64),
)

_strings = st.text(
    alphabet=st.characters(codec="utf-8", exclude_characters='\x00'),
    max_size=20,
)


def _atoms(depth: int = 3):
    base = st.one_of(
        _name.map(Sym),
        _name.map(Var),
        _numbers.map(Gnd),
        st.booleans().map(Gnd),
        _strings.map(Gnd),
    )
    return st.recursive(
        base,
        lambda inner: st.lists(inner, max_size=4).map(Expr),
        max_leaves=8,
    )


@given(_atoms())
def test_python_wire_round_trip(atom):
    assert from_wire(atom.to_wire()) == atom


@given(_atoms())
@settings(max_examples=60, deadline=None)
def test_engine_wire_round_trip(metta_session, atom):
    """Across the boundary and back: decode_shared then encode in Prolog."""
    rt = metta_session.runtime
    # _T stays goal-internal: janus cannot convert an unbound variable back
    # to Python, and a decoded Var is exactly that.
    row = rt.once(
        "petta_py_decode_shared(W, _T, _), petta_py_encode(_T, W2)", W=atom.to_wire()
    )
    assert alpha_eq(from_wire(row["W2"]), atom)


@given(_atoms())
@settings(max_examples=60, deadline=None)
def test_print_then_parse_agrees_with_the_engine(metta_session, atom):
    """The engine's printer and reader close the loop, up to variable names."""
    rt = metta_session.runtime
    printed = rt.once("petta_py_swrite(W, Str)", W=atom.to_wire())["Str"]
    reread = rt.once("petta_py_parse(Src, W2)", Src=printed)["W2"]
    assert alpha_eq(from_wire(reread), atom)


@given(_atoms(), _atoms())
def test_alpha_eq_is_an_equivalence(a, b):
    assert alpha_eq(a, a)
    assert alpha_eq(a, b) == alpha_eq(b, a)


@given(_atoms())
def test_alpha_eq_survives_renaming(atom):
    mapping = {}

    def rename(x):
        if isinstance(x, Var):
            fresh = mapping.setdefault(x.name, f"r{len(mapping)}")
            return Var(fresh)
        if isinstance(x, Expr):
            return Expr([rename(c) for c in x])
        return x

    assert alpha_eq(atom, rename(atom))


def _substitute(pattern, bindings):
    if isinstance(pattern, Var):
        return bindings.get(pattern.name, pattern)
    if isinstance(pattern, Expr):
        return Expr([_substitute(c, bindings) for c in pattern])
    return pattern


@given(_atoms())
def test_unify_is_sound(atom):
    """A pattern that matches binds variables such that substitution gives
    back the atom, checked with the pattern being the atom itself and with
    one subterm generalized."""
    got = unify(atom, atom)
    assert got is not None
    if isinstance(atom, Expr) and len(atom) > 0:
        pattern = Expr([Var("hole"), *atom.children[1:]])
        bound = unify(pattern, atom)
        assert bound is not None
        assert _substitute(pattern, bound) == atom


@pytest.fixture(scope="module")
def metta_session(metta):
    return metta


def test_the_boolean_atoms_are_one_term_with_their_symbols(metta_session):
    """Engine identification, pinned: the symbol true IS the boolean atom, so
    a Sym('true') crossing the boundary comes back as the boolean, exactly as
    a lowercase true in source reads as one."""
    from petta import Gnd, Sym, parse
    from petta.atoms import from_wire

    rt = metta_session.runtime
    row = rt.once(
        "petta_py_decode_shared(W, _T, _), petta_py_encode(_T, W2)",
        W=Sym("true").to_wire(),
    )
    assert from_wire(row["W2"]) == Gnd(True)
    assert parse("true") == Gnd(True)
