"""The Python twin of examples/control/metta4_streams.metta: a stream and its consumers.

This is the file the phase's deepest claim is about. `range` is a Python
GENERATOR, and the equation it compiles to is the original's, term for term:

    if k < n:                  -->  (if (< $K $N)
        yield k                -->      (superpose ($K
        yield counter(k + 1, n)-->                 (range (+ $K 1) $N)))
                               -->      (empty))

**Each `yield` is one answer, which is what `superpose` spells**, and an `if`
with no `else` contributes `(empty)`, so the base case needs no writing. Then
`forall` runs the stream to exhaustion, `once` commits to its first answer, and
`foldall` folds over it: three consumers, one producer, and the producer is an
ordinary Python function.

The recursive call deliberately uses `yield from counter(...)`. The compiler
knows self-recursion is nondeterministic even before registration and delegates
the call whole. Other engine calls whose cardinality is unknown are refused
with the two explicit spellings, so the old silent child splice cannot recur.
`gen`'s three clauses fix nothing, so they are written at the container door,
where non-exclusive equations on one head live.

The Python function is `counter` because `range` is a Python BUILTIN: a
compiled body lowers a call to one before it looks for the definition's own
name, so a function actually called `range` would compile its own recursion to
`py-range`.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10685 to 11690, +1005, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 10685 by 47554fc's control/types twin baseline.
BUDGET = 11690


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define(name="range")
    def counter(k, n):
        # (= (range $K $N)
        #    (if (< $K $N)
        #        (superpose ($K (range (+ $K 1) $N)))
        #        (empty)))
        if k < n:
            yield k
            yield from counter(k + 1, n)

    # Add every range item to space &s1 using metta4's for; an item
    # returning false "breaks" the loop.
    # !(forall (range 1 5) (|-> ($x) (add-atom &s1 (num $x)))) answers (True)
    yield m.eval(
        S["forall"](
            S["range"](1, 5),
            S["|->"](
                expr(V.x), S["add-atom"](S["&s1"], S.num(V.x))
            ),
        )
    )

    # Add only one committed option.
    # !(let $x (once (range 1 5)) (add-atom &s2 (num $x))) answers (())
    yield m.eval(
        S["let"](
            V.x,
            S["once"](S["range"](1, 5)),
            S["add-atom"](S["&s2"], S.num(V.x)),
        )
    )

    # !(test (collapse (get-atoms &s1)) ((num 1) (num 2) (num 3) (num 4)))
    yield m.eval(
        S.test(
            S["collapse"](S["get-atoms"](S["&s1"])),
            expr(S.num(1), S.num(2), S.num(3), S.num(4)),
        )
    )

    # !(test (collapse (get-atoms &s2)) ((num 1)))
    yield m.eval(
        S.test(
            S["collapse"](S["get-atoms"](S["&s2"])), expr(S.num(1))
        )
    )

    # (= (gen) 1)
    m += S["="](S.gen(), 1)
    # (= (gen) 2)
    m += S["="](S.gen(), 2)
    # (= (gen) 3)
    m += S["="](S.gen(), 3)

    # !(test (foldall (|-> ($x $y) (+ $x $y)) (gen) 0) 6)
    yield m.eval(
        S.test(
            S["foldall"](
                S["|->"](expr(V.x, V.y), S["+"](V.x, V.y)),
                S.gen(),
                0,
            ),
            6,
        )
    )
