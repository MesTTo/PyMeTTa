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
    test_swrite_writes_the_engines_own_boolean_literal; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every generated Expression has symmetric, hash-coherent equality with its
    recursively transparent tuple value [tested:
    test_expression_tuple_equality_is_symmetric_and_hash_coherent;
    commit=012413efb73b4dd27c71354c7f654862f349c03f]
  - from_pattern produces ground instances while retaining repeated-variable
    equality [tested:
    test_from_pattern_generates_ground_instances_without_losing_aliases and
    test_from_pattern_draws_anonymous_occurrences_independently;
    commit=5750e8fe84d8e933c1b5ef5d08c801846c8e5eb8]
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
        "metta_py_decode_shared(W, _T, _), metta_py_encode(_T, W2)", W=atom.to_wire()
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
        printed = rt.once("metta_py_swrite(W, Str)", W=atom.to_wire())["Str"]
    except EngineError as error:
        message = str(error)
        assert "cannot write" in message
        assert "read back as a different value" in message
        return
    reread = rt.once("metta_py_parse(Src, W2)", Src=printed)["W2"]
    assert wire.from_wire(reread).alpha_eq(atom)


def test_swrite_writes_the_engines_own_boolean_literal(metta_session):
    """The engine emits `true` and `false`, and reads both spellings back."""
    rt = metta_session.runtime
    #Either spelling READS to the same boolean, and the engine WRITES the
    #lowercase one, which is upstream PeTTa's
    #[source: PeTTa@ae66fa8 src/parser.pl:76-78 maps the capitalised pair on
    #read and carries no write-side inverse].
    for spelling in ("True", "true"):
        atom = metta_session.parse(spelling)
        assert rt.once("metta_py_swrite(W, Str)", W=atom.to_wire())["Str"] == "true"
    for spelling in ("False", "false"):
        atom = metta_session.parse(spelling)
        assert rt.once("metta_py_swrite(W, Str)", W=atom.to_wire())["Str"] == "false"


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
        "metta_py_decode_shared(W, _T, _), metta_py_encode(_T, W2)",
        W=Symbol("true").to_wire(),
    )
    assert wire.from_wire(row["W2"]) == Grounded(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert parse("true") == Grounded(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch


@settings(max_examples=80, deadline=None)
@given(
    a=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
    b=st.one_of(st.integers(-99, 99), st.floats(allow_nan=True, allow_infinity=False, width=32), st.booleans(), st.text("ab", max_size=3)),
)
def test_python_equality_is_engine_equality(metta, a, b):
    """Grounded against a RAW value answers exactly what the engine's == answers
    for two values of the same MeTTa type, NaN, negative zero and mixed
    numeric types included.

    `==` is declared `(-> $a $b Bool)`, two INDEPENDENT type variables, so it
    constrains nothing and every pair gets a verdict rather than a refusal:
    `(== 1 "a")` is False, not an error. The engine's == is EXACT where
    Python's coerces, and upstream agrees with the engine on all of them
    [measured 2026-08-30 against PeTTa@ae66fa8: `(== 0 0)` and `(== 0.0 0.0)`
    are True, `(== 1 1.0)`, `(== True 1)` and `(== 1 "a")` are False, and
    `(== 0.0 -0.0)` is False through both doors].

    So `Grounded.__eq__` is the engine's relation rather than Python's: where
    the two operands are the same Python type the verdicts agree exactly, and
    where they are not the engine answers False. What this pins is that the
    Python implementation of the relation and the Prolog one do not drift,
    which is why it compares the engine's own answer with the Python operator
    rather than asserting either alone. `__eq__` may not raise, or a Grounded
    could not sit in a dict beside a value of another kind.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    engine = metta.eval(Expression(S["=="], Grounded(a), Grounded(b)))
    assert len(engine) == 1
    if type(a) is type(b):
        assert engine[0].value is (Grounded(a) == b)
    else:
        assert engine[0].value is False


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


@settings(max_examples=40, deadline=None)
@given(
    pt.from_pattern(
        S.pair(Variable("shared"), S.nested(Variable("shared"), Variable("_")))
    )
)
def test_from_pattern_generates_ground_instances_without_losing_aliases(atom):
    """A pattern becomes ground without breaking its repeated-variable law."""
    assert atom.vars == ()
    assert atom[1] == atom[2][1]


def test_from_pattern_draws_anonymous_occurrences_independently():
    """Two anonymous holes can receive different ground values."""
    instance = hypothesis.find(
        pt.from_pattern(S.pair(Variable("_"), Variable("_")), max_leaves=2),
        lambda atom: atom[1] != atom[2],
    )
    assert instance.vars == ()


def test_testing_names_the_need_without_hypothesis(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    monkeypatch.setitem(sys.modules, "hypothesis", None)
    with pytest.raises(ImportError, match="hypothesis"):
        pt.names()
