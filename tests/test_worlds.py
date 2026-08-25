"""Purpose: prove immutable worlds branch, evaluate, and commit as values.

Guarantees:
  - reified evaluation leaves its parent unchanged and answers a new immutable
    world whose multiset diff can be committed as ordinary ordered events
    [tested: test_world_eval_branches_without_touching_parent,
    test_commit_applies_the_world_diff_as_post_commit_events; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - a composite containing a live provider without a snapshot capability
    refuses and names that member [tested:
    test_reify_refuses_and_names_a_live_composite_member; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - world evaluation fences State writes and emits no parent-space event
    [tested: test_world_eval_fences_state_and_emits_nothing; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - provider-owned journal commits persist the ordinary multiset diff before
    publishing it and replay that state after close [tested:
    test_a_journaled_world_commit_replays_its_ordinary_diff; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from dataclasses import FrozenInstanceError

import pytest

from metta import S, State, V, spaces
from metta.errors import PettaError


def test_world_eval_branches_without_touching_parent(metta):
    """Two successors share a base value and mutate neither it nor the store."""
    parent = metta._new_space()
    parent.add(S.base(1))
    world = parent.reify()

    answers, left = world.eval("(progn (add-atom &self (left 2)) done)")
    _, right = world.eval("(progn (add-atom &self (right 3)) done)")

    assert answers == [S.done]
    assert parent.atoms() == [S.base(1)]
    assert world.atoms == (S.base(1),)
    assert left.atoms == (S.base(1), S.left(2))
    assert right.atoms == (S.base(1), S.right(3))
    assert left.diff(right) == ([S.left(2)], [S.right(3)])
    with pytest.raises(FrozenInstanceError):
        left.atoms = ()


def test_world_rebases_copied_self_references_on_every_branch(metta):
    """An equation captured from a parent writes only into each scratch world."""
    parent = metta._new_space()
    parent.run("(= (world-plant) (add-atom &self (owned yes)))")

    _, planted = parent.reify().eval("(world-plant)")
    assert S.owned(S.yes) in planted.atoms
    assert list(parent.match(S.owned(V.what))) == []

    _, planted_twice = planted.eval("(world-plant)")
    assert planted_twice.atoms.count(S.owned(S.yes)) == 2
    assert list(parent.match(S.owned(V.what))) == []


def test_world_commit_preserves_multiplicity_and_refuses_stale_or_wrong_origins(metta):
    """A world is an origin-bound optimistic multiset value."""
    parent = metta._new_space()
    parent.add(S.dup(1))
    _, doubled = parent.reify().eval("(add-atom &self (dup 1))")

    parent.commit(doubled)
    assert parent.atoms() == [S.dup(1), S.dup(1)]
    with pytest.raises(PettaError, match=r"changed after.*reified|stale"):
        parent.commit(doubled)

    other = metta._new_space()
    try:
        with pytest.raises(PettaError, match="belongs to"):
            other.commit(doubled)
    finally:
        other.drop()


def test_commit_applies_the_world_diff_as_post_commit_events(metta):
    """Observers run after the whole remove/add diff is visible in the parent."""
    parent = metta._new_space()
    parent.add(S.old(1))
    _, world = parent.reify().eval("(progn (remove-atom &self (old 1)) (add-atom &self (new 2)))")
    seen = []
    snapshots = []
    removed = parent.subscribe(
        S.old(V.n),
        lambda event: (seen.append(event), snapshots.append(parent.atoms())),
        on="remove",
    )
    added = parent.subscribe(
        S.new(V.n), lambda event: (seen.append(event), snapshots.append(parent.atoms()))
    )
    try:
        parent.commit(world)
        assert [(event.action, event.atom) for event in seen] == [
            ("remove", S.old(1)),
            ("add", S.new(2)),
        ]
        assert snapshots == [[S.new(2)], [S.new(2)]]
        assert parent.atoms() == [S.new(2)]
    finally:
        added.cancel()
        removed.cancel()


def test_reify_refuses_and_names_a_live_composite_member(metta):
    """Enumeration is not a snapshot capability, even when it is iterable."""
    native = metta._new_space()
    live = spaces.object_view({"answer": 42})
    composite = metta.metta.space(backing=spaces.union(native, live))
    try:
        with pytest.raises(PettaError, match="ObjectView"):
            composite.reify()
    finally:
        composite.drop()


def test_world_eval_fences_state_and_emits_nothing(metta):
    """A world may alter its own atoms, never the parent event or cell stores."""
    parent = metta._new_space()
    cell = State(7, space=parent)
    seen = []
    subscription = parent.subscribe(S.world(V.n), seen.append)
    try:
        _, changed = parent.reify().eval("(add-atom &self (world 1))")
        assert changed.atoms == (S.world(1),)
        assert seen == []
        assert parent.atoms() == []

        with pytest.raises(PettaError, match=r"state.*world|world.*state"):
            parent.reify().eval(S["change-state!"](cell, 8))
        assert cell.value == 7
    finally:
        subscription.cancel()


def test_a_journaled_world_commit_replays_its_ordinary_diff(metta, tmp_path):
    """The durable provider lands first, then emits remove/add in diff order."""
    journal = tmp_path / "world.db"
    parent = metta.metta.space(
        journal=journal,
        schema={"edge": 2},
        sync="close",
    )
    parent.events("per-write-exactly", "ordered")
    parent.add(S.edge(S.old, 1))
    _, changed = parent.reify().eval(
        "(progn (remove-atom &self (edge old 1)) (add-atom &self (edge new 2)))"
    )
    seen = []
    snapshots = []
    removed = parent.subscribe(
        S.edge(S.old, V.n),
        lambda event: (seen.append(event), snapshots.append(parent.atoms())),
        on="remove",
    )
    added = parent.subscribe(
        S.edge(S.new, V.n),
        lambda event: (seen.append(event), snapshots.append(parent.atoms())),
    )
    try:
        parent.commit(changed)
        assert [(event.action, event.atom) for event in seen] == [
            ("remove", S.edge(S.old, 1)),
            ("add", S.edge(S.new, 2)),
        ]
        assert snapshots == [[S.edge(S.new, 2)], [S.edge(S.new, 2)]]
    finally:
        added.cancel()
        removed.cancel()
        parent.drop()

    reopened = metta.metta.space(
        journal=journal,
        schema={"edge": 2},
        sync="close",
    )
    try:
        assert reopened.atoms() == [S.edge(S.new, 2)]
    finally:
        reopened.drop()
