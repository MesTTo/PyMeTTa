"""Purpose: examples/reasoning/constructive_negation.metta in Python: negation that answers.

`not-provable` answers True for what an expression cannot prove and False for
what it can, and over an infinite domain it CONSTRAINS rather than enumerates.
The file walks that from the two defects it repairs, through `dif` against
`!=`, quantifying over a generator, negating a space query and a `case`, to
negating a CLP(FD) bound. Fifty claims, each an `assert`, and the example's own
eight sections are eight functions here.

Where a body is MeTTa's `(and ...)`, the equation is a `@m.rules` bundle: a
rules body EXECUTES, so `&` builds the conjunction term there, rung 3 of the
descent ladder, where Python's own `and` short-circuits on truthiness and would
store a different program for the dual to negate. Where a body is an ordinary
computation the equation is a compiled function, and three of them are:
`any-pass` binds with an assignment, `has-child` matches a NAMED space through
`match(space, pattern, template)`, and the two `mask-example` heads carry their
declarations as annotations, `int` for Number and `Atom` for the metatype that
keeps an argument unreduced.

Two things the surface still makes this file say the long way, both measured:

- `(let True (f $x) (let $x c $x))` is `solve` with a template that binds a
  SECOND variable, and `solve` derives its template from the subject. Those
  fourteen claims keep the term (friction, P14.7).
- `band`'s `(case $n ((90 True) (40 False)))` must stay a FLAT case. Python's
  `match` statement lowers to a NESTED tower, which compiles and answers
  correctly on a direct call and then fails its dual with
  ``Type error: `integer' expected, found `Empty'`` on any key past the first
  arm (friction, P14.4).

Comparisons are built by their operator WORDS, `S.ne`, `S.gt` and `S.eq`,
because Python's four rich comparisons order atoms rather than building terms.
Guarantees:
  - TRUE and FALSE used here are package values rather than local
    reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

import metta
from metta import FALSE, TRUE, Atom, S, V, equation, fn, match
from metta.vocabularies import NoMatchEnum

#: The nine relations the example gives NoMatchFail, so a missing proof is
#: relational failure instead of the P3 residual-call dispatch value.
FALLIBLE = (S.penguin, S.bird, S.student, S.married, S.invalid,
            S.over_65, S.paid_up, S.marks, S.edge)

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 129037 to 129188, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 129188 to 128587, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 128587 to 128305, on the release tree:
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
#: RE-PINNED 2026-08-25, 128305 to 128199, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 128199 to 130763 (+2564), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 130763


def defaults(m):
    """What `not` cannot say, what `not-provable` can, and the flying birds."""

    @m.rules
    def birds(who):
        """Two birds, one penguin, and the default rule over them."""
        # (= (bird tweety) True) (= (bird polly) True) (= (penguin polly) True)
        yield equation(S.bird(S.tweety)).to(TRUE)
        yield equation(S.bird(S.polly)).to(TRUE)
        yield equation(S.penguin(S.polly)).to(TRUE)
        # (= (flies $x) (and (bird $x) (not-provable (penguin $x))))
        yield equation(S.flies(who)).to(S.bird(who) & fn.not_provable(S.penguin(who)))

    # `not` is a boolean function, and an expression no equation matches does
    # not reduce to False: it stays as data, so there is nothing to negate.
    # !(test (collapse (not (penguin tweety))) ())
    assert m.eval(~S.penguin(S.tweety)) == []

    # not-provable can say it, in both directions.
    # !(test (not-provable (penguin tweety)) True)
    # !(test (not-provable (penguin polly)) False)
    assert m.fn.not_provable(S.penguin(S.tweety)) == [True]
    assert m.fn.not_provable(S.penguin(S.polly)) == [False]

    # Default reasoning: birds fly unless they are penguins. The negation runs
    # with $x already bound by (bird $x).
    # !(test (collapse (let True (flies $x) $x)) (tweety))
    assert m.solve(TRUE, S.flies(V.x)).x == S.tweety


def defects(m):
    """The two cases The Art of Prolog names, section 11.3 page 199."""

    @m.rules
    def repairs(who):
        """A student nobody married, and a value that is two and not one."""
        # (= (student bill) True) (= (married joe) True)
        yield equation(S.student(S.bill)).to(TRUE)
        yield equation(S.married(S.joe)).to(TRUE)
        # (= (unmarried-student $x) (and (not-provable (married $x)) (student $x)))
        yield equation(S.unmarried_student(who)).to(
            fn.not_provable(S.married(who)) & S.student(who)
        )
        # (= (two-but-not-one $x) (and (not-provable (== $x 1)) (let $x 2 True)))
        yield equation(S.two_but_not_one(who)).to(
            fn.not_provable(S.eq(who, 1)) & S.let(who, 2, TRUE)  # rung: a stored `let` that BINDS, where Python's assignment binds a Python name (P14.4)
        )

    # Prolog FAILS on unmarried_student(X), ignoring that X=bill is implied,
    # because the negation runs first with X unbound and cannot bind.
    # !(test (collapse (let True (unmarried-student $x) $x)) (bill))
    assert m.solve(TRUE, S.unmarried_student(V.x)).x == S.bill

    # `not (X=1), X=2` fails in Prolog although X=2 is a solution. Here the
    # negation leaves a disequality behind instead of a failed proof, and the
    # later binding satisfies it.
    # !(test (collapse (let True (two-but-not-one $x) $x)) (2))
    assert m.solve(TRUE, S.two_but_not_one(V.x)).x == 2


def welfare(m):
    """Section 11.5 page 207: a variable only the negation reads is universal."""

    @m.rules
    def entitlements(person, what, any_pension):
        """Three pensions, and the entitlement rule that negates all of them."""
        # (= (invalid mc-tavish) True), and the over-65 and paid-up facts
        yield equation(S.invalid(S.mc_tavish)).to(TRUE)
        for name in (S.mc_tavish, S.mc_donald, S.mc_duff):
            yield equation(S.over_65(name)).to(TRUE)
        for name in (S.mc_tavish, S.mc_donald):
            yield equation(S.paid_up(name)).to(TRUE)
        # (= (pension $p invalid-pension) (invalid $p)), and two more
        yield equation(S.pension(person, S.invalid_pension)).to(S.invalid(person))
        yield equation(S.pension(person, S.old_age_pension)).to(
            S.over_65(person) & S.paid_up(person)
        )
        yield equation(S.pension(person, S.supplementary_benefit)).to(
            S.over_65(person)
        )
        # (= (entitlement $p $what) (pension $p $what))
        # (= (entitlement $p nothing) (not-provable (pension $p $any)))
        yield equation(S.entitlement(person, what)).to(S.pension(person, what))
        yield equation(S.entitlement(person, S.nothing)).to(
            fn.not_provable(S.pension(person, any_pension))
        )

    # !(test (collapse (let True (entitlement mc-tavish $w) $w))
    #        (invalid-pension old-age-pension supplementary-benefit))
    assert m.solve(TRUE, S.entitlement(S.mc_tavish, V.w)).w == [
        S.invalid_pension, S.old_age_pension, S.supplementary_benefit,
    ]
    # !(test (collapse (let True (entitlement mc-duff $w) $w)) (supplementary-benefit))
    assert m.solve(TRUE, S.entitlement(S.mc_duff, V.w)).w == S.supplementary_benefit
    # !(test (collapse (let True (entitlement someone-else $w) $w)) (nothing))
    assert m.solve(TRUE, S.entitlement(S.someone_else, V.w)).w == S.nothing


def constraints(m):
    """Reading a constructive answer, and `dif` against `!=`."""

    @m.rules
    def graph(node, target):
        """Two edges, and the question with infinitely many answers."""
        # (= (edge a b) True) (= (edge b c) True)
        yield equation(S.edge(S.a, S.b)).to(TRUE)
        yield equation(S.edge(S.b, S.c)).to(TRUE)
        # (= (has-no-outgoing $x) (not-provable (edge $x $y)))
        yield equation(S.has_no_outgoing(node)).to(
            fn.not_provable(S.edge(node, target))
        )

    # !(test (has-no-outgoing c) True)
    # !(test (has-no-outgoing a) False)
    assert m.fn.has_no_outgoing(S.c) == [True]
    assert m.fn.has_no_outgoing(S.a) == [False]

    # And the constraint is live: bind the variable afterwards and it decides.
    # The template is a second `let`, which is what `solve` has no spelling
    # for, so these three keep the term.
    # !(test (collapse (let True (has-no-outgoing $x) (let $x c $x))) (c))
    # !(test (collapse (let True (has-no-outgoing $x) (let $x zzz $x))) (zzz))
    # !(test (collapse (let True (has-no-outgoing $x) (let $x a $x))) ())
    open_node = S.has_no_outgoing(V.x)
    assert m.eval(S.let(TRUE, open_node, S.let(V.x, S.c, V.x))) == [S.c]  # rung: the template BINDS a second variable, which solve derives from the subject (P14.7)
    assert m.eval(S.let(TRUE, open_node, S.let(V.x, S.zzz, V.x))) == [S.zzz]  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, open_node, S.let(V.x, S.a, V.x))) == []  # rung: the same shape (P14.7)

    # dif is the constraint the duals are built from, and it holds for as long
    # as the answer does.
    # !(test (dif 1 2) True)
    # !(test (collapse (let True (dif $q 5) (let $q 6 $q))) (6))
    # !(test (collapse (let True (dif $q 5) (let $q 5 $q))) ())
    assert m.fn.dif(1, 2) == [True]
    assert m.eval(S.let(TRUE, S.dif(V.q, 5), S.let(V.q, 6, V.q))) == [6]  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, S.dif(V.q, 5), S.let(V.q, 5, V.q))) == []  # rung: the same shape (P14.7)

    # `!=` asks whether two terms are identical NOW, so on an unbound variable
    # it says True and lets a later binding contradict it.
    # !(test (!= 1 2) True)
    # !(test (!= 1 1) False)
    # !(test (collapse (let True (!= $r 5) (let $r 5 $r))) (5))
    assert m.fn["!="](1, 2) == [True]
    assert m.fn["!="](1, 1) == [False]
    assert m.eval(S.let(TRUE, S.ne(V.r, 5), S.let(V.r, 5, V.r))) == [5]  # rung: the same shape (P14.7)


def quantifying(m):
    """A let is True when SOME answer makes it True, so its negation is a forall."""

    @m.rules
    def marks():
        """(= (marks carol) 90), and three more with a symbol in the head."""
        for who, mark in ((S.carol, 90), (S.carol, 30), (S.dave, 10), (S.dave, 20)):
            yield equation(S.marks(who)).to(mark)

    @m.define
    def any_pass(who):
        """(= (any-pass $w) (let $m (marks $w) (> $m 50)))."""
        mark = S.marks(who)
        return mark > 50

    # carol has two marks and one of them passes, so she IS provable; dave has
    # two and neither does.
    # !(test (collapse (any-pass carol)) (True False))
    # !(test (not-provable (any-pass carol)) False)
    # !(test (not-provable (any-pass dave)) True)
    assert any_pass(S.carol) == [True, False]
    assert m.fn.not_provable(S.any_pass(S.carol)) == [False]
    assert m.fn.not_provable(S.any_pass(S.dave)) == [True]

    # A value with no answer leaves the let with no answer, so it is not True.
    # !(test (not-provable (any-pass nobody)) True)
    assert m.fn.not_provable(S.any_pass(S.nobody)) == [True]

    # And the answer stays constructive: what the generator narrows a variable
    # to belongs IN the answer rather than being quantified away.
    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w dave $w))) (dave))
    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w carol $w))) ())
    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w erin $w))) (erin))
    failing = fn.not_provable(S.any_pass(V.w))
    assert m.eval(S.let(TRUE, failing, S.let(V.w, S.dave, V.w))) == [S.dave]  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, failing, S.let(V.w, S.carol, V.w))) == []  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, failing, S.let(V.w, S.erin, V.w))) == [S.erin]  # rung: the same shape (P14.7)


def over_a_space(m):
    """A match over a space is a generator too, and a finite one."""
    # !(bind! &kin (new-space))
    # !(add-atom &kin (parent alice bob)) !(add-atom &kin (parent carol dave))
    kin = metta.space()
    kin += S.parent(S.alice, S.bob)
    kin += S.parent(S.carol, S.dave)

    @m.define
    def has_child(person):
        """(= (has-child $x) (match &kin (parent $x $y) True))."""
        return match(kin, S.parent(person, V.y), True)  # noqa: FBT003  -- True is the match TEMPLATE, the atom this relation answers, not a flag

    # $y is local to the match and $x is not, which is the whole difference
    # between "has a child" and "who has no child".
    # !(test (not-provable (has-child alice)) False)
    # !(test (not-provable (has-child bob)) True)
    # !(test (not-provable (has-child stranger)) True)
    assert m.fn.not_provable(S.has_child(S.alice)) == [False]
    assert m.fn.not_provable(S.has_child(S.bob)) == [True]
    assert m.fn.not_provable(S.has_child(S.stranger)) == [True]

    # !(test (collapse (let True (not-provable (has-child $w)) (let $w bob $w))) (bob))
    # !(test (collapse (let True (not-provable (has-child $w)) (let $w alice $w))) ())
    # !(test (collapse (let True (not-provable (has-child $w)) (let $w nobody $w)))
    #        (nobody))
    childless = fn.not_provable(S.has_child(V.w))
    assert m.eval(S.let(TRUE, childless, S.let(V.w, S.bob, V.w))) == [S.bob]  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, childless, S.let(V.w, S.alice, V.w))) == []  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, childless, S.let(V.w, S.nobody, V.w))) == [S.nobody]  # rung: the same shape (P14.7)


def forms_with_no_answer(m):
    """A case commits to its first matching pattern, and its dual follows it."""

    @m.rules
    def bands(key):
        """(= (band $n) (case $n ((90 True) (40 False))))."""
        yield equation(S.band(key)).to(S.case(key, ((90, TRUE), (40, FALSE))))  # rung: Python's match statement lowers to a NESTED tower whose dual raises past the first arm (P14.4)

    # A key that matches no pattern leaves the case with no answer, and no
    # answer is not True.
    # !(test (not-provable (band 90)) False)
    # !(test (not-provable (band 40)) True)
    # !(test (not-provable (band 55)) True)
    assert m.fn.not_provable(S.band(90)) == [False]
    assert m.fn.not_provable(S.band(40)) == [True]
    assert m.fn.not_provable(S.band(55)) == [True]

    # A superpose answers each element in turn, so it is not True exactly when
    # none of them is. A collapse yields a LIST, so it is never True at all.
    # !(test (not-provable (superpose (False True))) False)
    # !(test (not-provable (superpose (False False))) True)
    # !(test (not-provable (superpose ())) True)
    assert m.fn.not_provable(fn.superpose((FALSE, TRUE))) == [False]
    assert m.fn.not_provable(fn.superpose((FALSE, FALSE))) == [True]
    assert m.fn.not_provable(fn.superpose(())) == [True]

    # A form whose negation cannot be computed soundly RAISES rather than
    # answering from an incomplete dual. The comparisons are the exception,
    # because each one's opposite is another comparison.
    # !(test (not-provable (> 1 2)) True)
    # !(test (not-provable (> 2 1)) False)
    # !(test (not-provable (== 1 1)) False)
    assert m.fn.not_provable(S.gt(1, 2)) == [True]
    assert m.fn.not_provable(S.gt(2, 1)) == [False]
    assert m.fn.not_provable(S.eq(1, 1)) == [False]


def bounds(m):
    """The # family is CLP(FD), so negating a bound POSTS the opposite bound."""
    # !(test (not-provable (#< 5 1)) True)
    # !(test (collapse (let True (not-provable (#< $x 5)) (let $x 7 $x))) (7))
    # !(test (collapse (let True (not-provable (#< $x 5)) (let $x 3 $x))) ())
    assert m.fn.not_provable(fn["#<"](5, 1)) == [True]
    below_five = fn.not_provable(fn["#<"](V.x, 5))
    assert m.eval(S.let(TRUE, below_five, S.let(V.x, 7, V.x))) == [7]  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, below_five, S.let(V.x, 3, V.x))) == []  # rung: the same shape (P14.7)
    # !(test (collapse (let True (not-provable (#= $y 4)) (let $y 9 $y))) (9))
    # !(test (collapse (let True (not-provable (#= $y 4)) (let $y 4 $y))) ())
    is_four = fn.not_provable(fn["#="](V.y, 4))
    assert m.eval(S.let(TRUE, is_four, S.let(V.y, 9, V.y))) == [9]  # rung: the same shape (P14.7)
    assert m.eval(S.let(TRUE, is_four, S.let(V.y, 4, V.y))) == []  # rung: the same shape (P14.7)


def masking(m):
    """An Atom-typed argument stays written on both sides of the negation."""

    @m.define
    def mask_example_double(x: int) -> int:
        """(: mask-example-double (-> Number Number)), (= ... (* $x 2))."""
        return x * 2

    @m.define
    def mask_example_holds(_x: Atom = 10) -> bool:
        """(: mask-example-holds (-> Atom Bool)), true of the written term 10."""
        return True

    # !(add-atom &petta (dispatch-policy mask-example-holds NoMatchEnum NoMatchFail))
    metta.reflection += S.dispatch_policy(
        S.mask_example_holds, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail]
    )

    # !(test (not-provable (mask-example-holds (mask-example-double 5))) True)
    # !(test (not-provable (mask-example-holds 10)) False)
    # !(test (collapse (mask-example-holds (mask-example-double 5))) ())
    written = S.mask_example_holds(S.mask_example_double(5))
    assert m.fn.not_provable(written) == [True]
    assert m.fn.not_provable(S.mask_example_holds(10)) == [False]
    assert m.eval(written) == []


def twin(m):
    """Walk negation from what `not` cannot say to a constrained domain."""
    # !(add-atom &petta (dispatch-policy penguin NoMatchEnum NoMatchFail)), and eight more
    reflection = metta.reflection
    for relation in FALLIBLE:
        reflection += S.dispatch_policy(
            relation, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail]
        )

    defaults(m)
    defects(m)
    welfare(m)
    constraints(m)
    quantifying(m)
    over_a_space(m)
    forms_with_no_answer(m)
    bounds(m)
    masking(m)
