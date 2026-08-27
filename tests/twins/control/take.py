"""Purpose: examples/control/take.metta in Python: at most k answers.

`take` answers at most k. `once` takes one and collapsing takes all, and
between them there was nothing, while the space seam had the idea one level
down all along in a provider's `match(pattern, limit=)`.

"At most k of a stream" is Python's own slice, and answers are a lazy view
that slices back into one, so every producer below is sliced, the endless one
included. `superpose(...)` is the expression-position door for the
alternatives, at the top level where `with m:` names the space it runs in and
inside `from`'s own equation where it is the fork the original writes; and the
two match forms take `limit=`, which the engine applies inside the query rather
than trimming afterwards.

Slicing the endless producer answers the right four numbers and suspends
the producer at the frontier the slice asked for, so the cost moves with k
rather than driving a self-recursive superposition to a fixed internal bound
[measured 2026-08-24: 140 inferences to pull 4 and 210 to pull 8 from
`(= (from $n) (superpose ($n (from (+ $n 1)))))`, where the same slices cost
1,500,141 each before the lazy view landed; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].

A refusal crosses the seam as a Python exception, so `catch` is `except` and
the branch that reads what came back is Python's own.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, superpose
from metta.errors import EngineError


def twin(m):
    """Bound a finite producer, an endless one, and two queries."""
    with m:
        # !(test (collapse (take 3 (superpose (a b c d e)))) (a b c))
        assert list(superpose(S.a, S.b, S.c, S.d, S.e)[:3]) == [S.a, S.b, S.c]

        # Fewer answers than the bound is not an error, and a bound of zero
        # answers nothing, which is what "at most" means.
        # !(test (collapse (take 9 (superpose (a b)))) (a b))
        assert list(superpose(S.a, S.b)[:9]) == [S.a, S.b]
        # !(test (collapse (take 0 (superpose (a b)))) ())
        assert list(superpose(S.a, S.b)[:0]) == []

    @m.define(name="from")
    def count_up(n):
        # (= (from $n) (superpose ($n (from (+ $n 1)))))
        return superpose(n, count_up(n + 1))

    # The bound is applied OUTSIDE the producer, so it cuts one that would not
    # stop on its own, and the slice is that bound.
    # !(test (collapse (take 4 (from 0))) (0 1 2 3))
    assert list(count_up(0)[:4]) == [0, 1, 2, 3]

    # A count that is not a whole number is a mistake rather than an empty
    # answer, because failing into "there is nothing there" sends you looking
    # at your data.
    # !(test (car-atom (catch (take foo (superpose (a b))))) Error)
    try:
        m.eval(S.take(S.foo, S.superpose((S.a, S.b))))
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
    edges = m.match(S.edge(V.x, V.y), limit=2)
    assert [S.edge(row.x, row.y) for row in edges] == [S.edge(S.a, S.b), S.edge(S.b, S.c)]

    # Across a join the bound belongs to the JOINED rows, and an outer match
    # truncated at k would lose the rows its later candidates join to.
    # !(test (collapse (take 2 (match &self (, (edge $x $y) (edge $y $z)) ($x $z))))
    #        ((a c) (b d)))
    paths = m.match(S.edge(V.x, V.y), S.edge(V.y, V.z), limit=2)
    assert [(row.x, row.z) for row in paths] == [(S.a, S.c), (S.b, S.d)]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 6989 to 7008, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 7008 to 7022, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 7022 to 6954, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 6954 to 6964, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 6964 to 6988 (+24), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 6988
