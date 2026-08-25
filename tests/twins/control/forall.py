"""Purpose: examples/control/forall.metta in Python: a check over every answer.

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
`(below 2)` answers `(partial below (2))` and `arities("below")` is `[3]`
[re-measured 2026-08-24; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. Filed as residue against P14.4. So
the two lambdas are built at the term door, once each, and the `let` and `let*`
that bind them are Python name bindings, which is what a `let` is.

The comparison inside a built lambda is built by its WORD, `S.lt(V.v, limit)`,
because Python's four rich comparisons are the engine's total ORDER over two
atoms: none of them builds a term, and one against a Python int raises. The
wrapped check is `if_`, the keyword builder for stored code, which has the
arity the engine's `if` has.
Guarantees:
  - TRUE used here is a package value rather than a local reconstruction
    [tested: test_the_canonical_atoms_are_public_values; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, S, V, equation, if_, rules

#: `(|-> ($x) (g $x))`, the generator lambda the original writes inline.
GENERATOR = S["|->"]((V.x,), S.g(V.x))

#: `(|-> ($x) (* 100 (g $x)))`, the generator that scales what it gives.
SCALED = S["|->"]((V.x,), 100 * S.g(V.x))

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 52958 to 51945, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 51945 to 51875, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 51875 to 51631, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 51631


def below(limit):
    """`(|-> ($v) (< $v <limit>))`, the check the original writes inline.

    The top rung builds the comparison with the operator, `V.v < limit`, and
    hands the lambda out of a definition:

        @m.define
        def below(limit):
            return lambda v: v < limit

    Neither works. The four rich comparisons are the engine's total ORDER
    over two atoms, so `V.v < 2` raises `'<' not supported between instances
    of 'Variable' and 'int'` instead of building `(< $v 2)`, and the term is
    built by its operator WORD instead. And a definition whose body IS a
    lambda folds the lambda's parameter into the head's arity, so `(below 2)`
    answers `(partial below (2))` and `arities("below")` is `[3]`.
    Residue: P14.4.
    """
    return S["|->"]((V.v,), S.lt(V.v, limit))


def twin(m):
    """Check every answer of a generator, nine ways of naming the two."""
    # The top rung stacks two clauses under one head, the way `g` does below:
    #
    #     @m.define(name="f")
    #     def f_one(): return 1
    #     @m.define(name="f")
    #     def f_two(): return 2
    #
    # A literal DEFAULT is what makes stacked clauses stack, so two clauses
    # fixing nothing have no `@m.define` spelling at all. Re-measured
    # 2026-08-24: rebinding one Python name under one MeTTa name stores only
    # the LAST equation, and two different Python functions carrying one
    # `name=` raise `IndexError: list assignment index out of range` from
    # `metta/_define_twins.py` `replace_twin_clause`. The crash is a defect on
    # its own. `@rules` is the door that writes a clause set without deriving a
    # first-match guard; what it cannot do is take Python SYNTAX for its
    # bodies. Residue: P14.4.
    @rules
    def f():
        # (= (f) 1) (= (f) 2)
        yield equation(S.f()).to(1)
        yield equation(S.f()).to(2)

    m += f

    # A literal default is the head PATTERN for that position, so the
    # parameter itself never appears in the equation and the underscore says
    # so to a Python reader as well. Both clauses name the head, because one
    # head with two clauses needs two Python functions and only one of them
    # could carry the name implicitly.
    @m.define(name="g")
    def g_one(_n=1):
        # (= (g 1) 1)
        return 1

    @m.define(name="g")
    def g_two(_n=2):
        # (= (g 2) 2)
        return 2

    # The def's own name IS the head, so `name=` is for heads Python cannot
    # spell, and a CAPITALISED function head is one of them here: `def P`
    # trips the N family, whose burn-down maximum is full, so the identifier
    # this repository's gate accepts is the lowercase one and the head is
    # named [measured 2026-08-24: `GATE_ONLY=1 sh check.sh` failed with
    # "P0.13 suppression burn-down increased (observed, maximum): {'N': (37, 35)}";
    # commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
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
    wrapped_2 = if_(TRUE, below(2), 42)
    wrapped_20 = if_(TRUE, below(20), 42)
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 2)) 42)) false)
    assert m.eval(S.forall((GENERATOR, V.z), wrapped_2)) == [False]
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 20)) 42)) true)
    assert m.eval(S.forall((GENERATOR, V.z), wrapped_20)) == [True]
    # !(test (forall ((|-> ($x) (* 100 (g $x))) $z) (if True (|-> ($v) (< $v 20)) 42)) false)
    assert m.eval(S.forall((SCALED, V.z), wrapped_20)) == [False]
