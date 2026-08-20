"""Purpose: what `remove-atom` does, on the two questions the engine used to
answer wrongly: how many occurrences one removal takes, and what a removal
that finds nothing answers.
Guarantees:
  - removing an atom a space does not hold answers an error naming the
    operation, the space and the atom, while removing one it holds stays unit
    [tested test_removing_an_absent_atom_is_an_error_not_a_silent_unit]
  - one removal takes one occurrence, on a native space, a Python provider
    and a journal-backed one alike [tested
    test_remove_atom_removes_one_occurrence_not_all,
    test_a_native_space_subtracts_one, test_a_python_provider_subtracts_one,
    test_a_persistent_space_subtracts_one_fact_like_a_native_one]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from petta import S, V, expr
from petta.foreign import SpaceProvider


@pytest.fixture()
def m(metta):
    return metta.new_space()


def error_text(answer):
    """The `(Error subject reason)` atom as source text."""
    return str(answer)


# The arbiter rules absence an error and success unit. LeaTTa's Hacks-Register
# row 15 answers Hyperon's own `stdlib/space.rs:219` TODO, "Is it necessary to
# distinguish whether the atom was removed or not?", with "Implement. Keep the
# distinction. The documentation independently complains about silent absence",
# and records it SATISFIED: `Metta.Minimal.removeAtomStep` answers
# `(Error (remove-atom <space> <atom>) "remove-atom: atom is not in the
# space")` for absence and unit only after membership succeeds. Hyperon as
# shipped answers unit for both, which is what this engine used to do.
def test_removing_an_absent_atom_is_an_error_not_a_silent_unit(m):
    m.run("!(add-atom &self (present 1))")
    present, absent = m.run(
        "!(remove-atom &self (present 1))\n!(remove-atom &self (never there))"
    )
    assert present == [expr()]
    assert "remove-atom: atom is not in the space" in error_text(absent[0])
    assert error_text(absent[0]).startswith("(Error (remove-atom ")
    assert "(never there)" in error_text(absent[0])


# Removing the same atom twice is the same distinction seen over time: the
# first removal empties the space and the second one has nothing to take.
def test_removing_the_same_atom_twice_errors_on_the_second(m):
    m.run("!(add-atom &self (once only))")
    first, second = m.run(
        "!(remove-atom &self (once only))\n!(remove-atom &self (once only))"
    )
    assert first == [expr()]
    assert "remove-atom: atom is not in the space" in error_text(second[0])


# The absence error is a value, so a program can branch on it rather than
# losing the directive to a throw.
def test_the_absence_error_is_data_a_collapse_can_hold(m):
    (collapsed,) = m.run("!(collapse (remove-atom &self (nothing here)))")
    assert len(collapsed[0]) == 1
    assert "remove-atom: atom is not in the space" in error_text(collapsed[0][0])


# A scalar atom lives in its own storage predicate, so it is a separate path
# to the same answer.
def test_a_scalar_removal_reports_absence_too(m):
    m.run("!(add-atom &self lonely)")
    present, absent = m.run("!(remove-atom &self lonely)\n!(remove-atom &self nobody)")
    assert present == [expr()]
    assert "remove-atom: atom is not in the space" in error_text(absent[0])


# An equation removes through its own path, which un-compiles the clause as
# well as dropping the atom, and it owes the same answer.
def test_an_absent_equation_removal_reports_absence(m):
    m.run("(= (kept-here $x) $x)")
    present, absent = m.run(
        "!(remove-atom &self (= (kept-here $x) $x))\n"
        "!(remove-atom &self (= (never-defined $x) $x))"
    )
    assert present == [expr()]
    assert "remove-atom: atom is not in the space" in error_text(absent[0])


# The Python surface removes through the same door, so it inherits the ruling
# rather than carrying a second opinion about absence.
def test_the_python_remove_surface_reports_absence(m):
    m.run("!(add-atom &self (kept 1))")
    with pytest.raises(Exception) as failure:
        m.one("(remove-atom &self (gone 1))")
    assert "not in the space" in str(failure.value)


# A space is a multiset on ADD and used to be a set on REMOVE: three adds of
# `(dup 1)` gave count 3 and ONE removal gave count 0. The premise the engine
# wrote down for that, "a MeTTa space is a multiset unless something forbids
# it, so removal takes EVERY occurrence", argues for the opposite conclusion,
# since multiset subtraction takes one occurrence. The arbiter settles it
# against the old reading: MettaHyperonFullTests/Properties.lean requires
# `remove-atom` to behave as MULTISET SUBTRACTION on the reader-visible view
# of `&self`, and LeaTTa's own u-space model removes the first exact
# occurrence through `subtraction-atom`.
def test_remove_atom_removes_one_occurrence_not_all(m):
    m.run("!(add-atom &self (dup 1))\n!(add-atom &self (dup 1))\n!(add-atom &self (dup 1))")
    (before,) = m.run("!(collapse (match &self (dup $x) $x))")
    assert len(before[0]) == 3
    m.run("!(remove-atom &self (dup 1))")
    (after,) = m.run("!(collapse (match &self (dup $x) $x))")
    assert len(after[0]) == 2


# Subtraction is repeatable, and the count walks down one at a time until the
# space no longer holds the atom, at which point P1.17's absence error takes
# over. The two rulings compose rather than colliding.
def test_repeated_subtraction_walks_the_count_down_to_absence(m):
    m.run("!(add-atom &self (dup 2))\n!(add-atom &self (dup 2))")
    first, second, third = m.run(
        "!(remove-atom &self (dup 2))\n"
        "!(remove-atom &self (dup 2))\n"
        "!(remove-atom &self (dup 2))"
    )
    assert first == [expr()]
    assert second == [expr()]
    assert "remove-atom: atom is not in the space" in error_text(third[0])


# Scalars live in their own storage predicate, so they are a separate path to
# the same law.
def test_a_scalar_removal_takes_one_copy(m):
    m.run("!(add-atom &self lone)\n!(add-atom &self lone)\n!(remove-atom &self lone)")
    (left,) = m.run("!(collapse (get-atoms &self))")
    assert len(left[0]) == 1


# An equation removes through its own path, which un-compiles the clause as
# well as dropping the atom, and it obeys the same law: two copies of a rule
# answer twice, and taking one away leaves the function answering once.
def test_removing_one_of_two_identical_equations_leaves_the_function_defined(m):
    m.run("(= (twice-defined) 1)\n(= (twice-defined) 1)")
    (both,) = m.run("!(collapse (twice-defined))")
    assert both == [expr(1, 1)]
    m.run("!(remove-atom &self (= (twice-defined) 1))")
    # The value, not the unreduced call: taking one equation away used to take
    # both, after which the collapse held `((twice-defined))`, which is also
    # one element and would pass a length check for the wrong reason.
    (one,) = m.run("!(collapse (twice-defined))")
    assert one == [expr(1)]


# A pattern with a variable removes ONE unifying occurrence, not every one.
# Which occurrence is not reported: the operation answers unit, and the
# pattern's variables come back as they went in.
def test_a_pattern_removal_takes_one_unifying_occurrence(m):
    m.run("!(add-atom &self (pair 1))\n!(add-atom &self (pair 2))")
    m.run("!(remove-atom &self (pair $x))")
    (left,) = m.run("!(collapse (match &self (pair $y) $y))")
    assert len(left[0]) == 1


# The Python door says the same thing about the same operation: remove() is
# multiset subtraction, and del is the bulk spelling that drains the pattern.
def test_the_python_remove_door_subtracts_one_copy(m):
    m.add(S.dup(3), S.dup(3), S.dup(3))
    assert m.remove(S.dup(3)) is True
    assert m.count() == 2


def test_delitem_drains_every_unifying_occurrence(m):
    m.add(S.edge(S.a, S.b), S.edge(S.a, S.b), S.edge(S.b, S.c))
    del m[S.edge(S.a, V.y)]
    assert m.atoms() == [S.edge(S.b, S.c)]
    with pytest.raises(KeyError):
        del m[S.edge(S.zz, V.y)]
    assert m.remove(S.edge(S.zz, V.y)) is False


# ----------------------------------------------------- one law, every space
#
# The law is the same whoever holds the atoms. It was not: the seam has
# always declared `metta_foreign_remove/3` as "remove one" (EXTENDING.md),
# while the native store took every occurrence, so `(remove-atom $s $a)`
# meant different things depending on how `$s` was implemented and nothing
# in the text said which. These run the same three-add-one-remove-count-two
# script against each kind of space there is.


def subtracts_one(space_name, m):
    """Three copies in, one removal, two left. The multiset law, asked of
    whichever space `space_name` refers to.
    """
    for _ in range(3):
        m.run(f"!(add-atom {space_name} (law 1))")
    before = m.run(f"!(collapse (match {space_name} (law $x) $x))")[0][0]
    m.run(f"!(remove-atom {space_name} (law 1))")
    after = m.run(f"!(collapse (match {space_name} (law $x) $x))")[0][0]
    return len(before), len(after)


def test_a_native_space_subtracts_one(m):
    assert subtracts_one("&self", m) == (3, 2)


def test_a_python_provider_subtracts_one(metta):
    """A registered Python provider, the seam's Python door."""

    class ListSpace(SpaceProvider):
        def __init__(self):
            self.stored = []

        def match(self, pattern):
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
    metta.register_space(provider, name)
    try:
        assert subtracts_one(name, metta) == (3, 2)
        assert len(provider.stored) == 2
    finally:
        metta.unregister_space(name)


def test_a_persistent_space_subtracts_one_fact_like_a_native_one(metta, tmp_path):
    """The journal-backed provider, which used to retractall and now
    retracts, so its journal records one removal rather than a sweep.
    """
    from petta.persistent import PersistentFactSpace

    provider = PersistentFactSpace(tmp_path / "law.db", {"law": 1})
    name = f"&lawstore{id(provider) % 100000}"
    metta.register_space(provider, name)
    try:
        assert subtracts_one(name, metta) == (3, 2)
        assert provider.remove(S.law(1)) is True
        assert provider.remove(S.law(1)) is True
        assert provider.remove(S.law(1)) is False
    finally:
        metta.unregister_space(name)
        provider.close()
