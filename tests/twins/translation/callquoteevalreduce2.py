"""examples/translation/callquoteevalreduce2.metta in Python: four ways to not reduce.

One inner term, `(fib (myfunc))`, under four wrappers. `call`, `eval` and
`reduce` all get to 5; `quote` holds the term as it was written. Each claim
wraps the answer in a symbol of its own so the comparison sees what came back
rather than what it would reduce to next.

Everything here compiles. `fib` and `myfunc` are ordinary functions, and the
four wrappers are ordinary functions whose bodies mention a translator form:
`call`, `quote`, `eval` and `reduce` are forms the compiler reads rather than
functions the catalog holds, so a body names them at the `S` door and hands
them a call built out of the two Python names beside it.

The outer wrappers in the claims are not functions at all. `fib-call` has no
equation, so evaluating `(fib-call (call-fib))` reduces what is inside it and
leaves the wrapper standing, which is exactly what the claim is measuring; that
makes each one a term to evaluate rather than a call to make.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 49843 to 49790, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 49790 to 49720, on the release tree:
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
BUDGET = 49720


def twin(m):
    """Wrap one term four ways, and see which of them reduce."""

    @m.define
    def fib(n):                          # (= (fib $N) (if (< $N 2) $N
        if n < 2:                        #     (+ (fib (- $N 1)) (fib (- $N 2)))))
            return n
        return fib(n - 1) + fib(n - 2)

    @m.define
    def myfunc():                        # (= (myfunc) 5)
        return 5

    @m.define
    def call_fib():                      # (= (call-fib) (call (fib (myfunc))))
        return S.call(fib(myfunc()))

    @m.define
    def quote_fib():                     # (= (quote-fib) (quote (fib (myfunc))))
        return S.quote(fib(myfunc()))

    @m.define
    def eval_fib():                      # (= (eval-fib) (eval (fib (myfunc))))
        return S.eval(fib(myfunc()))

    @m.define
    def reduce_fib():                    # (= (reduce-fib) (reduce (fib (myfunc))))
        return S.reduce(fib(myfunc()))

    inner = S.fib(S.myfunc())
    assert m.answers(S.fib_call(S.call_fib())) == [S.fib_call(5)]
    # quote keeps its wrapper AND the term under it, unreduced.
    assert m.answers(S.fib_quote(S.quote_fib())) == [S.fib_quote(S.quote(inner))]
    assert m.answers(S.fib_eval(S.eval_fib())) == [S.fib_eval(5)]
    assert m.answers(S.fib_reduce(S.reduce_fib())) == [S.fib_reduce(5)]
