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

`f` cannot use that door: its two clauses fix nothing, so there is no literal
default to tell them apart, and a literal default is the whole of what makes
clauses stack. Measured 2026-08-22, two `@m.define` decorations under one name
with identical heads do not stack: rebinding one Python name replaces the first
equation, and two different Python functions raise `IndexError` out of
`_define_twins.replace_twin_clause`. So `f` uses `@rules`, the definitional
door that writes a clause set and derives no guard over it; that is the same
choice `basics/time_and_pragmas` makes for `bounded-factorial`, where the
guard would prune the branch the example exists to show.

`P` is written `name="P"` over a lowercase Python function, because a
capitalised Python function name is not a Python spelling at all.
"""

from petta import S, V, equation, rules, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 27964 to 27983, +19, by lifting the 2-clause equation set from
#: repeated `m += equation(...).to(...)` to `@rules` plus one `m.add(*group)`. The whole of the
#: increase is the multi-atom add path, not the decorator: `rules` builds its equations in
#: Python and spends nothing on the engine, and one `m.add` of n atoms costs 13 + 3n inferences
#: more than n separate `m +=` calls (measured over three fresh processes each: 673 against 692
#: at two atoms, 1042 against 1064 at three, 0.0000% spread). Prior: #: RE-PINNED 2026-08-22, 26188 to 27964, +1776, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 26188 by 47554fc's control/types twin baseline.
BUDGET = 27983

#: (|-> ($x) (g $x)), the generator as a lambda, and the application of one.
GENERATOR = S["|->"]((V.x,), S.g(V.x))


def _check(bound):
    """(|-> ($v) (< $v <bound>)), the check as a lambda."""
    return S["|->"]((V.v,), V.v < bound)


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @rules
    def f():
        # (= (f) 1)
        yield equation(S.f()).to(1)
        # (= (f) 2)
        yield equation(S.f()).to(2)

    m.add(*f)

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
    yield m.eval(S.test(S.forall(S.f(), S.P), FALSE))

    # Arg-ful generator function plus check function.
    # !(test (forall (g $x) P) false)
    yield m.eval(S.test(S.forall(S.g(V.x), S.P), FALSE))

    # Arg-ful generator lambda plus check function.
    # !(test (let $genlambda (|-> ($x) (g $x)) (forall ($genlambda $z) P)) false)
    yield m.eval(
        S.test(
            S.let(
                V.genlambda,
                GENERATOR,
                S.forall((V.genlambda, V.z), S.P),
            ),
            FALSE,
        )
    )

    # Arg-ful generator function plus check lambda.
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    yield m.eval(
        S.test(
            S.let(
                V.checklambda,
                _check(2),
                S.forall(S.g(2), V.checklambda),
            ),
            FALSE,
        )
    )
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 1) $checklambda)) true)
    yield m.eval(
        S.test(
            S.let(
                V.checklambda,
                _check(2),
                S.forall(S.g(1), V.checklambda),
            ),
            TRUE,
        )
    )
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    yield m.eval(
        S.test(
            S.let(
                V.checklambda,
                _check(2),
                S.forall(S.g(2), V.checklambda),
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
                (
                    (V.checklambda, _check(2)),
                    (V.genlambda, GENERATOR),
                ),
                S.forall((V.genlambda, V.z), V.checklambda),
            ),
            FALSE,
        )
    )

    # Lambdas as arguments directly.
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 2))) false)
    yield m.eval(S.test(S.forall((GENERATOR, V.z), _check(2)), FALSE))
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 20))) true)
    yield m.eval(S.test(S.forall((GENERATOR, V.z), _check(20)), TRUE))

    # A lambda wrapped in a syntactic construct is still a lambda.
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 2)) 42)) false)
    yield m.eval(
        S.test(
            S.forall((GENERATOR, V.z), S["if"](TRUE, _check(2), 42)),
            FALSE,
        )
    )
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 20)) 42)) true)
    yield m.eval(
        S.test(
            S.forall((GENERATOR, V.z), S["if"](TRUE, _check(20), 42)),
            TRUE,
        )
    )
    # !(test (forall ((|-> ($x) (* 100 (g $x))) $z)
    #                (if True (|-> ($v) (< $v 20)) 42))
    #        false)
    yield m.eval(
        S.test(
            S.forall(
                (S["|->"]((V.x,), 100 * S.g(V.x)), V.z),
                S["if"](TRUE, _check(20), 42),
            ),
            FALSE,
        )
    )
