"""examples/ch18-performance/18-02-memoisation-and-tabling/02-memo_aggregate.metta in Python: the one claim Python cannot make.

`(config-memoize (aggregate sum))` folds a ground call's answers into one
cached value, so `(choices 5)` answers 18 rather than 5, 6 and 7. The folding
happens INSIDE the cache path, and a memoized function called from Python never
reaches lib_memo's dispatch hook, so from here the call answers all three. The
claim is a declined residue entry with its reproduction, not a silent gap.

What this twin does state is the half that does hold: the mode is accepted and
readable, and setting it back to `none` restores the default for whatever runs
next in the same process, which is why the example ends the way it does.

Three equations share one head, so they are three ALTERNATIVES of one function
rather than three definitions, and `yield` is what says that: each independent
yield stores one equation, and `match` sees all three.

A call through the function namespace is LAZY unless its resolved MeTTa name
ends in `!`, the effect marker, and `config-memoize` carries none: creating
the answer view performs no engine work, so `config(S.aggregate(S.sum))`
written for its EFFECT alone would silently do nothing and every later claim
would read the old mode. Both calls therefore state the `True` they answer,
which both pulls them and says what they answered.
"""

from metta import S, lib
from metta.vocabularies import MemoAggregate


def twin(m):
    """Ask for a summing cache, build the function, and read the mode back."""
    m += lib.memo

    config = m.fn.config_memoize
    assert config(S.aggregate(S[MemoAggregate.sum])) == [True]

    @m.define
    def choices(x):
        # (= (choices $x) $x), then (+ $x 1), then (+ $x 2)
        yield x
        yield x + 1
        yield x + 2

    m.eval(S.memoize(choices))

    read_config = m.fn.get_memoize_config
    [declared] = read_config()
    assert S.aggregate(S[MemoAggregate.sum]) in declared

    # Restore the default mode: the counters and the configuration are
    # process-global, so a later run in the same process would inherit this one.
    assert config(S.aggregate(S[MemoAggregate.none])) == [True]
    [restored] = read_config()
    assert S.aggregate(S[MemoAggregate.none]) in restored

    # The fold the cache would do is what Python cannot reach, so the three
    # alternatives answer separately here. Pinning that is the declined claim
    # written down: when the dispatch hook reaches Python this line goes red,
    # which is when the residue entry retires and the claim becomes 18.
    assert sorted(choices(5)) == [5, 6, 7]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 35112 to 35264, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 35264 to 35260, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 35260 to 35216, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 35216 to 36805 (+1589), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 36805 to 36835 (+30), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 36835 to 36845 (+10), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 36845 to 36928 (+83), one corpus pricing pass on the
#: merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 36928 to 36912 (-16), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 36912
