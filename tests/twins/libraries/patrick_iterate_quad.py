"""Purpose: examples/libraries/patrick_iterate_quad.metta in Python: a triangular walk under iterate.

The step carries a triple, (t i sum), and walks the lower triangle of a
thousand-by-thousand grid: when i reaches t the row is finished, so t advances
and i restarts, and otherwise i advances. `iterate` runs it n(n+1)/2 times and
`last` takes the final state; a compiled body says both through the STATIC `fn`
namespace and passes the step by its `S` name, because the step is data there.

`quad-step` stays at the container door, and that is the residue entry this
file carries: its head destructures its second argument, where a decorated
function's parameters are always plain variables.

Inside that built body the conditional is `if_`, the keyword builder with the
engine's own two-or-three arity, and the comparison is `S.eq`, the operator's
WORD. Both are what a STORED equation needs: Python's conditional expression
evaluates rather than building, and `V.i == V.t` is Python's own structural
equality between two variables, which is False. The arithmetic around them is
Python's own, because an operator with a VARIABLE operand builds the term.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation, fn, if_, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 55099208 to 55099246, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 55099246 to 55099188, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 55099188 to 55099157, on the release tree:
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
#: RE-PINNED 2026-08-25, 55099157 to 55099146, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 55099146


def twin(m):
    """Sum t*i over the lower triangle of a thousand rows."""
    m += lib.patrick

    m += equation(S.quad_step(V.dummy, Expression((V.t, V.i, V.sum)))).to(
        if_(
            S.eq(V.i, V.t),
            Expression((V.t + 1, 1, V.sum + V.t * V.i)),
            Expression((V.t, V.i + 1, V.sum + V.t * V.i)),
        )
    )

    @m.define
    def quad_sum(n):
        # (= (quad-sum $n) (last (iterate 0 (/ (* $n (+ $n 1)) 2) (1 1 0) quad-step)))
        return fn.last(fn.iterate(0, n * (n + 1) / 2, (1, 1, 0), S.quad_step))

    assert quad_sum(1000) == [125417041750]
