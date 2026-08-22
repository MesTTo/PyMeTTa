"""The Python twin of examples/libraries/foreign_rules.metta.

A foreign space that holds RULES, not only facts: an equation added to a
provider-backed space compiles the way a native one does, so the call reduces
instead of answering itself.

Every equation here is DATA the source hands to `add-atom`, so each is built
with `equation(...).to(...)` and passed to the form: that is the same builder in
the datum position it takes in the pattern position, which is what makes an
equation ordinary knowledge rather than a special form. `(metta $atom $type
$space)` is how you evaluate IN a space, so every assertion names `&rule_demo`.

`(* 2 $x)` and `(> $x 0)` are built by Python's own operators, because an
operand that is a variable makes the operator a builder. The `(* 2 3)` inside
`(+ 1 (* 2 3))` is over two ground numbers, where the same operator is
arithmetic and answers 6 before any term exists, so it names its head instead.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 48124 to 48124, +0 (+0.00%), by the P14 twin-style
#: rewrite: the twin's atoms are unchanged: every equation here is DATA the
#: source hands to add-atom, and equation(...).to(...) builds what
#: S["="](...) built. Prior: ADDED 2026-08-22 at 48124 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 48124

#: The space under test, named once because every form below evaluates in it.
DEMO = S["&rule_demo"]
UNDEFINED = S["%Undefined%"]


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_import))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_import)))
    # !(import_prolog_functions_from_file "./examples/libraries/_fixtures/rule_provider.pl" ())
    yield m.eval(
        S.import_prolog_functions_from_file(
            val("./examples/libraries/_fixtures/rule_provider.pl"), ()
        )
    )

    # A rule, added to the foreign space, evaluating. A rule belongs to the
    # space that holds it, exactly as a native named space's equations belong
    # to it.
    # !(add-atom &rule_demo (= (fdouble $x) (* 2 $x)))
    yield m.eval(S["add-atom"](DEMO, equation(S.fdouble(V.x)).to(2 * V.x)))
    # !(test (metta (fdouble 21) %Undefined% &rule_demo) 42)
    yield m.eval(S.test(S.metta(S.fdouble(21), UNDEFINED, DEMO), 42))

    # Several equations for one name are an answer SET, which is what MeTTa
    # promises. sort-atom because a set has no order.
    # !(add-atom &rule_demo (= (fpick) one))
    yield m.eval(S["add-atom"](DEMO, equation(S.fpick()).to(S.one)))
    # !(add-atom &rule_demo (= (fpick) two))
    yield m.eval(S["add-atom"](DEMO, equation(S.fpick()).to(S.two)))
    # !(test (sort-atom (collapse (metta (fpick) %Undefined% &rule_demo))) (one two))
    yield m.eval(
        S.test(
            S["sort-atom"](S.collapse(S.metta(S.fpick(), UNDEFINED, DEMO))),
            (S.one, S.two),
        )
    )

    # A body that is not a call IS the answer, the way a native equation with a
    # bare atom body behaves.
    # !(add-atom &rule_demo (= (fplain) settled))
    yield m.eval(S["add-atom"](DEMO, equation(S.fplain()).to(S.settled)))
    # !(test (metta (fplain) %Undefined% &rule_demo) settled)
    yield m.eval(S.test(S.metta(S.fplain(), UNDEFINED, DEMO), S.settled))

    # A body is evaluated FURTHER, so a nested call is evaluated inside out.
    # This is the case that decided the design: reading evaluation as "match the
    # space for (= (f Args) $body) and reduce $body" is the naive reading, and
    # here that shows up as (* 2 3) reaching + as a list instead of as 6.
    # !(add-atom &rule_demo (= (fnest) (+ 1 (* 2 3))))
    yield m.eval(
        S["add-atom"](DEMO, equation(S.fnest()).to(1 + S["*"](2, 3)))
    )
    # !(test (metta (fnest) %Undefined% &rule_demo) 7)
    yield m.eval(S.test(S.metta(S.fnest(), UNDEFINED, DEMO), 7))

    # Recursion, and if evaluating only the branch it takes. Neither is special
    # here: the equation compiles, so it recurses the way any compiled equation
    # does.
    # !(add-atom &rule_demo (= (ffact $x) (if (> $x 0) (* $x (ffact (- $x 1))) 1)))
    yield m.eval(
        S["add-atom"](
            DEMO,
            equation(S.ffact(V.x)).to(
                S["if"](V.x > 0, V.x * S.ffact(V.x - 1), 1)
            ),
        )
    )
    # !(test (metta (ffact 5) %Undefined% &rule_demo) 120)
    yield m.eval(S.test(S.metta(S.ffact(5), UNDEFINED, DEMO), 120))

    # And the space is still a data source. Holding rules is an addition, not a
    # replacement, which is the whole of what "both" means.
    # !(add-atom &rule_demo (edge a b))
    yield m.eval(S["add-atom"](DEMO, S.edge(S.a, S.b)))
    # !(test (collapse (match &rule_demo (edge $x $y) ($x $y))) ((a b)))
    yield m.eval(
        S.test(
            S.collapse(S.match(DEMO, S.edge(V.x, V.y), (V.x, V.y))),
            ((S.a, S.b),),
        )
    )
