"""The Python twin of examples/libraries/he_minimalmetta.metta.

Division by repeated subtraction, written in the core instructions themselves.

The equation stays at the container door because the instruction tier IS the
exercise: `chain`, `eval` and `unify` are what this file demonstrates, and a
compiled body spells sequencing as assignment, which lowers to `let*`. That is
a different program with a different instruction count, and the 350,000-step
run this file makes is exactly the measurement the difference would spoil.
Python's own operators still build the arithmetic operands, because those take
a variable and so read as terms rather than as arithmetic.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 83244559 to 83244559, +0 (+0.00%), by the P14
#: twin-style rewrite: the twin's atoms are unchanged: the instruction-tier
#: equation stays a container-door atom and equation(...).to(...) builds what
#: S["="](...) built. Prior: ADDED 2026-08-22 at 83244559 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 83244559


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    # (= (div $x $y $accum)
    #    (chain (eval (- $x $y)) $r1
    #      (chain (eval (< $r1 0)) $r2
    #        (chain (unify $r2 True
    #          $accum
    #          (chain (eval (+ 1 $accum)) $inc
    #            (chain (eval (div $r1 $y $inc)) $r4 $r4)
    #          )) $r3 $r3
    #        )
    #      )
    #    )
    # )
    m += equation(S.div(V.x, V.y, V.accum)).to(
        S.chain(
            S.eval(V.x - V.y),
            V.r1,
            S.chain(
                S.eval(V.r1 < 0),
                V.r2,
                S.chain(
                    S.unify(
                        V.r2,
                        TRUE,
                        V.accum,
                        S.chain(
                            S.eval(1 + V.accum),
                            V.inc,
                            S.chain(S.eval(S.div(V.r1, V.y, V.inc)), V.r4, V.r4),
                        ),
                    ),
                    V.r3,
                    V.r3,
                ),
            ),
        )
    )

    # The 70000-step interpreter exercise states a budget above the engine default.
    # !(test (with-pragma! ((max-stack-depth 1000000))
    #                      (chain (eval (div 350000 5 0)) $rr $rr))
    #        70000)
    yield m.eval(
        S.test(
            S["with-pragma!"](
                ((S["max-stack-depth"], 1000000),),
                S.chain(S.eval(S.div(350000, 5, 0)), V.rr, V.rr),
            ),
            70000,
        )
    )
