"""examples/basics/fib.metta in Python: the exponential fib, budgeted.

The naive fib is one Python function and the engine runs it as equations. The
deliberately exponential tree exceeds the evaluator's default branch-local
fuel, so the bound is raised first and the call is then an ordinary call.

The static settings tuple and `m.fn.with_pragma` preserve the source's scoped
`with-pragma!` boundary, including restoration after the call.
"""

from metta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 38117 to 38128, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 38128 to 38058, on the release tree:
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
BUDGET = 38058


def twin(m):
    """Raise the branch bound, then run the exponential fib."""
    @m.define
    def fib(n):
        # (= (fib $N) (if (< $N 2) $N (+ (fib (- $N 1)) (fib (- $N 2)))))
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    raised_stack = ((S.max_stack_depth, 100_000_000),)
    assert m.fn.with_pragma(raised_stack, S.fib(30)) == [832040]
