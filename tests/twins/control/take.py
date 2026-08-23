"""Purpose: examples/control/take.metta in Python: at most k answers.

`take` answers at most k. `once` takes one and collapsing takes all, and
between them there was nothing, while the space seam had the idea one level
down all along in a provider's `match(pattern, limit=)`.

"At most k of a stream" is Python's own slice, and answers are a lazy view, so
every producer below is sliced, the endless one included, and the two match
forms take `limit=`, which the engine applies inside the query rather than
trimming afterwards.

Slicing the endless producer answers the right four numbers and costs
1,500,141 inferences to do it, against 700 for the engine-side
`(take 4 (from 0))`, and the figure does not move with k: the first pull drives
a self-recursive superposition to a fixed internal bound whatever the slice
asks for, so the view is lazy in the answers it hands back and not in the
producer behind them [measured 2026-08-23: 1,500,147 / 1,500,141 / 1,500,141 /
1,500,141 inferences to pull 1, 2, 4 and 8; commit=WORKTREE]. That is the
library's cost to fix, not a reason to write the term: the pull has to suspend
the producer. Filed as residue against P14.4.

A refusal crosses the seam as a Python exception, so `catch` is `except` and
the branch that reads what came back is Python's own.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V
from petta.errors import EngineError

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Bound a finite producer, an endless one, and two queries."""
    letters = S.superpose((S.a, S.b, S.c, S.d, S.e))
    pair = S.superpose((S.a, S.b))

    # !(test (collapse (take 3 (superpose (a b c d e)))) (a b c))
    assert list(m.answers(letters)[:3]) == [S.a, S.b, S.c]

    # Fewer answers than the bound is not an error, and a bound of zero
    # answers nothing, which is what "at most" means.
    # !(test (collapse (take 9 (superpose (a b)))) (a b))
    assert list(m.answers(pair)[:9]) == [S.a, S.b]
    # !(test (collapse (take 0 (superpose (a b)))) ())
    assert list(m.answers(pair)[:0]) == []

    @m.define(name="from")
    def count_up(n):
        # (= (from $n) (superpose ($n (from (+ $n 1)))))
        yield n
        yield from count_up(n + 1)

    # The bound is applied OUTSIDE the producer, so it cuts one that would not
    # stop on its own, and the slice is that bound. This line is why the lane
    # reports a BAND finding on this file, twin 1,510,583 against the example's
    # 16,419 at ratio 92.00: the first pull drives the producer to a fixed
    # internal bound. Writing `m.eval(S.take(4, S["from"](0)))` instead would
    # clear the band at 700 inferences and is the wrong trade, because the
    # spelling is right and the cost is the library's. Residue: P14.4.
    # !(test (collapse (take 4 (from 0))) (0 1 2 3))
    assert list(count_up(0)[:4]) == [0, 1, 2, 3]

    # A count that is not a whole number is a mistake rather than an empty
    # answer, because failing into "there is nothing there" sends you looking
    # at your data.
    # !(test (car-atom (catch (take foo (superpose (a b))))) Error)
    try:
        m.eval(S.take(S.foo, pair))
        refused = None
    except EngineError as error:
        refused = error
    assert refused is not None

    # (edge a b) (edge b c) (edge c d)
    m += S.edge(S.a, S.b)
    m += S.edge(S.b, S.c)
    m += S.edge(S.c, S.d)

    # !(test (collapse (take 2 (match &self (edge $x $y) (edge $x $y))))
    #        ((edge a b) (edge b c)))
    edges = m.query(S.edge(V.x, V.y), limit=2)
    assert [S.edge(row.x, row.y) for row in edges] == [S.edge(S.a, S.b), S.edge(S.b, S.c)]

    # Across a join the bound belongs to the JOINED rows, and an outer match
    # truncated at k would lose the rows its later candidates join to.
    # !(test (collapse (take 2 (match &self (, (edge $x $y) (edge $y $z)) ($x $z))))
    #        ((a c) (b d)))
    paths = m.query(S.edge(V.x, V.y), S.edge(V.y, V.z), limit=2)
    assert [(row.x, row.z) for row in paths] == [(S.a, S.c), (S.b, S.d)]
