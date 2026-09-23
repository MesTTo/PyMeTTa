"""Purpose: a term a Python provider stores comes back as the engine term it
was, exactly as a native space gives it back.

The wire grammar reads a non-list compound as an expression, an improper or
partial list as a (cons Head Tail) chain and a dict as text. That is right for
an answer and wrong for a store, so the provider door carries every such term
as a handle (metta_py_encode_carried/4 in metta/_binding/wire.pl) and reads
everything else as the grammar does. Each property here stores generated terms
in a native space and in a provider side by side and requires the two to agree
on what match and get-atoms give back, on what a removal leaves, and on what a
stored partial application still computes.

The terms are generated as Prolog text and built by the engine's reader,
because a Python atom cannot spell a compound, a dict or an improper list:
only the engine makes one, which is why only the provider door meets them.
The oracle text is the engine's own writer with variables named by position,
so two readings agree exactly when the terms are variants.
Guarantees:
  - what a provider gives back through match and get-atoms is what a native
    space gives back, for leaves, proper, improper and partial lists,
    non-list compounds, dicts and partial applications [tested:
    test_every_kind_reads_back_as_a_native_space_reads_it_back,
    test_a_provider_reads_back_what_a_native_space_reads_back]
  - removing one stored term removes exactly that term from both
    [tested: test_removing_a_carried_term_removes_exactly_that_term,
    test_removing_one_term_removes_exactly_that_term]
  - a stored partial application applies when read back, and a variable it
    shares with the rest of its atom is bound through both [tested:
    test_a_stored_partial_application_still_applies,
    test_a_variable_shared_with_a_carried_term_stays_shared]
  - the provider meets a carried handle exactly for the terms the grammar
    would change, and one compares equal to the same term crossing again
    [tested: test_the_provider_meets_a_handle_exactly_where_the_grammar_would_change_the_term]
  - a rational tree is refused at the door with the error a native space
    gives [tested: test_a_rational_tree_is_refused_as_a_native_space_refuses_it]
  - a journalled provider and a table bridge refuse a carried term in words
    before writing [tested: test_a_persistent_space_refuses_a_carried_term_by_name,
    test_a_table_bridge_refuses_a_carried_term_by_name]
  - a carried term holds a janus Term, so dropping it hands its record to the
    next crossing's erase [tested:
    test_a_dropped_carried_term_hands_its_record_to_the_next_crossing]
  - a world over a provider reads carried terms back as the provider stored
    them, and two crossings of one term are one atom to diff, AlphaSet and a
    world commit [tested: test_a_world_over_a_provider_commits_only_what_changed,
    test_two_crossings_of_one_carried_term_are_one_atom_up_to_renaming]
  - a stored partial naming the provider's space, applied in a world over it,
    writes to the world until a commit [tested:
    test_a_stored_partial_applied_in_a_world_writes_to_the_world]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import gc
import pickle
import sqlite3
from collections.abc import Callable, Iterator

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from metta import Atom, Expression, S, Symbol, V, Variable
from metta import space as make_space
from metta._atoms.model import _CarriedTerm
from metta._binding import runtime as _runtime
from metta._declare import declarations as _space_declarations
from metta._errors.errors import EngineError, MettaError
from metta.foreign import SpaceProvider
from metta.foreign._persistent import PersistentFactSpace
from metta.spaces import diff
from metta.structures import AlphaSet
from metta.tables import TableBridge

#: The reader and writer the properties compare through, registered as MeTTa
#: functions for the length of each test. pc-text takes an Atom so the term it
#: is handed arrives as the stored term rather than evaluated.
_FIXTURE = """
:- metta_extension(provider_carry_fixture, [version('0.1.0')]).
:- metta_export("
    (: pc-term (-> String Atom))
    (: pc-text (-> Atom String))
").
'pc-term'(Text, Term) :- term_string(Term, Text, [double_quotes(string)]).
'pc-text'(Term, Text) :-
    copy_term_nat(Term, Copy),
    term_variables(Copy, Variables),
    pc_positions(Variables, 0, Names),
    format(string(Text), "~W",
           [Copy, [quoted(true), numbervars(false), variable_names(Names)]]).
pc_positions([], _, []).
pc_positions([V|Vs], I, [Name=V|Names]) :-
    format(atom(Name), "_~d", [I]),
    J is I + 1,
    pc_positions(Vs, J, Names).
"""


class _Store(SpaceProvider):
    """A list of atoms whose removal takes one occurrence the test names.

    `same` is how a removal recognises what it holds. Equality is enough for
    a ground term; a term with variables crosses under new names each time,
    for a plain variable and a carried one alike, so the removal tests
    compare up to renaming, which is the variant a native space removes.
    """

    def __init__(self, same: Callable[[Atom, Atom], bool] = Atom.alpha_eq) -> None:
        self.stored: list[Atom] = []
        self.same = same

    def match(self, _pattern: Atom) -> Iterator[Atom]:
        return iter(self.stored)

    def atoms(self) -> Iterator[Atom]:
        return iter(self.stored)

    def add(self, atom: Atom) -> None:
        self.stored.append(atom)

    def remove(self, atom: Atom) -> bool:
        for index, held in enumerate(self.stored):
            if self.same(held, atom):
                del self.stored[index]
                return True
        return False


class _WorldStore(_Store):
    """A store that can be reified and takes a world's diff in one call."""

    def __init__(self) -> None:
        super().__init__()
        self.commits: list[tuple[list[Atom], list[Atom]]] = []

    def snapshot(self) -> tuple[Atom, ...]:
        return tuple(self.stored)

    def commit_world(self, base: tuple[Atom, ...], removed: list[Atom], added: list[Atom]) -> None:
        del base
        self.commits.append((list(removed), list(added)))
        for atom in removed:
            self.remove(atom)
        self.stored.extend(added)


@pytest.fixture()
def carry(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.register_prolog(_FIXTURE)
    yield metta
    metta.unregister_prolog("provider_carry_fixture")


# ------------------------------------------------------------------ terms
#
# A small grammar of Prolog term text whose productions are the shapes the
# door has to tell apart. Three variable names are shared across a whole term,
# so a variable can occur in a carried part and in the rest at once.
#
# A composite rather than st.recursive over mapped branches: Hypothesis 6.165
# re-encodes a drawn value into its strategy's choices while it generates (a
# ValueHole, hypothesis/internal/conjecture/data.py draw), and a value a
# one_of cannot re-encode is reported with the one_of's whole repr, 85 kB for
# the recursive form, which the suite's warnings-as-errors turned into a
# failure of its own [measured 2026-09-24: HypothesisWarning "Generating
# overly large repr" from hypothesis/internal/reflection.py:331, then
# FlakyStrategyDefinition]. A composite's repr is its call.

_VARIABLES = ("X", "Y", "Z")
_LEAVES = st.one_of(
    st.sampled_from(("a", "b", "foo", "'Big'", "'x y'", "[]", "true")),
    st.integers(-3, 3).map(str),
    st.sampled_from(("1.5", "-0.0", "123456789012345678901234567890")),
    st.sampled_from(('"s"', '""', '"x y"')),
    st.sampled_from(_VARIABLES),
)
# A tail that makes a list improper: anything but a list or a variable.
_IMPROPER_TAILS = ("b", "1", '"s"', "f(x)")
_SHAPES = ("leaf", "list", "improper", "partial", "compound", "dict")


@st.composite
def _term_text(draw, depth: int = 3) -> str:
    """One term's text: a leaf, or a list, improper list, partial list,
    non-list compound (janus's tuple carrier -/N among them) or dict over
    terms one level shallower.
    """  # noqa: D205  -- the strategy's grammar is one continuous statement
    shape = draw(st.sampled_from(_SHAPES if depth > 0 else ("leaf",)))
    if shape == "leaf":
        return draw(_LEAVES)
    minimum = 0 if shape in ("list", "dict") else 1
    children = draw(st.lists(_term_text(depth - 1), min_size=minimum, max_size=3))
    items = ", ".join(children)
    if shape == "list":
        return f"[{items}]"
    if shape == "improper":
        return f"[{items}|{draw(st.sampled_from(_IMPROPER_TAILS))}]"
    if shape == "partial":
        return f"[{items}|{draw(st.sampled_from(_VARIABLES))}]"
    if shape == "compound":
        return f"{draw(st.sampled_from(('f', 'g', 'partial', '-')))}({items})"
    tag = draw(st.sampled_from(("_", "point")))
    # The space after the colon keeps a negative value from reading as `:-`.
    fields = ", ".join(
        f"{key}: {value}" for key, value in zip(("k", "m", "n"), children, strict=False)
    )
    return f"{tag}{{{fields}}}"


_TERMS = _term_text()

# One of every kind the door has to tell apart, run as its own case so a door
# reading any of them through the grammar fails whatever the properties draw.
# Pinned in a plain test rather than as an explicit example: Hypothesis tries
# to invert an explicit example into its strategy's choices, and a value the
# grammar above cannot draw fails that with an 85 kB repr of the strategy,
# which the suite's warnings-as-errors turns into a failure of its own.
_EVERY_KIND = [
    "partial(+, [1])",
    "f(X, [a|Y], X)",
    "[a|b]",
    "[a|T]",
    "_{k:1, m:X}",
    "point{x:[a|b]}",
    "-(a, b)",
    "[f, 1]",
    '"s"',
    "X",
]


def _store(target, index: int, text: str) -> None:
    """Build the term from its text in the engine and add (stored index term)."""
    target.eval(S.let(V.t, S["pc-term"](text), S["add-atom"](target, S.stored(index, V.t))))


def _matched(target) -> list[str]:
    """What match gives back, as oracle text, in a stable order."""
    answers = target.eval(
        S.match(target, S.stored(V.i, V.x), S["pc-text"](S.stored(V.i, V.x)))
    )
    return sorted(answer.value for answer in answers)


def _enumerated(target) -> list[str]:
    """What get-atoms gives back, as oracle text, in a stable order."""
    answers = target.eval(S.let(V.a, S["get-atoms"](target), S["pc-text"](V.a)))
    return sorted(answer.value for answer in answers)


def _reads_back_alike(metta, texts: list[str]) -> None:
    """Store the terms in a native space and a provider, and compare readings."""
    with metta._new_space() as native, make_space(backing=_Store()) as backed:
        for index, text in enumerate(texts):
            _store(native, index, text)
            _store(backed, index, text)
        assert _matched(backed) == _matched(native)
        assert _enumerated(backed) == _enumerated(native)


def _removes_alike(metta, texts: list[str], victim: int) -> None:
    """Remove one stored term from both, and compare what each has left.

    Each term is stored under its own index, so the removal pattern unifies
    with the one stored term it names and nothing else: a native space drains
    every atom that unifies, and a provider is asked for each one found.
    """
    with metta._new_space() as native, make_space(backing=_Store()) as backed:
        for index, text in enumerate(texts):
            _store(native, index, text)
            _store(backed, index, text)
        for target in (native, backed):
            target.eval(S.let(V.t, S["pc-term"](texts[victim]),
                              S["remove-atom"](target, S.stored(victim, V.t))))
        remaining = _enumerated(native)
        assert _enumerated(backed) == remaining
        assert len(remaining) == len(texts) - 1


def test_every_kind_reads_back_as_a_native_space_reads_it_back(carry):
    """One term of every kind, through match and get-atoms."""
    _reads_back_alike(carry, _EVERY_KIND)


@settings(max_examples=40, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.lists(_TERMS, min_size=1, max_size=5))
def test_a_provider_reads_back_what_a_native_space_reads_back(carry, texts):
    """Match and get-atoms answer the same terms through both spaces."""
    _reads_back_alike(carry, texts)


def test_removing_a_carried_term_removes_exactly_that_term(carry):
    """The compound with shared variables goes, and every other kind stays."""
    _removes_alike(carry, _EVERY_KIND, _EVERY_KIND.index("f(X, [a|Y], X)"))


@settings(max_examples=40, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.lists(_TERMS, min_size=1, max_size=5), st.integers(0, 9))
def test_removing_one_term_removes_exactly_that_term(carry, texts, drawn):
    """remove-atom of one stored term leaves both spaces holding the same rest."""
    _removes_alike(carry, texts, drawn % len(texts))


@settings(max_examples=20, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.integers(-5, 5), st.integers(-5, 5))
@example(1, 2)
def test_a_stored_partial_application_still_applies(carry, bound, argument):
    """(id (+ k)) stored and read back applies to k + m through both spaces.

    This is the probe that found the defect: the provider answered
    ((partial + (1)) 2) where the native space answered 3
    [measured 2026-09-24: CMeTTa-Examples/ai-tmp/probe/providerpy.py].
    """
    with carry._new_space() as native, make_space(backing=_Store()) as backed:
        applied = []
        for target in (native, backed):
            target.eval(S.let(V.p, S.id(S["+"](bound)),
                              S["add-atom"](target, S.stored(0, V.p))))
            applied.append(target.eval(S.match(target, S.stored(0, V.f), Expression(V.f, argument))))
        assert applied == [[bound + argument]] * 2


def test_a_variable_shared_with_a_carried_term_stays_shared(carry):
    """(pair $v (+ $v)) stored with $v open answers 6 once $v is 5.

    The partial holds the pair's own variable, so the carried term has to name
    it as the rest of the atom does or binding $v reaches only one of them.
    """
    with carry._new_space() as native, make_space(backing=_Store()) as backed:
        for target in (native, backed):
            target.eval(S.let(V.p, S.id(S["+"](V.v)), S["add-atom"](target, S.pair(V.v, V.p))))
        assert [
            target.eval(S.match(target, S.pair(5, V.f), Expression(V.f, 1)))
            for target in (native, backed)
        ] == [[6], [6]]


@pytest.mark.usefixtures("carry")
def test_the_provider_meets_a_handle_exactly_where_the_grammar_would_change_the_term():
    """A compound, a dict and an improper or partial list arrive as handles.

    Everything else arrives as the atom it is, and a handle compares equal to
    the same term crossing again, so a provider removing by == finds it.
    """
    store = _Store(same=lambda held, atom: held == atom)
    # (text, the class the provider meets, whether the term is ground). An
    # untagged dict is not ground: its tag is a variable.
    kinds = [
        ("partial(+, [1])", _CarriedTerm, True),
        ('g("q")', _CarriedTerm, True),
        ("[a|b]", _CarriedTerm, True),
        ("[a|T]", _CarriedTerm, False),
        ("_{k:1}", _CarriedTerm, False),
        ("point{k:[a|b]}", _CarriedTerm, True),
        ("-(a, b)", _CarriedTerm, True),
        ("[f, 1]", Expression, True),
        ("foo", Symbol, True),
        ("X", Variable, False),
    ]
    with make_space(backing=store) as backed:
        for index, (text, _, _) in enumerate(kinds):
            _store(backed, index, text)
        assert [type(atom.children[2]) for atom in store.stored] == [
            kind for _, kind, _ in kinds
        ]
        # A ground term crosses again as an equal atom, so == finds it; a
        # term with variables crosses under new names, carried or not.
        for index, (text, _, ground) in enumerate(kinds):
            if ground:
                backed.eval(S.let(V.t, S["pc-term"](text),
                                  S["remove-atom"](backed, S.stored(index, V.t))))
        assert [atom.children[1] for atom in store.stored] == [
            index for index, (_, _, ground) in enumerate(kinds) if not ground
        ]
        with pytest.raises(TypeError, match="process-local"):
            pickle.dumps(store.stored[0].children[2])


def test_a_rational_tree_is_refused_as_a_native_space_refuses_it(carry):
    """(let $x (a $x) ...) is refused by name, and the provider holds nothing.

    Before the door refused it, the encoder followed the cycle until the
    engine's stack limit, where a native space's assertz refuses at once
    [measured 2026-09-24: StackLimitError at the 7.5Gb limit, this test's
    program against the door at
    commit=5563480af32ac9e00708654acfe1ad8d9a8150fc, the carried door's parent].
    """
    store = _Store()
    with carry._new_space() as native, make_space(backing=store) as backed:
        for target in (native, backed):
            with pytest.raises(EngineError, match="cyclic_term"):
                target.run(f"!(let $x (a $x) (add-atom {target.name} (cyc $x)))")
    assert store.stored == []


def test_a_persistent_space_refuses_a_carried_term_by_name(carry, tmp_path):
    """A journal cannot hold an engine term by reference, so the add says so.

    The argument check read the value slot of every Grounded, and a handle
    leaves that slot unset, so a carried term raised AttributeError where the
    documented refusal belongs.
    """
    provider = PersistentFactSpace(tmp_path / "carried.db", {"stored": 2})
    name = f"&persistent-carry{id(provider)}"
    _space_declarations._register_space(carry, provider, name)
    try:
        with pytest.raises(MettaError, match="held by reference"):
            carry.run(f"!(let $p (id (+ 1)) (add-atom {name} (stored 0 $p)))")
        assert list(provider.atoms()) == []
    finally:
        _space_declarations._unregister_space(carry, name)
        provider.close()


def test_a_table_bridge_refuses_a_carried_term_by_name(carry):
    """A table cell cannot hold an engine term by reference, and says which term.

    The bridge refused every h cell with the native blob's sentence, which
    sends the reader to accessors a partial application does not have.
    """
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE rows (value TEXT)")
    provider = TableBridge(carry.parse, connection, "(bridge (row $value) (row rows (value $value)))")
    name = f"&bridge-carry{id(provider)}"
    _space_declarations._register_space(carry, provider, name)
    try:
        with pytest.raises(MettaError, match=r"partial\(\+,\[1\]\) is an engine term held by reference"):
            carry.run(f"!(let $p (id (+ 1)) (add-atom {name} (row $p)))")
        assert connection.execute("SELECT COUNT(*) FROM rows").fetchone() == (0,)
    finally:
        _space_declarations._unregister_space(carry, name)


@pytest.mark.usefixtures("carry")
def test_a_world_over_a_provider_commits_only_what_changed():
    """Reify, add one atom in the world, commit: the provider is told of that
    atom alone, and the partial it stored still applies.

    The world read its image back through the answer grammar while the base
    the provider's snapshot supplies holds each compound as the handle it
    stored, so every compound diffed as removed and re-added and commit handed
    the provider the grammar's spelling in its place; a term with variables
    diffed the same way under the canonical form until that renamed a carried
    term's names too.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    store = _WorldStore()
    with make_space(backing=store) as backed:
        backed.covers("writesState")
        backed.eval(S.let(V.p, S.id(S["+"](1)), S["add-atom"](backed, S.stored(0, V.p))))
        _store(backed, 1, "f(X, [a|Y], X)")
        world = backed.reify()
        try:
            _, changed = world.eval("(progn (add-atom &self (extra 1)) done)")
            try:
                backed.commit(changed)
            finally:
                changed.close()
        finally:
            world.close()
        assert store.commits == [([], [S.extra(1)])]
        assert backed.eval(S.match(backed, S.stored(0, V.f), Expression(V.f, 2))) == [3]


def test_a_stored_partial_applied_in_a_world_writes_to_the_world():
    """A partial application naming the provider's space, applied inside a
    world over that provider, writes to the world, and the commit hands the
    provider that write alone.

    The world rebases its origin's name to its own space so nothing evaluated
    in it reaches the origin before a commit. The rebase walked proper lists
    only, every term the grammar gives back; the carried door hands the partial
    back as partial(Head, Args), and applying it wrote into the provider during
    the evaluation.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    store = _WorldStore()
    with make_space(backing=store) as backed:
        backed.covers("oracleIO")
        backed.eval(S.let(V.p, S.id(S["add-atom"](backed)), S["add-atom"](backed, S.stored(0, V.p))))
        before = list(store.stored)
        world = backed.reify()
        try:
            _, changed = world.eval("(match &self (stored 0 $f) ($f (written 1)))")
            try:
                assert store.stored == before
                assert S.written(1) in changed.atoms
                backed.commit(changed)
            finally:
                changed.close()
        finally:
            world.close()
        assert store.commits == [([], [S.written(1)])]


@pytest.mark.usefixtures("carry")
def test_two_crossings_of_one_carried_term_are_one_atom_up_to_renaming():
    """One term with variables stored twice crosses under two sets of names:
    unequal, alpha-equivalent, and one atom to diff and to an AlphaSet.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    first, second = _Store(), _Store()
    with make_space(backing=first) as one, make_space(backing=second) as other:
        _store(one, 0, "f(X, [a|Y], X)")
        _store(other, 0, "f(X, [a|Y], X)")
    held, again = first.stored[0], second.stored[0]
    assert isinstance(held.children[2], _CarriedTerm)
    assert held != again
    assert held.alpha_eq(again)
    assert diff(first, second) == ([], [])
    assert again in AlphaSet([held])


@pytest.mark.usefixtures("carry")
def test_a_dropped_carried_term_hands_its_record_to_the_next_crossing():
    """The handle's record is a janus Term, so the deferred release reaches it:
    dropping the last reference queues the record, and the next crossing
    erases it, with no call into Prolog from the finaliser.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    store = _Store()
    with make_space(backing=store) as backed:
        _store(backed, 0, "f(a)")
        carried = store.stored.pop().children[2]
        assert type(carried.record) is _runtime.bridge().Term
        record = carried.record._record  # the id the release defers
        del carried
        gc.collect()
        assert (_runtime._ERASE_RECORD, record) in _runtime._DEFERRED_WORK
        backed.eval(S.foo)
        assert (_runtime._ERASE_RECORD, record) not in _runtime._DEFERRED_WORK
