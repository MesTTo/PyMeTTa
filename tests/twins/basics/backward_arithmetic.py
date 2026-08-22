"""The Python twin of examples/basics/backward_arithmetic.metta.

`+ - * /` are RELATIONS: give any two of the three and the engine solves for
the third, so a function written forwards reads backwards for free. Past one
unknown the rearrangement runs out and a constraint begins, which is what the
`#` family is for.

Nothing here needs a new door. `@m.define` writes the two equations, `let`
and `collapse` are ordinary terms, and the expected values are terms too.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 40672 to 40680, +8, and this one is
#: UNATTRIBUTED: it reproduces byte-stably across three runs and survives an
#: A/B of both candidate causes (the lib_json/lib_file/lib_thread counter
#: change and this file's own comment block each measure identically either
#: way), and engine/metta.pl is byte-identical to the tree the earlier figure
#: was taken on. Ten of the eighteen twins moved by exactly eight and
#: constraint_domains by forty-eight, which is the shape of the +/-8
#: instruction-layout floor this tree records elsewhere rather than a cost.
#: Pinned at the reproducible reading. Prior: #: RE-PINNED 2026-08-22, 40698 to 40672, -26, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 40044 to 40698, +654 (+1.63%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
BUDGET = 40680


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def double(x):
        # (= (double $x) (* 2 $x))
        return 2 * x

    # !(test (double 5) 10)
    yield m.eval(S.test(double(5), 10))
    # !(test (let 10 (double $x) $x) 5)
    yield m.eval(S.test(S["let"](10, double(V.x), V.x), 5))

    # Each operator solves for its one unbound slot.
    # !(test (let 5 (+ $p 2) $p) 3)
    yield m.eval(S.test(S["let"](5, S["+"](V.p, 2), V.p), 3))
    # !(test (let 12 (* $q 4) $q) 3)
    yield m.eval(S.test(S["let"](12, S["*"](V.q, 4), V.q), 3))
    # !(test (let 6 (- $r 4) $r) 10)
    yield m.eval(S.test(S["let"](6, S["-"](V.r, 4), V.r), 10))
    # !(test (let 3 (/ $s 4) $s) 12)
    yield m.eval(S.test(S["let"](3, S["/"](V.s, 4), V.s), 12))

    # No integer answers it, so it FAILS rather than erroring: the empty
    # collapse IS the answer.
    # !(test (collapse (let 7 (double $x) $x)) ())
    yield m.eval(S.test(S["collapse"](S["let"](7, double(V.x), V.x)), expr()))

    @m.define
    def square(x):
        # (= (square $x) (* $x $x))
        return x * x

    # A nonlinear inverse is posted to CLP(FD) and labelled, so it answers
    # every solution rather than one.
    # !(test (collapse (let 25 (square $x) $x)) (noeval (-5 5)))
    yield m.eval(
        S.test(
            S["collapse"](S["let"](25, square(V.x), V.x)),
            S.noeval(expr(-5, 5)),
        )
    )
    # !(test (collapse (let 25 (* $x $y) ($x $y))) (noeval ((-25 -1) ...)))
    yield m.eval(
        S.test(
            S["collapse"](S["let"](25, S["*"](V.x, V.y), expr(V.x, V.y))),
            S.noeval(
                expr(
                    expr(-25, -1),
                    expr(-5, -5),
                    expr(-1, -25),
                    expr(1, 25),
                    expr(5, 5),
                    expr(25, 1),
                )
            ),
        )
    )

    # Bounding the unknown first is what the refusal asks for, and the `#`
    # family is how a MeTTa program bounds one.
    # !(test (collapse (let True (#>= $x 0) (let 25 (square $x) $x))) (5))
    yield m.eval(
        S.test(
            S["collapse"](
                S["let"](TRUE, S["#>="](V.x, 0), S["let"](25, square(V.x), V.x))
            ),
            expr(5),
        )
    )

    # THE LIMIT: ordinary evaluation is inside-out, so a composed backward
    # query reaches the inner operation with two unknowns. The `#` operators
    # POST rather than solve, so the inner constraint waits.
    # !(test (let 20 (#* (#+ $a 1) 4) $a) 4)
    yield m.eval(S.test(S["let"](20, S["#*"](S["#+"](V.a, 1), 4), V.a), 4))

    # Integer division, remainder, and the two extremes.
    # !(test (#div 13 4) 3)
    yield m.eval(S.test(S["#div"](13, 4), 3))
    # !(test (#mod 13 4) 1)
    yield m.eval(S.test(S["#mod"](13, 4), 1))
    # !(test (#min 3 7) 3)
    yield m.eval(S.test(S["#min"](3, 7), 3))
    # !(test (#max 3 7) 7)
    yield m.eval(S.test(S["#max"](3, 7), 7))

    # All six comparisons.
    # !(test (#< 1 2) True)
    yield m.eval(S.test(S["#<"](1, 2), TRUE))
    # !(test (#< 2 1) False)
    yield m.eval(S.test(S["#<"](2, 1), FALSE))
    # !(test (#> 2 1) True)
    yield m.eval(S.test(S["#>"](2, 1), TRUE))
    # !(test (#= 3 3) True)
    yield m.eval(S.test(S["#="](3, 3), TRUE))
    # !(test (#\= 3 4) True)
    yield m.eval(S.test(S[r"#\="](3, 4), TRUE))
    # !(test (#=< 1 2) True)
    yield m.eval(S.test(S["#=<"](1, 2), TRUE))
    # !(test (#=< 2 1) False)
    yield m.eval(S.test(S["#=<"](2, 1), FALSE))
    # !(test (#>= 2 1) True)
    yield m.eval(S.test(S["#>="](2, 1), TRUE))
    # !(test (#>= 1 2) False)
    yield m.eval(S.test(S["#>="](1, 2), FALSE))

    # Composed, and still solvable backwards through two constraints.
    # !(test (let 20 (#* (#+ $a 1) 4) $a) 4)
    yield m.eval(S.test(S["let"](20, S["#*"](S["#+"](V.a, 1), 4), V.a), 4))
