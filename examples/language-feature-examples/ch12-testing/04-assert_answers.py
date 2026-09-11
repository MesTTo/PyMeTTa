"""Purpose: examples/ch12-testing/04-assert_answers.metta in Python: the door every assertion reports through.

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
from metta._errors.errors import AssertionFailure


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
#: RE-PINNED 2026-09-08, 10282 to 10431 (+149), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 10431 to 10619 (+188), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 10431 to 10518 (+87), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 10518 to 10706 (+188), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 10431 to 10422 (-9), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 10422 to 10536 (+114), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 10536 to 10811 (+275), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +105 against the trunk's own pin of 10706 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +170 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 10811 to 9554 (-1257), the binding resolves Janus
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
#: RE-PINNED 2026-09-11, 9554 to 9727 (+173), end-of-wave re-pin on the merged
#: tree after FROM's reference rows and four engine units, the closed-set
#: derivations and two host services, BINDING's one native evaluation entry and
#: boot import, W-OBSERVE's observer guard, PERF's receipts batching and cursor
#: retirement, and the three REDS repairs (derived runtime resources and the
#: shared loader, the tool-lane repairs, the corpus example); serial minimum of
#: three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
BUDGET = 9727
