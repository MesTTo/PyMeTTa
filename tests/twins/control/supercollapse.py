"""The Python twin of examples/control/supercollapse.metta: concatenating tuples.

`TupleConcat` superposes two collapsed tuples back apart and collapses the
result, which is how a program written entirely in answer sets appends. `range`
then builds 1..9 out of nothing but that.

`range` is a computation and is written as one, with two things to notice. The
Python function is `count_from` because `range` is a Python BUILTIN and a
compiled body lowers a call to one before it looks for the definition's own
name, so a function actually called `range` would compile its own recursion to
`py-range`; `name="range"` puts the MeTTa name on the equation and recursion
resolves to it. And `()` is Python's empty tuple, which is the empty
expression, so the base case needs no spelling of its own.

`TupleConcat` is written at the container door: its body is
`(superpose ((superpose $Ev1) (superpose $Ev2)))`, and `superpose(ev1)` in a
compiled body means `(superpose ($ev1))`, one alternative that happens to be
`$ev1`, not the superposition OF `$ev1`. The residue table records that
against P14.4.

The name is bound at module level, `TupleConcat = S.TupleConcat`, and it
has to be that exact spelling: a compiled body resolves a free name EXACTLY,
so `tuple_concat` would reach nothing. Binding it as the symbol rather than as
`m.fn(...)` keeps it at module scope, where CapWords is ordinary Python and
needs no naming suppression, and calling the symbol builds the same term the
equation stores.
"""

from petta import S, V, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `TupleConcat`'s body superposes two BOUND values, and `superpose(ev1)` in a compiled
#: body means `(superpose ($ev1))`, one alternative that happens to be `$ev1`.
RUNG = "container door for TupleConcat: superpose over a bound value has no compiled spelling"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6633 to 7810, +1177, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 6633 by 47554fc's control/types twin baseline.
BUDGET = 7810

#: The MeTTa name, kept verbatim, so the compiled body below can spell it.
TupleConcat = S.TupleConcat


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (TupleConcat $Ev1 $Ev2)
    #    (collapse (superpose ((superpose $Ev1) (superpose $Ev2)))))
    m += equation(TupleConcat(V.first, V.second)).to(
        S.collapse(S.superpose((S.superpose(V.first), S.superpose(V.second))))
    )

    @m.define(name="range")
    def count_from(k, n):
        # (= (range $K $N)
        #    (if (< $K $N)
        #        (TupleConcat ($K) (range (+ $K 1) $N))
        #        ()))
        return TupleConcat((k,), count_from(k + 1, n)) if k < n else ()

    # !(test (range 1 10) (1 2 3 4 5 6 7 8 9))
    yield m.eval(S.test(S.range(1, 10), (1, 2, 3, 4, 5, 6, 7, 8, 9)))
