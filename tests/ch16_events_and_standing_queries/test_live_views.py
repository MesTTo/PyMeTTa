"""Purpose: `m.live(query)` and its three maintenance strategies, blackbox.

Guarantees:
  - a pattern view delivers a signed delta per change and one progress delta
    per commit, so a transaction of two writes is two adds and ONE progress
    [tested: test_a_transaction_delivers_one_progress_after_its_deltas;
    commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - a conjunction view re-answers exactly once per touching commit, holds the
    join's multiset, and never re-answers for a write its heads do not name
    [tested: test_a_conjunction_view_re_answers_the_join_on_a_touching_commit,
    test_an_untouching_write_does_not_re_answer_a_conjunction_view;
    commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - a tabled view refreshes when a write to the relation its body reads moves
    the table's invalidation counter [tested:
    test_a_tabled_view_refreshes_after_a_write_to_the_relation; commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - the strategy chosen for a query is the one its shape names
    [tested: test_the_chosen_strategy_is_the_one_the_shape_names; commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - the async face delivers the same deltas as the blocking one
    [tested: test_the_async_face_sees_the_same_deltas; commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - the refusals: an unsubscribable provider, a query whose own head writes,
    and a tabled strategy over a head with no table
    [tested: test_a_provider_that_delivers_no_events_refuses_a_view,
    test_a_query_whose_head_writes_refuses,
    test_the_tabled_strategy_refuses_a_head_that_is_not_tabled;
    commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - a changes() stream that cannot take a delta refuses the write rather than
    dropping it, and every other open stream is offered it first [tested:
    test_a_full_changes_stream_does_not_starve_another; commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager

import pytest

import metta as metta_module
from metta import S, V, aio
from metta.errors import MettaError
from metta.foreign import SpaceProvider
from metta.live import Delta, Live
from metta.vocabularies import LiveStrategy


def _tabling(space):
    """Load lib_tabling, so `!(tabled ...)` is a declaration.

    Without it the form is an ordinary expression whose argument reduces
    first.
    """
    space.run("!(import! &self (library lib_tabling))")


@contextmanager
def _private_table(space, name):
    """A view's atomic seed requires a private incremental table."""
    _tabling(space)
    row = f"(cache {name} (incremental private))"
    space.run(f"!(add-atom &metta {row})")
    try:
        yield
    finally:
        space.run(f"!(remove-atom &metta {row})")


def test_a_transaction_delivers_one_progress_after_its_deltas(metta):
    """The commit is the boundary, so its whole diff shares one progress.

    Materialize's SUBSCRIBE progress row says the same thing: no update older
    than this timestamp will arrive [source:
    https://materialize.com/docs/sql/subscribe/].
    """
    with metta._new_space() as sp, sp.live(S.alert(V.level)) as alerts:
        with alerts.changes(timeout=2) as deltas:
            sp.add(S.alert(S.red))
            sp.transaction(lambda: sp.add(S.alert(S.amber), S.alert(S.green)))
            sp.remove(S.alert(S.red))
            seen = [
                (delta.kind, delta.diff, str(delta.atom))
                for delta in _take(deltas, 6)
            ]
        assert [kind for kind, _diff, _atom in seen] == [
            "add", "progress", "add", "add", "progress", "remove",
        ]
        assert [diff for _kind, diff, _atom in seen] == [1, 0, 1, 1, 0, -1]
        assert seen[0][2] == "(alert red)"
        assert len(alerts) == 2
        assert alerts.count(S.alert(S.amber)) == 1
        assert S.alert(S.red) not in alerts


def test_a_pattern_view_holds_the_multiset_through_both_removal_shapes(metta):
    """A ground removal decrements locally; a pattern one re-reads."""
    with metta._new_space() as sp, sp.live(S.alert(V.level)) as alerts:
        sp.add(S.alert(S.red), S.alert(S.red), S.alert(S.amber))
        assert len(alerts) == 3 == len(sp)
        assert alerts.count(S.alert(S.red)) == 2
        assert alerts.count({"level": S.red}) == 2
        assert [str(row) for row in alerts.rows] == [
            "Row(level=red)", "Row(level=red)", "Row(level=amber)"
        ]
        sp.remove(S.alert(S.red))
        assert alerts.count(S.alert(S.red)) == 1
        sp.remove(S.alert(V.q))
        assert len(alerts) == 1 == len(sp)
        assert alerts.atoms() == list(sp.atoms())


def test_a_conjunction_view_re_answers_the_join_on_a_touching_commit(metta):
    """The view holds what the join answers, add and remove alike."""
    with metta._new_space() as sp:
        sp.add(S.person(S.bob, 30), S.city(S.bob, S.nyc), S.person(S.eve, 25))
        with sp.live(S.person(V.n, V.a), S.city(V.n, V.c)) as joined:
            assert joined.strategy is LiveStrategy.heads
            assert joined.columns == ("n", "a", "c")
            assert len(joined) == 1
            with joined.changes(timeout=2) as deltas:
                sp.add(S.city(S.eve, S.la))
                sp.remove(S.city(S.bob, S.nyc))
                seen = [
                    (delta.kind, delta.diff, delta.row) for delta in _take(deltas, 4)
                ]
            assert [kind for kind, _diff, _row in seen] == [
                "add", "progress", "remove", "progress",
            ]
            assert seen[0][2]["n"] == S.eve
            assert seen[2][2]["c"] == S.nyc
            assert {str(row) for row in joined.rows} == {
                "Row(n=eve, a=Grounded(25), c=la)"
            }
            # A join answers rows and no single atom, and says so.
            with pytest.raises(MettaError, match="joins 2 patterns"):
                joined.atoms()


def test_an_untouching_write_does_not_re_answer_a_conjunction_view(metta):
    """Theta(query) per TOUCHING commit, and a flat cost for the others.

    The subscriptions are per head, so a write the query cannot see never
    reaches the view and its cost does not move with how much the view holds.
    Measured 2026-09-07 over joins of 10, 100 and 1,000 rows: 91 inferences
    flat, where the touching write's own cost went 167, 445, 3,173.
    """
    def untouching_cost(size):
        # Minimum of three, the repository's own measurement rule; inferences
        # are deterministic where wall clock on this box is not.
        with metta._new_space() as sp:
            sp.add(*[S.person(S[f"p{index}"], index) for index in range(size)])
            sp.add(*[S.city(S[f"p{index}"], S.here) for index in range(size)])
            with sp.live(S.person(V.n, V.a), S.city(V.n, V.c)) as joined:
                costs = []
                for index in range(3):
                    with metta.stats() as spent:
                        sp.add(S.noise(index))
                    costs.append(spent.inferences)
                assert len(joined) == size
            return min(costs)

    small, large = untouching_cost(10), untouching_cost(200)
    assert small == large, (
        f"an untouching write cost {small} over a join of 10 and {large} over "
        f"a join of 200; the view re-answered for a write its heads do not name"
    )


def test_a_tabled_view_refreshes_after_a_write_to_the_relation(metta):
    """The TabledMap shape: the computed answer follows the read relation."""
    with metta._new_space() as sp, _private_table(sp, "live-cheapest"):
        sp.add(S.price(S.apple, 3), S.price(S.pear, 4))
        sp.run(
            f"(= (live-cheapest) (min-atom (collapse "
            f"(match {sp.name} (price $i $p) $p))))"
        )
        assert sp.run("!(tabled (live-cheapest))") == [[True]]
        with sp.live(S["live-cheapest"]()) as best:
            assert best.strategy is LiveStrategy.tabled
            assert best.columns == ("value",)
            assert [str(row) for row in best.rows] == ["Row(value=Grounded(3))"]
            with best.changes(timeout=2) as deltas:
                sp.add(S.price(S.plum, 1))
                moved = {
                    (delta.kind, delta.diff, str(delta.atom))
                    for delta in _take(deltas, 3)
                    if delta.kind != "progress"
                }
            assert moved == {("add", 1, "1"), ("remove", -1, "3")}
            assert [str(row) for row in best.rows] == ["Row(value=Grounded(1))"]


def test_the_chosen_strategy_is_the_one_the_shape_names(metta):
    """One atom is a pattern, a tabled head is a call, several are a join."""
    with metta._new_space() as sp, _private_table(sp, "live-shape"):
        sp.add(S.edge(S.a, S.b))
        sp.run("(= (live-shape) 1)")
        assert sp.run("!(tabled (live-shape))") == [[True]]
        with sp.live(S.edge(V.x, V.y)) as one:
            assert one.strategy is LiveStrategy.pattern
        with sp.live(S.edge(V.x, V.y), S.edge(V.y, V.z)) as several:
            assert several.strategy is LiveStrategy.heads
        with sp.live(S["live-shape"]()) as called:
            assert called.strategy is LiveStrategy.tabled
        # An explicit word overrides the shape, and the view still answers.
        with sp.live(S.edge(V.x, V.y), strategy="heads") as forced:
            assert forced.strategy is LiveStrategy.heads
            assert len(forced) == 1


def test_a_shared_tabled_view_refuses_its_transactional_seed(metta):
    """The view keeps atomic seeding and exposes the engine's private remedy."""
    with metta._new_space() as sp:
        _tabling(sp)
        sp.run("(= (live-shared) 1) !(tabled (live-shared))")
        with pytest.raises(MettaError, match="incremental private"):
            sp.live(S["live-shared"]())
        assert sp.eval(S["live-shared"]()) == [1]


def test_the_async_face_sees_the_same_deltas(metta):
    """`async for` over the same view, through the generated aio mirror."""
    async def go():
        async with aio.AsyncMeTTa(metta=metta) as am:
            scratch = await am.space()
            try:
                live = await scratch.live(S.beacon(V.n))
                deltas = live.changes(timeout=3)
                seen: list[tuple[str, int]] = []

                async def consume():
                    async for delta in deltas:
                        seen.append((delta.kind, delta.diff))
                        if len(seen) >= 3:
                            return

                task = asyncio.create_task(consume())
                await asyncio.sleep(0.1)
                await scratch.add(S.beacon(1))
                await scratch.add(S.beacon(2))
                await task
                await deltas.aclose()
                await live.aclose()
                return seen, len(live)
            finally:
                await scratch.drop()

    seen, held = asyncio.run(go())
    assert seen == [("add", 1), ("progress", 0), ("add", 1)]
    assert held == 2


@pytest.mark.usefixtures("metta")
def test_a_provider_that_delivers_no_events_refuses_a_view():
    """A view is only as current as the changes it hears about.

    The fixture boots the process engine the module-level attach needs, and
    nothing else here reads it.
    """
    class Quiet(SpaceProvider):
        def __init__(self):
            self._atoms = []

        def atoms(self):
            return list(self._atoms)

        def add(self, atom):
            self._atoms.append(atom)

    with metta_module.attach("&live_quiet", Quiet()) as store:
        with pytest.raises(MettaError, match="live cannot use &live_quiet"):
            store.live(S.thing(V.x))


def test_a_query_whose_head_writes_refuses(metta):
    """A view MATCHES, so a call written where a pattern belongs refuses.

    A head the space also defines with an effectful body is NOT this case:
    the plan names the body's operation and not the head, and the view over
    the stored atoms stands.
    """
    with metta._new_space() as sp:
        with pytest.raises(MettaError, match="writes \\(add-atom writesState\\)"):
            sp.live(S["add-atom"](S[str(sp.name)], S.x))
        with pytest.raises(MettaError, match="writes \\(println! writesState\\)"):
            sp.live(S["println!"](S.x))
        sp.run("(= (live-shadow $x) (println! $x))")
        sp.add(S["live-shadow"](S.red))
        with sp.live(S["live-shadow"](V.l)) as shadowed:
            assert len(shadowed) == 1


def test_the_tabled_strategy_refuses_a_head_that_is_not_tabled(metta):
    """No table means no invalidation counter, and the remedy is the row."""
    with metta._new_space() as sp:
        with pytest.raises(MettaError, match="is not tabled in"):
            sp.live(S["live-absent"](), strategy="tabled")
        with pytest.raises(MettaError, match="maintains ONE pattern"):
            sp.live(S.a(V.x), S.b(V.x), strategy="pattern")
        with pytest.raises(ValueError, match="strategy must be one of"):
            sp.live(S.a(V.x), strategy="magic")
        with pytest.raises(MettaError, match="a live view needs a query"):
            sp.live()


def test_a_view_matches_a_delta_structurally(metta):
    """Delta is frozen and slotted, so a consumer reads it with `match`."""
    with metta._new_space() as sp, sp.live(S.tick(V.n)) as ticks:
        with ticks.changes(timeout=2) as deltas:
            sp.add(S.tick(1))
            read: list[str] = []
            for delta in _take(deltas, 2):
                match delta:
                    case Delta("add", 1, row, _atom, _generation):
                        read.append(f"add {row['n']}")
                    case Delta("progress", _, None, None, generation):
                        read.append(f"progress {generation > 0}")
        assert read == ["add 1", "progress True"]
        with pytest.raises(AttributeError):
            delta.kind = "remove"  # frozen


def test_a_closed_view_keeps_its_answer_and_stops_tracking(metta):
    """close() ends the maintenance; the last answer stays readable."""
    with metta._new_space() as sp:
        view = Live(sp, S.gauge(V.n))
        sp.add(S.gauge(1))
        assert len(view) == 1
        view.close()
        view.close()  # idempotent
        sp.add(S.gauge(2))
        assert len(view) == 1
        with pytest.raises(MettaError, match="this live view is closed"):
            view.changes()


def _take(deltas, count):
    """The next `count` deltas, or as many as the stream gives."""
    taken = []
    for delta in deltas:
        taken.append(delta)
        if len(taken) == count:
            break
    return taken


def test_a_full_changes_stream_does_not_starve_another(metta):
    """Every open stream is offered a delta before any refusal is raised.

    The rule the fold registry already holds for a failed watcher: one
    consumer that cannot take a change is not a reason for the others to miss
    it. The refusal reaches the writer, because the write committed.
    """
    with metta._new_space() as sp, sp.live(S.gate(V.n)) as view:
        with (
            view.changes(timeout=2, queue_max=1) as small,
            view.changes(timeout=2) as roomy,
        ):
            # The add fills the one-delta buffer; the progress marker that
            # closes the same commit has nowhere to go.
            with pytest.raises(MettaError, match="undelivered deltas"):
                sp.add(S.gate(1))
            assert [delta.kind for delta in _take(roomy, 2)] == ["add", "progress"]
            assert [delta.kind for delta in _take(small, 1)] == ["add"]
        assert len(view) == 1
        with pytest.raises(ValueError, match="queue_max must be positive"):
            view.changes(queue_max=0)
        with pytest.raises(TypeError, match="queue_max must be a positive integer"):
            view.changes(queue_max=1.5)
