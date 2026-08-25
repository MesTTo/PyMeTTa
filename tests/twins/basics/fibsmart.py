"""examples/basics/fibsmart.metta in Python: the accumulator fib.

Two equations by one decorator, and the second one shows how a compiled body
reaches a sibling whose MeTTa name is not its Python name. No Python
identifier carries a hyphen, so `def fib_tr` is installed as `fib-tr` by the
naming ladder's own underscore map, and nothing has to say that name twice.
`fib`'s body then CALLS the Python object, and the compiler emits the MeTTa
name that object was installed under, so the stored equation is the
original's.

Compiled-body equality lowers to the engine's `==`, so `fib-tr`'s stored body
matches the original equation as well.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 13288 to 13307, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 13307 to 13320, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 13320 to 13252, on the release tree:
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
BUDGET = 13252


def twin(m):
    """Define the accumulator fib and its entry point, then run it."""
    @m.define
    def fib_tr(n, a, b):
        # (= (fib-tr $n $a $b) (if (== $n 0) $a (fib-tr (- $n 1) $b (+ $a $b))))
        return a if n == 0 else fib_tr(n - 1, b, a + b)

    # A body calling the definition above it is the ordinary call: `fib_tr` is
    # bound here to the decorated object, and the compiler emits that object's
    # installed MeTTa name, so the stored body is `(fib-tr $n 0 1)` even
    # though the two names differ.
    @m.define
    def fib(n):
        # (= (fib $n) (fib-tr $n 0 1))
        return fib_tr(n, 0, 1)

    assert fib(100) == [354224848179261915075]
