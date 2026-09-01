"""Purpose: examples/ch18-performance/18-01-larger-workloads/04-peanofast.metta in Python: 2500 successors, and how to count them.

`expandK` writes `(num Z)`, `(num (S Z))`, and so on down 2500 levels;
`demo-peano` starts it from `Z`. Then the space is asked how many `num` atoms
it holds.

Both equations are ordinary Python functions under the decorator. `expandK`
writes with the engine's own `add-atom`, spelled through the mention door
because a hyphen is not a Python identifier, and answers the lowercase symbol
`S.done` in its base case; the mention door reads both as syntax, so the whole
body compiles. `demo-peano` calls it by name and starts it from the data
constructor `S.Z`.

The count stays in the engine: `match(pattern, under=counting).one()` maps
each derivation to one, preserves the bag, aggregates there, and crosses only
the integer 2500. No depth-K Peano term is materialized in Python [tested:
tools/twin_coverage.py --measure examples/ch18-performance/18-01-larger-workloads/04-peanofast.metta;
commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
"""

from metta import S, V, counting, fn


def twin(m):
    """Build 2500 Peano successors, then count them."""

    # `expandK` is camelCase, which the naming ladder's underscore map does
    # not produce from any Python identifier, so this one door states the
    # exact name while the Python side stays snake_case.
    @m.define(name="expandK")
    def expand_k(expression, n):
        if fn.eq(n, 0):
            return S.done
        space = fn.context_space()
        space += S.num(expression)
        return expand_k(S.S(expression), fn.sub(n, 1))

    @m.define
    def demo_peano(k):
        """Expand from zero, k times."""
        # One rule at both call sites: a compiled body naming a bound
        # `Defined` sibling emits the MeTTa name that object was installed
        # under, so this stores `(expandK Z $k)`.
        return expand_k(S.Z, k)

    assert demo_peano(2500) == [S.done]
    assert m.match(S.num(V.stored), under=counting).one() == 2500


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 25104030 to 25104049, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 25104049 to 25104055, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 25104055 to 25104022, on the release tree:
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
#: RE-PINNED 2026-08-25, 25104022 to 25104027, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 25104027 to 103089: under=counting now omits
#: caller-row encoding before the engine aggregate, so the 2,500 depth-growing
#: Peano answers are never materialized and counting stays linear [measured:
#: 103089 inferences; command=python extensions/python/tools/twin_coverage.py;
#: fixture=full-lane 2500 successors; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
#: RE-PINNED 2026-08-26, 103089 to 103139 (+50), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 103139 to 103161 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 103161 to 89335 (-13826), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 89335 to 89324 (-11), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 89324 to 82575 (-6749), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 82575
