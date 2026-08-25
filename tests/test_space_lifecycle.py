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
  - an inherited space reads its own multiset before its ancestors, joins
    across those layers, and mutates only its own store
    [tested: test_a_child_space_reads_through_its_parent_and_writes_locally;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import PettaError, S, V


@pytest.fixture()
def drained(metta):
    """A pool with nothing in it, so the next release is the next handout.

    Without this the name a test drops goes to the back of a queue whose
    front holds whatever earlier tests released, and "the same name comes
    back" becomes true only by accident of test order.
    """
    free = metta.runtime.once("aggregate_all(count, petta_py_free_space(_), N)")["N"]
    parked = [metta._new_space() for _ in range(free)]
    yield metta
    for space in parked:
        space.drop()


def test_a_dropped_name_comes_back(drained):
    """The premise. Without name reuse there is nothing to inherit, and a
    test that never recycled would pass while proving nothing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    first = drained._new_space()
    name = first.name
    first.drop()
    second = drained._new_space()
    assert second.name == name
    second.drop()


def _execution_module_owns(metta, space_name):
    """What a space's execution module still holds, by name and clause count.

    The one query in this file that is not the public surface, and it is here
    because the contract IS about that module: an equation leaves through the
    removal funnel and can be checked by asking the space, while a lambda and a
    specialization have no stored atom behind them and can only be seen here.
    """
    row = metta.runtime.once(
        "atom_string(_S, Space), space_module(_S, _M), "
        "findall(_T, (current_predicate(_M:_N/_A), functor(_H, _N, _A), "
        "             \\+ predicate_property(_M:_H, imported_from(_)), "
        "             predicate_property(_M:_H, number_of_clauses(_C)), "
        '             format(atom(_T), "~w/~w x~w", [_N, _A, _C])), Owned)',
        Space=space_name,
    )
    return sorted(row["Owned"])


# The equation half is what the engine's own clear used to leave standing:
# storage went, the compiled clauses stayed, and a space holding nothing
# answered its own functions. The Python door was whole because its clear
# funnels equations before reaching the engine's, so this is the end-to-end
# guard over a door that was already right; the engine door's own red is
# spaces_execution_modules:clearing_a_space_empties_its_execution_module.
#
# The GENERATED half is the one that was still leaking on 2026-08-22. A clear
# takes equations out one per stored (= ...) atom, so a predicate the compiler
# made with no stored equation behind it was never reached: a compiled lambda
# kept its clauses and a specialization kept its predicate. Measured on that
# tree, a dropped space's module still held lambda_2/2 with its clause and
# twice_Spec_[inc]/3, and the recycled name answered
# !(callPredicate (Predicate (lambda_2 5 $y))) with True, running a lambda body
# belonging to a space that no longer existed. Nothing gave a wrong ANSWER,
# because the lambda counter is process-global and the specialization rebuilds,
# so the harm was a module that grew by one dead predicate per lambda per life
# and an escape hatch that reached into a finished one.
def test_a_recycled_space_name_inherits_no_clauses_from_its_past_life(drained):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    first = drained._new_space()
    name = first.name
    first.add(S.plain(1))
    first.run("(= (past-life) inherited)")
    first.run("(: past-typed (-> Number Number))\n(= (past-typed $x) $x)")
    # A compiled lambda and a specialization, the two shapes with no stored
    # equation to leave through.
    first.run("(= (past-inc $x) (+ $x 1))")
    first.run("(= (past-twice $f $x) ($f ($f $x)))")
    assert first.run("!(past-twice past-inc 5)") == [[7]]
    assert first.run("!((|-> ($x) (* $x 10)) 7)") == [[70]]
    owned = _execution_module_owns(drained, name)
    assert owned != []
    # The lambda's generated name is READ rather than written down. It comes
    # from a process-global counter, so which number this life reaches depends
    # on every lambda compiled before it in the same process; a name written
    # down here is one an unrelated test can already own in the PARENT module,
    # where the recycled space would inherit it and the hatch below would find
    # something rather than nothing.
    past_lambda = next(
        entry.split("/")[0] for entry in owned if entry.startswith("lambda_")
    )
    # Tabling instruments the compiled function, so it is declared after the
    # equation and with the call's own shape; `(tabled past-tabled)` on the
    # bare name is refused, loudly, by lib_tabling.
    first.run("!(import! &self (library lib_tabling))")
    first.run("(= (past-tabled $x) $x)\n!(tabled (past-tabled $x))")
    assert first.run("!(past-life)") == [[S.inherited]]
    assert first.run("!(past-typed 1)") == [[1]]
    assert first.run("!(past-tabled 1)") == [[1]]
    first.drop()
    # Nothing at all, rather than nothing with a stored atom behind it.
    assert _execution_module_owns(drained, name) == []

    second = drained._new_space()
    assert second.name == name, "the point of the test is the reused name"
    try:
        assert second.atoms() == []
        assert second.run("!(past-twice past-inc 5)") == [
            [S["past-twice"](S["past-inc"], 5)]
        ]
        # The raw-Prolog hatch is how a past life's lambda was reachable at
        # all, its generated name being one no MeTTa program writes. It has to
        # find nothing now, which for that hatch is a Prolog existence error.
        with pytest.raises(PettaError, match=past_lambda):
            second.run(f"!(callPredicate (Predicate ({past_lambda} 5 $y)))")
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
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    source = tmp_path / "life.metta"
    source.write_text("(imported-fact payload)\n")

    first = drained._new_space()
    name = first.name
    first.run(f'!(import! &self "{source}")')
    assert first.atoms() == [S["imported-fact"](S.payload)]
    first.drop()

    second = drained._new_space()
    assert second.name == name
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
def test_a_recycled_name_still_sees_process_wide_registrations(drained):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    sibling = drained._new_space()
    first = drained._new_space()
    name = first.name
    first.op(lambda: 3, name="lifecycle-py", effect="pureStructural")
    try:
        assert sibling.run("!(lifecycle-py)") == [[3]]
        assert drained.run("!(lifecycle-py)") == [[3]]
        first.drop()
        second = drained._new_space()
        assert second.name == name
        assert second.run("!(lifecycle-py)") == [[3]]
        second.drop()
    finally:
        drained.unregister_op("lifecycle-py")
        sibling.drop()


def test_a_dropped_handle_refuses_rather_than_writing_into_the_next_life(metta):
    """The other half of name reuse: the dead handle must not reach the
    engine, because its name may already belong to somebody else.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    first = metta._new_space()
    first.drop()
    with pytest.raises(Exception, match="dropped"):
        first.add(S.late(1))


def test_a_child_space_reads_through_its_parent_and_writes_locally(metta):
    """Inheritance is a child-first read union and a front-only mutation."""
    with metta._new_space() as parent:
        parent.add(
            S.edge(S.a, S.b), S.parent_only(1), S.copy(S.same), S.layer(S.parent)
        )
        with metta._new_space(inherits=parent) as child:
            child.add(
                S.edge(S.b, S.c), S.child_only(2), S.copy(S.same), S.layer(S.child)
            )

            assert sorted(map(str, child.atoms())) == sorted(map(str, [
                S.edge(S.b, S.c),
                S.child_only(2),
                S.copy(S.same),
                S.layer(S.child),
                S.edge(S.a, S.b),
                S.parent_only(1),
                S.copy(S.same),
                S.layer(S.parent),
            ]))
            assert [row.x for row in child.match(S.layer(V.x))] == [
                S.child,
                S.parent,
            ]
            assert [(row.x, row.z) for row in child.match(
                S.edge(V.x, V.y), S.edge(V.y, V.z)
            )] == [(S.a, S.c)]
            assert len(child) == 8
            assert child.run("!(space-atom-count (context-space))") == [[4]]
            assert not parent.match(S.child_only(V.x))

            parent.run("(= (layer-answer) parent)")
            assert child.run("!(layer-answer)") == [[S.parent]]
            child.run("(= (layer-answer) child)")
            assert child.run("!(layer-answer)") == [[S.child]]
            assert parent.run("!(layer-answer)") == [[S.parent]]

            assert child.remove(S.parent_only(1)) is False
            assert parent.match(S.parent_only(1))
            assert child.remove(V.any) is True
            assert child.run("!(space-atom-count (context-space))") == [[0]]
            assert child.remove(V.any) is False
            assert child.match(S.parent_only(1))
            assert child.run("!(layer-answer)") == [[S.parent]]
            child.clear()
            assert len(child) == 5
            assert child.run("!(space-atom-count (context-space))") == [[0]]
            assert child.match(S.parent_only(1))
            assert parent.match(S.parent_only(1))

        assert parent.match(S.parent_only(1))


def test_a_parent_cannot_drop_while_a_live_child_names_it(metta):
    """A parent refuses to drop while a live child inherits from its name."""
    parent = metta._new_space()
    child = metta._new_space(inherits=parent)
    try:
        with pytest.raises(PettaError, match="live child"):
            parent.drop()
        parent.add(S.still_live(1))
        assert child.match(S.still_live(1))
    finally:
        child.drop()
        parent.drop()


def test_a_recycled_child_name_may_choose_a_different_parent(drained):
    """A recycled child name may declare a different parent in its next life."""
    first_parent = drained._new_space()
    second_parent = drained._new_space()
    first_parent.add(S.from_parent(S.first))
    second_parent.add(S.from_parent(S.second))
    first_parent.run("(= (parent-answer) first)")
    second_parent.run("(= (parent-answer) second)")
    first_child = drained._new_space(inherits=first_parent)
    name = first_child.name
    assert first_child.run("!(parent-answer)") == [[S.first]]
    first_child.drop()

    second_child = drained._new_space(inherits=second_parent)
    try:
        assert second_child.name == name
        assert not second_child.match(S.from_parent(S.first))
        assert second_child.match(S.from_parent(S.second))
        assert second_child.run("!(parent-answer)") == [[S.second]]
    finally:
        second_child.drop()
        first_parent.drop()
        second_parent.drop()
