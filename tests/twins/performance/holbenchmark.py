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
must be a literal" [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT: two
`@m.define`s whose parameters carry the patterns, the way the equations do.
Residue P14.4.

The recursive list builders name every value before passing it to `cons`.
Rules-bundle bodies build the stored `let` terms; compiled bodies use plain
assignment, which lowers to `let*`.
[source: examples/performance/holbenchmark.metta:1; commit=WORKTREE]

Each claim states its own branch allowance above the evaluator's 100000
default, which is a term because `m.limits` bounds inferences and time and not
stack depth (residue, P14.14). It is load-bearing for the compiled kernels
twice over: a compiled `if` wraps its condition in `py-truthy` and `==` lowers
to `py-eq`, so every level of these million-step recursions spends reductions
the original does not.
"""

from metta import S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1

#: `(+ 1)`, the partially applied increment all four kernels are driven with. A
#: one-argument application has no operator spelling, so it is the tuple MeTTa
#: writes it as.
INC = S.add(1)

#: The branch allowance these million-step kernels state above the evaluator's
#: 100000 default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S.max_stack_depth(100_000_000),)


def twin(m):
    """Four higher-order kernels, each run to a million steps."""
    # A map that flattens as it goes, over a cons list built by counting down.
    m += equation(S.map_flat(V.f, ())).to(())  # rung: a compiled head pattern may only be a literal default
    m += equation(S.map_flat(V.f, S.cons(V.x, V.xs))).to(  # rung: as above
        S.let(  # rung: this rules body has no Python statement position for the required binding
            V.head,
            (V.f, V.x),
            S.let(  # rung: the recursive value must be named before cons receives its Expression-typed tail
                V.rest,
                S.map_flat(V.f, V.xs),
                S.cons(V.head, V.rest),
            ),
        )
    )

    # The define door applies rung 4's underscore map like every other door,
    # so a hyphenated MeTTa name needs nothing said twice. This one still
    # takes `name=`: `range` is a Python builtin, so the def carries rung 2's
    # trailing underscore, which the map would turn into a trailing hyphen.
    # `def range` would consume the gate's zero A-family headroom and report
    # `P0.13 suppression burn-down increased (observed, maximum): {'N': (37,
    # 35), 'A': (9, 8)}`; it would also redirect recursion to `py-range`.
    @m.define(name="range")
    def range_(n):
        if n == 0:
            return ()
        rest = range_(n - 1)
        return S.cons(n, rest)

    assert m.fn.with_pragma(DEEP, S.length(S.map_flat(INC, S.range(1_000_000)))).one() == 1_000_000

    # A fold that recurses into nested expressions rather than over them.
    m += equation(S.fold_nested(V.f, V.init, ())).to(V.init)  # rung: as above
    m += equation(S.fold_nested(V.f, V.init, S.cons(V.x, V.xs))).to(  # rung: as above
        if_(S.is_expr(V.x),  # rung: the stored body of an equation the decorator cannot compile
            S.fold_nested(V.f, S.fold_nested(V.f, V.init, V.x), V.xs),
            S.fold_nested(V.f, (V.f, V.init, V.x), V.xs)))

    @m.define
    def deep_nest(n):
        if n == 0:
            return ()
        row = fn.range(50)
        rest = deep_nest(n - 1)
        return S.cons(row, rest)

    assert m.fn.with_pragma(
        DEEP, S.fold_nested(S.add, 0, S.deep_nest(20_000))
    ).one() == 25_500_000

    # A hundred thousand applications of one function to one value.
    @m.define
    def apply_many(f, n, x):
        if n == 0:
            return x
        return apply_many(f, n - 1, f(x))

    assert m.fn.with_pragma(DEEP, S.apply_many(INC, 100_000, 0)).one() == 100_000

    # And a polynomial sum, which applies the parameter inside an addition.
    @m.define
    def poly(f, n):
        if n == 0:
            return 0
        return f(n) + poly(f, n - 1)

    assert m.fn.with_pragma(DEEP, S.poly(INC, 1_000_000)).one() == 500_001_500_000
