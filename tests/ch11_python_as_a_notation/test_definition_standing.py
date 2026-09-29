"""Purpose: the space decides what a Python definition still publishes.

A definition's process record describes what ``define`` wrote; whether it is
still there is asked of the space. These tests remove a definition's atoms
through every public door and through a MeTTa program, inside transactions
that commit and roll back and inside ``speculative()``, and check that a
re-define publishes again, that the declaration, doc, reflection rows, twin
family and lint evidence follow, that ``m.remove(<Defined>)`` takes a
definition out whole, and that a define failing at any of its writes leaves
everything as it was.

Guarantees:
  - after any interleaving of define, re-define, removal of the name's atoms
    by ``remove``, ``-=``, ``transfer`` and ``del``, removal of the Defined by
    ``remove`` and ``-=``, and clear, each run plainly, inside a committed or
    rolled-back transaction or inside ``speculative()``, the held atoms are
    the recorded ones the space holds, the reflection rows, twin family,
    generator reading and parameter roster agree with what the space holds,
    and every define leaves the space holding exactly the definition's atoms
    once [tested 2026-09-30T08:34:03+10:00:
    test_definition_caches_agree_with_the_space].
  - with removed atoms also returned by ``transfer`` and ``add`` in any of
    those scopes, the same caches follow the space, a clause brought back
    included, and a define leaves every atom of the definition held
    [tested 2026-09-30T08:34:03+10:00: test_definition_caches_follow_atoms_given_back].
"""

from __future__ import annotations

import contextlib
import re
import threading
from collections import Counter

import pytest

from metta import Atom, Expression, S, Symbol, V, catalog, equation, parse, space
from metta._declare import definitions
from metta._declare.define import PrologBacked
from metta._errors.errors import (
    CompileError,
    EngineError,
    MettaError,
    PartialWriteError,
    SubscriberError,
)
from metta._roots import workspace
from metta.foreign import SpaceProvider

hypothesis = pytest.importorskip("hypothesis")
stateful = pytest.importorskip("hypothesis.stateful")
st = hypothesis.strategies


@pytest.fixture()
def m(metta):
    """One scratch space per scenario, dropped with its definitions."""
    with metta._new_space() as space:
        yield space


def stable():  # noqa: D103 -- the report's function as it wrote it, whose doc atom would be one more atom to count
    return 7


def _one():
    def subject(x: int) -> int:
        """One more."""
        return x + 1

    return subject


def _two():
    def subject(x: int) -> int:
        """Two more, through a loop helper."""
        total = 0
        while total < 2:
            total += 1
        return x + total

    return subject


def _zero():
    def subject(x: int = 0) -> int:  # noqa: ARG001 -- the default is the clause head pattern
        """The literal zero."""
        return 100

    return subject


def _many():
    def subject(x: int):
        """Two answers."""
        yield x
        yield x + 10

    return subject


VARIANTS = {"one": _one, "two": _two, "zero": _zero, "many": _many}


def _about(atom, name: str) -> bool:
    """Whether a stored atom is one of name's equations, helpers, declarations or doc."""
    if not isinstance(atom, Expression) or len(atom.children) < 2:
        return False
    head, subject = atom.children[0], atom.children[1]
    if head == Symbol("=") and isinstance(subject, Expression) and subject.children:
        subject = subject.children[0]
    elif head not in (Symbol(":"), Symbol("@doc")):
        return False
    return isinstance(subject, Symbol) and (
        subject.name == name or subject.name.startswith(f"{name}--")
    )


def _stored(space, name: str) -> list:
    return [atom for atom in space.atoms() if _about(atom, name)]


def _canonical(atoms) -> list[str]:
    """Atoms as text with variables numbered by first appearance, sorted."""
    return sorted(_renumbered(str(atom)) for atom in atoms)


def _renumbered(text: str) -> str:
    names: dict[str, str] = {}
    return re.sub(r"\$[\w-]+", lambda found: names.setdefault(found.group(0), f"$v{len(names)}"), text)


def _reflected(space, name: str) -> bool:
    return bool(catalog.match(S.defined(S[str(space.name)], S[name])))


def test_redefining_after_an_equation_removal_publishes_again(m):
    """The report's program: the space lost the equation, so define writes it."""
    m.define(stable)
    assert m.eval(S.stable()) == [7]
    assert m.remove(equation(S.stable()).to(7))
    assert not _reflected(m, "stable")
    m.define(stable)
    assert m.eval(S.stable()) == [7]
    assert _reflected(m, "stable")


@pytest.mark.parametrize(
    "door",
    [
        pytest.param(lambda m, _sink, atom: m.remove(atom), id="remove"),
        pytest.param(lambda m, _sink, atom: m.__isub__(atom), id="isub"),
        pytest.param(lambda m, _sink, _atom: m.__delitem__(S["="](S.stable(), V.body)), id="delitem"),
        pytest.param(lambda m, sink, atom: m.transfer(atom, to=sink), id="transfer"),
    ],
)
def test_every_removal_door_retires_what_it_took(m, metta, door):
    """Each Python door that removes an equation retires its definition's rows."""
    m.define(stable)
    with metta._new_space() as sink:
        door(m, sink, equation(S.stable()).to(7))
    assert m.eval(S.stable()) == [S.stable()]
    assert not _reflected(m, "stable")
    m.define(stable)
    assert m.eval(S.stable()) == [7]
    assert _reflected(m, "stable")


def test_a_redefinition_restores_a_removed_declaration_and_doc(m):
    """Every atom a removal took from an unchanged definition comes back once."""
    subject = _one()
    m.define(subject)
    published = _canonical(_stored(m, "subject"))
    assert len(published) == 3
    for atom in _stored(m, "subject"):
        assert m.remove(atom)
    assert _stored(m, "subject") == []
    m.define(subject)
    assert _canonical(_stored(m, "subject")) == published
    assert m.eval(S.subject(1)) == [2]


def test_a_redefinition_restores_only_what_a_removal_took(m):
    """A lost helper comes back and nothing is published twice."""
    subject = _two()
    m.define(subject)
    before = _stored(m, "subject")
    helper = next(atom for atom in before if str(atom).startswith("(= (subject--"))
    assert m.remove(helper)
    m.define(subject)
    after = _stored(m, "subject")
    assert len(after) == len(before)
    assert m.eval(S.subject(1)) == [3]


def test_removing_a_defined_takes_its_whole_definition(m):
    """The door takes equations, helpers, declaration, doc and reflection."""
    defined = m.define(_two())
    assert len(_stored(m, "subject")) == 4
    assert _reflected(m, "subject")
    assert m.remove(defined) is True
    assert _stored(m, "subject") == []
    assert not _reflected(m, "subject")
    assert m.eval(S.subject(1)) == [S.subject(1)]
    assert m.remove(defined) is False
    m.define(_two())
    assert m.eval(S.subject(1)) == [3]


def test_removing_a_stacked_defined_takes_every_clause(m):
    """A Defined names every stacked clause of its name, through -= too."""
    m.define(_zero())
    stacked = m.define(_one())
    assert m.eval(S.subject(0)) == [100]
    m -= stacked
    assert _stored(m, "subject") == []
    assert not _reflected(m, "subject")


def test_the_door_leaves_an_older_equation_that_unifies_with_its_own(m, metta):
    """The door takes the definition's equation, not an older unifier of it.

    (= (subject $y) $y) unifies with the definition's (= (subject $x) (+ $x 10))
    through a rational tree. Moving the definition's equation out and back
    makes it the newer of the two, the order in which a removal by
    unification alone took the wrong one.
    """

    def subject(x: int) -> int:
        """Ten more."""
        return x + 10

    defined = m.define(subject)
    [own] = [atom for atom in _stored(m, "subject") if atom.children[0] == Symbol("=")]
    m.add(parse("(= (subject $y) $y)"))
    with metta._new_space() as elsewhere:
        assert m.transfer(own, to=elsewhere) == 1
        assert elsewhere.transfer(own, to=m) == 1
    assert sorted(m.eval(S.subject(1))) == [1, 11]
    assert m.remove(defined) is True
    assert _canonical(_stored(m, "subject")) == ["(= (subject $v0) $v0)"]
    assert m.eval(S.subject(1)) == [1]


def test_several_operands_remove_in_one_transaction(m):
    """A Defined among atoms counts as one found operand."""
    defined = m.define(_one())
    m.add(S.marker(1))
    assert m.remove(defined, S.marker(1), S.marker(2)) == 2
    assert _stored(m, "subject") == []
    assert S.marker(1) not in m


def test_a_defined_of_another_space_removes_nothing_here(m, metta):
    """Removing another space's definition answers False and leaves it."""
    with metta._new_space() as other:
        defined = other.define(_one())
        assert m.remove(defined) is False
        assert other.eval(S.subject(1)) == [2]


def test_a_prolog_backed_definition_refuses_the_door(m):
    """A registered predicate publishes no equations, so the door names its own."""
    backed = PrologBacked("dt-dot", ["a", "b"], lambda a, _b: a, m, "fast.pl")
    with pytest.raises(TypeError, match="unregister_prolog"):
        m.remove(backed)


def test_the_collision_refusal_names_the_definition_door(m):
    """The refusal's remedy is a door that exists and works."""
    def first(x: int) -> int:
        return x + 1

    def second(x: int) -> int:
        return x + 2

    owner = m.define(first, name="shared")
    with pytest.raises(CompileError, match=r"m\.remove\(first\)") as refused:
        m.define(second, name="shared")
    assert refused.value.remedy is not None
    assert refused.value.remedy.python == "m.remove(first)"
    assert m.remove(owner)
    m.define(second, name="shared")
    assert m.eval(S.shared(1)) == [3]


def test_a_removal_by_value_frees_the_head(m):
    """A head no equation answers through is free for another function."""
    def first(x: int) -> int:
        return x + 1

    def second(x: int) -> int:
        return x + 2

    m.define(first, name="shared")
    for atom in _stored(m, "shared"):
        if atom.children[0] == Symbol("="):
            assert m.remove(atom)
    m.define(second, name="shared")
    assert m.eval(S.shared(1)) == [3]


def test_a_removed_definition_starts_a_new_twin_family(m):
    """A retained twin keeps its clauses; the next define starts afresh."""
    kept = m.define(_one())
    assert m.remove(kept)
    replacement = m.define(_two())
    assert replacement.py(1) == 3
    assert kept.py(1) == 2
    assert kept.py is not replacement.py


def test_a_removed_definition_takes_its_parameter_row(m):
    """A keyword binds through the definition that owns the parameter names."""
    def weighted(left: int, right: int) -> int:
        return left * 10 + right

    m.define(weighted)
    assert m.fn.weighted(3, right=4) == [34]
    for atom in _stored(m, "weighted"):
        if atom.children[0] == Symbol("="):
            assert m.remove(atom)
    m.add(parse("(= (weighted $a $b) 73)"))
    with pytest.raises(TypeError, match="positionally"):
        m.fn.weighted(3, right=4)
    assert m.fn.weighted(3, 4) == [73]
    m.remove(parse("(= (weighted $a $b) 73)"))
    m.define(weighted)
    assert m.fn.weighted(3, right=4) == [34]


def test_a_metta_program_removal_is_observed_at_the_next_define(m):
    """A removal no Python door made is still read from the space by define."""
    m.define(stable)
    m.run(f"!(remove-atom {m.name} (= (stable) 7))")
    assert m.eval(S.stable()) == [S.stable()]
    m.define(stable)
    assert m.eval(S.stable()) == [7]
    assert _reflected(m, "stable")


class _RollbackError(Exception):
    pass


def _in_transaction(space, step, *, keep: bool) -> None:
    def body():
        step()
        if not keep:
            raise _RollbackError

    try:
        space.transaction(body)
    except _RollbackError:
        assert not keep


@pytest.mark.parametrize("commit", [True, False], ids=["commit", "rollback"])
def test_an_equation_removal_follows_its_transaction(m, commit):
    """Rollback of a removal leaves the definition published and described."""
    m.define(stable)
    _in_transaction(m, lambda: m.remove(equation(S.stable()).to(7)), keep=commit)
    assert _reflected(m, "stable") is not commit
    m.define(stable)
    assert m.eval(S.stable()) == [7]
    assert len(_stored(m, "stable")) == 1


@pytest.mark.parametrize("commit", [True, False], ids=["commit", "rollback"])
def test_the_door_follows_its_transaction(m, commit):
    """The door commits or rolls back whole, record included."""
    defined = m.define(_two())
    published = _canonical(_stored(m, "subject"))
    _in_transaction(m, lambda: m.remove(defined), keep=commit)
    assert _canonical(_stored(m, "subject")) == ([] if commit else published)
    assert _reflected(m, "subject") is not commit
    assert m.remove(defined) is not commit


@pytest.mark.parametrize("commit", [True, False], ids=["commit", "rollback"])
def test_a_rolled_back_redefinition_restores_the_twin(m, commit):
    """A rolled-back replacement leaves the old clause, twin and record."""
    first = m.define(_one())
    _in_transaction(m, lambda: m.define(_two()), keep=commit)
    assert m.eval(S.subject(1)) == ([3] if commit else [2])
    again = m.define(_one() if not commit else _two())
    assert again.py is (first.py if not commit else again.py)
    assert len([a for a in _stored(m, "subject") if a.children[0] == Symbol("=")]) == (
        2 if commit else 1
    )


@pytest.mark.parametrize("commit", [True, False], ids=["commit", "rollback"])
def test_a_rolled_back_clear_keeps_its_definitions(m, commit):
    """A rolled-back clear keeps the definitions it would have cleared."""
    m.define(stable)
    _in_transaction(m, m.clear, keep=commit)
    assert _reflected(m, "stable") is not commit
    m.define(stable)
    assert m.eval(S.stable()) == [7]
    assert len(_stored(m, "stable")) == 1


def test_a_speculative_define_and_removal_leave_no_trace(m):
    """A speculative define or removal changes neither the space nor the record."""
    with m.speculative():
        discarded = m.define(stable)
    assert discarded.py() == 7
    assert _stored(m, "stable") == []
    assert not _reflected(m, "stable")
    assert (m.name, "stable") not in definitions._DEFINITIONS
    defined = m.define(stable)
    with m.speculative():
        assert m.remove(defined) is True
        assert m.remove(equation(S.stable()).to(7)) is True
    assert m.eval(S.stable()) == [7]
    assert _reflected(m, "stable")
    assert m.remove(defined) is True


def _loop_lint(m, name):
    return [
        finding
        for finding in m.lint()
        if finding.kind == "operation-crossing-in-loop" and finding.subject == name
    ]


def test_a_removed_definition_withdraws_its_lint_evidence(m):
    """The loop-crossing evidence a definition filed goes with it."""
    @m.op(name="standing_loop_bump", effect="pureStructural")
    def standing_loop_bump(value: int) -> int:
        return value + 1

    def looped(values):
        total = 0
        for value in values:
            total += standing_loop_bump(value)
        return total

    defined = m.define(looped, name="standing-loop-sum")
    assert len(_loop_lint(m, "standing_loop_bump")) == 1
    assert m.remove(defined)
    assert _loop_lint(m, "standing_loop_bump") == []


def test_a_rolled_back_definition_leaves_no_lint_evidence(m):
    """A rolled-back define files no lint evidence, and a later one does."""
    @m.op(name="standing_rolled_bump", effect="pureStructural")
    def standing_rolled_bump(value: int) -> int:
        return value + 1

    def looped(values):
        total = 0
        for value in values:
            total += standing_rolled_bump(value)
        return total

    _in_transaction(m, lambda: m.define(looped, name="standing-rolled-sum"), keep=False)
    assert _loop_lint(m, "standing_rolled_bump") == []
    m.define(looped, name="standing-rolled-sum")
    assert len(_loop_lint(m, "standing_rolled_bump")) == 1


@pytest.mark.parametrize("door", ["transfer", "add"])
def test_a_definition_brought_back_is_reflected_again(m, metta, door):
    """A clause whose equation leaves and comes back is reflected again.

    Its reflection row, twin family and lint evidence retire when the space
    loses its head equation and return when a transfer or an add brings it
    back.
    """
    bump_name, name = f"standing_{door}_bump", f"standing-{door}-sum"

    @m.op(name=bump_name, effect="pureStructural")
    def bump(value: int) -> int:
        return value + 1

    def looped(values):
        total = 0
        for value in values:
            total += bump(value)
        return total

    m.define(looped, name=name)
    family = definitions._DEFINE_TWINS[m.name]._families[name]
    heads = [
        atom
        for atom in _stored(m, name)
        if atom.children[0] == Symbol("=") and atom.children[1].children[0] == Symbol(name)
    ]
    with metta._new_space() as elsewhere:
        assert m.transfer(*heads, to=elsewhere) == len(heads)
        assert not _reflected(m, name)
        assert _loop_lint(m, bump_name) == []
        if door == "transfer":
            assert elsewhere.transfer(*heads, to=m) == len(heads)
        else:
            m.add(*heads)
    assert _reflected(m, name)
    assert len(_loop_lint(m, bump_name)) == 1
    # The same clauses came back, so the retired family itself is reinstated,
    # where the references it kept still point.
    assert definitions._DEFINE_TWINS[m.name]._families[name] is family


def _looped(m, label: str) -> tuple[str, str]:
    """Define a function whose loop calls an operation, so it files lint
    evidence, and answer the definition's name and the operation's.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    bump_name, name = f"standing_{label}_bump", f"standing-{label}-sum"

    @m.op(name=bump_name, effect="pureStructural")
    def bump(value: int) -> int:
        return value + 1

    def looped(values):
        total = 0
        for value in values:
            total += bump(value)
        return total

    m.define(looped, name=name)
    return name, bump_name


def _head_equations(m, name: str) -> list:
    return [
        atom
        for atom in _stored(m, name)
        if atom.children[0] == Symbol("=") and atom.children[1].children[0] == Symbol(name)
    ]


def _program(verb: str, m, atoms) -> str:
    """A MeTTa program running verb over the atoms in m's space by its name."""
    return " ".join(f"!({verb} {m.name} {atom})" for atom in atoms)


@pytest.mark.parametrize("home", ["named", "parametric"])
def test_a_program_removing_and_restoring_an_equation_moves_the_definition(metta, home):
    """A program's remove-atom retires the definition's reflection row, lint
    evidence and twin family, and its add-atom brings all three back, with no
    Python door between: the space tells the definition through the engine's
    equation notice, in a parametric space as in a named one.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    m = metta._new_space() if home == "named" else space(S["standing-program-home"](1))
    try:
        name, bump_name = _looped(m, f"program-{home}")
        family = definitions._DEFINE_TWINS[m.name]._families[name]
        heads = _head_equations(m, name)
        m.run(_program("remove-atom", m, heads))
        assert not _reflected(m, name)
        assert _loop_lint(m, bump_name) == []
        assert name not in definitions._DEFINE_TWINS[m.name]._families
        m.run(_program("add-atom", m, heads))
        assert _reflected(m, name)
        assert len(_loop_lint(m, bump_name)) == 1
        assert definitions._DEFINE_TWINS[m.name]._families[name] is family
        assert m.eval(S[name](parse("(1 2)"))) == [5]
    finally:
        m.drop()


@pytest.mark.parametrize("scope", ["python", "metta"])
def test_a_rolled_back_program_removal_changes_nothing(m, scope):
    """A program's removal inside a transaction that rolls back, Python's or
    MeTTa's own (transaction ...), leaves the definition reflected, evidenced
    and in its family: a rolled-back write is never heard.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    name, bump_name = _looped(m, f"rolled-{scope}")
    family = definitions._DEFINE_TWINS[m.name]._families[name]
    (head,) = _head_equations(m, name)
    if scope == "python":
        _in_transaction(m, lambda: m.run(_program("remove-atom", m, [head])), keep=False)
    else:
        assert m.transaction(parse(f"(let $removed (remove-atom {m.name} {head}) (empty))")) == []
    assert _canonical(_head_equations(m, name)) == _canonical([head])
    assert _reflected(m, name)
    assert len(_loop_lint(m, bump_name)) == 1
    assert definitions._DEFINE_TWINS[m.name]._families[name] is family


def test_a_program_removal_is_heard_once_its_transaction_commits(m):
    """Inside the transaction the removal is not yet heard; after its commit it is."""
    name, bump_name = _looped(m, "committed")
    inside: list[bool] = []

    def body():
        m.run(_program("remove-atom", m, _head_equations(m, name)))
        inside.append(_reflected(m, name))

    m.transaction(body)
    assert inside == [True]
    assert not _reflected(m, name)
    assert _loop_lint(m, bump_name) == []


def test_a_speculative_program_removal_commits_nothing(m):
    """Inside speculative() a program's removal is discarded and never heard."""
    name, bump_name = _looped(m, "speculated")
    family = definitions._DEFINE_TWINS[m.name]._families[name]
    with m.speculative():
        m.run(_program("remove-atom", m, _head_equations(m, name)))
    assert _reflected(m, name)
    assert len(_loop_lint(m, bump_name)) == 1
    assert definitions._DEFINE_TWINS[m.name]._families[name] is family
    assert m.eval(S[name](parse("(1 2)"))) == [5]


def test_an_unwatched_equation_write_crosses_to_no_python(m):
    """A program's write to a head no definition publishes reaches no Python;
    one to a definition's head is recorded for that definition during the
    program's crossing, since its writer can hold an engine lock there, and
    reconciled at the next crossing made outside the engine.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    m.define(stable)
    unrelated = parse("(= (standing-unrelated $x) $x)")
    m.run(_program("add-atom", m, [unrelated]) + " " + _program("remove-atom", m, [unrelated]))
    assert list(definitions._NOTICED) == []
    m.run(_program("remove-atom", m, [equation(S.stable()).to(7)]))
    assert [name for _space, name in definitions._NOTICED] == ["stable"]
    assert not _reflected(m, "stable")
    assert list(definitions._NOTICED) == []


def test_a_notice_neither_locks_nor_crosses(m, monkeypatch):
    """The engine's notice returns while another thread holds the definitions
    lock, and makes no crossing: a single equation added outside any
    transaction is heard while its writer holds the typing policy lock, which a
    define holding the definitions lock can be waiting for, so a notice that
    waited on that lock, or crossed, could close the cycle.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    m.define(stable)
    locked, release = threading.Event(), threading.Event()
    crossed: list[str] = []
    runtime_type = type(m.runtime)
    thread_lock = runtime_type._thread_lock

    def counted(runtime):
        crossed.append(threading.current_thread().name)
        return thread_lock(runtime)

    def hold_the_lock():
        with definitions._DEFINE_LOCK:
            locked.set()
            release.wait()

    def notice():
        definitions.equation_changed(["p", str(m.name)], "stable")

    holder = threading.Thread(target=hold_the_lock, name="lock-holder", daemon=True)
    noticer = threading.Thread(target=notice, name="noticer", daemon=True)
    monkeypatch.setattr(runtime_type, "_thread_lock", counted)
    holder.start()
    locked.wait()
    try:
        noticer.start()
        # Far above an append and a dict store; a notice waiting on the lock
        # waits until release.set() below, whatever this bound.
        noticer.join(timeout=30)
        waited_on_the_lock = noticer.is_alive()
    finally:
        release.set()
        holder.join()
        noticer.join()
        monkeypatch.undo()
    assert not waited_on_the_lock, "the notice waited on the definitions lock"
    assert "noticer" not in crossed, "the notice crossed into the engine"
    assert _reflected(m, "stable")
    assert list(definitions._NOTICED) == []


def _stacked_first():
    def subject(x=0):  # noqa: ARG001 -- the default is the clause head pattern
        yield 100

    return subject


def _stacked_second():
    def subject(x=1):  # noqa: ARG001 -- the default is the clause head pattern
        yield 200
        yield 300

    return subject


def test_a_define_failing_part_way_leaves_an_equal_equation_standing(m):
    """A define whose equation batch is refused part way adds nothing and
    leaves an equal equation the space already held: every write of a define
    rides one transaction. Removing the batch by value after the failure took
    the held equation, which the define had never added.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    m.define(_stacked_first())
    held = parse("(= (subject 1) 300)")
    m.add(held)
    # The judge reads the offered equation as data: an Atom parameter, and
    # unify rather than case, which would run (= ...) as a goal.
    m.run(
        "(: standing-batch-guard (-> Atom %Undefined%)) "
        "(= (standing-batch-guard $atom) "
        "(unify $atom (= (subject 1) 300) (Refuse \"forced\") (Accept)))"
    )
    m.run(f"!(declare-pre-add! {m.name} standing-batch-guard)")
    try:
        before = _canonical(m.atoms())
        with pytest.raises(MettaError, match="forced"):
            m.define(_stacked_second())
        assert _canonical(m.atoms()) == before
        assert sorted(m.eval(S.subject(1)), key=str) == [300]
        assert m.eval(S.subject(0)) == [100]
    finally:
        m.run(f"!(undeclare-pre-add! {m.name})")


def test_a_define_failing_at_any_write_changes_nothing(m, monkeypatch):
    """Whichever of a re-define's writes fails, the space, the reflection rows,
    the record and the twin family are as they were and no subscriber heard
    any of its writes, and a define after it publishes normally and is heard.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    first = m.define(_one())
    key = (m.name, "subject")
    atoms = _canonical(m.atoms())
    reflection = _canonical(catalog.match(S["source-span"](S[m.name], S.subject, V.p, V.a, V.b, V.c, V.d)))
    record = definitions._DEFINITIONS[key]
    family = definitions._DEFINE_TWINS[m.name]._families["subject"]
    clauses = list(family._clauses)
    runtime_type = type(m.runtime)
    publish = runtime_type.do
    position = 0
    written: list[int] = []

    def failing_at(runtime, predicate, *inputs):
        if predicate == "metta_py_publish_definition":
            writes, watches = inputs
            written.append(len(writes))
            inputs = ([*writes[:position], ["refuse", m.name, []], *writes[position:]], watches)
        return publish(runtime, predicate, *inputs)

    monkeypatch.setattr(runtime_type, "do", failing_at)
    heard: list = []
    subscriptions = [m.subscribe(V.x, heard.append, on=kind) for kind in ("add", "remove")]
    try:
        while not written or position <= written[-1]:
            with pytest.raises(EngineError, match="metta_py_publish_definition"):
                m.define(_two())
            assert _canonical(m.atoms()) == atoms
            assert _canonical(catalog.match(S["source-span"](S[m.name], S.subject, V.p, V.a, V.b, V.c, V.d))) == reflection
            assert definitions._DEFINITIONS[key] is record
            assert definitions._DEFINE_TWINS[m.name]._families["subject"] is family
            assert family._clauses == clauses
            assert first.py(1) == 2
            assert heard == []
            position += 1
        monkeypatch.undo()
        assert position > 1
        m.define(_two())
        assert m.eval(S.subject(1)) == [3]
        assert heard
    finally:
        for subscription in subscriptions:
            subscription.cancel()


def test_a_watcher_failing_after_a_definition_commits_leaves_it_recorded(m):
    """A watcher raising on a define's writes, or on a removal's, does not undo
    them, since it runs once they committed, so the definition records what
    stands before the SubscriberError reaches the caller: the function answers
    and is reflected, defining it again is a re-define rather than a refusal
    of a head no record describes, and after a removal whose watcher raised
    nothing of it is left recorded or reflected and a define publishes it
    afresh.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def refuse(_event):
        msg = "the watcher says no"
        raise ValueError(msg)

    subscription = m.subscribe(V.x, refuse, on="add")
    try:
        with pytest.raises(SubscriberError):
            m.define(stable)
    finally:
        subscription.cancel()
    assert m.eval(S.stable()) == [7]
    assert (m.name, "stable") in definitions._DEFINITIONS
    assert _reflected(m, "stable")
    defined = m.define(stable)
    assert m.eval(S.stable()) == [7]
    subscription = m.subscribe(V.x, refuse, on="remove")
    try:
        with pytest.raises(SubscriberError):
            m.remove(defined)
    finally:
        subscription.cancel()
    assert (m.name, "stable") not in definitions._DEFINITIONS
    assert not _reflected(m, "stable")
    assert m.eval(S.stable()) != [7]
    m.define(stable)
    assert m.eval(S.stable()) == [7]
    assert _reflected(m, "stable")


_RULE_PROVIDER = (
    workspace() / "examples" / "ch20-extending-the-engine" / "20-03-prolog-underneath"
    / "_fixtures" / "rule_provider.pl"
)


def test_a_defined_function_keeps_its_static_type_shortcuts(m):
    """A define compiles its clauses inside its own transaction, and a clause
    compiled inside a transaction that opened before the typing-policy mutex
    keeps every dynamic type check, since its snapshot may predate a policy
    another owner published; the publication takes the mutex first, as the
    engine's own writers do, so a Number argument is decided by number/1
    before the general check, as it is for a function defined outside any
    transaction.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def countdown(n: int) -> int:
        return 0 if n == 0 else countdown(n - 1)

    m.define(countdown)
    assert m.eval(S.countdown(5)) == [0]
    assert "number(" in m.fn.countdown.compiled


def test_a_definition_publishes_into_and_leaves_a_provider_that_declares_nothing(m):
    """A provider that holds rules and says nothing about how its writes meet
    a transaction takes a define and gives it back, as it takes the engine's
    own rule registration: a define's one transaction is the engine's internal
    form, which never asks a provider to roll back, where the user's
    (transaction ...) form refused the write as one it could not undo.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    m.register_prolog(path=_RULE_PROVIDER)
    demo = space(S["rule_demo"])
    try:

        def fdouble(x: int) -> int:
            return 2 * x

        defined = demo.define(fdouble)
        assert demo.eval(S.fdouble(21)) == [42]
        assert demo.remove(defined)
        assert not demo.match(S["="](S.fdouble(V.x), V.body))
    finally:
        demo.remove(V.anything)
        m.unregister_prolog("rule_demo")


class _RuleList(SpaceProvider):
    """Rules kept in a Python list: storage no engine transaction reaches.

    A removal takes one occurrence up to renaming, since a term with
    variables crosses under new names each time.
    """

    def __init__(self) -> None:
        self.stored: list[Atom] = []

    def atoms(self):
        return iter(list(self.stored))

    def match(self, _pattern):
        return iter(list(self.stored))

    def add(self, atom) -> None:
        self.stored.append(atom)

    def remove(self, atom) -> bool:
        for index, held in enumerate(self.stored):
            if Atom.alpha_eq(held, atom):
                del self.stored[index]
                return True
        return False

    def can_run(self, capability, /, **request):
        return capability == "rules" or super().can_run(capability, **request)


class _TransactionalRuleList(_RuleList):
    """The same list taking part in the engine's transactions."""

    def __init__(self) -> None:
        super().__init__()
        self.log: list[str] = []
        self.saved: list[Atom] = []

    def begin(self) -> None:
        self.log.append("begin")
        self.saved = list(self.stored)

    def commit(self) -> None:
        self.log.append("commit")

    def rollback(self) -> None:
        self.log.append("rollback")
        self.stored[:] = self.saved


def _failing_after_every_write(monkeypatch, runtime) -> None:
    """Fail the next define's publication after each of its writes has run."""
    runtime_type = type(runtime)
    publish = runtime_type.do

    def failing(rt, predicate, *inputs):
        if predicate == "metta_py_publish_definition":
            writes, watches = inputs
            inputs = ([*writes, ["refuse", "&self", []]], watches)
        return publish(rt, predicate, *inputs)

    monkeypatch.setattr(runtime_type, "do", failing)


def _unmatched(left, right) -> list:
    """The atoms of ``left`` no atom of ``right`` answers one for one, up to renaming."""
    rest = list(right)
    unmatched = []
    for atom in left:
        for index, other in enumerate(rest):
            if Atom.alpha_eq(atom, other):
                del rest[index]
                break
        else:
            unmatched.append(atom)
    return unmatched


@pytest.mark.usefixtures("metta")  # the session engine, whose value these do not read
def test_a_define_failing_in_a_provider_outside_the_engine_names_what_it_kept(monkeypatch):
    """A provider whose storage no engine transaction reaches keeps what a
    failed re-define gave it and loses what it took, so the define raises
    PartialWriteError naming exactly those atoms, counted against what the
    provider held before, with the failure as its cause; the caller's repair
    from the error leaves the provider as it was.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    provider = _RuleList()
    with space(backing=provider) as home:

        def subject(x: int) -> int:
            return x + 1

        home.define(subject)
        before = list(provider.stored)

        def subject(x: int) -> int:
            return x + 2

        _failing_after_every_write(monkeypatch, home.runtime)
        with pytest.raises(PartialWriteError) as raised:
            home.define(subject)
        monkeypatch.undo()
        error = raised.value
        gained, gone = _unmatched(provider.stored, before), _unmatched(before, provider.stored)
        assert gained and gone
        assert not _unmatched(error.kept, gained) and not _unmatched(gained, error.kept)
        assert not _unmatched(error.lost, gone) and not _unmatched(gone, error.lost)
        assert error.space == str(home.name)
        assert error.capability == "transactional"
        assert "not transactional" in str(error)
        assert isinstance(error.__cause__, EngineError)
        # One atom at a time: a batch removal opens a transaction of the
        # user's kind, which a provider that declares nothing refuses.
        for atom in error.kept:
            home.remove(atom)
        for atom in error.lost:
            home.add(atom)
        assert not _unmatched(provider.stored, before) and not _unmatched(before, provider.stored)


def test_a_define_failing_in_the_foreign_rules_provider_leaves_it_as_it_was(m, monkeypatch):
    """The foreign-rules example's provider stores its atoms as clauses of
    its own, so the define's transaction reaches them: a re-define failing
    after every write leaves the provider as it was and raises the failure
    itself, with nothing kept to name.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    m.register_prolog(path=_RULE_PROVIDER)
    demo = space(S["rule_demo"])
    defined = None
    try:

        def fdouble(x: int) -> int:
            return 2 * x

        defined = demo.define(fdouble)
        before = list(demo.atoms())

        def fdouble(x: int) -> int:
            return 3 * x

        _failing_after_every_write(monkeypatch, demo.runtime)
        with pytest.raises(EngineError) as raised:
            demo.define(fdouble)
        monkeypatch.undo()
        assert not isinstance(raised.value, PartialWriteError)
        after = list(demo.atoms())
        assert not _unmatched(after, before) and not _unmatched(before, after)
        assert demo.eval(S.fdouble(21)) == [42]
    finally:
        if defined is not None:
            demo.remove(defined)
        demo.remove(V.anything)
        m.unregister_prolog("rule_demo")


@pytest.mark.usefixtures("metta")  # the session engine, whose value these do not read
def test_a_removal_failing_in_a_provider_outside_the_engine_names_what_it_lost(monkeypatch):
    """Removing a Defined publishes through the same crossing as define, so a
    removal failing after every write in a provider outside the engine names
    the atoms the provider no longer holds, and the definition stays recorded.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    provider = _RuleList()
    with space(backing=provider) as home:

        def subject(x: int) -> int:
            return x + 1

        defined = home.define(subject)
        before = list(provider.stored)
        _failing_after_every_write(monkeypatch, home.runtime)
        with pytest.raises(PartialWriteError) as raised:
            home.remove(defined)
        monkeypatch.undo()
        error = raised.value
        assert error.kept == ()
        assert not _unmatched(error.lost, before) and not _unmatched(before, error.lost)
        assert provider.stored == []
        assert (home.name, "subject") in definitions._DEFINITIONS


class _UnreadableAfterAdd(_RuleList):
    """A rule list whose reads fail once an atom has arrived."""

    def __init__(self) -> None:
        super().__init__()
        self.readable = True

    def match(self, pattern):
        if not self.readable:
            msg = "the backing store went away"
            raise ConnectionError(msg)
        return super().match(pattern)

    def add(self, atom) -> None:
        super().add(atom)
        self.readable = False


@pytest.mark.usefixtures("metta")  # the session engine, whose value these do not read
def test_a_provider_unreadable_after_a_failed_define_is_named_not_hidden(monkeypatch):
    """What a provider kept of a failed define is read back from it, so a
    provider that cannot be read then fails loudly, naming itself, the read's
    error and the define's failure, rather than leaving what it kept unsaid.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    provider = _UnreadableAfterAdd()
    with space(backing=provider) as home:

        def subject(x: int) -> int:
            return x + 1

        _failing_after_every_write(monkeypatch, home.runtime)
        with pytest.raises(EngineError, match="could not be read back") as raised:
            home.define(subject)
        monkeypatch.undo()
        assert str(home.name) in str(raised.value)


@pytest.mark.usefixtures("metta")  # the session engine, whose value these do not read
def test_a_define_into_a_transactional_provider_rolls_it_back(monkeypatch):
    """A provider declaring transactional writes is enlisted in the define's
    transaction, which only the engine's coordinator does, so a re-define
    failing after every write rolls the provider back with the engine and
    raises the failure itself; a define that stands commits it.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    provider = _TransactionalRuleList()
    with space(backing=provider) as home:
        home.atomicity("transactional")

        def subject(x: int) -> int:
            return x + 1

        home.define(subject)
        assert provider.log[-2:] == ["begin", "commit"]
        before = list(provider.stored)

        def subject(x: int) -> int:
            return x + 2

        _failing_after_every_write(monkeypatch, home.runtime)
        with pytest.raises(EngineError) as raised:
            home.define(subject)
        monkeypatch.undo()
        assert not isinstance(raised.value, PartialWriteError)
        assert provider.log[-2:] == ["begin", "rollback"]
        assert not _unmatched(provider.stored, before) and not _unmatched(before, provider.stored)
        assert home.eval(S.subject(1)) == [2]


# The property: whatever sequence of writes ran, each plainly, inside a
# committed or rolled-back transaction, or inside speculative(), what the
# definition's caches answer is what the space holds. A step is one write
# crossed with one scope, drawn independently, and a removal is one Python
# removal door crossed with its target: one of the name's stored atoms, or
# the Defined itself where the door reads one. A give-back is one Python add
# door returning an atom a transfer parked in the sink.
_REMOVERS = {
    "remove": lambda space, _sink, target: space.remove(target),
    "isub": lambda space, _sink, target: space.__isub__(target),
    "transfer": lambda space, sink, target: space.transfer(target, to=sink),
}
_RESTORERS = {
    "restore": lambda space, sink, parked: sink.transfer(parked, to=space),
    "add_copy": lambda space, _sink, parked: space.add(parked),
}
_OPERATIONS = st.one_of(
    st.tuples(st.just("define"), st.sampled_from(sorted(VARIANTS))),
    st.tuples(st.sampled_from(sorted(_REMOVERS)), st.integers(min_value=0, max_value=5)),
    st.tuples(st.sampled_from(("remove", "isub")), st.just(None)),
    st.tuples(st.just("drain"), st.just(None)),
    st.tuples(st.just("clear"), st.just(None)),
)
_GIVE_BACKS = st.tuples(st.sampled_from(sorted(_RESTORERS)), st.integers(min_value=0, max_value=5))
_SCOPES = st.sampled_from(("plain", "commit", "rollback", "speculative"))


class _DefinitionStanding(stateful.RuleBasedStateMachine):
    """One space, one name, the definition's own writers and every scope.

    Only define and the removal doors write the name's atoms here, so besides
    agreeing with the space the caches describe exactly what it holds.
    """

    exclusive = True

    def __init__(self, metta):
        super().__init__()
        self.space = metta._new_space()
        self.sink = metta._new_space()
        self.defined = None

    def teardown(self):
        self.space.drop()
        self.sink.drop()

    def _operate(self, operation, argument):
        """Run one write; answers whether it was a define that was not refused."""
        space = self.space
        if operation == "define":
            try:
                self.defined = space.define(VARIANTS[argument]())
            except CompileError:
                return False
            return True
        if operation == "clear":
            space.clear()
        elif operation == "drain":
            with contextlib.suppress(KeyError):
                del space[S["="](S.subject(V.x), V.body)]
        elif operation in _RESTORERS:
            parked = sorted(_stored(self.sink, "subject"), key=str)
            if parked:
                _RESTORERS[operation](space, self.sink, parked[argument % len(parked)])
        elif argument is None:
            if self.defined is not None:
                _REMOVERS[operation](space, self.sink, self.defined)
        else:
            stored = sorted(_stored(space, "subject"), key=str)
            if stored:
                _REMOVERS[operation](space, self.sink, stored[argument % len(stored)])
        return False

    def _step(self, step, scope):
        operation, argument = step
        stood: list[bool] = []
        if scope == "plain":
            stood.append(self._operate(operation, argument))
        elif scope == "speculative":
            with self.space.speculative():
                self._operate(operation, argument)
        else:
            _in_transaction(
                self.space,
                lambda: stood.append(self._operate(operation, argument)),
                keep=scope == "commit",
            )
        if scope in ("plain", "commit") and any(stood):
            self._converged()

    @stateful.rule(step=_OPERATIONS, scope=_SCOPES)
    def write(self, step, scope):
        self._step(step, scope)

    def _converged(self):
        """A define that stood leaves the space holding its definition, once when exclusive."""
        record = definitions._DEFINITIONS.get((self.space.name, "subject"))
        if record is None:
            return
        standing = definitions._standing(self.space, record)
        expected = [
            *definitions._physical_atoms(standing.live),
            *standing.declared,
            *((record.documented,) if standing.documented else ()),
        ]
        missing, extra = definitions._alpha_multiset_delta(expected, _stored(self.space, "subject"))
        assert missing == []
        if self.exclusive:
            assert extra == []

    @stateful.invariant()
    def caches_agree_with_the_space(self):
        space = self.space
        # A write's notice is reconciled at the next crossing made outside the
        # engine, and every public read crosses; this one reads the registry
        # directly, so it crosses first.
        stored = space.atoms()
        record = definitions._DEFINITIONS.get((space.name, "subject"), definitions._UNRECORDED)
        standing = definitions._standing(space, record)
        # The held atoms, recomputed from the space's own contents: every
        # recorded atom the space holds a variant of, one stored copy each.
        held = Counter(_canonical(definitions._physical_atoms(record.clauses)))
        assert Counter(_canonical(standing.held)) == held & Counter(_canonical(stored))
        live = list(standing.live)
        assert _reflected(space, "subject") is bool(live)
        assert record.reflected == definitions._definition_facts(space, "subject", live)
        for fact in record.reflected:
            assert definitions._DEFINE_FACT_REFS.get(str(fact), 0) >= 1
            assert fact in catalog
        namespace = definitions._DEFINE_TWINS.get(space.name)
        family = None if namespace is None else namespace._families.get("subject")
        twins = [] if family is None else list(family._clauses)
        assert len(twins) == len(live)
        assert all(twin is clause["twin"] for twin, clause in zip(twins, live, strict=True))
        assert definitions._is_nondeterministic(space, "subject") is any(
            clause["generator"] for clause in live
        )
        rosters = {clause["params"] for clause in live if clause["arity"] == 1}
        expected = next(iter(rosters)) if len(rosters) == 1 else None
        assert definitions.call_parameter_names(space, "subject", 1) == expected
        # Read from the space directly rather than through the record: it
        # holds a head equation while some clause is live, and when only the
        # definition writes the name, a head equation it holds is always one a
        # live clause describes and it holds none otherwise.
        heads = [
            atom
            for atom in _stored(space, "subject")
            if atom.children[0] == Symbol("=") and atom.children[1].children[0] == Symbol("subject")
        ]
        described = [atom for clause in live for atom in clause["equations"]]
        assert bool(heads) or not live
        if self.exclusive:
            assert bool(heads) is bool(live)
            assert definitions._alpha_multiset_delta(described, heads)[1] == []


class _DefinitionStandingGivenBack(_DefinitionStanding):
    """The same machine with removed atoms coming back through add and transfer.

    Another writer's equal copy, or a former equation back after its
    definition went, is the space's to hold, so what is asked is that the
    caches follow the space, a clause brought back included.
    """

    exclusive = False

    # A give-back returns only what a transfer parked, which a uniform choice
    # among the writes almost never lines up: 1,892 give-backs of a 300-example
    # run all found the sink empty. So parking has a rule of its own while the
    # space holds the name's atoms, and giving back runs while the sink holds
    # one of them.
    @stateful.precondition(lambda self: bool(_stored(self.space, "subject")))
    @stateful.rule(argument=st.integers(min_value=0, max_value=5), scope=_SCOPES)
    def park(self, argument, scope):
        self._step(("transfer", argument), scope)

    @stateful.precondition(lambda self: bool(_stored(self.sink, "subject")))
    @stateful.rule(step=_GIVE_BACKS, scope=_SCOPES)
    def give_back(self, step, scope):
        self._step(step, scope)


def test_definition_caches_agree_with_the_space(metta):
    """Hypothesis walks the operation-by-scope writes; every state agrees."""
    stateful.run_state_machine_as_test(
        lambda: _DefinitionStanding(metta),
        settings=hypothesis.settings(max_examples=30, stateful_step_count=10, deadline=None),
    )


def test_definition_caches_follow_atoms_given_back(metta):
    """With atoms returned by add and transfer too, every state agrees."""
    stateful.run_state_machine_as_test(
        lambda: _DefinitionStandingGivenBack(metta),
        settings=hypothesis.settings(max_examples=30, stateful_step_count=10, deadline=None),
    )
