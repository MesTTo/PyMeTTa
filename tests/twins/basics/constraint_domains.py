"""The Python twin of examples/basics/constraint_domains.metta: CLP(Q), CLP(B).

Both solvers take their constraint AS WRITTEN, unevaluated, which is exactly
what a built term is: `S["clpq"](S["="](S["*"](2, V.x), 1))` hands over
`(= (* 2 $x) 1)` without running the multiplication. That is the same reason
the original writes it inside `clpq` rather than letting it evaluate, so the
Python spelling and the MeTTa spelling agree about why.

The two expected values that are strings are `repr` output, compared as
text; `val(...)` says they are data.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 94115


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_constraints)) answers (())
    yield m.eval(S["import!"](S["&self"], expr(S.library, S.lib_constraints)))

    # ---------------------------------------------------------- CLP(Q)
    # Exact rationals. The reader has no rational literal, so 1r2 is
    # asserted through repr.
    # !(test (let True (clpq (= (* 2 $x) 1)) (repr $x)) "1r2")
    yield m.eval(
        S.test(
            S["let"](TRUE, S["clpq"](S["="](S["*"](2, V.x), 1)), S["repr"](V.x)),
            val("1r2"),
        )
    )
    # !(test (let True (clpq (= (* 2 $x) 1)) (* 2 $x)) 1)
    yield m.eval(
        S.test(
            S["let"](TRUE, S["clpq"](S["="](S["*"](2, V.x), 1)), S["*"](2, V.x)),
            1,
        )
    )

    # Entailment: is this constraint already implied by what was posted?
    # !(test (collapse (let True (clpq (>= $a 0)) (clpq-entailed (>= $a 0)))) (True))
    yield m.eval(
        S.test(
            S["collapse"](
                S["let"](
                    TRUE,
                    S["clpq"](S[">="](V.a, 0)),
                    S["clpq-entailed"](S[">="](V.a, 0)),
                )
            ),
            expr(TRUE),
        )
    )
    # !(test (collapse (let True (clpq (>= $b 0)) (clpq-entailed (>= $b 5)))) (False))
    yield m.eval(
        S.test(
            S["collapse"](
                S["let"](
                    TRUE,
                    S["clpq"](S[">="](V.b, 0)),
                    S["clpq-entailed"](S[">="](V.b, 5)),
                )
            ),
            expr(FALSE),
        )
    )

    # A contradiction fails rather than answering, which is how a constraint
    # says no.
    # !(test (collapse (let True (clpq (= $c 1)) (clpq (= $c 2)))) ())
    yield m.eval(
        S.test(
            S["collapse"](
                S["let"](
                    TRUE, S["clpq"](S["="](V.c, 1)), S["clpq"](S["="](V.c, 2))
                )
            ),
            expr(),
        )
    )

    # Disequations over the rationals, dif's numeric analogue.
    # !(test (collapse (let True (clpq (= $d 1))
    #                    (let True (clpq (= $e 2)) (clpq (=\= $d $e))))) (True))
    yield m.eval(
        S.test(
            S["collapse"](
                S["let"](
                    TRUE,
                    S["clpq"](S["="](V.d, 1)),
                    S["let"](
                        TRUE,
                        S["clpq"](S["="](V.e, 2)),
                        S["clpq"](S[r"=\="](V.d, V.e)),
                    ),
                )
            ),
            expr(TRUE),
        )
    )

    # The constraints an answer still carries read back through
    # residual-goals, rendered with repr because a test's expected value is
    # EVALUATED and `(>= $g 0)` inside it would run as arithmetic.
    # !(test (let True (clpq (>= $f 0))
    #          (let True (clpq (=< $f 3)) (repr (residual-goals $f))))
    #        "(({} (, (>= $_0 0) (=< $_0 3))))")
    yield m.eval(
        S.test(
            S["let"](
                TRUE,
                S["clpq"](S[">="](V.f, 0)),
                S["let"](
                    TRUE,
                    S["clpq"](S["=<"](V.f, 3)),
                    S["repr"](S["residual-goals"](V.f)),
                ),
            ),
            val("(({} (, (>= $_0 0) (=< $_0 3))))"),
        )
    )

    # ---------------------------------------------------------- CLP(B)
    # `(card (1) ($p $q))` is "exactly one of these is true", so a list here
    # stays a list rather than becoming an operator.
    # !(test (collapse (let True (clpb (card (1) ($m $n))) (clpb-labeling ($m $n))))
    #        ((0 1) (1 0)))
    yield m.eval(
        S.test(
            S["collapse"](
                S["let"](
                    TRUE,
                    S["clpb"](S.card(expr(1), expr(V.m, V.n))),
                    S["clpb-labeling"](expr(V.m, V.n)),
                )
            ),
            expr(expr(0, 1), expr(1, 0)),
        )
    )

    # Tautology and contradiction, decided without enumerating anything.
    # !(test (clpb-taut (+ $t (~ $t))) True)
    yield m.eval(
        S.test(S["clpb-taut"](S["+"](V.t, S["~"](V.t))), TRUE)
    )
    # !(test (clpb-taut (* $u (~ $u))) False)
    yield m.eval(
        S.test(S["clpb-taut"](S["*"](V.u, S["~"](V.u))), FALSE)
    )

    # The engine's own and/or/not are NOT replaced by this and should not be.
    # !(test (if (and (or $x True) $y) ($x $y)) ((True True) (False True)))
    yield m.eval(
        S.test(
            S["if"]((V.x | TRUE) & V.y, expr(V.x, V.y)),
            expr(expr(TRUE, TRUE), expr(FALSE, TRUE)),
        )
    )
