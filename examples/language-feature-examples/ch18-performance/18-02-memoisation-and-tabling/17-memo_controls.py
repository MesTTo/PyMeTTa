"""examples/ch18-performance/18-02-memoisation-and-tabling/17-memo_controls.metta in Python: what lib_memo lets you ask and change.

`get-memoize-config` and the no-argument `get-memoize-stats` take NOTHING,
because what they describe is one global budget rather than a per-function
setting; the per-function question is the other arity of the same name.

WHAT THIS TWIN CANNOT SHOW is the counters' values, for the reason
`08-memo_stats.py` already records: a memoized function called from Python
does not reach lib_memo's dispatch hook, so two calls record a miss each where
two `!` forms in a file record one hit and one miss, and the per-function
entries stay at zero. Every claim below is one that holds either way -- the
answers, the shapes, and what each control DELETES -- and the counter
divergence is in the residue table with its reproduction.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib


def counters(report):
    """Whether a stats answer is pairs of a name and a non-negative count."""
    return all(
        len(pair) == 2 and isinstance(pair[1].value, int) and pair[1].value >= 0
        for pair in report
    )


def twin(m):
    """Memoize exactly, read the policy and the counters, then clear both."""
    m += lib.memo

    @m.define
    def sq(x: int) -> int:
        # (= (sq $x) (* $x $x))
        return x * x

    exact = m.fn["memoize-exact"]
    config, stats = m.fn["get-memoize-config"], m.fn["get-memoize-stats"]
    clear_stats, invalidate = m.fn["clear-memoize-stats"], m.fn["invalidate-memoize"]
    clear, memoized = m.fn["clear-memoize"], m.fn["is-memoized"]

    # `memoize-exact` is `memoize` with the policies that change what a
    # function ANSWERS switched off.
    exact(S.sq).one()
    assert memoized(S.sq) == [True]
    assert m.fn.sq(9) == [81]
    assert m.fn.sq(9) == [81]

    # The policy the library is running under, which takes no argument.
    assert len(config()[0]) == 6
    assert config()[0][0][0] == S.strategy

    # Two arities, two questions: the global counters, and one function's
    # stored entries and answers.
    assert counters(stats()[0])
    assert [pair[0] for pair in stats(S.sq)[0]] == [S.entries, S.answers]
    assert counters(stats(S.sq)[0])

    # A second key is a second call, and the report keeps its shape.
    assert m.fn.sq(4) == [16]
    assert counters(stats(S.sq)[0])
    assert len(stats(S.sq)[0]) == 2

    # `clear-memoize-stats` DELETES the global counters rather than zeroing
    # them, so the report is empty until something is counted again.
    clear_stats().one()
    assert stats() == [()]
    assert m.fn.sq(9) == [81]
    assert counters(stats()[0])
    assert len(stats()[0]) >= 1
    assert counters(stats(S.sq)[0])

    # `invalidate-memoize` drops ONE function's cached answers in this space
    # and leaves the decision to cache it standing.
    invalidate(S.sq).one()
    assert stats(S.sq) == [(S.entries(0), S.answers(0))]
    assert memoized(S.sq) == [True]
    assert m.fn.sq(9) == [81]
    assert counters(stats(S.sq)[0])

    # `clear-memoize` is the wide one: every space's cache, because the
    # memory budget it resets is global. It clears ANSWERS, not decisions.
    clear().one()
    assert stats(S.sq) == [(S.entries(0), S.answers(0))]
    assert memoized(S.sq) == [True]
    assert m.fn.sq(9) == [81]
    assert counters(stats(S.sq)[0])


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 43181 inferences, 0.8699x the example's 49638; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 43181 to 43210 (+29), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 43210 to 43180 (-30), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 43180 to 43107 (-73), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 43107 to 43124 (+17), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 43107 to 43964 (+857), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 43964 to 43974 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
BUDGET = 43974
