"""Purpose: examples/performance/holbenchmark.metta in Python: four million-step kernels.

A map over a million-long cons list, a fold over a nested one, a hundred
thousand applications of one function, and a polynomial sum. All four are
higher-order: the function being applied arrives as an argument and is called
through a variable.

Applying a parameter is Python's own call syntax now, `f(x)` lowering to
`($f $x)`, so `apply-many` and `poly` are ordinary functions under the
decorator, and so are the two list builders `range` and `deep-nest`, whose
empty-expression base case is Python's `()`.

`map-flat` and `fold-nested` stay at the container door for a blocker the
subset still has: each is two clauses that destructure in the HEAD, `()` and
`(cons $x $xs)`, and a compiled head pattern may only be a LITERAL default, so
a structural default is refused with "a default here is a head pattern, so it
must be a literal" [measured 2026-08-23; commit=WORKTREE]. PERFECT: two
`@m.define`s whose parameters carry the patterns, the way the equations do.
Residue P14.4.

Each claim states its own branch allowance above the evaluator's 100000
default, which is a term because `m.limits` bounds inferences and time and not
stack depth (residue, P14.14). It is load-bearing for the compiled kernels
twice over: a compiled `if` wraps its condition in `py-truthy` and `==` lowers
to `py-eq`, so every level of these million-step recursions spends reductions
the original does not.
"""

from petta import S, V, equation, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1

#: `(+ 1)`, the partially applied increment all four kernels are driven with. A
#: one-argument application has no operator spelling, so it is the tuple MeTTa
#: writes it as.
INC = (S["+"], 1)

#: The branch allowance these million-step kernels state above the evaluator's
#: 100000 default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S["max-stack-depth"](100_000_000),)


def twin(m):
    """Four higher-order kernels, each run to a million steps."""
    # A map that flattens as it goes, over a cons list built by counting down.
    m += equation(S["map-flat"](V.f, ())).to(())  # rung: a compiled head pattern may only be a literal default
    m += equation(S["map-flat"](V.f, S.cons(V.x, V.xs))).to(  # rung: as above
        S.cons((V.f, V.x), S["map-flat"](V.f, V.xs))
    )

    # DEFECT: the descent ladder documents rung 4 as TOTAL in both
    # directions, "def not_provable lands as not-provable", and the define
    # door does not apply it: `def find_divisor` lands as `find_divisor`
    # [measured 2026-08-23; commit=WORKTREE]. So every hyphenated MeTTa name
    # below states itself through `name=`. PERFECT: the map applies at the
    # define door the way it applies at the S, V and fn factories, and only
    # a name Python cannot spell at all needs `name=` -- here `range`, which
    # is a Python builtin, so the def takes rung 2's trailing underscore.
    @m.define(name="range")
    def range_(n):
        if n == 0:
            return ()
        return S.cons(n, range_(n - 1))

    assert m.eval(
        S["with-pragma!"](DEEP, S.length(S["map-flat"](INC, S.range(1_000_000))))
    ) == [1_000_000]

    # A fold that recurses into nested expressions rather than over them.
    m += equation(S["fold-nested"](V.f, V.init, ())).to(V.init)  # rung: as above
    m += equation(S["fold-nested"](V.f, V.init, S.cons(V.x, V.xs))).to(  # rung: as above
        S["if"](S["is-expr"](V.x),  # rung: the stored body of an equation the decorator cannot compile
                S["fold-nested"](V.f, S["fold-nested"](V.f, V.init, V.x), V.xs),
                S["fold-nested"](V.f, (V.f, V.init, V.x), V.xs)))

    @m.define(name="deep-nest")
    def deep_nest(n):
        if n == 0:
            return ()
        return S.cons(fn.range(50), deep_nest(n - 1))

    assert m.eval(
        S["with-pragma!"](DEEP, S["fold-nested"](S["+"], 0, S["deep-nest"](20_000)))
    ) == [25_500_000]

    # A hundred thousand applications of one function to one value.
    @m.define(name="apply-many")
    def apply_many(f, n, x):
        if n == 0:
            return x
        return apply_many(f, n - 1, f(x))

    assert m.eval(S["with-pragma!"](DEEP, S["apply-many"](INC, 100_000, 0))) == [100_000]

    # And a polynomial sum, which applies the parameter inside an addition.
    @m.define
    def poly(f, n):
        if n == 0:
            return 0
        return f(n) + poly(f, n - 1)

    assert m.eval(S["with-pragma!"](DEEP, S.poly(INC, 1_000_000))) == [500_001_500_000]
