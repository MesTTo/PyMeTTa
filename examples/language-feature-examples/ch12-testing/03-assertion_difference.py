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
from metta._errors.errors import AssertionFailure


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
#: RE-PINNED 2026-09-08, 9167 to 9193 (+26), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 9167 to 9248 (+81), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 9248 to 9401 (+153), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 9401 to 9589 (+188), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 9401 to 9428 (+27), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 9428 to 9616 (+188), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 9401 to 9377 (-24), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 9377 to 9592 (+215), the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): boot publishes the initial vocabulary
#: types from a compiled payload through the tokenized funnel, a warm
#: membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, -24 against the trunk's own pin of 9616 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +239 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 9592 to 8343 (-1249), the binding resolves Janus
#: maplist/2 at boot, removing its first-failure autoload; one compiled option
#: policy removes repeated evaluation frames, and keyed dispatch removes
#: repeated transport/context selection. Indexed source-macro hooks preserve
#: unrelated compilation costs. Same-cut controls and all before/after rows are
#: in docs/journal/2026-09-09-the-binding-collapse.md. These three fresh serial
#: processes set file_search_cache_time=9223372036854775807 before boot,
#: matching the validated full-lane/277/workers=32/file-cache-
#: time=9223372036854775807 environment. Workloads, point tolerances and
#: empirical envelopes are unchanged [measured 2026-09-10: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
#: RE-PINNED 2026-09-11, 8343 to 8469 (+126), end-of-wave re-pin on the merged
#: tree after FROM's reference rows and four engine units, the closed-set
#: derivations and two host services, BINDING's one native evaluation entry and
#: boot import, W-OBSERVE's observer guard, PERF's receipts batching and cursor
#: retirement, and the three REDS repairs (derived runtime resources and the
#: shared loader, the tool-lane repairs, the corpus example); serial minimum of
#: three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 8343 to 8451 (+108), the branch's landings since the
#: 09-10 pins, re-taken on the tip f06186a96: the compiled call law (e59104ace:
#: an Atom argument enters as written, a Python object crosses as a value, a
#: positional call of a bound callee is the plain application and a compiled
#: lambda is bare where it is applied), the one codec at the grounded call
#: (fd0af38f7, whose read of a call site's written keyword tail costs about six
#: inferences per translated site, read once since 7cc8fb863), the runnable
#: cache's dependency index written by the producer (a9e2c06d3, which takes
#: back the walk of the generated code 5416e741d charged at every miss), the
#: host patches of 09-17 and the class units of 09-13 to 09-16 the ladder in
#: docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
BUDGET = BUDGET = 8451
