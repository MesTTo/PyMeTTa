"""Purpose: property-based tests over the atom model and the boundary.
Hypothesis generates random atoms; the laws are wire round trips in Python
and through the live engine, print-then-parse agreement with the engine's own
reader, alpha-equivalence being an equivalence, and unification soundness.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import sys

import pytest

from petta import (
    Expr,
    Gnd,
    S,
    Sym,
    Var,
    alpha_eq,
    expr,
    parse,
    unify,
)

# The generators are the library's own public ones: petta.testing carries
# the engine truths (readable names, boolean canonicalization, printer
# limits) so users fuzz with exactly what this suite fuzzes with.
from petta import testing as pt
from petta.atoms import from_wire, variables

hypothesis = pytest.importorskip("hypothesis")
example = hypothesis.example
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

_name = pt.names()
_numbers = pt.numbers()
_strings = pt.texts()
_atoms = pt.atoms


@given(_atoms())
def test_python_wire_round_trip(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


# Counterexamples this project already paid for, pinned so they run on every
# invocation instead of when the generator happens to rediscover them. The
# newline is the one that mattered: swrite emitted it raw, the MORK bridge
# splits dumps on newlines, and the fuzz round read that back as corruption.
# The other four are the rest of hyperon's five string escapes, which the
# reader decodes and the printer therefore has to emit.
@example(atom=Gnd("line one\nline two"))
@example(atom=Gnd("a\tb"))
@example(atom=Gnd('say "hi"'))
@example(atom=Gnd("back\\slash"))
@example(atom=Gnd("carriage\rreturn"))
@example(atom=expr(S.s, Gnd("nested\nnewline")))
@given(_atoms())
@settings(max_examples=60, deadline=None)
def test_print_then_parse_agrees_with_the_engine(metta_session, atom):
    """The engine's printer and reader close the loop, up to variable names."""
    rt = metta_session.runtime
    printed = rt.once("petta_py_swrite(W, Str)", W=atom.to_wire())["Str"]
    reread = rt.once("petta_py_parse(Src, W2)", Src=printed)["W2"]
    assert alpha_eq(from_wire(reread), atom)


@given(_atoms(), _atoms())
def test_alpha_eq_is_an_equivalence(a, b):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert alpha_eq(a, a)
    assert alpha_eq(a, b) == alpha_eq(b, a)


@given(_atoms())
def test_alpha_eq_survives_renaming(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
    one subterm generalized.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    got = unify(atom, atom)
    assert got is not None
    if isinstance(atom, Expr) and len(atom) > 0:
        pattern = Expr([Var("hole"), *atom.children[1:]])
        bound = unify(pattern, atom)
        assert bound is not None
        assert _substitute(pattern, bound) == atom


@pytest.fixture(scope="module")
def metta_session(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta


def test_the_boolean_atoms_are_one_term_with_their_symbols(metta_session):
    """Engine identification, pinned: the symbol true IS the boolean atom, so
    a Sym('true') crossing the boundary comes back as the boolean, exactly as
    a lowercase true in source reads as one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    rt = metta_session.runtime
    row = rt.once(
        "petta_py_decode_shared(W, _T, _), petta_py_encode(_T, W2)",
        W=Sym("true").to_wire(),
    )
    assert from_wire(row["W2"]) == Gnd(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert parse("true") == Gnd(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch


def _kind(value):
    """The MeTTa type a Python value crosses as. bool first, because it is a
    subclass of int in Python and is Bool rather than Number in MeTTa.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    if isinstance(value, bool):
        return "Bool"
    if isinstance(value, (int, float)):
        return "Number"
    return "String"


@settings(max_examples=80, deadline=None)
@given(
    a=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
    b=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
)
def test_python_equality_is_engine_equality(metta, a, b):
    """Gnd == Gnd answers exactly what the engine's == answers for two values
    of the same MeTTa type, NaN, negative zero and mixed numeric types
    included.

    Across two DIFFERENT types the engine answers its refusal rather than a
    verdict, since `==` is declared `(-> $a $a Bool)` and the question has
    none: the answer is `(Error <call> (BadArgType ...))`. Python still answers
    False there, and has to: `__eq__` may not raise, or a Gnd could not sit in
    a dict beside a value of another kind. So the law is "same kind, same
    verdict; different kind, the engine says so", which is the strongest form
    both sides can hold at once.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    if _kind(a) != _kind(b):
        refused = metta.eval(expr(S["=="], Gnd(a), Gnd(b)))
        assert len(refused) == 1
        assert str(refused[0]).startswith("(Error (==")
        assert "BadArgType" in str(refused[0])
        assert (Gnd(a) == Gnd(b)) is False
        return
    engine = metta.eval(expr(S["=="], Gnd(a), Gnd(b)))
    assert len(engine) == 1
    assert engine[0].value is (Gnd(a) == Gnd(b))


@given(pt.atoms(ground=True))
def test_ground_strategy_generates_no_variables(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert list(variables(atom)) == []


def test_testing_names_the_need_without_hypothesis(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    monkeypatch.setitem(sys.modules, "hypothesis", None)
    with pytest.raises(ImportError, match="hypothesis"):
        pt.names()
