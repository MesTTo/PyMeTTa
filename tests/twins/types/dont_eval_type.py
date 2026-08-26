"""Purpose: examples/types/dont_eval_type.metta in Python: a user-declared lazy type.

`DontEvalType` is a kind of type, and a parameter declared with a type of that
kind receives its argument BEFORE evaluation. So `inspect-opaque` sees the term
`(+ 1 2)` rather than 3, and reports its metatype, Expression.

The declaration is an ordinary annotated signature: `OpaquePayload` is a Python
class so the parameter can name it, `Symbol` is the metatype class the answer
has, and `@m.define` publishes `(: inspect-opaque (-> OpaquePayload Symbol))`
from the two. Only the KIND declaration stays an atom, because `DontEvalType`
says something about the type rather than about a function.

The body names `get-metatype` through the function namespace. Python's own
`type()` is the metatype accessor out here, where the atom is already in hand,
and the last line says so by asking both sides about the same term; inside a
compiled body `type()` has no lowering, which is the friction P14.4 records.
"""

from metta import Expression, S, Symbol, fn, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 3743 to 3761, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3761 to 3767, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3767 to 3734, on the release tree:
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
#: RE-PINNED 2026-08-25, 3734 to 3739, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 3739 to 5306 (+1567), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=WORKTREE].
BUDGET = 5306


class OpaquePayload:
    """The MeTTa type `OpaquePayload`, so a signature can name it."""


def twin(m):
    """Declare the lazy type, then read what the body was handed."""
    # (: OpaquePayload DontEvalType)
    m += typed(S.OpaquePayload, S.DontEvalType)

    @m.define
    def inspect_opaque(written: OpaquePayload) -> Symbol:
        """(= (inspect-opaque $written) (get-metatype $written))."""
        return fn.get_metatype(written)

    sum_term = S.add(1, 2)

    # !(test (inspect-opaque (+ 1 2)) Expression)
    assert inspect_opaque(sum_term) == [S.Expression]

    # The same question on the Python side of the seam: the metatype IS the
    # class, so nothing crosses to ask it.
    assert type(sum_term) is Expression
