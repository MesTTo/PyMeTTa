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
  - the refusal never joins the answers of a match against a real space, in a
    proof walk any more than in evaluation [tested
    test_a_proof_over_a_match_does_not_carry_the_refusal]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from petta import MeTTa, S


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


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
def test_get_atoms_on_an_unbound_space_names_the_operation(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
def test_a_conjunctive_match_on_an_unbound_space_refuses_the_same_way(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (answer,) = m.run("!(match $u (, (foo $x) (bar $x)) $x)")
    assert "match expects a space as the first argument" in error_text(answer[0])


# A space is a symbol here, so anything that is not one is refused whether it
# is unbound or merely the wrong kind of value.
def test_a_non_symbol_first_argument_is_refused_by_the_read_path(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atoms, matched = m.run("!(get-atoms 5)\n!(match (1 2) (foo $x) $x)")
    assert "get-atoms expects a space as its argument" in error_text(atoms[0])
    assert "match expects a space as the first argument" in error_text(matched[0])


# The refusal is an answer rather than a throw, which is what makes it
# collectable: a raise would have emptied the collapse instead
# [source: LeaTTa tests/semantics/spaces/add_atom.metta, quoted at
# engine/spaces.pl's petta_space_name/1].
def test_the_read_refusal_is_data_a_collapse_can_hold(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (collapsed,) = m.run("!(collapse (get-atoms $u))")
    assert len(collapsed[0]) == 1
    assert "get-atoms expects a space as its argument" in error_text(collapsed[0][0])


# A symbol that is not a SPACE NAME is refused the same way, which is the rule
# is-space states and evalc has always enforced: a space name begins with &.
# Before this, `(add-atom not-a-space (bad add))` made a space called
# `not-a-space` and `(get-atoms not-a-space)` read it back, while
# `(is-space not-a-space)` answered False in the same program
# [source: LeaTTa tests/semantics/spaces/add_atom.metta, get_atoms.metta and
# match.metta, all STATUS conforms].
def test_a_symbol_that_is_not_a_space_name_is_refused(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    add, atoms, matched = m.run(
        "!(add-atom not-a-space (bad add))\n"
        "!(get-atoms not-a-space)\n"
        "!(match not-a-space (foo $x) $x)"
    )
    assert "add-atom expects a space as the first argument" in error_text(add[0])
    assert "get-atoms expects a space as its argument" in error_text(atoms[0])
    assert "match expects a space as the first argument" in error_text(matched[0])


# The prefix is the whole of the rule, so a name nothing has bound yet is a
# space the moment it is written to. That is what a space being created on
# demand means here, and it is why the rule cannot be the registry.
def test_a_fresh_ampersand_name_is_created_by_writing_to_it(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    written, found = m.run(
        "!(add-atom &fresh-on-write (canary 1))\n"
        "!(match &fresh-on-write (canary $x) $x)"
    )
    assert str(written[0]) == "()"
    assert str(found[0]) == "1"


def test_a_fresh_engine_refuses_an_unbound_read_the_same_way():
    """The refusal is the engine's, not a fixture's, so a fresh one agrees."""
    fresh = MeTTa().space()
    (answer,) = fresh.run("!(get-atoms $u)")
    assert "get-atoms expects a space as its argument" in error_text(answer[0])


# A proof walk enumerates a predicate's clauses and calls each body through
# call/1, where a cut in an earlier body prunes nothing, so a refusal clause
# that leans on one answers BESIDE the rows a real space gave. That grew a
# second answer for every match and `(anc $x $y)` recursed on it until the
# process hung, which is why each clause guards itself
# [reproduced 2026-08-20 through bindings/python/tests/test_derivation.py].
def test_a_proof_over_a_match_does_not_carry_the_refusal(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(par-p Tom Bob)\n(= (anc-p $x $y) (match &self (par-p $x $y) $y))")
    proofs = m.derivation(S["anc-p"](S.Tom, S.Bob))
    assert len(proofs) == 1
    assert [str(fact.atom) for fact in proofs[0].facts] == ["(par-p Tom Bob)"]
