"""Purpose: examples/reasoning/constructive_negation.metta in Python: negation that answers.

`not-provable` answers True for what an expression cannot prove and False for
what it can, and over an infinite domain it CONSTRAINS rather than enumerates.
The file walks that from the two defects it repairs, through `dif` against
`!=`, quantifying over a generator, negating a space query and a `case`, to
negating a CLP(FD) bound. Fifty claims, each an `assert`.

Two spellings recur and both are the same wall. `(collapse X)` dissolves into
the answer list `m.eval` already hands back, so it is gone; but
`(let True (f $x) $x)` does not, because `$x` is a BINDING and an evaluation
answers VALUES. No Python door hands back an evaluation's bindings, so the
variable has to leave through the term, and that is what every `S.let(TRUE,
..., ...)` below is doing. The other recurring wall is the equation bodies:
they are MeTTa's `and`, a generate-and-test where Python's `and`
short-circuits on truthiness, and a `case`, and a `match` against a NAMED
space, so they stay at the container door (residue, P14.4).

The two `mask-example` definitions ARE ordinary Python functions: the
annotations are the example's `(: ...)` declarations, `int` is Number and
`Atom` is the metatype that keeps the argument unreduced, and `10` as a
parameter default is the equation's head pattern rather than a Python default.

Where an operator builds the term it is used: `~` is `not`, `&` is `and`, `>`
and `*` are themselves, and `x.eq(y)` is the equality TERM because `==` between
atoms is Python's own structural equality. Where it cannot, the tuple is:
MeTTa's `(> 1 2)` reads as `(GT, 1, 2)`, because `1 > 2` computes and
`V.r != 5` compares the atom rather than building `(!= $r 5)`.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, REFLECTION_SPACE, TRUE, Atom, S, V, equation

#: Why this file sits below the top rung: every equation body is MeTTa's `and`,
#: a `case`, or a `match` against a named space, and every claim that reads a
#: binding has to carry it out through a `let`.
RUNG = "the equation bodies are MeTTa's and, a case, and a match against a named space; and a claim that reads a binding carries it out through a let, which no Python door replaces"

#: The three comparison heads this file needs as TERMS over operands Python's
#: own operators would compute on, or would build the wrong term for: `!=` on
#: atoms is structural inequality and `==` is structural equality.
NE, GT, EQ = S["!="], S[">"], S["=="]

#: The nine relations the example gives NoMatchFail, so a missing proof is
#: relational failure instead of the P3 residual-call dispatch value.
FALLIBLE = (S.penguin, S.bird, S.student, S.married, S.invalid,
            S["over-65"], S["paid-up"], S.marks, S.edge)

#: The kinship space the negated space query reads. Its name is written because
#: an equation body names its space; the handle is built from that name.
KIN = S["&kin"]  # rung: an equation body carries a space NAME, not a handle

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 97384 to 80623, -16761 (-17.2%), by the twin contract
#: change: fifty `test` wrappers and twenty-five `collapse` calls left the
#: engine for Python's own `assert` and the answer list, and ten `add-atom`
#: forms became `space += atom`. The two `mask-example` definitions were already
#: compiled at the previous pin, so `@m.define`'s per-name admission is inside
#: both figures. Against the example's 158187 the ratio is 0.5097 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/reasoning/constructive_negation.metta`]. Prior: RE-PINNED at 97384,
#: +1822, when the two `mask-example` definitions gained the decorator (~1.6k
#: inferences of admission each); ADDED 2026-08-22 at 95562 by the wave-3 twin
#: baseline.
BUDGET = 80623


def twin(m):
    """Walk negation from what `not` cannot say to a constrained domain."""
    reflection = m.space(REFLECTION_SPACE)
    for relation in FALLIBLE:
        reflection += S["dispatch-policy"](relation, S.NoMatchEnum, S.NoMatchFail)

    m += equation(S.bird(S.tweety)).to(TRUE)
    m += equation(S.bird(S.polly)).to(TRUE)
    m += equation(S.penguin(S.polly)).to(TRUE)

    # `not` is a boolean function, and an expression no equation matches does
    # not reduce to False: it stays as data, so there is nothing to negate.
    assert m.eval(~S.penguin(S.tweety)) == []

    # not-provable can say it, in both directions.
    assert m.eval(S["not-provable"](S.penguin(S.tweety))) == [True]
    assert m.eval(S["not-provable"](S.penguin(S.polly))) == [False]

    # Default reasoning: birds fly unless they are penguins. The negation runs
    # with $x already bound by (bird $x).
    m += equation(S.flies(V.x)).to(S.bird(V.x) & S["not-provable"](S.penguin(V.x)))
    assert m.eval(S.let(TRUE, S.flies(V.x), V.x)) == [S.tweety]

    # The first defect, from The Art of Prolog 2nd ed. section 11.3 page 199:
    # Prolog FAILS on unmarried_student(X), ignoring that X=bill is implied,
    # because the negation runs first with X unbound and cannot bind.
    m += equation(S.student(S.bill)).to(TRUE)
    m += equation(S.married(S.joe)).to(TRUE)
    m += equation(S["unmarried-student"](V.x)).to(
        S["not-provable"](S.married(V.x)) & S.student(V.x)
    )
    assert m.eval(S.let(TRUE, S["unmarried-student"](V.x), V.x)) == [S.bill]

    # The second, same page: `not (X=1), X=2` fails in Prolog although X=2 is a
    # solution. Here the negation leaves a disequality behind instead of a
    # failed proof, and the later binding satisfies it.
    m += equation(S["two-but-not-one"](V.x)).to(
        S["not-provable"](V.x.eq(1)) & S.let(V.x, 2, TRUE)
    )
    assert m.eval(S.let(TRUE, S["two-but-not-one"](V.x), V.x)) == [2]

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
    m += equation(S.entitlement(V.p, S.nothing)).to(S["not-provable"](S.pension(V.p, V.any)))

    assert m.eval(S.let(TRUE, S.entitlement(S["mc-tavish"], V.w), V.w)) == [
        S["invalid-pension"], S["old-age-pension"], S["supplementary-benefit"],
    ]
    assert m.eval(S.let(TRUE, S.entitlement(S["mc-duff"], V.w), V.w)) == [
        S["supplementary-benefit"]
    ]
    assert m.eval(S.let(TRUE, S.entitlement(S["someone-else"], V.w), V.w)) == [S.nothing]

    # "Which node has no outgoing edge" has infinitely many answers, so the
    # answer is a constraint rather than a list.
    m += equation(S.edge(S.a, S.b)).to(TRUE)
    m += equation(S.edge(S.b, S.c)).to(TRUE)
    m += equation(S["has-no-outgoing"](V.x)).to(S["not-provable"](S.edge(V.x, V.y)))

    assert m.eval(S["has-no-outgoing"](S.c)) == [True]
    assert m.eval(S["has-no-outgoing"](S.a)) == [False]

    # And the constraint is live: bind the variable afterwards and it decides.
    assert m.eval(S.let(TRUE, S["has-no-outgoing"](V.x), S.let(V.x, S.c, V.x))) == [S.c]
    assert m.eval(S.let(TRUE, S["has-no-outgoing"](V.x), S.let(V.x, S.zzz, V.x))) == [S.zzz]
    assert m.eval(S.let(TRUE, S["has-no-outgoing"](V.x), S.let(V.x, S.a, V.x))) == []

    # dif is the constraint the duals are built from, and it holds for as long
    # as the answer does.
    assert m.eval(S.dif(1, 2)) == [True]
    assert m.eval(S.let(TRUE, S.dif(V.q, 5), S.let(V.q, 6, V.q))) == [6]
    assert m.eval(S.let(TRUE, S.dif(V.q, 5), S.let(V.q, 5, V.q))) == []

    # `!=` asks whether two terms are identical NOW, so on an unbound variable
    # it says True and lets a later binding contradict it.
    assert m.eval((NE, 1, 2)) == [True]
    assert m.eval((NE, 1, 1)) == [False]
    assert m.eval(S.let(TRUE, (NE, V.r, 5), S.let(V.r, 5, V.r))) == [5]

    # A let is True when SOME answer of its value makes its body True, so it is
    # not True when EVERY one of them fails: a universal quantification over a
    # generator rather than over every term there is.
    m += equation(S.marks(S.carol)).to(90)
    m += equation(S.marks(S.carol)).to(30)
    m += equation(S.marks(S.dave)).to(10)
    m += equation(S.marks(S.dave)).to(20)
    m += equation(S["any-pass"](V.w)).to(S.let(V.m, S.marks(V.w), V.m > 50))

    assert m.eval(S["any-pass"](S.carol)) == [True, False]
    assert m.eval(S["not-provable"](S["any-pass"](S.carol))) == [False]
    assert m.eval(S["not-provable"](S["any-pass"](S.dave))) == [True]

    # A value with no answer leaves the let with no answer, so it is not True.
    assert m.eval(S["not-provable"](S["any-pass"](S.nobody))) == [True]

    # And the answer stays constructive: what the generator narrows a variable
    # to belongs IN the answer rather than being quantified away.
    assert m.eval(S.let(TRUE, S["not-provable"](S["any-pass"](V.w)),
                        S.let(V.w, S.dave, V.w))) == [S.dave]
    assert m.eval(S.let(TRUE, S["not-provable"](S["any-pass"](V.w)),
                        S.let(V.w, S.carol, V.w))) == []
    assert m.eval(S.let(TRUE, S["not-provable"](S["any-pass"](V.w)),
                        S.let(V.w, S.erin, V.w))) == [S.erin]

    # A match over a space is a generator too, and better behaved than a let: a
    # space is finite, so what it narrows a variable to is an enumeration and
    # never a constraint. $y is local to the match and $x is not, which is the
    # whole difference between "has a child" and "who has no child".
    kin = m.space(KIN.name)
    kin += S.parent(S.alice, S.bob)
    kin += S.parent(S.carol, S.dave)
    m += equation(S["has-child"](V.x)).to(S.match(KIN, S.parent(V.x, V.y), TRUE))

    assert m.eval(S["not-provable"](S["has-child"](S.alice))) == [False]
    assert m.eval(S["not-provable"](S["has-child"](S.bob))) == [True]
    assert m.eval(S["not-provable"](S["has-child"](S.stranger))) == [True]

    assert m.eval(S.let(TRUE, S["not-provable"](S["has-child"](V.w)),
                        S.let(V.w, S.bob, V.w))) == [S.bob]
    assert m.eval(S.let(TRUE, S["not-provable"](S["has-child"](V.w)),
                        S.let(V.w, S.alice, V.w))) == []
    assert m.eval(S.let(TRUE, S["not-provable"](S["has-child"](V.w)),
                        S.let(V.w, S.nobody, V.w))) == [S.nobody]

    # A case commits to the FIRST pattern its key matches, so its dual is the
    # same chain with each branch dualised, ending in True: a key that matches
    # no pattern leaves the case with no answer, and no answer is not True.
    m += equation(S.band(V.n)).to(S.case(V.n, ((90, TRUE), (40, FALSE))))

    assert m.eval(S["not-provable"](S.band(90))) == [False]
    assert m.eval(S["not-provable"](S.band(40))) == [True]
    assert m.eval(S["not-provable"](S.band(55))) == [True]

    # A superpose answers each element in turn, so it is not True exactly when
    # none of them is. A collapse yields a LIST, so it is never True at all.
    assert m.eval(S["not-provable"](S.superpose((FALSE, TRUE)))) == [False]
    assert m.eval(S["not-provable"](S.superpose((FALSE, FALSE)))) == [True]
    assert m.eval(S["not-provable"](S.superpose(()))) == [True]

    # A form whose negation cannot be computed soundly RAISES rather than
    # answering from an incomplete dual. The comparisons are the exception,
    # because each one's opposite is another comparison.
    assert m.eval(S["not-provable"]((GT, 1, 2))) == [True]
    assert m.eval(S["not-provable"]((GT, 2, 1))) == [False]
    assert m.eval(S["not-provable"]((EQ, 1, 1))) == [False]

    # The # family is CLP(FD), so negating a bound POSTS the opposite bound and
    # leaves it standing: it cuts the domain down instead of enumerating it.
    assert m.eval(S["not-provable"](S["#<"](5, 1))) == [True]
    assert m.eval(S.let(TRUE, S["not-provable"](S["#<"](V.x, 5)),
                        S.let(V.x, 7, V.x))) == [7]
    assert m.eval(S.let(TRUE, S["not-provable"](S["#<"](V.x, 5)),
                        S.let(V.x, 3, V.x))) == []
    assert m.eval(S.let(TRUE, S["not-provable"](S["#="](V.y, 4)),
                        S.let(V.y, 9, V.y))) == [9]
    assert m.eval(S.let(TRUE, S["not-provable"](S["#="](V.y, 4)),
                        S.let(V.y, 4, V.y))) == []

    # A declaration can make an argument data, and both the positive and the
    # constructive-negation path preserve the written term instead of reducing
    # it. `10` as a parameter default is the equation's head pattern.
    @m.define(name="mask-example-double")
    def mask_example_double(x: int) -> int:
        """Twice x."""
        return x * 2

    @m.define(name="mask-example-holds")
    def mask_example_holds(_x: Atom = 10) -> bool:
        """True of the written term 10, and of nothing else."""
        return True

    reflection += S["dispatch-policy"](S["mask-example-holds"], S.NoMatchEnum, S.NoMatchFail)

    assert m.eval(
        S["not-provable"](S["mask-example-holds"](S["mask-example-double"](5)))
    ) == [True]
    assert m.eval(S["not-provable"](S["mask-example-holds"](10))) == [False]
    assert m.eval(S["mask-example-holds"](S["mask-example-double"](5))) == []
