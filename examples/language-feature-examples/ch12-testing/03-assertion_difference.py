"""Purpose: examples/ch12-testing/03-assertion_difference.metta in Python: the answer bags a failing comparison hands over.

The example has to work to read its own failure. `catch` reifies the ball as
`(Error <ball> <context>)`, `unify` is the one door whose operands are held
long enough to take an error value apart, and `repr` writes the ball as text
the file can compare. Python has the object, so all three dissolve into
`except AssertionFailure as failure` and the fields are read directly:
`.missing` is what was expected and never produced, `.excess` what was produced
and never expected, both tuples of decoded atoms.

`.excess` is `None` for a form that computed no such difference, and `None` is
a different answer from `()`. Two empty tuples say the comparison RAN and the
bags agree, so the answers differ only in order; `None` says there was no bag
comparison to report, which is what `assert` gives, whose operand is a verdict,
and what the excess side of a containment gives, whose surplus answers are
legal. The example shows the same distinction as `$_0` against `()`, the
writer's spelling for an unbound argument.

`m.fn.<name>(...)` is LAZY, so a claim nobody pulls is a claim nobody checks:
`refused` below pulls with `list` before deciding that the call held.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S
from metta.errors import AssertionFailure


def refused(claim, *arguments):
    """The AssertionFailure one false claim raises, or None where it held.

    `list` is what pulls it. A `fn` call answers a lazy view, so a failing
    assertion nobody observes raises nothing at all, and a helper that
    returned on a bare call would report every claim in this file as holding.
    The `is not None` beside each use is what says the claim really did fail.
    """
    try:
        list(claim(*arguments))
    except AssertionFailure as failure:
        return failure
    return None


def twin(m):
    """Read each failing comparison's own report, then the passing forms."""
    # Both directions at once: 3 was wanted and never came, 2 came and was
    # never wanted. The message names the call AS WRITTEN rather than the
    # False it reduced to, so the report points at something a reader can
    # find in the source.
    two_sided = refused(m.fn.assertEqual, S.add(1, 1), 3)
    assert two_sided is not None
    assert two_sided.missing == (3,)
    assert two_sided.excess == (2,)
    assert "(assertEqual (+ 1 1) 3)" in str(two_sided)

    # One direction. The other bag is EMPTY rather than absent: the
    # comparison ran and found nothing in excess.
    one_direction = refused(m.fn.assertEqualToResult, S.superpose((1, 2)), (1, 2, 3))
    assert one_direction is not None
    assert one_direction.missing == (3,)
    assert one_direction.excess == ()

    # A bag difference, not a set difference. One occurrence on one side
    # consumes exactly one on the other, so (a a b) against (a b b) leaves one
    # b wanted and one a produced rather than nothing at all.
    bags = refused(
        m.fn.assertEqual,
        S.superpose((S.a, S.a, S.b)),
        S.superpose((S.a, S.b, S.b)),
    )
    assert bags is not None
    assert bags.missing == (S.b,)
    assert bags.excess == (S.a,)

    # A ONE-SIDED question gets a one-sided answer. This relation allows an
    # answer in excess of its expectation, so 1 and 2 are both produced, both
    # unexpected, and neither is a reason for the failure: the excess side is
    # absent rather than empty and no `excess` line is printed.
    containment = refused(m.fn.assertIncludes, S.superpose((1, 2)), (7,))
    assert containment is not None
    assert containment.missing == (7,)
    assert containment.excess is None
    assert "excess" not in str(containment)

    # Two EMPTY bags beside a failure is the diagnosis rather than a puzzle.
    # assertEqual compares the collapsed tuples by term equality, so a
    # permutation fails while the answers themselves agree.
    permuted = refused(m.fn.assertEqual, S.superpose((1, 2)), S.superpose((2, 1)))
    assert permuted is not None
    assert permuted.missing == ()
    assert permuted.excess == ()
    assert "differ only in order" in str(permuted)

    # The Msg forms carry a message the engine used to accept and drop.
    # Reporting the call as written carries it, with no separate channel.
    with_message = refused(m.fn.assertEqualMsg, S.add(1, 2), 4, G("sums differ"))
    assert with_message is not None
    assert with_message.missing == (4,)
    assert with_message.excess == (3,)
    assert "sums differ" in str(with_message)

    # `assert` takes a VERDICT, not two answer bags, so there is nothing to
    # subtract and the ball carries neither. Its name is a Python keyword, so
    # the exact door spells it. Absence is a different answer from two empty
    # bags: one says there was no bag comparison here, the other says the
    # comparison ran and the bags agreed.
    verdict = refused(m.fn["assert"], S["=="](1, 2))
    assert verdict is not None
    assert verdict.missing is None
    assert verdict.excess is None

    # The load-bearing half: the evidence travels, the verdicts do not move.
    assert m.fn.assertEqual(S.add(1, 2), S.sub(6, 3)) == [True]
    assert m.fn.assertEqualToResult(S.superpose((1, 2)), (2, 1)) == [True]
    assert m.fn.assertEqualMsg(S.add(1, 2), S.sub(6, 3), G("sums differ")) == [True]
    assert m.fn.assertIncludes(S.superpose((1, 2, 3)), (2, 1)) == [True]


#: Why this twin sits below the top rung: the subject is the assert family's
#: own failure reports, so each claim reads a field of the AssertionFailure one
#: of its members raised, and naming the member is what the file is about.
RUNG = "the assert family's failure report is this file's subject, so each claim names the member that raised"

#: PRICED 2026-09-07, the twin's first measurement, on the branch that gives
#: assertIncludes its one-sided report. Min of three serial fresh processes,
#: and the same number on three separate invocations of that protocol at
#: loadavg 53 and 78, which is what makes it a point pin rather than an
#: envelope: inferences are counted, not timed. The example itself costs 15331
#: on the same runs, so this twin is 0.54 of its MeTTa side
#: [measured 2026-09-07: 8295 inferences, three identical readings;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch12-testing/03-assertion_difference.metta; fixture=worktree
#: ai-tmp/wt-assertion-followups on fix/assertion-and-seam-followups, held to
#: the corpus's own two-sided +-4 point tolerance; commit=2b1e14e9ba176f724e3d9676047f47b6fbbffa1b].
#: RE-PINNED 2026-09-07, 8295 to 9180 (+885), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 9180 to 9167 (-13), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 9167 to 9248 (+81), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
BUDGET = 9248
