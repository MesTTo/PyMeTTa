"""Purpose: pin the cost of the multi-space idiom against the NAME being shared.

A space per test, a space per request and a space per world all reuse ordinary
head names, so `fib`, `step` and `run` end up defined in many live spaces at
once. Three separate mechanisms priced that: the automatic-memo reconciliation
rebuilt a changed name in every module holding it, an equation arrival
invalidated the support view of every module that had ever called the name, and
a recycled execution module walked its whole visible predicate table looking
for weak imports to rebase. The first two are O(spaces sharing the name) per
operation and therefore O(N^2) over the program.

Inferences are the meter. They are deterministic here where wall clock is not:
the same probe answered 17,457 on five consecutive runs of a loaded box, and
`m.stats()` reports the engine's own counter over the block.

Assumes: every space here is opened under a WRITTEN name nothing else uses,
  because a pooled anonymous name can hand back an execution module whose
  previous life named a different parent, and rebasing that module's weak
  imports is a real cost this measurement is not about.
Guarantees:
  - a first evaluation of a head costs the same in the eighth live space
    defining it as in the second [tested:
    test_a_first_evaluation_costs_the_same_in_every_space; commit=22ce91dd50882975ccb175dcd2b235f4110ab6ff]
  - and still does when an annotated arrow is live somewhere else in the
    process, which used to turn a per-module effect scan back on [tested:
    test_a_first_evaluation_costs_the_same_in_every_space_beside_an_annotated_arrow;
    commit=ccad9f6d588270ec2f0810fc56c30e9e59207e7c]
  - defining that head costs the same in the eighth as in the second [tested:
    test_defining_a_shared_head_costs_the_same_in_every_space; commit=22ce91dd50882975ccb175dcd2b235f4110ab6ff]
  - and still does while a table stands somewhere in the process, because the
    tabling library learns of a change from the engine's own invalidation
    wave rather than from a walk of every space calling the name [tested:
    test_a_declared_table_keeps_a_shared_heads_definition_cost_flat; commit=WORKTREE]
  - a recycled space name defines for a fresh name's cost [tested:
    test_a_recycled_space_name_defines_for_a_fresh_names_cost; commit=22ce91dd50882975ccb175dcd2b235f4110ab6ff]
  - narrowing those three did not narrow what a definition REACHES: an
    inheriting space still retargets to its parent's new definition, a sibling
    still cannot move it, and every space's copy is still memoized [tested:
    test_a_definition_reaches_an_inheriting_spaces_view,
    test_a_sibling_definition_does_not_move_an_inheriting_spaces_answer,
    test_every_space_defining_a_shared_head_still_memoizes_it; commit=22ce91dd50882975ccb175dcd2b235f4110ab6ff]
Fails when: read as a pin on the absolute numbers. Every assertion here is a
  RATIO between two spaces of one run, so an engine that gets faster or slower
  everywhere passes unchanged and only a slope reopens it.
"""

import itertools

import pytest

from metta import S, space

SPACES = 8
DEPTH = 12
# Five percent of the base measurement. The defect it separates is +76% at
# this width and the residual slope is +0.6%, so the band is wide enough that
# ordinary drift never reaches it and narrow enough that the defect cannot
# return unnoticed.
BAND = 0.05


def _fibonacci(head: str) -> str:
    return (
        f"(= ({head} $n) (if (< $n 2) $n "
        f"(+ ({head} (- $n 1)) ({head} (- $n 2)))))"
    )


@pytest.fixture()
def rooms():
    """Spaces that are all dropped however the test leaves."""
    live = []
    try:
        yield live
    finally:
        for room in reversed(live):
            room.drop()


def _shared_head_costs(metta, live, head):
    """Define `head` in SPACES live spaces and evaluate it once in each.

    The names are WRITTEN rather than minted. An anonymous handle takes
    whatever the pool has free, and a name whose previous life named a
    different parent legitimately pays to rebase its execution module's weak
    imports; sharing a worker with the tests that create inheriting and
    restricted spaces therefore put a 1,855-inference rebase into the middle
    of this measurement [measured 2026-09-05]. A written name that nothing
    else uses is a fresh module every time, which is the cost this is about.
    """
    defining = []
    evaluating = []
    equation = _fibonacci(head)
    for index in range(SPACES):
        room = space(f"&{head}-room-{index}")
        live.append(room)
        with metta.stats() as arrival:
            room.run(equation)
        with metta.stats() as first_call:
            answer = room.run(f"!({head} {DEPTH})")
        assert answer == [[144]], f"{head} answered {answer}"
        defining.append(arrival.inferences)
        evaluating.append(first_call.inferences)
    return defining, evaluating


def _report(costs):
    """The measurement as the failure message should read it."""
    steps = [later - earlier for earlier, later in itertools.pairwise(costs[1:])]
    return (
        f"per-space costs {costs}, so the slope after the first space is "
        f"{steps} and the eighth is {costs[-1] - costs[1]} above the second"
    )


def test_a_first_evaluation_costs_the_same_in_every_space(metta, rooms):
    """The first evaluation must not price other spaces holding the name.

    Every space here defines its own `(= (psh-eval $n) ...)`, so nothing about
    the eighth space's evaluation depends on the other seven; the module a
    call resolves in decides its dispatch, and a sibling module is not on that
    chain. Measured 2026-09-05 before the repair, over six spaces rather than
    eight: 17,457 inferences in the first and 29,084 in the sixth, +2,325 a
    space. The distinct-name control, one head per space, was flat at 15,370
    to 15,442 over the same six, which is what this now reads.
    """
    _, evaluating = _shared_head_costs(metta, rooms, "psh-eval")
    second, eighth = evaluating[1], evaluating[-1]
    assert eighth <= second * (1 + BAND), (
        f"a first evaluation of psh-eval costs {eighth} inferences in the "
        f"eighth live space defining it against {second} in the second, so it "
        f"is still paying for the spaces beside it: {_report(evaluating)}"
    )


def test_a_first_evaluation_costs_the_same_in_every_space_beside_an_annotated_arrow(
    metta, rooms
):
    """One annotated arrow anywhere must not reopen the per-module scan.

    The arrow is on `psh-annotated`, in a room of its own, and the measurement
    is of `psh-eval-annotated`, which nothing declares. They have nothing to do
    with each other, and that was the point: the removed compile-time check was
    guarded by `metta_annotated_operation_effect(_, _)`, both arguments
    unbound, which asks whether ANY annotated arrow exists anywhere in the
    process rather than anything about the name being compiled. One live
    declaration therefore turned the check on for every cached name, and its
    body then computed a host goal effect plan in every module holding that
    name, so a first evaluation cost O(spaces sharing the head).

    Measured over eight rooms. With the check:
    `[13484, 16353, 19090, 21823, 24548, 27297, 30010, 32773]`, a slope of
    `[2737, 2733, 2725, 2749, 2713, 2763]` and an eighth 100.4% above the
    second. Without it: `[15582, 13538, 13557, 13578, 13583, 13618, 13613,
    13662]`, a slope of `[19, 21, 5, 35, -5, 49]` and an eighth 0.92% above the
    second.

    The second and the eighth, which are what the assertion reads, repeat
    exactly across runs and across three trunk tips; the fourth and fifth rooms
    move by two inferences between runs, which is why this compares an endpoint
    pair rather than pinning the list. Against an engine three merges older the
    same pair read 3,730 and 17 a space, before the autoload-search guards took
    about 11,000 inferences off every row: the slope is what this pins, not the
    level.
    """
    annotated = space("&psh-annotated-room")
    rooms.append(annotated)
    annotated.run("!(import! (context-space) (library lib_memo))")
    annotated.run("(: psh-annotated (-[det]-> Number Number))")

    _, evaluating = _shared_head_costs(metta, rooms, "psh-eval-annotated")
    second, eighth = evaluating[1], evaluating[-1]
    assert eighth <= second * (1 + BAND), (
        f"a first evaluation of psh-eval-annotated costs {eighth} inferences "
        f"in the eighth live space defining it against {second} in the second, "
        f"so one annotated arrow elsewhere is still pricing it: "
        f"{_report(evaluating)}"
    )


def test_defining_a_shared_head_costs_the_same_in_every_space(metta, rooms):
    """An equation arrival must not price the spaces that already call the name.

    An arrival invalidates the compiled forms whose resolution of the head it
    can move, and it can move only this module's and those of the spaces that
    inherit through it. Reading every module that had ever called the name
    instead cost 644 inferences to define in the first of six live spaces and
    928 in the sixth, and over forty spaces the definitions alone cost 71,390
    inferences against 23,111 here [measured 2026-09-05].
    """
    defining, _ = _shared_head_costs(metta, rooms, "psh-define")
    second, eighth = defining[1], defining[-1]
    assert eighth <= second * (1 + BAND), (
        f"defining psh-define costs {eighth} inferences in the eighth live "
        f"space against {second} in the second: {_report(defining)}"
    )


def test_a_declared_table_keeps_a_shared_heads_definition_cost_flat(metta, rooms):
    """A standing table must not price a definition by the spaces calling its name.

    The tabling library hears of a change through the invalidation wave the
    engine already runs, from a node the tabled function supports, so a
    definition costs what it costs with no table standing. A walk of its own
    rooted at every view of the changed name read [838, 989, 1176, 1427,
    1518, 1609, 1976, 2063] over these eight rooms with one table standing
    [measured 2026-09-17].
    """
    metta.run("!(import! &self (library lib_tabling))")
    metta.run("(= (psh-standing $n) (+ $n 1)) !(tabled (psh-standing $n)) !(psh-standing 1)")
    try:
        defining, _ = _shared_head_costs(metta, rooms, "psh-define-tabled")
    finally:
        assert metta.run("!(untabled (psh-standing $n))") == [[True]]
    second, eighth = defining[1], defining[-1]
    assert eighth <= second * (1 + BAND), (
        f"defining psh-define-tabled costs {eighth} inferences in the eighth "
        f"live space against {second} in the second with a table standing: "
        f"{_report(defining)}"
    )


def test_a_recycled_space_name_defines_for_a_fresh_names_cost(metta):
    """Reusing a retired space name must not cost more than taking a new one.

    A pooled execution module captures the weak imports of its previous life
    so they can follow a new parent, and that capture walks every predicate
    the module can see. A life that keeps the same base has nothing to rebase,
    name and 3,022 in the same name's second life, and costs 607 here
    [measured 2026-09-05].

    The name is WRITTEN rather than minted. An anonymous handle takes whatever
    the pool has free, and after a few spaces have come and gone that is a
    different name each time, which would leave three fresh modules measured
    and nothing recycled.
    """
    equation = "(= (psh-recycled $n) (+ $n 1))"
    costs = []
    for _ in range(3):
        room = space("&psh-recycled-room")
        try:
            with metta.stats() as arrival:
                room.run(equation)
        finally:
            room.drop()
        costs.append(arrival.inferences)
    assert costs[-1] <= costs[0] * (1 + BAND), (
        f"defining psh-recycled cost {costs[0]} inferences in "
        f"&psh-recycled-room's first life and {costs[-1]} in its third, so "
        f"the reused name is still paying for the module it inherited: {costs}"
    )


@pytest.mark.usefixtures("metta")  # the session engine, whose value these do not read
def test_a_definition_reaches_an_inheriting_spaces_view(rooms):
    """A parent's later definition must retarget a child's compiled call.

    This is the half of the invalidation the cost repair had to keep. The
    child compiles `(psh-inherit-wrap)` while nothing defines
    `psh-inherit-base`, so the call site compiles the head as data; the
    parent then defines it and the child's form has to be rebuilt against the
    definition it can now see.
    """
    parent = space("&psh-inherit-parent")
    rooms.append(parent)
    child = space("&psh-inherit-child", inherits=parent)
    rooms.append(child)

    child.run("(= (psh-inherit-wrap) (psh-inherit-base))")
    assert child.run("!(psh-inherit-wrap)") == [[S["psh-inherit-base"]()]]

    parent.run("(= (psh-inherit-base) from-parent)")
    assert child.run("!(psh-inherit-wrap)") == [[S["from-parent"]]]


@pytest.mark.usefixtures("metta")  # the session engine, whose value these do not read
def test_a_sibling_definition_does_not_move_an_inheriting_spaces_answer(rooms):
    """A name resolves up a space's own chain and never sideways.

    The other half: a sibling space is not on the child's chain, so its
    definition of the same head is invisible here. This held before the cost
    repair too and is the property that makes the narrower invalidation sound.
    """
    parent = space("&psh-sibling-parent")
    rooms.append(parent)
    child = space("&psh-sibling-child", inherits=parent)
    rooms.append(child)
    parent.run("(= (psh-sibling-base) from-parent)")
    child.run("(= (psh-sibling-wrap) (psh-sibling-base))")
    assert child.run("!(psh-sibling-wrap)") == [[S["from-parent"]]]

    sibling = space("&psh-sibling-other")
    rooms.append(sibling)
    sibling.run("(= (psh-sibling-base) from-sibling)")

    assert child.run("!(psh-sibling-wrap)") == [[S["from-parent"]]]
    assert sibling.run("!(psh-sibling-base)") == [[S["from-sibling"]]]


def test_every_space_defining_a_shared_head_still_memoizes_it(metta, rooms):
    """Scoping the recompile to one module must not lose the other modules'.

    The reconciliation now rebuilds the module whose decision moved rather
    than the name everywhere, and each module's decision is its own, so every
    space's copy is memoized on its own account. Without the cache
    `(psh-memo 22)` is the plain exponential; with it every space reads the
    same linear count.
    """
    equation = _fibonacci("psh-memo")
    counts = []
    for index in range(4):
        room = space(f"&psh-memo-room-{index}")
        rooms.append(room)
        room.run(equation)
        room.run("!(import! (context-space) (library lib_memo))")
        assert room.run("!(is-memoized psh-memo)") == [[True]]
        with metta.stats() as block:
            assert room.run("!(psh-memo 22)") == [[17711]]
        counts.append(block.inferences)
    assert counts[-1] <= counts[0] * (1 + BAND), (
        f"(psh-memo 22) cost {counts[0]} inferences in the first space and "
        f"{counts[-1]} in the fourth, so a later space lost the cache: {counts}"
    )
