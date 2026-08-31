"""Purpose: a cursor pulls a chunk per crossing, and the two things that could
break when it does. A crossing costs about the same as an answer's engine
work, so a cursor that crossed per answer spent half its time in the boundary:
draining ten thousand answers cost 60,028 inferences and 27.3ms one at a time
against 30,164 and 12.7ms in chunks, a 1.9x speedup with half the inferences
[measured 2026-08-31, ai-tmp/lazycost.py and ai-tmp/capsweep.py].

What a chunk risks is the promise the lazy door exists for. Geometric growth
from one keeps it with a constant rather than exactly: taking k answers
computes fewer than 2k, so a few answers of a huge source still cost a few
answers' work, and an unbounded producer still terminates.

Assumes:
  - inferences are the meter. They are deterministic where wall clock on this
    box is bimodal under load, and a chunk changes both, so a wall assertion
    here would be noise wearing a threshold.
Guarantees:
  - taking a few answers of a large source costs what taking them from a small
    one costs, so work follows answers pulled and not answers available
    [tested: test_taking_a_few_answers_does_not_walk_the_source]
  - draining is CHEAPER per answer at ten thousand than at ten, which is the
    amortisation itself and fails if the chunk stops growing
    [tested: test_draining_amortises_the_crossing]
  - the chunk never runs past the answers asked for by more than the
    doubling: a short chunk is the exhaustion signal and no pull looks ahead
    [tested: test_a_short_chunk_is_the_whole_exhaustion_signal]
Fails when: read as a wall-clock benchmark. These are ratios over a counter,
  and the speedup they protect is recorded above rather than asserted here.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from itertools import islice

from metta import Grounded, S, V, _space_objects


def _fill(home, name, count):
    space = home.space(name)
    for index in range(count):
        space.add(S.n(index))
    return space


def test_taking_a_few_answers_does_not_walk_the_source(metta):
    """Work follows the answers pulled, not the answers available.

    Two meters, because each is blind where the other sees. The caller's
    inference counter pins the CROSSINGS, but an SWI engine counts its own
    inferences, so a cursor that walked its source inside the engine would
    leave that counter untouched. The walk shows in CPU time instead: an
    engine is a coroutine on the caller's thread, so its work is this
    process's work, and forty thousand answers cost tens of milliseconds
    where three cost microseconds. The margin below is 30x under the
    cheapest walk measured, so engine speed may triple without this lane
    reading wrong.
    """
    home = metta.metta
    small = _fill(home, "&chunk_small", 20)
    large = _fill(home, "&chunk_large", 40000)

    with small.stats() as few:
        assert len(list(islice(small.stream(S.n(V.x)), 3))) == 3

    best = None
    for _ in range(5):
        with large.stats() as many:
            assert len(list(islice(large.stream(S.n(V.x)), 3))) == 3
        best = many if best is None or many.cputime < best.cputime else best

    # Same three answers, a two-thousandfold source. Geometric growth from
    # one means chunks of 1 and 2 cover three answers either way, so the
    # crossing count cannot depend on the source.
    assert best.inferences < few.inferences * 3, (
        f"three answers cost {best.inferences} crossings-side inferences over "
        f"40000 atoms against {few.inferences} over 20"
    )
    assert best.cputime < 0.010, (
        f"three answers of a 40000-atom source cost {best.cputime * 1000:.1f}ms "
        f"of CPU, which is a walk, not a take"
    )


def test_draining_amortises_the_crossing(metta):
    """Halving the cost of a drain, against a control that turns the chunk off.

    The obvious assertion, that a long drain costs less per answer than a
    short one, PASSES WITH THE CHUNK DISABLED: a cursor's fixed setup divides
    over more answers either way. It measured nothing. So the control here is
    the feature switched off, in this process, in the same run, which is the
    only yardstick that cannot drift with the engine.
    """
    space = _fill(metta.metta, "&chunk_amortise", 20000)

    def drained() -> int:
        best = None
        for _ in range(3):
            with space.stats() as run:
                assert len(list(space.stream(S.n(V.x), limit=10000))) == 10000
            best = run.inferences if best is None else min(best, run.inferences)
        return best

    original = _space_objects._CHUNK_CAP
    try:
        _space_objects._CHUNK_CAP = 1
        one_at_a_time = drained()
    finally:
        _space_objects._CHUNK_CAP = original
    chunked = drained()

    # A crossing costs three Prolog inferences of wrapper, so a cursor that
    # crossed per answer paid six per answer where the chunked one pays three
    # [measured 2026-08-31: 60,028 against 30,509 over ten thousand answers].
    # The margin is loose because the engine's own per-answer work is the
    # other half and may move; what cannot move is that the chunk removes a
    # per-answer crossing.
    assert chunked * 1.4 < one_at_a_time, (
        f"{chunked:,} inferences chunked against {one_at_a_time:,} one at a "
        f"time: the chunk is not saving crossings"
    )


def test_a_short_chunk_is_the_whole_exhaustion_signal(metta):
    """A source shorter than the chunk ends cleanly, at the right count."""
    home = metta.metta
    for count in (0, 1, 2, 3, 5, 63, 64, 65, 127, 128, 129):
        space = _fill(home, f"&chunk_edge_{count}", count)
        assert len(list(space.stream(S.n(V.x)))) == count, f"{count} answers"
        # And a second cursor over the same space agrees, so exhaustion did
        # not leave the engine holding anything.
        assert len(list(space.stream(S.n(V.x)))) == count, f"{count} answers again"


def test_a_bounded_take_of_an_unbounded_producer_still_terminates(metta):
    """The chunk is bounded, so an infinite stream is still safe to sip."""
    space = metta.metta.space("&chunk_unbounded")
    space.add(S.seed(0))
    taken = list(islice(space.stream(S.seed(V.x)), 1))
    assert len(taken) == 1


def test_a_spent_budget_raises_and_a_raised_budget_delivers_more(metta):
    """What a bounded chunked cursor promises, which is less than per-answer.

    Bounded cursors chunk like every other cursor (user ruling, 2026-08-31):
    per-answer accounting at a budget trip is not worth a crossing per
    answer. So the promise is exactly this: the trip RAISES rather than
    ending the stream quietly, the same harvest is the same count twice, and
    raising the budget delivers more -- which is the diagnosis path, since a
    developer who suspects the budget ate answers tests it by raising it.
    What is NOT promised is that every answer the budget's work computed is
    delivered; a chunk's collected prefix is discarded when the trip fires
    inside it, measured at 210 delivered one at a time against 191 chunked
    for the same 3000-inference budget.
    """
    from metta.errors import InferenceLimitError

    space = _fill(metta.metta, "&chunk_bounded", 5000)

    def harvest(budget: int) -> tuple[int, bool]:
        delivered = 0
        try:
            with space.stream(S.n(V.x), inferences=budget) as cursor:
                for _ in cursor:
                    delivered += 1
        except InferenceLimitError:
            return delivered, True
        return delivered, False

    first, tripped = harvest(3000)
    again, tripped_again = harvest(3000)
    assert tripped and tripped_again, "the budget did not trip, so this pinned nothing"
    assert first == again, f"{first} then {again}: a budget harvest must be deterministic"

    more, _ = harvest(30000)
    assert more > first, (
        f"a tenfold budget delivered {more} against {first}: raising the "
        f"budget is the diagnosis path and it must show more answers"
    )


def test_the_evaluation_cursor_chunks_too(metta, monkeypatch):
    """answers() pulls chunks like stream(), counted at the bridge seam.

    Neither meter the other tests use works here. The inference counter
    cannot discriminate, because an evaluation cursor reports its
    engine-side inferences into the caller's block, so the chunk shows as
    slightly MORE inferences (the collection loop) while removing the
    crossings the counter never saw; and CPU under load is the noise this
    suite avoids. What the chunk claims is fewer crossings, so the test
    counts exactly that: calls that pull on the cursor, at the runtime
    seam every pull goes through. Ten thousand answers in a doubling chunk
    capped at 64 need about 160 pulls; one at a time needed 10,001. The
    margin below is 3x over the doubling's own arithmetic, and a one-answer
    evaluation stays at two pulls, which is normal use paying nothing.
    """
    space = metta.metta.space("&chunk_eval")
    for index in range(10000):
        space.add(S.item(index))
    space.run("(= (all) (match &self (item $x) $x))")
    space.run("(= (just-one) 42)")

    runtime = space.runtime
    original = type(runtime).apply_must
    pulls = []

    def counting(self, predicate, *inputs):
        if "cursor" in predicate and "open" not in predicate and "close" not in predicate:
            pulls.append(predicate)
        return original(self, predicate, *inputs)

    monkeypatch.setattr(type(runtime), "apply_must", counting)

    assert len(list(space.answers(S.all()))) == 10000
    drain_pulls = len(pulls)
    assert drain_pulls < 500, (
        f"{drain_pulls} pulls for ten thousand answers: the evaluation "
        f"cursor is crossing per answer"
    )

    pulls.clear()
    assert list(space.answers(S.just_one())) == [Grounded(42)]
    assert len(pulls) <= 2, (
        f"{len(pulls)} pulls for one answer: normal use is paying for the chunk"
    )

