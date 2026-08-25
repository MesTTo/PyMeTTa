"""Purpose: examples/types/parametric_types.metta in Python: an arrow with variables.

`apply` takes a function and an argument and applies it, and its type says so
with two type variables: `(-> (-> $tx $ty) $tx $ty)`. That arrow is what
`Callable[[X], Y]` and `-> Y` mean, so the annotation IS the declaration, and
mypy checks the Python half of the same claim the engine checks at run time.
The type parameters are written in Python's own syntax for them, which needs no
name to be spelled as a string.

The example's last claim instantiates the arrow at `(-> Bool Bool)` and `Bool`
and reads the result type off it, which is a `let` whose PATTERN carries the
answer variable. `solve` says that directly, because its answer template takes
the variables the pattern introduces as well as the subject's.
"""

from collections.abc import Callable

from metta import FALSE, S, V, arrow, fn

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 8968 to 8985, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 8985 to 8991, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 8991 to 8958, on the release tree:
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
#: RE-PINNED 2026-08-25, 8958 to 8965, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 8965


def twin(m):
    """Apply a function through a parametrically typed applier."""

    @m.define
    def apply[X, Y](f: Callable[[X], Y], x: X) -> Y:
        """(: apply (-> (-> $tx $ty) $tx $ty)), (= (apply $f $x) ($f $x))."""
        return f(x)

    # !(apply not False)
    assert apply(S["not"], FALSE) == [True]

    # The example's last claim instantiates the arrow at `(-> Bool Bool)` and
    # `Bool` and reads the result type off it, a `let` whose PATTERN carries
    # the answer variable.
    # !(test (let (get-type apply) (-> (-> Bool Bool) Bool $result) $result) Bool)
    assert m.solve(arrow(arrow(bool, bool), bool, V.result),
                   fn.get_type(S.apply)).result == S.Bool
