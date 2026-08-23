"""Purpose: examples/reasoning/constructive_negation.metta in Python: negation that answers.

`not-provable` answers True for what an expression cannot prove and False for
what it can, and over an infinite domain it CONSTRAINS rather than enumerates.
The file walks that from the two defects it repairs, through `dif` against
`!=`, quantifying over a generator, negating a space query and a `case`, to
negating a CLP(FD) bound. Fifty claims, each an `assert`.

Two spellings recur. `(collapse X)` dissolves into the answer list a call
already hands back, so it is gone. `(let True (f $x) $x)` is `solve`, the
relational let: it evaluates the subject, unifies the answer with the pattern,
and hands back the subject's own variables, which is how `$x` leaves. Where the
example's template is itself a `let`, binding a SECOND variable to test the
constraint that the first one left standing, the term stays: `solve` derives
its template from the subject and has no spelling for that (residue, P14.7).

The equation bodies stay at the container door: they are MeTTa's `and`, a
generate-and-test where Python's `and` short-circuits on truthiness, and a
`case`, and a `match` against a space (residue, P14.4).

The two `mask-example` definitions ARE ordinary Python functions: the
annotations are the example's `(: ...)` declarations, `int` is Number and
`Atom` is the metatype that keeps the argument unreduced, and `10` as a
parameter default is the equation's head pattern rather than a Python default.

Where an operator builds the term it is used: `~` is `not`, `&` is `and`, `>`
and `*` are themselves, and `x.eq(y)` is the equality TERM because `==` between
atoms is Python's own structural equality. Where it cannot, the head is named:
`(> 1 2)` and `(< 5 1)` have GROUND left operands, which Python's comparisons
mirror rather than build, and `V.r != 5` compares the atom rather than building
`(!= $r 5)`.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import petta
from petta import FALSE, TRUE, Atom, S, V, equation, fn

#: The three comparison heads this file needs as TERMS over operands Python's
#: own operators would compute on, or would build the wrong term for: `!=` on
#: atoms is structural inequality and `==` is structural equality.
#:
#: Known issue: `<` builds no term at all now that appendix stamp 6 gave
#: `Atom.__lt__` to the engine's sort order, and none of the four comparisons
#: has a right-hand method, so a GROUND left operand mirrors instead of
#: building. `(> 1 2)` should read `1 > 2` and build, not compute.
NE, GT, EQ = fn["!="], fn[">"], fn["=="]

#: The nine relations the example gives NoMatchFail, so a missing proof is
#: relational failure instead of the P3 residual-call dispatch value.
FALLIBLE = (S.penguin, S.bird, S.student, S.married, S.invalid,
            S["over-65"], S["paid-up"], S.marks, S.edge)

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Walk negation from what `not` cannot say to a constrained domain."""
    reflection = petta.reflection
    for relation in FALLIBLE:
        reflection += S["dispatch-policy"](relation, S.NoMatchEnum, S.NoMatchFail)

    m += equation(S.bird(S.tweety)).to(TRUE)
    m += equation(S.bird(S.polly)).to(TRUE)
    m += equation(S.penguin(S.polly)).to(TRUE)

    # `not` is a boolean function, and an expression no equation matches does
    # not reduce to False: it stays as data, so there is nothing to negate.
    assert m.eval(~S.penguin(S.tweety)) == []

    # not-provable can say it, in both directions.
    assert m.fn.not_provable(S.penguin(S.tweety)) == [True]
    assert m.fn.not_provable(S.penguin(S.polly)) == [False]

    # Default reasoning: birds fly unless they are penguins. The negation runs
    # with $x already bound by (bird $x).
    m += equation(S.flies(V.x)).to(S.bird(V.x) & fn.not_provable(S.penguin(V.x)))
    assert m.solve(TRUE, S.flies(V.x)).x == S.tweety

    # The first defect, from The Art of Prolog 2nd ed. section 11.3 page 199:
    # Prolog FAILS on unmarried_student(X), ignoring that X=bill is implied,
    # because the negation runs first with X unbound and cannot bind.
    m += equation(S.student(S.bill)).to(TRUE)
    m += equation(S.married(S.joe)).to(TRUE)
    m += equation(S["unmarried-student"](V.x)).to(
        fn.not_provable(S.married(V.x)) & S.student(V.x)
    )
    assert m.solve(TRUE, S["unmarried-student"](V.x)).x == S.bill

    # The second, same page: `not (X=1), X=2` fails in Prolog although X=2 is a
    # solution. Here the negation leaves a disequality behind instead of a
    # failed proof, and the later binding satisfies it.
    m += equation(S["two-but-not-one"](V.x)).to(
        fn.not_provable(V.x.eq(1)) & fn.let(V.x, 2, TRUE)  # rung: a let that BINDS inside a stored body, where Python's assignment binds a Python name (P14.4)
    )
    assert m.solve(TRUE, S["two-but-not-one"](V.x)).x == 2

    # Section 11.5 page 207, the welfare default. `$any` occurs nowhere else,
    # so it means "no pension at all" rather than "some Y that is not one": a
    # variable only the negation reads is universal under it.
    m += equation(S.invalid(S["mc-tavish"])).to(TRUE)
    for person in (S["mc-tavish"], S["mc-donald"], S["mc-duff"]):
        m += equation(S["over-65"](person)).to(TRUE)
    for person in (S["mc-tavish"], S["mc-donald"]):
        m += equation(S["paid-up"](person)).to(TRUE)

    m += equation(S.pension(V.p, S["invalid-pension"])).to(S.invalid(V.p))
    m += equation(S.pension(V.p, S["old-age-pension"])).to(S["over-65"](V.p) & S["paid-up"](V.p))
    m += equation(S.pension(V.p, S["supplementary-benefit"])).to(S["over-65"](V.p))
    m += equation(S.entitlement(V.p, V.what)).to(S.pension(V.p, V.what))
    m += equation(S.entitlement(V.p, S.nothing)).to(fn.not_provable(S.pension(V.p, V.any)))

    assert m.solve(TRUE, S.entitlement(S["mc-tavish"], V.w)).w == [
        S["invalid-pension"], S["old-age-pension"], S["supplementary-benefit"],
    ]
    assert m.solve(TRUE, S.entitlement(S["mc-duff"], V.w)).w == S["supplementary-benefit"]
    assert m.solve(TRUE, S.entitlement(S["someone-else"], V.w)).w == S.nothing

    # "Which node has no outgoing edge" has infinitely many answers, so the
    # answer is a constraint rather than a list.
    m += equation(S.edge(S.a, S.b)).to(TRUE)
    m += equation(S.edge(S.b, S.c)).to(TRUE)
    m += equation(S["has-no-outgoing"](V.x)).to(fn.not_provable(S.edge(V.x, V.y)))

    assert m.fn.has_no_outgoing(S.c) == [True]
    assert m.fn.has_no_outgoing(S.a) == [False]

    # And the constraint is live: bind the variable afterwards and it decides.
    # The template is a second `let`, which is what `solve` has no spelling
    # for, so these three keep the term.
    assert m.eval(fn.let(TRUE, S["has-no-outgoing"](V.x), fn.let(V.x, S.c, V.x))) == [S.c]  # rung: the template BINDS a second variable, which solve derives from the subject (P14.7)
    assert m.eval(fn.let(TRUE, S["has-no-outgoing"](V.x), fn.let(V.x, S.zzz, V.x))) == [S.zzz]  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, S["has-no-outgoing"](V.x), fn.let(V.x, S.a, V.x))) == []  # rung: the same shape (P14.7)

    # dif is the constraint the duals are built from, and it holds for as long
    # as the answer does.
    assert m.fn.dif(1, 2) == [True]
    assert m.eval(fn.let(TRUE, S.dif(V.q, 5), fn.let(V.q, 6, V.q))) == [6]  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, S.dif(V.q, 5), fn.let(V.q, 5, V.q))) == []  # rung: the same shape (P14.7)

    # `!=` asks whether two terms are identical NOW, so on an unbound variable
    # it says True and lets a later binding contradict it.
    assert m.fn["!="](1, 2) == [True]
    assert m.fn["!="](1, 1) == [False]
    assert m.eval(fn.let(TRUE, NE(V.r, 5), fn.let(V.r, 5, V.r))) == [5]  # rung: the same shape (P14.7)

    # A let is True when SOME answer of its value makes its body True, so it is
    # not True when EVERY one of them fails: a universal quantification over a
    # generator rather than over every term there is.
    m += equation(S.marks(S.carol)).to(90)
    m += equation(S.marks(S.carol)).to(30)
    m += equation(S.marks(S.dave)).to(10)
    m += equation(S.marks(S.dave)).to(20)
    m += equation(S["any-pass"](V.w)).to(fn.let(V.m, S.marks(V.w), V.m > 50))  # rung: a let that BINDS inside a stored body (P14.4)

    assert m.fn.any_pass(S.carol) == [True, False]
    assert m.fn.not_provable(S["any-pass"](S.carol)) == [False]
    assert m.fn.not_provable(S["any-pass"](S.dave)) == [True]

    # A value with no answer leaves the let with no answer, so it is not True.
    assert m.fn.not_provable(S["any-pass"](S.nobody)) == [True]

    # And the answer stays constructive: what the generator narrows a variable
    # to belongs IN the answer rather than being quantified away.
    unprovable = fn.not_provable(S["any-pass"](V.w))
    assert m.eval(fn.let(TRUE, unprovable, fn.let(V.w, S.dave, V.w))) == [S.dave]  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, unprovable, fn.let(V.w, S.carol, V.w))) == []  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, unprovable, fn.let(V.w, S.erin, V.w))) == [S.erin]  # rung: the same shape (P14.7)

    # A match over a space is a generator too, and better behaved than a let: a
    # space is finite, so what it narrows a variable to is an enumeration and
    # never a constraint. $y is local to the match and $x is not, which is the
    # whole difference between "has a child" and "who has no child".
    kin = petta.space()
    kin += S.parent(S.alice, S.bob)
    kin += S.parent(S.carol, S.dave)
    m += equation(S["has-child"](V.x)).to(fn.match(kin, S.parent(V.x, V.y), TRUE))  # rung: a match INSIDE a stored body, where the subscript door is a Python read (P14.4)

    assert m.fn.not_provable(S["has-child"](S.alice)) == [False]
    assert m.fn.not_provable(S["has-child"](S.bob)) == [True]
    assert m.fn.not_provable(S["has-child"](S.stranger)) == [True]

    childless = fn.not_provable(S["has-child"](V.w))
    assert m.eval(fn.let(TRUE, childless, fn.let(V.w, S.bob, V.w))) == [S.bob]  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, childless, fn.let(V.w, S.alice, V.w))) == []  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, childless, fn.let(V.w, S.nobody, V.w))) == [S.nobody]  # rung: the same shape (P14.7)

    # A case commits to the FIRST pattern its key matches, so its dual is the
    # same chain with each branch dualised, ending in True: a key that matches
    # no pattern leaves the case with no answer, and no answer is not True.
    m += equation(S.band(V.n)).to(fn.case(V.n, ((90, TRUE), (40, FALSE))))  # rung: a `case` inside a stored body, where Python's match statement is the reader's spelling (P14.4)

    assert m.fn.not_provable(S.band(90)) == [False]
    assert m.fn.not_provable(S.band(40)) == [True]
    assert m.fn.not_provable(S.band(55)) == [True]

    # A superpose answers each element in turn, so it is not True exactly when
    # none of them is. A collapse yields a LIST, so it is never True at all.
    assert m.fn.not_provable(fn.superpose((FALSE, TRUE))) == [False]
    assert m.fn.not_provable(fn.superpose((FALSE, FALSE))) == [True]
    assert m.fn.not_provable(fn.superpose(())) == [True]

    # A form whose negation cannot be computed soundly RAISES rather than
    # answering from an incomplete dual. The comparisons are the exception,
    # because each one's opposite is another comparison.
    assert m.fn.not_provable(GT(1, 2)) == [True]
    assert m.fn.not_provable(GT(2, 1)) == [False]
    assert m.fn.not_provable(EQ(1, 1)) == [False]

    # The # family is CLP(FD), so negating a bound POSTS the opposite bound and
    # leaves it standing: it cuts the domain down instead of enumerating it.
    assert m.fn.not_provable(fn["#<"](5, 1)) == [True]
    below_five = fn.not_provable(fn["#<"](V.x, 5))
    assert m.eval(fn.let(TRUE, below_five, fn.let(V.x, 7, V.x))) == [7]  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, below_five, fn.let(V.x, 3, V.x))) == []  # rung: the same shape (P14.7)
    is_four = fn.not_provable(fn["#="](V.y, 4))
    assert m.eval(fn.let(TRUE, is_four, fn.let(V.y, 9, V.y))) == [9]  # rung: the same shape (P14.7)
    assert m.eval(fn.let(TRUE, is_four, fn.let(V.y, 4, V.y))) == []  # rung: the same shape (P14.7)

    # A declaration can make an argument data, and both the positive and the
    # constructive-negation path preserve the written term instead of reducing
    # it. `10` as a parameter default is the equation's head pattern.
    #
    # Known issue: `@m.define` takes the Python name VERBATIM, where the `S`,
    # `V` and `fn` factories map every underscore to a hyphen, so a hyphenated
    # MeTTa name needs `name=` at this one door. Both should read
    # `@m.define` over their Python names.
    @m.define(name="mask-example-double")
    def mask_example_double(x: int) -> int:
        """Twice x."""
        return x * 2

    @m.define(name="mask-example-holds")
    def mask_example_holds(_x: Atom = 10) -> bool:
        """True of the written term 10, and of nothing else."""
        return True

    reflection += S["dispatch-policy"](S["mask-example-holds"], S.NoMatchEnum, S.NoMatchFail)

    written = S["mask-example-holds"](S["mask-example-double"](5))
    assert m.fn.not_provable(written) == [True]
    assert m.fn.not_provable(S["mask-example-holds"](10)) == [False]
    assert m.eval(written) == []
