"""The Python twin of examples/libraries/he_assert.metta.

The assert family: equality, alpha-equality, expected-result tuples, inclusion,
and the Msg variants that add a failure message.

`(= (adder) ($x))` stays at the container door because its body is a free MeTTa
VARIABLE the head does not bind, and a compiled body reads every free name as a
parameter, a known function or a constructor, none of which a fresh variable is;
the residue table records that against P14.4. `(quote (+ $x $y))` beside it is
built by Python's own `+`, because both operands are variables, while `(+ 1 2)`
and `(- 6 3)` name their heads: Python's operators on two ground numbers are
arithmetic and answer 3 before any term exists.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 21497 to 21497, +0 (+0.00%), by the P14 twin-style
#: rewrite: the twin's atoms are unchanged: (= (adder) ()) stays a
#: container-door atom because its body is a free variable, and every other
#: form is a term whose spelling changed without changing the atom. Prior:
#: ADDED 2026-08-22 at 21497 by the wave-3 libraries baseline, which recorded
#: no cause.
BUDGET = 21497

def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    # !(test (assertEqual (+ 1 2) (- 6 3)) True)
    yield m.eval(S.test(S.assertEqual(S["+"](1, 2), S["-"](6, 3)), TRUE))
    # !(test (assertAlphaEqual (h $x $y) (h $a $b)) True)
    yield m.eval(
        S.test(S.assertAlphaEqual(S.h(V.x, V.y), S.h(V.a, V.b)), TRUE)
    )
    # !(test (assertAlphaEqual (quote (+ $x $y)) (quote (+ $a $b))) True)
    yield m.eval(
        S.test(
            S.assertAlphaEqual(S.quote(V.x + V.y), S.quote(V.a + V.b)), TRUE
        )
    )

    # The ToResult forms take the expected results as a tuple, not a bare value,
    # and do not evaluate it. A single result is therefore written (3), not 3.
    # !(test (assertEqualToResult (+ 1 2) (3)) True)
    yield m.eval(S.test(S.assertEqualToResult(S["+"](1, 2), (3,)), TRUE))
    # !(test (assertEqualToResult (superpose (1 2)) (1 2)) True)
    yield m.eval(
        S.test(S.assertEqualToResult(S.superpose((1, 2)), (1, 2)), TRUE)
    )

    # (= (adder) ($x))
    m += equation(S.adder()).to((V.x,))

    # !(test (assertAlphaEqualToResult (adder) (($y))) True)
    yield m.eval(
        S.test(S.assertAlphaEqualToResult(S.adder(), ((V.y,),)), TRUE)
    )

    # Every expected result must appear among those produced.
    # !(test (assertIncludes (superpose (1 2 3)) (2)) True)
    yield m.eval(S.test(S.assertIncludes(S.superpose((1, 2, 3)), (2,)), TRUE))
    # !(test (assertIncludes (superpose (1 2 3)) (2 3)) True)
    yield m.eval(S.test(S.assertIncludes(S.superpose((1, 2, 3)), (2, 3)), TRUE))

    # The Msg variants take a failure message and otherwise behave as their bases.
    # !(test (assertEqualMsg (+ 1 2) (- 6 3) "sums differ") True)
    yield m.eval(
        S.test(
            S.assertEqualMsg(S["+"](1, 2), S["-"](6, 3), val("sums differ")), TRUE
        )
    )
    # !(test (assertAlphaEqualMsg (h $x $y) (h $a $b) "not alpha equal") True)
    yield m.eval(
        S.test(
            S.assertAlphaEqualMsg(
                S.h(V.x, V.y), S.h(V.a, V.b), val("not alpha equal")
            ),
            TRUE,
        )
    )
    # !(test (assertEqualToResultMsg (+ 1 2) (3) "not the expected result") True)
    yield m.eval(
        S.test(
            S.assertEqualToResultMsg(
                S["+"](1, 2), (3,), val("not the expected result")
            ),
            TRUE,
        )
    )
    # !(test (assertAlphaEqualToResultMsg (adder) (($y)) "not alpha equal") True)
    yield m.eval(
        S.test(
            S.assertAlphaEqualToResultMsg(
                S.adder(), ((V.y,),), val("not alpha equal")
            ),
            TRUE,
        )
    )
