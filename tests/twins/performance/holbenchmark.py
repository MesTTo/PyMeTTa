"""examples/performance/holbenchmark.metta in Python: four million-step kernels.

A map over a million-long cons list, a fold over a nested one, a hundred
thousand applications of one function, and a polynomial sum. All four are
higher-order: the function being applied arrives as an argument and is called
through a variable.

Every definition stays in the engine, and the four walls are the ones this
corpus keeps meeting:

- `map-flat` and `fold-nested` destructure in the HEAD, `(cons $x $xs)` and
  `()`, and a compiled clause's head pattern must be a literal;
- all four kernels APPLY a parameter, `($f $x)`, and a compiled body calls a
  plain name, never a variable;
- `range`, `deep-nest`, `apply-many` and `poly` test `(== $n 0)` in the inner
  loop, and Python's `==` in a compiled body lowers to the prelude's `py-eq`,
  re-measured at +71.96% on a search of exactly this shape (superpose_primes.py);
- `fold-nested` names `is-expr`, which is not a Python identifier either.

Each is a residue entry against P14.4. What is left for Python is the four
claims, which are `assert`.
"""

from petta import S, V, equation

#: Why this file sits below the top rung: all four kernels are the benchmark and
#: none of them compiles, for the four reasons the docstring lists.
RUNG = "all four kernels destructure in the head, apply a parameter, test (== $n 0), or name is-expr, and a compiled body can do none of those"

#: `(+ 1)`, the partially applied increment all four kernels are driven with. A
#: one-argument application has no operator spelling, so it is the tuple MeTTa
#: writes it as.
INC = (S["+"], 1)

#: The branch allowance these million-step kernels state above the evaluator's
#: 100000 default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S["max-stack-depth"](100_000_000),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 139184129 to 139183402, -727 (-0.00052%), by the twin
#: contract change: four `test` wrappers left the engine for Python's own
#: `assert`, which is all that could move. The four kernels are the benchmark.
#: Against the example's 139197665 the ratio is 0.9999 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure
#: examples/performance/holbenchmark.metta`]. Prior: ADDED 2026-08-22 at
#: 139184129 by the wave-3 twin baseline.
BUDGET = 139183402


def twin(m):
    """Four higher-order kernels, each run to a million steps."""
    # A map that flattens as it goes, over a cons list built by counting down.
    m += equation(S["map-flat"](V.f, ())).to(())
    m += equation(S["map-flat"](V.f, S.cons(V.x, V.xs))).to(
        S.cons((V.f, V.x), S["map-flat"](V.f, V.xs))
    )
    m += equation(S.range(V.n)).to(
        S["if"](V.n.eq(0), (), S.cons(V.n, S.range(V.n - 1))))

    assert m.eval(
        S["with-pragma!"](DEEP, S.length(S["map-flat"](INC, S.range(1_000_000))))
    ) == [1_000_000]

    # A fold that recurses into nested expressions rather than over them.
    m += equation(S["fold-nested"](V.f, V.init, ())).to(V.init)
    m += equation(S["fold-nested"](V.f, V.init, S.cons(V.x, V.xs))).to(
        S["if"](S["is-expr"](V.x),
                S["fold-nested"](V.f, S["fold-nested"](V.f, V.init, V.x), V.xs),
                S["fold-nested"](V.f, (V.f, V.init, V.x), V.xs)))
    m += equation(S["deep-nest"](V.n)).to(
        S["if"](V.n.eq(0), (), S.cons(S.range(50), S["deep-nest"](V.n - 1))))

    assert m.eval(
        S["with-pragma!"](DEEP, S["fold-nested"](S["+"], 0, S["deep-nest"](20_000)))
    ) == [25_500_000]

    # A hundred thousand applications of one function to one value.
    m += equation(S["apply-many"](V.f, V.n, V.x)).to(
        S["if"](V.n.eq(0), V.x, S["apply-many"](V.f, V.n - 1, (V.f, V.x))))

    assert m.eval(S["with-pragma!"](DEEP, S["apply-many"](INC, 100_000, 0))) == [100_000]

    # And a polynomial sum, which applies the parameter inside an addition.
    m += equation(S.poly(V.f, V.n)).to(
        S["if"](V.n.eq(0),
                0,
                (V.f, V.n) + S.poly(V.f, V.n - 1)))  # noqa: RUF005  -- not tuple concatenation: the right operand is an Expr, so this is Expr.__radd__ building (+ ($f $n) (poly ...))

    assert m.eval(S["with-pragma!"](DEEP, S.poly(INC, 1_000_000))) == [500_001_500_000]
