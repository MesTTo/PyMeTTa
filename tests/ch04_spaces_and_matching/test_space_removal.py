"""Purpose: what `remove-atom` does, on the two questions it answers
differently from the Python doors beside it: how many occurrences one removal
takes, and what a removal that finds nothing answers.
Guarantees:
  - a removal answers True whether or not the space held the atom, which is
    upstream's answer [tested test_removing_an_absent_atom_answers_true]
  - one removal drains EVERY unifying occurrence, on a native space, a Python
    provider and a journal-backed one alike [tested
    test_remove_atom_drains_every_occurrence, test_a_native_space_drains,
    test_a_python_provider_drains, test_a_persistent_space_drains_like_a_native_one]
  - the Python doors keep the finer grain the MeTTa door gave up:
    `space.remove(atom)` still subtracts ONE copy and reports whether it found
    one [tested test_the_python_remove_door_subtracts_one_copy]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import TRUE, Expression, S, V
from metta.foreign import SpaceProvider


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


# TRUE EITHER WAY, which is upstream's answer and now this engine's
# [measured 2026-08-30 against PeTTa@ae66fa8: `!(remove-atom &self (never
# there))` answers `true` there]. It answered
# `(Error (remove-atom <space> <atom>) "remove-atom: atom is not in the
# space")` here until then, on LeaTTa's Hacks-Register row 15, which answered
# Hyperon's own `stdlib/space.rs:219` TODO -- "Is it necessary to distinguish
# whether the atom was removed or not?" -- with "Implement. Keep the
# distinction". PeTTa is the arbiter now, and a different ANSWER to the same
# call is the one thing the superset rule does not allow. The distinction is
# not lost: `space.remove(atom)` below still reports it.
def test_removing_an_absent_atom_answers_true(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self (present 1))")
    present, absent = m.run(
        "!(remove-atom &self (present 1))\n!(remove-atom &self (never there))"
    )
    assert present == [TRUE]
    assert absent == [TRUE]


# Twice over is the same answer seen over time: the first removal empties the
# space and the second one has nothing to take and says so no differently.
def test_removing_the_same_atom_twice_answers_true_both_times(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self (once only))")
    first, second = m.run(
        "!(remove-atom &self (once only))\n!(remove-atom &self (once only))"
    )
    assert first == [TRUE]
    assert second == [TRUE]


# One answer, so a collapse holds exactly one: a removal is not a generator
# and absence does not make it one.
def test_a_removal_answers_once_and_a_collapse_holds_it(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (collapsed,) = m.run("!(collapse (remove-atom &self (nothing here)))")
    assert collapsed == [Expression(TRUE)]


# A scalar atom lives in its own storage predicate, so it is a separate path
# to the same answer.
def test_a_scalar_removal_answers_true_too(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self lonely)")
    present, absent = m.run("!(remove-atom &self lonely)\n!(remove-atom &self nobody)")
    assert present == [TRUE]
    assert absent == [TRUE]


# An equation removes through its own path, which un-compiles the clause as
# well as dropping the atom, and it owes the same answer.
def test_an_absent_equation_removal_answers_true(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (kept-here $x) $x)")
    present, absent = m.run(
        "!(remove-atom &self (= (kept-here $x) $x))\n"
        "!(remove-atom &self (= (never-defined $x) $x))"
    )
    assert present == [TRUE]
    assert absent == [TRUE]


# WHERE THE DISTINCTION WENT. The MeTTa door gave up reporting absence to
# match upstream; the Python door keeps it, because Python's own idiom for a
# removal that finds nothing is to say so.
def test_the_python_remove_door_still_reports_absence(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.kept(1))
    assert m.remove(S.kept(1)) is True
    assert m.remove(S.gone(1)) is False


# ONE REMOVAL DRAINS THE ATOM. Upstream's is `retractall/1` under a comment
# reading "Remove all same atoms", so three adds of `(dup 1)` and one removal
# leave none [source: PeTTa@ae66fa8 src/spaces.pl:5-7 and :43-44; measured
# 2026-08-30, where this engine left two]. It took ONE occurrence here until
# then, as multiset subtraction, on LeaTTa's Properties.lean. Multiset
# subtraction did not go anywhere: it is `space.remove(atom)` below, which is
# also the door the engine's own machinery uses.
def test_remove_atom_drains_every_occurrence(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self (dup 1))\n!(add-atom &self (dup 1))\n!(add-atom &self (dup 1))")
    (before,) = m.run("!(collapse (match &self (dup $x) $x))")
    assert len(before[0]) == 3
    m.run("!(remove-atom &self (dup 1))")
    (after,) = m.run("!(collapse (match &self (dup $x) $x))")
    assert after == [Expression()]


# Draining is idempotent, which is the whole content of answering True either
# way: the first removal empties the atom and every later one is a no-op that
# answers the same thing.
def test_repeated_removal_is_idempotent(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self (dup 2))\n!(add-atom &self (dup 2))")
    first, second, third = m.run(
        "!(remove-atom &self (dup 2))\n"
        "!(remove-atom &self (dup 2))\n"
        "!(remove-atom &self (dup 2))"
    )
    assert first == second == third == [TRUE]
    (left,) = m.run("!(collapse (match &self (dup $x) $x))")
    assert left == [Expression()]


# Scalars live in their own storage predicate, so they are a separate path to
# the same law.
def test_a_scalar_removal_drains_its_copies(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self lone)\n!(add-atom &self lone)\n!(remove-atom &self lone)")
    (left,) = m.run("!(collapse (get-atoms &self))")
    assert left == [Expression()]


# An equation removes through its own path, which un-compiles the clause as
# well as dropping the atom, and it obeys the same law: two copies of a rule
# answer twice, and removing the equation takes both, leaving the call
# unreduced. Upstream leaves `((twice))` for exactly this program
# [measured 2026-08-30 against PeTTa@ae66fa8].
def test_removing_a_duplicated_equation_undefines_the_function(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (twice-defined) 1)\n(= (twice-defined) 1)")
    (both,) = m.run("!(collapse (twice-defined))")
    assert both == [Expression(1, 1)]
    m.run("!(remove-atom &self (= (twice-defined) 1))")
    (none,) = m.run("!(collapse (twice-defined))")
    assert none == [Expression(S["twice-defined"]())]


# A pattern with a variable drains every unifying occurrence, and the
# pattern's variables come back as they went in, which is what lets the same
# call be written twice.
def test_a_pattern_removal_drains_every_unifying_occurrence(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(add-atom &self (pair 1))\n!(add-atom &self (pair 2))")
    m.run("!(remove-atom &self (pair $x))")
    (left,) = m.run("!(collapse (match &self (pair $y) $y))")
    assert left == [Expression()]


# The Python door says the same thing about the same operation: remove() is
# multiset subtraction, and del is the bulk spelling that drains the pattern.
def test_the_python_remove_door_subtracts_one_copy(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.dup(3), S.dup(3), S.dup(3))
    assert m.remove(S.dup(3)) is True
    assert len(m) == 2


def test_delitem_drains_every_unifying_occurrence(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.edge(S.a, S.b), S.edge(S.a, S.b), S.edge(S.b, S.c))
    del m[S.edge(S.a, V.y)]
    assert m.atoms() == [S.edge(S.b, S.c)]
    with pytest.raises(KeyError):
        del m[S.edge(S.zz, V.y)]
    assert m.remove(S.edge(S.zz, V.y)) is False


# ----------------------------------------------------- one law, every space
#
# The law is the same whoever holds the atoms, and it is the MeTTa door's
# law: one removal drains the atom. The seam below it still declares
# `seam:foreign_remove/3` as "remove one" (EXTENDING.md) and still means it;
# what changed is that the door above calls it once per stored copy instead
# of once. These run the same three-add-one-remove-count-none script against
# each kind of space there is, so a provider cannot quietly implement a
# different law.


def drains(space_name, m):
    """Three copies in, one removal, none left, asked of whichever space
    `space_name` refers to.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for _ in range(3):
        m.run(f"!(add-atom {space_name} (law 1))")
    before = m.run(f"!(collapse (match {space_name} (law $x) $x))")[0][0]
    m.run(f"!(remove-atom {space_name} (law 1))")
    after = m.run(f"!(collapse (match {space_name} (law $x) $x))")[0][0]
    return len(before), len(after)


def test_a_native_space_drains(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert drains("&self", m) == (3, 0)


def test_a_python_provider_drains(metta):
    """A registered Python provider, the seam's Python door."""

    class ListSpace(SpaceProvider):
        def __init__(self):
            self.stored = []

        def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return iter(self.stored)

        def atoms(self):
            return iter(self.stored)

        def add(self, atom):
            self.stored.append(atom)

        def remove(self, atom):
            for index, held in enumerate(self.stored):
                if held == atom:
                    del self.stored[index]
                    return True
            return False

    provider = ListSpace()
    name = f"&lawlist{id(provider) % 100000}"
    metta._register_space(provider, name)
    try:
        assert drains(name, metta) == (3, 0)
        assert provider.stored == []
    finally:
        metta._unregister_space(name)


def test_a_persistent_space_drains_like_a_native_one(metta, tmp_path):
    """The journal-backed provider, which records one journal entry per copy
    removed rather than a single sweep, so a replay reconstructs the same
    counts.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from metta._persistent import PersistentFactSpace

    provider = PersistentFactSpace(tmp_path / "law.db", {"law": 1})
    name = f"&lawstore{id(provider) % 100000}"
    metta._register_space(provider, name)
    try:
        assert drains(name, metta) == (3, 0)
        # The provider's OWN door is still one-at-a-time, which is what the
        # door above it calls once per copy.
        for _ in range(2):
            metta.run(f"!(add-atom {name} (law 1))")
        assert provider.remove(S.law(1)) is True
        assert provider.remove(S.law(1)) is True
        assert provider.remove(S.law(1)) is False
    finally:
        metta._unregister_space(name)
        provider.close()
