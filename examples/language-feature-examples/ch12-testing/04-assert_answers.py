"""examples/ch12-testing/04-assert_answers.metta in Python: the door every assertion reports through.

`assert-answers` and `assert-includes-answers` take a verdict, the call to
report, and two answer bags, and RAISE on a false verdict. Python already has
that shape, so `catch`, `unify` and `repr` all dissolve into
`except AssertionFailure as failure`: `.missing` is what was expected and
never produced, `.excess` what was produced and never expected, and `None`
for a side no comparison computed.

A `fn` call answers a lazy view, so a claim nobody pulls is a claim nobody
checks; `list` is what pulls it.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, S, V, arrow, equation, fn, typed
from metta.errors import AssertionFailure


def refused(claim, *arguments):
    """The AssertionFailure one false claim raises, or None where it held."""
    try:
        list(claim(*arguments))
    except AssertionFailure as failure:
        return failure
    return None


def twin(m):
    """A true verdict, four false ones, and an assertion form of our own."""
    answers = m.fn["assert-answers"]
    includes = m.fn["assert-includes-answers"]

    # A true verdict answers `true` and prints nothing.
    assert answers(TRUE, S.my_check(1), (1, 2), (1, 2)) == [True]
    assert answers(m.fn["=="](1, 1)[0], S.my_check(1), (1,), (1,)) == [True]

    # A false verdict raises, carrying the call AS WRITTEN and the two
    # directed bag differences.
    two_sided = refused(answers, FALSE, S.my_check(1), (1, 2), (1, 3))
    assert two_sided is not None
    assert (two_sided.missing, two_sided.excess) == ((3,), (2,))
    assert "(my-check 1)" in str(two_sided)

    # A repeated answer counts every time it appears, so (a a b) against
    # (a b b) leaves one b wanted and one a produced.
    bags = refused(
        answers, FALSE, S.checked(S.f(1)), (S.a, S.a, S.b), (S.a, S.b, S.b)
    )
    assert bags is not None
    assert (bags.missing, bags.excess) == ((S.b,), (S.a,))

    # The one-sided twin: an answer in excess of the expectation is legal, so
    # the excess side is ABSENT rather than empty.
    assert includes(TRUE, S.my_check(2), (1, 2, 3), (1, 2)) == [True]
    one_sided = refused(includes, FALSE, S.my_check(2), (1, 2), (7,))
    assert one_sided is not None
    assert one_sided.missing == (7,)
    assert one_sided.excess is None

    # Which is exactly the difference between the two shipped reports.
    equal = refused(m.fn.assertEqual, fn.add(1, 1), 3)
    assert equal is not None
    assert (equal.missing, equal.excess) == ((3,), (2,))
    contained = refused(m.fn.assertIncludes, fn.superpose((1, 2)), (7,))
    assert contained is not None
    assert (contained.missing, contained.excess) == ((7,), None)

    # Writing your own assertion form is those three steps and nothing else,
    # and the declaration is the load-bearing part: an assertion form HOLDS
    # the expression it is checking, or the argument is evaluated at the call
    # site and the form runs once per answer. The `Atom` annotation IS that
    # declaration: it publishes (: assert-sorted (-> Atom Bool)).
    # Built as DATA rather than compiled, because what this claim is about is
    # the equation's own shape: a `let*` with TWO bindings has no Python
    # spelling, two statements compile to two nested ones, and the stored
    # program would then differ from the original's. `equation(head).to(body)`
    # stores exactly what the file says.
    m += typed(S.assert_sorted, arrow(S.Atom, S.Bool))
    collapsed, ordered = V.answers, V.sorted

    @m.rules
    def sortedness(expression):
        """(= (assert-sorted $e) (let* ((...)) (assert-answers ...)))."""
        yield equation(S.assert_sorted(expression)).to(
            S["let*"](  # rung: the equation is DATA here, so its let* is a term
                (
                    (collapsed, S.collapse(expression)),  # rung: a stored collapse is a term
                    (ordered, S.sort_atom(collapsed)),
                ),
                S.assert_answers(
                    S["=="](collapsed, ordered),
                    S.assert_sorted(expression),
                    collapsed,
                    ordered,
                ),
            )
        )

    assert m.fn.assert_sorted(fn.superpose((1, 2, 3))) == [True]
    unsorted = refused(m.fn.assert_sorted, fn.superpose((3, 1, 2)))
    assert unsorted is not None
    assert "(assert-sorted (superpose (3 1 2)))" in str(unsorted)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 10215 inferences, 0.6704x the example's 15238; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 10215
