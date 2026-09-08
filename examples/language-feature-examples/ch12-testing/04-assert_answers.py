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
#: RE-PINNED 2026-09-08, 10215 to 10307 (+92), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 10307 to 10222 (-85), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 10222 to 10208 (-14), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 10208 to 10232 (+24), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 10208 to 10282 (+74), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
BUDGET = 10282
