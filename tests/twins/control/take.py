"""examples/control/take.metta in Python: at most k answers.

`take` answers at most k. `once` takes one and collapsing takes all, and
between them there was nothing, while the space seam had the idea one level
down all along in a provider's `match(pattern, limit=)`.

That last sentence is also this twin's shape. Where the answers come from a
MATCH, `limit=` is the Python door and the engine applies the bound inside the
query rather than trimming afterwards, so the two match forms below are
ordinary queries. Where they come from evaluating a TERM there is no Python
door at all: `m.query` takes `limit=` and `m.eval` takes none, and slicing the
answers afterwards would not cut a producer that never stops, which is exactly
what `(from 0)` is. Filed as residue against P14.4.

A refusal crosses the seam as a Python exception, so `catch` is `except` and
the branch that reads what came back is Python's own.
"""

from petta import S, V
from petta.errors import EngineError

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9052 to 6072, -2980 (-32.9%), by the twin contract
#: change: the two match forms became `m.query(..., limit=)`, which bounds
#: inside the query rather than trimming afterwards, and `catch`/`car-atom`
#: became Python's `except`; the three bounded superpositions and the bounded
#: endless producer still run in the engine, because `m.eval` takes no bound.
#: Measured min-of-3 over fresh processes with the MORK backend linked in,
#: which the artefact-free worktree omits and which moves a compiled twin by
#: about 10 inferences per definition; against the example's 15846 the ratio
#: is 0.3832. Prior: 9052, the transliterated twin this replaces.
BUDGET = 6072


def twin(m):
    """Bound a finite producer, an endless one, and two queries."""
    letters = S.superpose((S.a, S.b, S.c, S.d, S.e))
    pair = S.superpose((S.a, S.b))

    # !(test (collapse (take 3 (superpose (a b c d e)))) (a b c))
    assert m.eval(S.take(3, letters)) == [S.a, S.b, S.c]

    # Fewer answers than the bound is not an error, and a bound of zero
    # answers nothing, which is what "at most" means.
    # !(test (collapse (take 9 (superpose (a b)))) (a b))
    assert m.eval(S.take(9, pair)) == [S.a, S.b]
    # !(test (collapse (take 0 (superpose (a b)))) ())
    assert m.eval(S.take(0, pair)) == []

    @m.define(name="from")
    def count_up(n):
        # (= (from $n) (superpose ($n (from (+ $n 1)))))
        yield n
        yield from count_up(n + 1)

    # The bound is applied OUTSIDE the producer, so it cuts one that would not
    # stop on its own. Calling `count_up` would never return; the bound has to
    # reach the engine with the term, not after it.
    # !(test (collapse (take 4 (from 0))) (0 1 2 3))
    assert m.eval(S.take(4, S["from"](0))) == [0, 1, 2, 3]

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
