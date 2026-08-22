"""The Python twin of examples/reasoning/constructive_negation.metta.

`not-provable` answers True for what an expression cannot prove and False for
what it can, and over an infinite domain it CONSTRAINS rather than enumerates.
The file walks that from the two defects it repairs, through dif against `!=`,
quantifying over a generator, negating a space query and a `case`, to negating
a CLP(FD) bound.

The two `mask-example` definitions are ordinary Python functions: the
annotations ARE the example's `(: ...)` declarations, `int` is Number and
`Atom` is the metatype that keeps the argument unreduced, and `10` as a
parameter default is the equation's head PATTERN rather than a Python default.
Everything else stays at the term door because its body is a MeTTa `and` (a
generate-and-test where Python's `and` short-circuits on truthiness), a `case`
(what Python's `match` statement would spell), or a `match` against a named
space, and each is a residue entry against P14.4.

Where an operator builds the term it is used: `~` is `not`, `&` is `and`, `>`
and `*` are themselves, and `x.eq(y)` is the equality TERM because `==` between
atoms is structural equality. Where it cannot, the tuple is: MeTTa's `(> 1 2)`
reads as Python's `(GT, 1, 2)`, because `1 > 2` computes and `V.r != 5` compares
the atom rather than building `(!= $r 5)`.
"""

from petta import Atom, S, V, equation, val

#: The three comparison heads this file needs as TERMS over operands Python's
#: own operators would compute on, or would build the wrong term for: `!=` on
#: atoms is structural inequality and `==` is structural equality.
NE, GT, EQ = S["!="], S[">"], S["=="]

#: The nine relations the example gives NoMatchFail, so a missing proof is
#: relational failure instead of the P3 residual-call dispatch value.
FALLIBLE = (
    S.penguin,
    S.bird,
    S.student,
    S.married,
    S.invalid,
    S["over-65"],
    S["paid-up"],
    S.marks,
    S.edge,
)

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 95562 to 97384, +1822 (+1.91%), by the two `mask-example`
#: definitions moving to the definitional decorator, which emits the example's
#: `(: ...)` declaration from the annotation and its equation from the body.
#: The compiled clauses are the same clauses; the charge is @m.define's per-name
#: admission, the three reflection facts the container door never writes
#: (`(defined &self <name>)`, `(effect <name> immutable)` and
#: `(source-span &self <name> ...)`), measured at ~1.6k inferences per decorated
#: name and paid once at decoration. Prior: ADDED 2026-08-22 at 95562 by the
#: wave-3 twin baseline.
BUDGET = 97384


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(add-atom &petta (dispatch-policy penguin NoMatchEnum NoMatchFail))
    # ... one per relation, through (dispatch-policy edge ...)
    for relation in FALLIBLE:
        yield m.eval(
            S["add-atom"](
                S["&petta"],
                S["dispatch-policy"](relation, S.NoMatchEnum, S.NoMatchFail),
            )
        )

    # (= (bird tweety) True)
    m += equation(S.bird(S.tweety)).to(TRUE)

    # (= (bird polly) True)
    m += equation(S.bird(S.polly)).to(TRUE)

    # (= (penguin polly) True)
    m += equation(S.penguin(S.polly)).to(TRUE)

    # !(test (collapse (not (penguin tweety))) ())
    yield m.eval(
        S.test(S.collapse(~S.penguin(S.tweety)), ())
    )

    # !(test (not-provable (penguin tweety)) True)
    yield m.eval(
        S.test(S["not-provable"](S.penguin(S.tweety)), TRUE)
    )

    # !(test (not-provable (penguin polly)) False)
    yield m.eval(
        S.test(S["not-provable"](S.penguin(S.polly)), FALSE)
    )

    # (= (flies $x) (and (bird $x) (not-provable (penguin $x))))
    m += equation(S.flies(V.x)).to(S.bird(V.x) & S["not-provable"](S.penguin(V.x)))

    # !(test (collapse (let True (flies $x) $x)) (tweety))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE, S.flies(V.x), V.x)),
            (S.tweety,))
    )

    # (= (student bill) True)
    m += equation(S.student(S.bill)).to(TRUE)

    # (= (married joe) True)
    m += equation(S.married(S.joe)).to(TRUE)

    # (= (unmarried-student $x)
    #    (and (not-provable (married $x)) (student $x)))
    m += equation(S["unmarried-student"](V.x)).to(
        S["not-provable"](S.married(V.x)) & S.student(V.x)
    )

    # !(test (collapse (let True (unmarried-student $x) $x)) (bill))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE, S["unmarried-student"](V.x), V.x)),
            (S.bill,))
    )

    # (= (two-but-not-one $x)
    #    (and (not-provable (== $x 1)) (let $x 2 True)))
    m += equation(S["two-but-not-one"](V.x)).to(S["not-provable"](V.x.eq(1)) & (
            S.let(V.x, 2, TRUE)))

    # !(test (collapse (let True (two-but-not-one $x) $x)) (2))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE, S["two-but-not-one"](V.x), V.x)),
            (2,))
    )

    # (= (invalid mc-tavish) True)
    m += equation(S.invalid(S["mc-tavish"])).to(TRUE)

    # (= (over-65 mc-tavish) True)
    m += equation(S["over-65"](S["mc-tavish"])).to(TRUE)

    # (= (over-65 mc-donald) True)
    m += equation(S["over-65"](S["mc-donald"])).to(TRUE)

    # (= (over-65 mc-duff) True)
    m += equation(S["over-65"](S["mc-duff"])).to(TRUE)

    # (= (paid-up mc-tavish) True)
    m += equation(S["paid-up"](S["mc-tavish"])).to(TRUE)

    # (= (paid-up mc-donald) True)
    m += equation(S["paid-up"](S["mc-donald"])).to(TRUE)

    # (= (pension $p invalid-pension) (invalid $p))
    m += equation(S.pension(V.p, S["invalid-pension"])).to(S.invalid(V.p))

    # (= (pension $p old-age-pension) (and (over-65 $p) (paid-up $p)))
    m += equation(S.pension(V.p, S["old-age-pension"])).to(S["over-65"](V.p) & S["paid-up"](V.p))

    # (= (pension $p supplementary-benefit) (over-65 $p))
    m += equation(S.pension(V.p, S["supplementary-benefit"])).to(S["over-65"](V.p))

    # (= (entitlement $p $what) (pension $p $what))
    m += equation(S.entitlement(V.p, V.what)).to(S.pension(V.p, V.what))

    # (= (entitlement $p nothing) (not-provable (pension $p $any)))
    m += equation(S.entitlement(V.p, S.nothing)).to(S["not-provable"](S.pension(V.p, V.any)))

    # !(test (collapse (let True (entitlement mc-tavish $w) $w))
    #        (invalid-pension old-age-pension supplementary-benefit))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S.entitlement(S["mc-tavish"], V.w),
                    V.w)),
            (S["invalid-pension"], S["old-age-pension"], S["supplementary-benefit"]))
    )

    # !(test (collapse (let True (entitlement mc-duff $w) $w))
    #        (supplementary-benefit))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE, S.entitlement(S["mc-duff"], V.w), V.w)),
            (S["supplementary-benefit"],))
    )

    # !(test (collapse (let True (entitlement someone-else $w) $w)) (nothing))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S.entitlement(S["someone-else"], V.w),
                    V.w)),
            (S.nothing,))
    )

    # (= (edge a b) True)
    m += equation(S.edge(S.a, S.b)).to(TRUE)

    # (= (edge b c) True)
    m += equation(S.edge(S.b, S.c)).to(TRUE)

    # (= (has-no-outgoing $x) (not-provable (edge $x $y)))
    m += equation(S["has-no-outgoing"](V.x)).to(S["not-provable"](S.edge(V.x, V.y)))

    # !(test (has-no-outgoing c) True)
    yield m.eval(S.test(S["has-no-outgoing"](S.c), TRUE))

    # !(test (has-no-outgoing a) False)
    yield m.eval(S.test(S["has-no-outgoing"](S.a), FALSE))

    # !(test (collapse (let True (has-no-outgoing $x) (let $x c $x))) (c))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["has-no-outgoing"](V.x),
                    S.let(V.x, S.c, V.x))),
            (S.c,))
    )

    # !(test (collapse (let True (has-no-outgoing $x) (let $x zzz $x))) (zzz))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["has-no-outgoing"](V.x),
                    S.let(V.x, S.zzz, V.x))),
            (S.zzz,))
    )

    # !(test (collapse (let True (has-no-outgoing $x) (let $x a $x))) ())
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["has-no-outgoing"](V.x),
                    S.let(V.x, S.a, V.x))),
            ())
    )

    # !(test (dif 1 2) True)
    yield m.eval(S.test(S.dif(1, 2), TRUE))

    # !(test (collapse (let True (dif $q 5) (let $q 6 $q))) (6))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S.dif(V.q, 5),
                    S.let(V.q, 6, V.q))),
            (6,))
    )

    # !(test (collapse (let True (dif $q 5) (let $q 5 $q))) ())
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S.dif(V.q, 5),
                    S.let(V.q, 5, V.q))),
            ())
    )

    # !(test (!= 1 2) True)
    yield m.eval(S.test((NE, 1, 2), TRUE))

    # !(test (!= 1 1) False)
    yield m.eval(S.test((NE, 1, 1), FALSE))

    # !(test (collapse (let True (!= $r 5) (let $r 5 $r))) (5))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    (NE, V.r, 5),
                    S.let(V.r, 5, V.r))),
            (5,))
    )

    # (= (marks carol) 90)
    m += equation(S.marks(S.carol)).to(90)

    # (= (marks carol) 30)
    m += equation(S.marks(S.carol)).to(30)

    # (= (marks dave) 10)
    m += equation(S.marks(S.dave)).to(10)

    # (= (marks dave) 20)
    m += equation(S.marks(S.dave)).to(20)

    # (= (any-pass $w) (let $m (marks $w) (> $m 50)))
    m += equation(S["any-pass"](V.w)).to(S.let(V.m, S.marks(V.w), V.m > 50))

    # !(test (collapse (any-pass carol)) (True False))
    yield m.eval(
        S.test(S.collapse(S["any-pass"](S.carol)),
            (True, False))
    )

    # !(test (not-provable (any-pass carol)) False)
    yield m.eval(
        S.test(S["not-provable"](S["any-pass"](S.carol)), FALSE)
    )

    # !(test (not-provable (any-pass dave)) True)
    yield m.eval(
        S.test(S["not-provable"](S["any-pass"](S.dave)), TRUE)
    )

    # !(test (not-provable (any-pass nobody)) True)
    yield m.eval(
        S.test(S["not-provable"](S["any-pass"](S.nobody)), TRUE)
    )

    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w dave $w)))
    #        (dave))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["any-pass"](V.w)),
                    S.let(V.w, S.dave, V.w))),
            (S.dave,))
    )

    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w carol $w))) ())
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["any-pass"](V.w)),
                    S.let(V.w, S.carol, V.w))),
            ())
    )

    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w erin $w)))
    #        (erin))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["any-pass"](V.w)),
                    S.let(V.w, S.erin, V.w))),
            (S.erin,))
    )

    # !(bind! &kin (new-space))
    yield m.eval(S["bind!"](S["&kin"], S["new-space"]()))

    # !(add-atom &kin (parent alice bob))
    yield m.eval(S["add-atom"](S["&kin"], S.parent(S.alice, S.bob)))

    # !(add-atom &kin (parent carol dave))
    yield m.eval(S["add-atom"](S["&kin"], S.parent(S.carol, S.dave)))

    # (= (has-child $x) (match &kin (parent $x $y) True))
    m += equation(S["has-child"](V.x)).to(S.match(S["&kin"], S.parent(V.x, V.y), TRUE))

    # !(test (not-provable (has-child alice)) False)
    yield m.eval(
        S.test(S["not-provable"](S["has-child"](S.alice)), FALSE)
    )

    # !(test (not-provable (has-child bob)) True)
    yield m.eval(
        S.test(S["not-provable"](S["has-child"](S.bob)), TRUE)
    )

    # !(test (not-provable (has-child stranger)) True)
    yield m.eval(
        S.test(S["not-provable"](S["has-child"](S.stranger)), TRUE)
    )

    # !(test (collapse (let True (not-provable (has-child $w)) (let $w bob $w)))
    #        (bob))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["has-child"](V.w)),
                    S.let(V.w, S.bob, V.w))),
            (S.bob,))
    )

    # !(test (collapse (let True (not-provable (has-child $w)) (let $w alice $w))) ())
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["has-child"](V.w)),
                    S.let(V.w, S.alice, V.w))),
            ())
    )

    # !(test (collapse (let True (not-provable (has-child $w)) (let $w nobody $w)))
    #        (nobody))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["has-child"](V.w)),
                    S.let(V.w, S.nobody, V.w))),
            (S.nobody,))
    )

    # (= (band $n) (case $n ((90 True) (40 False))))
    m += equation(S.band(V.n)).to(S.case(V.n, ((90, True), (40, False))))

    # !(test (not-provable (band 90)) False)
    yield m.eval(S.test(S["not-provable"](S.band(90)), FALSE))

    # !(test (not-provable (band 40)) True)
    yield m.eval(S.test(S["not-provable"](S.band(40)), TRUE))

    # !(test (not-provable (band 55)) True)
    yield m.eval(S.test(S["not-provable"](S.band(55)), TRUE))

    # !(test (not-provable (superpose (False True))) False)
    yield m.eval(
        S.test(S["not-provable"](S.superpose((False, True))),
            FALSE)
    )

    # !(test (not-provable (superpose (False False))) True)
    yield m.eval(
        S.test(S["not-provable"](S.superpose((False, False))),
            TRUE)
    )

    # !(test (not-provable (superpose ())) True)
    yield m.eval(
        S.test(S["not-provable"](S.superpose(())), TRUE)
    )

    # !(test (not-provable (> 1 2)) True)
    yield m.eval(S.test(S["not-provable"]((GT, 1, 2)), TRUE))

    # !(test (not-provable (> 2 1)) False)
    yield m.eval(S.test(S["not-provable"]((GT, 2, 1)), FALSE))

    # !(test (not-provable (== 1 1)) False)
    yield m.eval(S.test(S["not-provable"]((EQ, 1, 1)), FALSE))

    # !(test (not-provable (#< 5 1)) True)
    yield m.eval(S.test(S["not-provable"](S["#<"](5, 1)), TRUE))

    # !(test (collapse (let True (not-provable (#< $x 5)) (let $x 7 $x))) (7))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["#<"](V.x, 5)),
                    S.let(V.x, 7, V.x))),
            (7,))
    )

    # !(test (collapse (let True (not-provable (#< $x 5)) (let $x 3 $x))) ())
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["#<"](V.x, 5)),
                    S.let(V.x, 3, V.x))),
            ())
    )

    # !(test (collapse (let True (not-provable (#= $y 4)) (let $y 9 $y))) (9))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["#="](V.y, 4)),
                    S.let(V.y, 9, V.y))),
            (9,))
    )

    # !(test (collapse (let True (not-provable (#= $y 4)) (let $y 4 $y))) ())
    yield m.eval(
        S.test(S.collapse(S.let(TRUE,
                    S["not-provable"](S["#="](V.y, 4)),
                    S.let(V.y, 4, V.y))),
            ())
    )

    @m.define(name="mask-example-double")
    def mask_example_double(x: int) -> int:
        # (: mask-example-double (-> Number Number))
        # (= (mask-example-double $x) (* $x 2))
        return x * 2

    @m.define(name="mask-example-holds")
    def mask_example_holds(_x: Atom = 10) -> bool:
        # (: mask-example-holds (-> Atom Bool))
        # (= (mask-example-holds 10) True)
        return True

    # !(add-atom &petta (dispatch-policy mask-example-holds NoMatchEnum NoMatchFail))
    yield m.eval(
        S["add-atom"](S["&petta"],
            S["dispatch-policy"](S["mask-example-holds"], S.NoMatchEnum, S.NoMatchFail))
    )

    # !(test (not-provable (mask-example-holds (mask-example-double 5))) True)
    yield m.eval(
        S.test(S["not-provable"](S["mask-example-holds"](S["mask-example-double"](5))),
            TRUE)
    )

    # !(test (not-provable (mask-example-holds 10)) False)
    yield m.eval(
        S.test(S["not-provable"](S["mask-example-holds"](10)), FALSE)
    )

    # !(test (collapse (mask-example-holds (mask-example-double 5))) ())
    yield m.eval(
        S.test(S.collapse(S["mask-example-holds"](S["mask-example-double"](5))),
            ())
    )
