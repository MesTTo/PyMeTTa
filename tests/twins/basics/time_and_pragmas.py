"""The Python twin of examples/basics/time_and_pragmas.metta: bounds and time.

`timeout`, `elapsed`, `inferences` and `with-pragma!` are special forms: their
expression must reach them UNEVALUATED. A built term is unevaluated by
construction, so the term door is the natural Python spelling for all four
and there is nothing to quote.

One form of this file is DECLINED and the residue table says why: `!(bounded-
factorial 5)` answers `(120 (Error -3 StackOverflow))` because the two
equations are non-exclusive and `max-stack-depth` stops the runaway branch.
Writing the two equations is not the problem, `m += S["="](head, body)` does
that; the problem is that no zero-string evaluation door OPENS A FUEL SCOPE,
so from Python the runaway branch overflows Prolog's stack instead of
answering the error atom.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 48356 to 43530, -4826 (-9.98%), by
#: INLINING the fuel charge into the compiled clause instead of calling a
#: shared petta_fuel_step/2. The cost of a charged reduction is a
#: compile-time constant, so the charge is BUILT where the call used to be
#: emitted and the constant lands as a literal in the subtraction: six
#: inferences per charged reduction become four, and the drop tracks each
#: twin's charged-reduction count rather than its size. Prior: #: RE-PINNED 2026-08-22, 48348 to 48356, +8, and this one is
#: UNATTRIBUTED: it reproduces byte-stably across three runs and survives an
#: A/B of both candidate causes (the lib_json/lib_file/lib_thread counter
#: change and this file's own comment block each measure identically either
#: way), and engine/metta.pl is byte-identical to the tree the earlier figure
#: was taken on. Ten of the eighteen twins moved by exactly eight and
#: constraint_domains by forty-eight, which is the shape of the +/-8
#: instruction-layout floor this tree records elsewhere rather than a cost.
#: Pinned at the reproducible reading. Prior: #: RE-PINNED 2026-08-22, 48376 to 48348, -28, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 39521 to 48376, +8855 (+22.41%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
#: RE-PINNED 2026-08-22, 43530 to 44687, at P14.17 automatic tabling: spin
#: and bounded-factorial publish their recursive call heads and both
#: single-call bodies are declined; +1157, re-measured min-of-three
#: fresh-process.
#: RE-PINNED 2026-08-22, 44687 to 44789, at P14.17 per-function invalidation:
#: indexed ground event clauses replace the shared guarded handler and add
#: 102 inferences across the two definitions; min-of-three fresh-process.
BUDGET = 44789


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (spin $n) (if (> $n 0) (spin (- $n 1)) done))
    # Written at the container door because `done` is a lowercase SYMBOL: a
    # compiled body resolves a lowercase free name as a function and reads a
    # capitalised one as a constructor, so it has no spelling for this atom.
    spin = S.spin
    m += S["="](
        spin(V.n), S["if"](S[">"](V.n, 0), spin(S["-"](V.n, 1)), S.done)
    )

    # A bound that is not reached is invisible.
    # !(test (timeout 30 (spin 100)) done)
    yield m.eval(S.test(S["timeout"](30, spin(100)), S.done))
    # !(test (timeout 30 (+ 1 2)) 3)
    yield m.eval(S.test(S["timeout"](30, S["+"](1, 2)), 3))

    # Bounding an expression does NOT collapse it to one answer.
    # !(test (collapse (timeout 30 (superpose (1 2 3)))) (1 2 3))
    yield m.eval(
        S.test(
            S["collapse"](S["timeout"](30, S["superpose"](expr(1, 2, 3)))),
            expr(1, 2, 3),
        )
    )

    # elapsed answers (Value Seconds); only the value is asserted.
    # !(test (car-atom (elapsed (spin 100))) done)
    yield m.eval(S.test(S["car-atom"](S["elapsed"](spin(100))), S.done))
    # !(test (sleep 0.01) True)
    yield m.eval(S.test(S["sleep"](0.01), TRUE))

    # metta/3 interprets an atom in a named space; evalc already is that.
    # !(test (metta (+ 1 2) %Undefined% &self) 3)
    yield m.eval(
        S.test(S["metta"](S["+"](1, 2), S["%Undefined%"], S["&self"]), 3)
    )
    # !(test (evalc (+ 1 2) &self) 3)
    yield m.eval(S.test(S["evalc"](S["+"](1, 2), S["&self"]), 3))

    # Pragmas. Each answers the unit value ().
    # !(test (pragma! max-time 30) ())
    yield m.eval(S.test(S["pragma!"](S["max-time"], 30), expr()))
    # !(test (pragma! max-inferences 100000000) ())
    yield m.eval(S.test(S["pragma!"](S["max-inferences"], 100000000), expr()))
    # !(test (pragma! max-time none) ())
    yield m.eval(S.test(S["pragma!"](S["max-time"], S.none), expr()))
    # !(test (pragma! max-inferences none) ())
    yield m.eval(S.test(S["pragma!"](S["max-inferences"], S.none), expr()))

    # max-stack-depth answers its own error rather than raising.
    # !(test (pragma! max-stack-depth 0) ())
    yield m.eval(S.test(S["pragma!"](S["max-stack-depth"], 0), expr()))
    # !(test (pragma! max-stack-depth -1)
    #        (Error (pragma! max-stack-depth -1) UnsignedIntegerIsExpected))
    yield m.eval(
        S.test(
            S["pragma!"](S["max-stack-depth"], -1),
            S.Error(
                S["pragma!"](S["max-stack-depth"], -1),
                S.UnsignedIntegerIsExpected,
            ),
        )
    )
    # !(test (pragma! max-stack-depth none) ())
    yield m.eval(S.test(S["pragma!"](S["max-stack-depth"], S.none), expr()))

    # !(pragma! max-stack-depth 20) answers (())
    yield m.eval(S["pragma!"](S["max-stack-depth"], 20))

    # The two equations are NON-EXCLUSIVE: both apply at 0, which is what
    # makes the runaway branch reachable. `@m.define`'s stacked clauses
    # would derive a first-match guard and prune it, so the container door
    # writes them as the atoms they are.
    # (= (bounded-factorial 0) 1)
    m += S["="](S["bounded-factorial"](0), 1)
    # (= (bounded-factorial $n) (* $n (bounded-factorial (- $n 1))))
    m += S["="](
        S["bounded-factorial"](V.n),
        S["*"](V.n, S["bounded-factorial"](S["-"](V.n, 1))),
    )
    # !(bounded-factorial 5) answers (120 (Error -3 StackOverflow)).
    # Twinnable since P14.8: m.eval opens the same fuel scope a runnable form
    # opens, so max-stack-depth bounds the runaway branch here too and the
    # base case keeps its answer.
    yield m.eval(S["bounded-factorial"](5))

    # !(pragma! max-stack-depth none) answers (())
    yield m.eval(S["pragma!"](S["max-stack-depth"], S.none))

    # (inferences $n $expr) is timeout's deterministic twin.
    # !(test (inferences 100000 (spin 100)) done)
    yield m.eval(S.test(S["inferences"](100000, spin(100)), S.done))
    # !(test (collapse (inferences 100000 (superpose (1 2 3)))) (1 2 3))
    yield m.eval(
        S.test(
            S["collapse"](S["inferences"](100000, S["superpose"](expr(1, 2, 3)))),
            expr(1, 2, 3),
        )
    )

    # with-pragma! scopes settings to ONE expression.
    # !(test (with-pragma! ((max-inferences 100000)) (+ 20 22)) 42)
    yield m.eval(
        S.test(
            S["with-pragma!"](
                expr(expr(S["max-inferences"], 100000)), S["+"](20, 22)
            ),
            42,
        )
    )
    # !(test (with-pragma! ((max-time 30) (max-inferences 100000)) (spin 100)) done)
    yield m.eval(
        S.test(
            S["with-pragma!"](
                expr(
                    expr(S["max-time"], 30),
                    expr(S["max-inferences"], 100000),
                ),
                spin(100),
            ),
            S.done,
        )
    )
    # !(test (spin 2000) done)
    yield m.eval(S.test(spin(2000), S.done))

    # Relational integer arithmetic: one unbound argument solves for itself.
    # !(test (let 4 (- $x 1) $x) 5)
    yield m.eval(S.test(S["let"](4, S["-"](V.x, 1), V.x), 5))
    # !(test (let 10 (+ $x 3) $x) 7)
    yield m.eval(S.test(S["let"](10, S["+"](V.x, 3), V.x), 7))
    # !(test (let 6 (* $x 2) $x) 3)
    yield m.eval(S.test(S["let"](6, S["*"](V.x, 2), V.x), 3))
    # !(test (let 3 (/ $x 2) $x) 6)
    yield m.eval(S.test(S["let"](3, S["/"](V.x, 2), V.x), 6))
    # !(test (collapse (let 7 (* $x 2) $x)) ())
    yield m.eval(S.test(S["collapse"](S["let"](7, S["*"](V.x, 2), V.x)), expr()))
