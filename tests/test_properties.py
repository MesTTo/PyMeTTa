"""Purpose: property-based tests over the atom model and the boundary.
Hypothesis generates random atoms; the laws are wire round trips in Python
and through the live engine, writer refusal or print-then-parse agreement with
the engine's own reader, alpha-equivalence being an equivalence, and
unification soundness.
Guarantees:
  - every generated atom either survives the engine writer-reader round trip
    or receives the writer's explicit loss-of-identity refusal [tested:
    test_every_generated_atom_survives_the_write_parse_round_trip;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - booleans use MeTTa's canonical True and False text [tested:
    test_swrite_writes_mettas_own_boolean_literal; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every generated Expression has symmetric, hash-coherent equality with its
    recursively transparent tuple value [tested:
    test_expression_tuple_equality_is_symmetric_and_hash_coherent;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import sys

import pytest

from metta import (
    Expression,
    Grounded,
    S,
    Symbol,
    Variable,
    parse,
    unify,
    wire,
)

# The generators are the library's own public ones: metta.testing carries
# the engine truths (readable names, boolean canonicalization, printer
# limits) so users fuzz with exactly what this suite fuzzes with.
from metta import testing as pt
from metta.errors import EngineError

hypothesis = pytest.importorskip("hypothesis")
example = hypothesis.example
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

_name = pt.names()
_numbers = pt.numbers()
_strings = pt.texts()
_atoms = pt.atoms

# This lane deliberately goes beyond metta.testing.atoms(), whose public
# strategy generates only reader-safe names and serializable grounded values.
# The writer law must cover values at the edge of its domain too: arbitrary
# UTF-8 symbol names, and Janus tuples that have no MeTTa literal.
_any_text = st.text(
    alphabet=st.characters(codec="utf-8", exclude_characters="\x00"), max_size=20
)
_host_tuples = st.one_of(
    st.just(()),
    st.tuples(st.integers(-100, 100), _any_text),
)
_writer_atoms = st.recursive(
    st.one_of(
        _any_text.map(Symbol),
        pt.variables(),
        pt.grounded(),
        _host_tuples.map(Grounded),
    ),
    lambda inner: st.lists(inner, max_size=4).map(Expression),
    max_leaves=10,
)


@given(_atoms())
def test_python_wire_round_trip(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert wire.from_wire(atom.to_wire()) == atom


@given(_atoms())
@settings(max_examples=60, deadline=None)
def test_engine_wire_round_trip(metta_session, atom):
    """Across the boundary and back: decode_shared then encode in Prolog."""
    rt = metta_session.runtime
    # _T stays goal-internal: janus cannot convert an unbound variable back
    # to Python, and a decoded Variable is exactly that.
    row = rt.once(
        "petta_py_decode_shared(W, _T, _), petta_py_encode(_T, W2)", W=atom.to_wire()
    )
    assert wire.from_wire(row["W2"]).alpha_eq(atom)


# Counterexamples this project already paid for, pinned so they run on every
# invocation instead of when the generator happens to rediscover them. The
# newline is the one that mattered: swrite emitted it raw, the MORK bridge
# splits dumps on newlines, and the fuzz round read that back as corruption.
# The other four are the rest of hyperon's five string escapes, which the
# reader decodes and the printer therefore has to emit.
@example(atom=Symbol("$notvar"))
@example(atom=Symbol("has space"))
@example(atom=Symbol("42"))
@example(atom=Grounded((1, 2)))
@example(atom=Grounded(()))
@example(atom=Grounded("line one\nline two"))
@example(atom=Grounded("a\tb"))
@example(atom=Grounded('say "hi"'))
@example(atom=Grounded("back\\slash"))
@example(atom=Grounded("carriage\rreturn"))
@example(atom=Expression(S.s, Grounded("nested\nnewline")))
@given(_writer_atoms)
@settings(max_examples=100, deadline=None)
def test_every_generated_atom_survives_the_write_parse_round_trip(
    metta_session, atom
):
    """The writer either closes the reader loop or refuses before text exists."""
    rt = metta_session.runtime
    try:
        printed = rt.once("petta_py_swrite(W, Str)", W=atom.to_wire())["Str"]
    except EngineError as error:
        message = str(error)
        assert "cannot write" in message
        assert "read back as a different value" in message
        return
    reread = rt.once("petta_py_parse(Src, W2)", Src=printed)["W2"]
    assert wire.from_wire(reread).alpha_eq(atom)


def test_swrite_writes_mettas_own_boolean_literal(metta_session):
    """The engine emits the language's canonical boolean spellings."""
    rt = metta_session.runtime
    true_atom = metta_session.parse("True")
    false_atom = metta_session.parse("False")
    assert rt.once("petta_py_swrite(W, Str)", W=true_atom.to_wire())["Str"] == "True"
    assert rt.once("petta_py_swrite(W, Str)", W=false_atom.to_wire())["Str"] == "False"


@given(_atoms(), _atoms())
def test_alpha_eq_is_an_equivalence(a, b):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert a.alpha_eq(a)
    assert a.alpha_eq(b) == b.alpha_eq(a)


@given(_atoms())
def test_alpha_eq_survives_renaming(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    mapping = {}

    def rename(x):
        if isinstance(x, Variable):
            fresh = mapping.setdefault(x.name, f"r{len(mapping)}")
            return Variable(fresh)
        if isinstance(x, Expression):
            return Expression([rename(c) for c in x])
        return x

    assert atom.alpha_eq(rename(atom))


def _transparent_tuple(atom):
    """Spell an Expression tree as nested immutable Python tuples."""
    if isinstance(atom, Expression):
        return tuple(_transparent_tuple(child) for child in atom)
    return atom


@given(pt.expressions())
def test_expression_tuple_equality_is_symmetric_and_hash_coherent(atom):
    """Cross-representation equality obeys symmetry and Python's hash law."""
    transparent = _transparent_tuple(atom)

    assert atom == transparent
    assert transparent == atom
    assert hash(atom) == hash(transparent)


def _substitute(pattern, bindings):
    if isinstance(pattern, Variable):
        return bindings.get(pattern.name, pattern)
    if isinstance(pattern, Expression):
        return Expression([_substitute(c, bindings) for c in pattern])
    return pattern


@given(_atoms())
def test_unify_is_sound(atom):
    """A pattern that matches binds variables such that substitution gives
    back the atom, checked with the pattern being the atom itself and with
    one subterm generalized.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    got = unify(atom, atom)
    assert got is not None
    if isinstance(atom, Expression) and len(atom) > 0:
        pattern = Expression([Variable("hole"), *atom.children[1:]])
        bound = unify(pattern, atom)
        assert bound is not None
        assert _substitute(pattern, bound) == atom


@pytest.fixture(scope="module")
def metta_session(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta


def test_the_boolean_atoms_are_one_term_with_their_symbols(metta_session):
    """Engine identification, pinned: the symbol true IS the boolean atom, so
    a Symbol('true') crossing the boundary comes back as the boolean, exactly as
    a lowercase true in source reads as one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    rt = metta_session.runtime
    row = rt.once(
        "petta_py_decode_shared(W, _T, _), petta_py_encode(_T, W2)",
        W=Symbol("true").to_wire(),
    )
    assert wire.from_wire(row["W2"]) == Grounded(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert parse("true") == Grounded(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch


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
    """Grounded against a RAW value answers exactly what the engine's == answers
    for two values of the same MeTTa type, NaN, negative zero and mixed
    numeric types included.

    Across two DIFFERENT types the engine answers its refusal rather than a
    verdict, since `==` is declared `(-> $a $a Bool)` and the question has
    none: the answer is `(Error <call> (BadArgType ...))`. Python still answers
    False there, and has to: `__eq__` may not raise, or a Grounded could not sit in
    a dict beside a value of another kind. So the law is "same kind, same
    verdict; different kind, the engine says so", which is the strongest form
    both sides can hold at once. The raw operand carries the == operator's
    relation; two ATOMS carry unification instead, the next law down.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    if _kind(a) != _kind(b):
        refused = metta.eval(Expression(S["=="], Grounded(a), Grounded(b)))
        assert len(refused) == 1
        assert str(refused[0]).startswith("(Error (==")
        assert "BadArgType" in str(refused[0])
        assert (Grounded(a) == b) is False
        return
    engine = metta.eval(Expression(S["=="], Grounded(a), Grounded(b)))
    assert len(engine) == 1
    assert engine[0].value is (Grounded(a) == b)


@settings(max_examples=80, deadline=None)
@given(
    a=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
    b=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
)
def test_atom_equality_is_engine_unification(metta, a, b):
    """Grounded against another ATOM answers exactly what the engine's matcher
    answers, one universal law with no kind split: an integer atom never
    matches a float atom even where == answers True, 0.0 and -0.0 are two
    atoms, and one NaN atom matches another where == answers False. Java
    draws the same line between == and Double.equals so hash collections
    stay coherent; here the line is the engine's own unification, and unify
    and hashing follow it. Found by the space state machine: its Counter
    model diverged from storage on exactly the pairs the two relations split.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with metta._new_space() as space:
        space.add(Expression([Grounded(b)]))
        matched = len(list(space.match(Expression([Grounded(a)])))) == 1
    assert (Grounded(a) == Grounded(b)) is matched
    assert (unify(Grounded(a), Grounded(b)) is not None) is matched
    if matched:
        assert hash(Grounded(a)) == hash(Grounded(b))


@given(pt.atoms(ground=True))
def test_ground_strategy_generates_no_variables(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert list(atom.vars) == []


def test_testing_names_the_need_without_hypothesis(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    monkeypatch.setitem(sys.modules, "hypothesis", None)
    with pytest.raises(ImportError, match="hypothesis"):
        pt.names()
