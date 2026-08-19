"""Purpose: every space operation refuses a first argument that is not a
space the same way, by answering a MeTTa `(Error ...)` atom that names itself
and the call, rather than raising an engine exception.
Assumes:
  - `petta.MeTTa.run` answers an `(Error ...)` atom as data, so a refusal is
    readable without a `pytest.raises` [tested
    test_get_atoms_on_an_unbound_space_names_the_operation]
Guarantees:
  - `get-atoms` and `match` refuse an unbound space the way `add-atom`
    already refuses one, naming themselves [tested
    test_get_atoms_on_an_unbound_space_names_the_operation]
  - a conjunctive pattern is refused on the same terms as a single one
    [tested test_a_conjunctive_match_on_an_unbound_space_refuses_the_same_way]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import MeTTa


@pytest.fixture()
def m(metta):
    return metta.new_space()


def error_text(answer):
    """The `(Error subject reason)` atom as source text."""
    return str(answer)


# The write path already refuses a first argument that is not a space, with a
# diagnostic naming itself, and the read path raised SWI's bare
# `Arguments are not sufficiently instantiated` instead, which names nothing.
# The arbiter answers all three the same way, and words `get-atoms` differently
# because upstream does: pinned `space.rs:143` says "its argument" where
# `:172` and `:199` say "the first argument"
# [source: LeaTTa MettaHyperonFull/Minimal/Interpreter.lean, getAtomsStep at
# 5450-5453, matchStep at 5144-5146, addAtomStep at 5384-5388].
def test_get_atoms_on_an_unbound_space_names_the_operation(m):
    add, atoms, matched = m.run(
        "!(add-atom $u (foo 1))\n!(get-atoms $u)\n!(match $u (foo $x) $x)"
    )
    assert "add-atom expects a space as the first argument" in error_text(add[0])
    assert "get-atoms expects a space as its argument" in error_text(atoms[0])
    assert "match expects a space as the first argument" in error_text(matched[0])
    # Each error names its own operation and carries the call that failed, so
    # the three are distinguishable by their subject and not only by the text.
    assert error_text(atoms[0]).startswith("(Error (get-atoms ")
    assert error_text(matched[0]).startswith("(Error (match ")


# A conjunctive pattern reaches match through its own routing clause, so the
# refusal has to be reached from there too rather than only from the single
# pattern path.
def test_a_conjunctive_match_on_an_unbound_space_refuses_the_same_way(m):
    (answer,) = m.run("!(match $u (, (foo $x) (bar $x)) $x)")
    assert "match expects a space as the first argument" in error_text(answer[0])


# A space is a symbol here, so anything that is not one is refused whether it
# is unbound or merely the wrong kind of value.
def test_a_non_symbol_first_argument_is_refused_by_the_read_path(m):
    atoms, matched = m.run("!(get-atoms 5)\n!(match (1 2) (foo $x) $x)")
    assert "get-atoms expects a space as its argument" in error_text(atoms[0])
    assert "match expects a space as the first argument" in error_text(matched[0])


# The refusal is an answer rather than a throw, which is what makes it
# collectable: a raise would have emptied the collapse instead
# [source: LeaTTa tests/semantics/spaces/add_atom.metta, quoted at
# src/spaces.pl's metta_space_argument/1].
def test_the_read_refusal_is_data_a_collapse_can_hold(m):
    (collapsed,) = m.run("!(collapse (get-atoms $u))")
    assert len(collapsed[0]) == 1
    assert "get-atoms expects a space as its argument" in error_text(collapsed[0][0])


def test_a_fresh_engine_refuses_an_unbound_read_the_same_way():
    """The refusal is the engine's, not a fixture's, so a fresh one agrees."""
    fresh = MeTTa().new_space()
    (answer,) = fresh.run("!(get-atoms $u)")
    assert "get-atoms expects a space as its argument" in error_text(answer[0])
