"""Purpose: what `remove-atom` does, on the two questions the engine used to
answer wrongly: how many occurrences one removal takes, and what a removal
that finds nothing answers.
Guarantees:
  - removing an atom a space does not hold answers an error naming the
    operation, the space and the atom, while removing one it holds stays unit
    [tested test_removing_an_absent_atom_is_an_error_not_a_silent_unit]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import expr


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
