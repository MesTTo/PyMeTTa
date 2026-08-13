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

# The generators are the library's own public ones: petta.testing carries
# the engine truths (readable names, boolean canonicalization, printer
# limits) so users fuzz with exactly what this suite fuzzes with.
from petta import testing as pt  # noqa: E402

_name = pt.names()
_numbers = pt.numbers()
_strings = pt.texts()
_atoms = pt.atoms


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


@settings(max_examples=80, deadline=None)
@given(
    a=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
    b=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
)
def test_python_equality_is_engine_equality(metta, a, b):
    """Gnd == Gnd answers exactly what the engine's == answers for the same
    two values, NaN, negative zero and mixed numeric types included."""
    from petta.atoms import Gnd

    engine = metta.eval(expr(S["=="], Gnd(a), Gnd(b)))
    assert len(engine) == 1
    assert engine[0].value is (Gnd(a) == Gnd(b))


@given(pt.atoms(ground=True))
def test_ground_strategy_generates_no_variables(atom):
    from petta.atoms import variables

    assert list(variables(atom)) == []


def test_testing_names_the_need_without_hypothesis(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "hypothesis", None)
    with pytest.raises(ImportError, match="hypothesis"):
        pt.names()
