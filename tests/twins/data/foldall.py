"""The Python twin of examples/data/foldall.metta: folding a generator.

`foldall` takes an aggregating function and a GENERATOR, and folds the
generator's answers. The example varies both halves: the aggregator is a named
function or a `|->` lambda, and the generator is a call with no arguments, a
call with one, or a lambda applied to a free variable.

`merge` and `g` are computations and are written as ones. `g`'s two clauses
are two `def`s whose literal defaults are their head patterns, which is the
compiled subset's own spelling for stacked equations.

`f` is the one that drops a rung. Its two clauses share a nullary head, so
there is no head pattern to tell one `def` from the other and a second `def f`
REBINDS the name rather than stacking a clause; the equivalent Python is a
generator, which stores `(= (f) (superpose (2 3)))` instead of two equations.
The answers are the same multiset, which is what `foldall` folds, and the
residue table records the missing spelling against P14.4.

The `let`, `let*` and `|->` forms stay at the term door because they are
runnable FORMS rather than function bodies: there is no Python statement
position to spell a `let` in, and the aggregator being bound is the thing each
form is about.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE = val(value=True)

#: The two lambdas the example passes around, named once because the forms
#: below differ in how they are BOUND, not in what they are.
#: `(|-> ($x $y) (+ $x $y))` aggregates and `(|-> ($z) ...)` generates.
add2 = S["|->"]((V.x, V.y), V.x + V.y)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 22960 to 24789, +1829 (+7.97%), by the wave-4 idiom
#: rewrite moving `f`, `g` and `merge` onto @m.define. COMPILING a definition
#: costs more than STORING one, and the difference is paid once per process
#: plus a little per definition, never per call: four trivial one-parameter
#: definitions in a fresh process measured 2221 / 2986 / 3751 / 4516
#: inferences through @m.define against 592 / 1164 / 1736 / 2308 through
#: `m += equation(...).to(...)`, so the first compiled definition costs 1,629
#: more and each one after it 193 more. The net here is smaller than four
#: times that because the generator spelling of `f` stores ONE equation where
#: the original stores two: measured all-container 22960, generator `f` alone
#: 24339, compiled `merge` alone 24589, compiled `g` alone 24653.
BUDGET = 24789


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """

    @m.define
    def f():
        # (= (f) 2) (= (f) 3), as one generator: yield IS superpose
        yield 2
        yield 3

    @m.define
    def g(n=1):  # noqa: ARG001  -- a literal default is the head PATTERN for that position, so the parameter is matched rather than read
        # (= (g 1) 2): a literal default is the head pattern for that position
        return 2

    @m.define
    def g(n=2):  # noqa: ARG001, F811  -- a literal default is the head PATTERN for that position, so the parameter is matched rather than read; and this is a second clause of the same equation, not a redefinition
        # (= (g 2) 3)
        return 3

    @m.define
    def merge(a, b):
        # (= (merge $A $B) (+ $A $B))
        return a + b

    # agg function plus arg-free generator
    # !(test (foldall merge (f) 0) 5)
    yield m.eval(S.test(S.foldall(S.merge, S.f(), 0), 5))

    # agg function plus arg-ful generator
    # !(test (foldall merge (g $x) 0) 5)
    yield m.eval(S.test(S.foldall(S.merge, S.g(V.x), 0), 5))

    # agg lambda plus arg-free generator
    # !(test (let $agglambda (|-> ($x $y) (+ $x $y)) (foldall $agglambda (f) 0)) 5)
    yield m.eval(
        S.test(S.let(V.agglambda, add2, S.foldall(V.agglambda, S.f(), 0)), 5)
    )

    # agg lambda plus arg-ful generator, written twice in the original
    # !(test (let $agglambda (|-> ($x $y) (+ $x $y)) (foldall $agglambda (g $z) 0)) 5)
    for _ in range(2):
        yield m.eval(
            S.test(
                S.let(V.agglambda, add2, S.foldall(V.agglambda, S.g(V.z), 0)), 5
            )
        )

    # agg lambda plus lambda arg-free generator
    # !(test (let* (($agglambda (|-> ($x $y) (+ $x $y)))
    #               ($genlambda (|-> ($z) (f))))
    #             (foldall $agglambda ($genlambda $x) 0)) 5)
    yield m.eval(
        S.test(
            S["let*"](
                ((V.agglambda, add2), (V.genlambda, S["|->"]((V.z,), S.f()))),
                S.foldall(V.agglambda, (V.genlambda, V.x), 0),
            ),
            5,
        )
    )

    # agg lambda plus lambda arg-ful generator
    # !(test (let* (($agglambda (|-> ($x $y) (+ $x $y)))
    #               ($genlambda (|-> ($z) (g $z))))
    #             (foldall $agglambda ($genlambda $x) 0)) 5)
    yield m.eval(
        S.test(
            S["let*"](
                (
                    (V.agglambda, add2),
                    (V.genlambda, S["|->"]((V.z,), S.g(V.z))),
                ),
                S.foldall(V.agglambda, (V.genlambda, V.x), 0),
            ),
            5,
        )
    )

    # lambdas as arg directly
    # !(test (foldall (|-> ($x $y) (+ $x $y)) ((|-> ($z) (g $z)) $w) 0) 5)
    yield m.eval(
        S.test(
            S.foldall(add2, (S["|->"]((V.z,), S.g(V.z)), V.w), 0),
            5,
        )
    )

    # lambdas as arg directly within syntactic construct
    # !(test (foldall (if True (let $f (|-> ($x $y) (+ $x $y)) $f) (empty))
    #                 ((|-> ($z) (g $z)) $w) 0) 5)
    yield m.eval(
        S.test(
            S.foldall(
                S["if"](TRUE, S.let(V.f, add2, V.f), S.empty()),
                (S["|->"]((V.z,), S.g(V.z)), V.w),
                0,
            ),
            5,
        )
    )
    # !(test (foldall (if True (let $f (|-> ($x $y) (+ $x $y)) $f) (empty))
    #                 ((|-> ($z) (* 2 (g $z))) $w) 0) 10)
    yield m.eval(
        S.test(
            S.foldall(
                S["if"](TRUE, S.let(V.f, add2, V.f), S.empty()),
                (S["|->"]((V.z,), 2 * S.g(V.z)), V.w),
                0,
            ),
            10,
        )
    )
