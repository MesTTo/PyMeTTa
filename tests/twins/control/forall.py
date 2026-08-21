r"""The Python twin of examples/control/forall.metta: a bounded check over a stream.

`forall` compiles to Prolog's own `forall/2`, `\+ (Gen, \+ Test)`, so it STOPS
the generator at the first answer the check refuses. That is what makes a
bounded take writable in MeTTa, and it is why the generator and the check are
both first-class here: either may be a function name or a lambda, and a lambda
may arrive through a `let`, through a `let*`, written inline, or wrapped in an
`if` that answers one.

`g` uses the stacked-clause door, which is the Python spelling of literal head
patterns: a literal default is not a Python default there, it is the
equation's head pattern, so `def g_one(n=1)` writes `(= (g 1) 1)`. The two
clauses are two Python functions carrying one `name=`, because two functions
of one name in one module is a redefinition to every Python reader and to
ruff.

`f` cannot use that door: its two clauses fix nothing, and the file's own point
is that `(f)` answers twice, which stacked clauses read as first-match. So it
is written at the container door, the same choice `basics/time_and_pragmas`
makes for `bounded-factorial`.

`P` is written `name="P"` over a lowercase Python function, because a
capitalised Python function name is not a Python spelling at all.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 26188

#: (|-> ($x) (g $x)), the generator as a lambda, and the application of one.
GENERATOR = S["|->"](expr(V.x), S.g(V.x))


def _check(bound):
    """(|-> ($v) (< $v <bound>)), the check as a lambda."""
    return S["|->"](expr(V.v), S["<"](V.v, bound))


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (f) 1)
    m += S["="](S.f(), 1)
    # (= (f) 2)
    m += S["="](S.f(), 2)

    # A literal default is the head PATTERN for that position, so the
    # parameter itself never appears in the equation and the underscore says
    # so to a Python reader as well.
    @m.define(name="g")
    def g_one(_n=1):
        # (= (g 1) 1)
        return 1

    @m.define(name="g")
    def g_two(_n=2):
        # (= (g 2) 2)
        return 2

    @m.define(name="P")
    def below_two(x):
        # (= (P $X) (< $X 2))
        return x < 2

    # Arg-free generator function plus check function.
    # !(test (forall (f) P) false)
    yield m.eval(S.test(S["forall"](S.f(), S.P), FALSE))

    # Arg-ful generator function plus check function.
    # !(test (forall (g $x) P) false)
    yield m.eval(S.test(S["forall"](g_one(V.x), S.P), FALSE))

    # Arg-ful generator lambda plus check function.
    # !(test (let $genlambda (|-> ($x) (g $x)) (forall ($genlambda $z) P)) false)
    yield m.eval(
        S.test(
            S["let"](
                V.genlambda,
                GENERATOR,
                S["forall"](expr(V.genlambda, V.z), S.P),
            ),
            FALSE,
        )
    )

    # Arg-ful generator function plus check lambda.
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    yield m.eval(
        S.test(
            S["let"](
                V.checklambda,
                _check(2),
                S["forall"](g_one(2), V.checklambda),
            ),
            FALSE,
        )
    )
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 1) $checklambda)) true)
    yield m.eval(
        S.test(
            S["let"](
                V.checklambda,
                _check(2),
                S["forall"](g_one(1), V.checklambda),
            ),
            TRUE,
        )
    )
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    yield m.eval(
        S.test(
            S["let"](
                V.checklambda,
                _check(2),
                S["forall"](g_one(2), V.checklambda),
            ),
            FALSE,
        )
    )

    # Arg-ful generator lambda plus check lambda.
    # !(test (let* (($checklambda (|-> ($v) (< $v 2)))
    #               ($genlambda (|-> ($x) (g $x))))
    #              (forall ($genlambda $z) $checklambda))
    #        false)
    yield m.eval(
        S.test(
            S["let*"](
                expr(
                    expr(V.checklambda, _check(2)),
                    expr(V.genlambda, GENERATOR),
                ),
                S["forall"](expr(V.genlambda, V.z), V.checklambda),
            ),
            FALSE,
        )
    )

    # Lambdas as arguments directly.
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 2))) false)
    yield m.eval(
        S.test(
            S["forall"](expr(GENERATOR, V.z), _check(2)), FALSE
        )
    )
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 20))) true)
    yield m.eval(
        S.test(
            S["forall"](expr(GENERATOR, V.z), _check(20)), TRUE
        )
    )

    # A lambda wrapped in a syntactic construct is still a lambda.
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 2)) 42)) false)
    yield m.eval(
        S.test(
            S["forall"](
                expr(GENERATOR, V.z), S["if"](TRUE, _check(2), 42)
            ),
            FALSE,
        )
    )
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 20)) 42)) true)
    yield m.eval(
        S.test(
            S["forall"](
                expr(GENERATOR, V.z), S["if"](TRUE, _check(20), 42)
            ),
            TRUE,
        )
    )
    # !(test (forall ((|-> ($x) (* 100 (g $x))) $z)
    #                (if True (|-> ($v) (< $v 20)) 42))
    #        false)
    yield m.eval(
        S.test(
            S["forall"](
                expr(
                    S["|->"](expr(V.x), S["*"](100, S.g(V.x))), V.z
                ),
                S["if"](TRUE, _check(20), 42),
            ),
            FALSE,
        )
    )
