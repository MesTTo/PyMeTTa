"""Purpose: what a space's name carries from one life to the next. Anonymous
names are POOLED, so `drop()` returns one and a later `new_space()` hands the
same name to a new space; everything the old space held has to be gone by
then, in both halves, the atoms it stored and the functions it compiled.
Assumes:
  - the free pool is FIFO, so a name comes back only once the names released
    before it have, which is why every test here parks the pool first; the
    idiom is test_import_reuse.py's [tested test_a_dropped_name_comes_back]
Guarantees:
  - a recycled name inherits no stored atom, no equation, no declaration and
    no tabling from its past life [tested
    test_a_recycled_space_name_inherits_no_clauses_from_its_past_life]
  - what a recycled name DOES carry is the process-wide registrations, which
    belong to no space [tested
    test_a_recycled_name_still_sees_process_wide_registrations]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S


@pytest.fixture()
def drained(metta):
    """A pool with nothing in it, so the next release is the next handout.

    Without this the name a test drops goes to the back of a queue whose
    front holds whatever earlier tests released, and "the same name comes
    back" becomes true only by accident of test order.
    """
    free = metta.runtime.once("aggregate_all(count, petta_py_free_space(_), N)")["N"]
    parked = [metta.new_space() for _ in range(free)]
    yield metta
    for space in parked:
        space.drop()


def test_a_dropped_name_comes_back(drained):
    """The premise. Without name reuse there is nothing to inherit, and a
    test that never recycled would pass while proving nothing.
    """
    first = drained.new_space()
    name = first.space_name
    first.drop()
    second = drained.new_space()
    assert second.space_name == name
    second.drop()


# The equation half is what the engine's own clear used to leave standing:
# storage went, the compiled clauses stayed, and a space holding nothing
# answered its own functions. The Python door was whole because its clear
# funnels equations before reaching the engine's, so this is the end-to-end
# guard over a door that was already right; the engine door's own red is
# spaces_execution_modules:clearing_a_space_empties_its_execution_module.
def test_a_recycled_space_name_inherits_no_clauses_from_its_past_life(drained):
    first = drained.new_space()
    name = first.space_name
    first.add(S.plain(1))
    first.run("(= (past-life) inherited)")
    first.run("(: past-typed (-> Number Number))\n(= (past-typed $x) $x)")
    # Tabling instruments the compiled function, so it is declared after the
    # equation and with the call's own shape; `(tabled past-tabled)` on the
    # bare name is refused, loudly, by lib_tabling.
    first.run("!(import! &self (library lib_tabling))")
    first.run("(= (past-tabled $x) $x)\n!(tabled (past-tabled $x))")
    assert first.run("!(past-life)") == [[S.inherited]]
    assert first.run("!(past-typed 1)") == [[1]]
    assert first.run("!(past-tabled 1)") == [[1]]
    first.drop()

    second = drained.new_space()
    assert second.space_name == name, "the point of the test is the reused name"
    try:
        assert second.atoms() == []
        # Unreduced, which is what a call to a function nothing defines
        # answers. A past life's value here would be the defect.
        assert second.run("!(past-life)") == [[S["past-life"]()]]
        assert second.run("!(past-typed 1)") == [[S["past-typed"](1)]]
        assert second.run("!(past-tabled 1)") == [[S["past-tabled"](1)]]
        # And the name is usable: a second life may define the same function
        # at a different arity without the first life's shape reaching it.
        second.run("(= (past-life $x $y) fresh)")
        assert second.run("!(past-life 1 2)") == [[S.fresh]]
    finally:
        second.drop()


def test_a_recycled_name_can_reimport_what_its_past_life_imported(tmp_path, drained):
    """Import bookkeeping is per space, so a recycled name must not remember
    a file the previous life loaded and skip it as already imported.
    """
    source = tmp_path / "life.metta"
    source.write_text("(imported-fact payload)\n")

    first = drained.new_space()
    name = first.space_name
    first.run(f'!(import! &self "{source}")')
    assert first.atoms() == [S["imported-fact"](S.payload)]
    first.drop()

    second = drained.new_space()
    assert second.space_name == name
    try:
        assert second.atoms() == []
        second.run(f'!(import! &self "{source}")')
        assert second.atoms() == [S["imported-fact"](S.payload)]
    finally:
        second.drop()


# Not a leak, and worth pinning as not one: register_op and register_prolog
# are documented as process-wide, "only equations are space-scoped, so a
# new_space() isolates one of the three things you can register and shares
# the other two". They answer from &self and from a sibling space while the
# registering space is still alive, so their surviving its drop is that same
# fact rather than a past life reaching through a name.
def test_a_recycled_name_still_sees_process_wide_registrations(drained):
    sibling = drained.new_space()
    first = drained.new_space()
    name = first.space_name
    first.register_op(lambda: 3, name="lifecycle-py")
    try:
        assert sibling.run("!(lifecycle-py)") == [[3]]
        assert drained.run("!(lifecycle-py)") == [[3]]
        first.drop()
        second = drained.new_space()
        assert second.space_name == name
        assert second.run("!(lifecycle-py)") == [[3]]
        second.drop()
    finally:
        drained.unregister_op("lifecycle-py")
        sibling.drop()


def test_a_dropped_handle_refuses_rather_than_writing_into_the_next_life(metta):
    """The other half of name reuse: the dead handle must not reach the
    engine, because its name may already belong to somebody else.
    """
    first = metta.new_space()
    first.drop()
    with pytest.raises(Exception, match="dropped"):
        first.add(S.late(1))
