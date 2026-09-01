"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-03-search/01-newtons_method.metta in Python: memoised double recursion.

`energy` calls itself twice on the same smaller argument, so without a cache it
doubles at every level. The example imports lib_memo, sets a cache policy, and
memoises the function by name; then two claims read it.

`energy` is an ordinary Python function. The `if` is MeTTa's `if`, the
arithmetic is Python's own operators over the compiled parameters, and the two
recursive calls are the calls the equation makes, so `@m.define` lands the
example's own equation up to variable naming and `memoize` reaches it by name
like any other definition. Calling it evaluates, which is why the claims read
`energy(2.0, 0)` and not a rebuilt term.

The three directives stay terms: each names an engine service rather than a
computation, none of them is banged, and lib_memo has no Python face and needs
none. There was once a `@m.cache` decorator here, a host door for ONE library
that reached the exact-bag variant no other seat could spell; it is gone, and
`memoize-exact` is an ordinary library form every seat reaches. The import takes
the space HANDLE, because a space crosses a term position as itself.

The definition is written FIRST, where the example writes it fourth. A file
loader registers a file's function names before it runs the file's `!` forms,
so `!(memoize energy)` finds `energy` there; a Python program has no such
pre-pass and `memoize` on an unknown name is a domain error. The residue
records the missing batch door against P14.4.
"""

from metta import S, lib
from metta.vocabularies import MemoStrategy


def twin(m):
    """Define the recursion, memoise it, then read two of its values."""
    # The library's file name is `lib_memo.metta`, and the factory attribute
    # door maps every underscore to a hyphen, so the name takes the bracket.
    # !(import! &self (library lib_memo))
    m += lib.memo

    @m.define
    def energy(x, n):
        """(= (energy $x $n) (if (<= $n 0) (* $x $x) (+ (energy ...) (energy ...))))."""
        if n <= 0:
            return x * x
        return energy(0.5 * x + 0.4, n - 1) + energy(0.5 * x + 0.4, n - 1)

    # !(config-memoize (strategy wtinylfu) (unique-limit 100))
    # !(memoize energy)
    m.eval(S.config_memoize(S.strategy(S[MemoStrategy.wtinylfu]), S.unique_limit(100)))
    m.eval(S.memoize(energy))

    # Base case: x*x.
    # !(test (energy 2.0 0) 4.0)
    assert energy(2.0, 0) == [4.0]
    # One level down: 1.4*1.4 twice.
    # !(test (energy 2.0 1) 3.9199999999999995)
    assert energy(2.0, 1) == [3.9199999999999995]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 96526 to 96621, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 96621 to 96640, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 96640 to 96580, on the release tree:
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
#: RE-PINNED 2026-08-25, 96580 to 96590, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 96590 to 98128 (+1538), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 98128 to 98150 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 98150 to 64903 (-33247), one corpus pricing pass on
#: the merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 64903 to 64884 (-19), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 64884
