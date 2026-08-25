"""examples/libraries/memo_aggregate.metta in Python: the one claim Python cannot make.

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
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
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
BUDGET = 35216


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
