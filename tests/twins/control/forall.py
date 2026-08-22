"""examples/control/forall.metta in Python: a check over every answer.

`forall` runs its check on every answer its generator gives and stops at the
first one that fails. Both slots take a function name, a call with an unbound
argument, or a lambda, and the file walks every combination of the two.

The generator and the check are ordinary definitions and are written as ones:
`g`'s two clauses stack, because a literal default IS the head pattern for
that position, and `f`'s two clauses fix nothing at all, which stacking reads
as redefinition, so `f` goes through `@rules` instead. `P` is a computation
and compiles.

The lambdas are terms. A Python lambda inside a compiled body does lower to
the engine's own `|->`, but a definition whose BODY is a lambda cannot hand
one out as data: the lambda's parameter folds into the head's arity, so
`(below 2)` answers `(partial below (2))`, and a nullary one answers a lifted
closure symbol. Measured 2026-08-22; filed as residue against P14.4. So the
two lambdas are built at the term door, once each, and the `let` and `let*`
that bind them are Python name bindings, which is what a `let` is.
"""

from petta import S, V, equation, rules, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE = val(value=True)

#: `(|-> ($x) (g $x))`, the generator lambda the original writes inline.
GENERATOR = S["|->"]((V.x,), S.g(V.x))

#: `(|-> ($x) (* 100 (g $x)))`, the generator that scales what it gives.
SCALED = S["|->"]((V.x,), 100 * S.g(V.x))

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 27983 to 24004, -3979 (-14.2%), by the twin contract
#: change: twelve `test` wrappers LEFT the engine for twelve `assert`s; every
#: `forall` still runs there, which is the file's subject, and the two
#: lambdas are still terms because a definition whose body is a lambda
#: answers a partial application rather than the lambda. Measured min-of-3
#: over fresh processes with the MORK backend linked in, which the artefact-
#: free worktree omits and which moves a compiled twin by about 10 inferences
#: per definition; against the example's 39434 the ratio is 0.6087. Prior:
#: 27983, the transliterated twin this replaces.
BUDGET = 24004


def below(limit):
    """`(|-> ($v) (< $v <limit>))`, the check the original writes inline."""
    return S["|->"]((V.v,), V.v < limit)


def twin(m):
    """Check every answer of a generator, nine ways of naming the two."""
    @rules
    def f():
        # (= (f) 1) (= (f) 2)
        yield equation(S.f()).to(1)
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
    assert m.eval(S.forall(S.f(), S.P)) == [False]

    # Arg-ful generator function plus check function.
    # !(test (forall (g $x) P) false)
    assert m.eval(S.forall(S.g(V.x), S.P)) == [False]

    # Arg-ful generator lambda plus check function. The `let` that names the
    # lambda is a Python name binding, which is what a `let` is.
    # !(test (let $genlambda (|-> ($x) (g $x)) (forall ($genlambda $z) P)) false)
    genlambda = GENERATOR
    assert m.eval(S.forall((genlambda, V.z), S.P)) == [False]

    # Arg-ful generator function plus check lambda.
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    checklambda = below(2)
    assert m.eval(S.forall(S.g(2), checklambda)) == [False]
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 1) $checklambda)) true)
    assert m.eval(S.forall(S.g(1), checklambda)) == [True]
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    assert m.eval(S.forall(S.g(2), below(2))) == [False]

    # Arg-ful generator lambda plus check lambda; a `let*` is two bindings.
    # !(test (let* (($checklambda (|-> ($v) (< $v 2)))
    #               ($genlambda (|-> ($x) (g $x))))
    #              (forall ($genlambda $z) $checklambda))
    #        false)
    assert m.eval(S.forall((genlambda, V.z), checklambda)) == [False]

    # Lambdas as arguments directly.
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 2))) false)
    assert m.eval(S.forall((GENERATOR, V.z), below(2))) == [False]
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 20))) true)
    assert m.eval(S.forall((GENERATOR, V.z), below(20))) == [True]

    # A lambda wrapped in a syntactic construct is still a lambda.
    wrapped_2 = S["if"](TRUE, below(2), 42)  # rung: the wrapper IS the claim, so the `if` has to be the form the claim is about
    wrapped_20 = S["if"](TRUE, below(20), 42)  # rung: the same wrapper, with the other bound
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 2)) 42)) false)
    assert m.eval(S.forall((GENERATOR, V.z), wrapped_2)) == [False]
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 20)) 42)) true)
    assert m.eval(S.forall((GENERATOR, V.z), wrapped_20)) == [True]
    # !(test (forall ((|-> ($x) (* 100 (g $x))) $z) (if True (|-> ($v) (< $v 20)) 42)) false)
    assert m.eval(S.forall((SCALED, V.z), wrapped_20)) == [False]
