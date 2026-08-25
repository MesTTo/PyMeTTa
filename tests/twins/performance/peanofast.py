"""Purpose: examples/performance/peanofast.metta in Python: 2500 successors, and how to count them.

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
tools/twin_coverage.py --measure examples/performance/peanofast.metta;
commit=WORKTREE].
"""

from metta import S, V, counting, fn

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
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
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
#: 103089 inferences; command=python bindings/python/tools/twin_coverage.py;
#: fixture=full-lane 2500 successors; commit=WORKTREE].
BUDGET = 103089


def twin(m):
    """Build 2500 Peano successors, then count them."""

    # `expandK` is camelCase, which the naming ladder's underscore map does
    # not produce from any Python identifier, so this one door states the
    # exact name while the Python side stays snake_case.
    @m.define(name="expandK")
    def expand_k(expression, n):
        if n == 0:
            return S.done
        space = fn.context_space()
        space += S.num(expression)
        return expand_k(S.S(expression), n - 1)

    @m.define
    def demo_peano(k):
        """Expand from zero, k times."""
        # One rule at both call sites: a compiled body naming a bound
        # `Defined` sibling emits the MeTTa name that object was installed
        # under, so this stores `(expandK Z $k)`.
        return expand_k(S.Z, k)

    assert demo_peano(2500) == [S.done]
    assert m.match(S.num(V.stored), under=counting).one() == 2500
