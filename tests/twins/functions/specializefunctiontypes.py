"""examples/functions/specializefunctiontypes.metta in Python: types survive specialization.

`f` applies its first argument, so calling `(f g 42)` specializes `f` on `g`,
and the specialized function keeps `f`'s TYPES: both declared arrows reappear
on `f_Spec_[g]`. Asking whether they are there is a match over the space, and
`m[pattern]` is that door: a query with no rows is falsy, so the claim reads
as an ordinary Python truth test.

Both definitions are ordinary Python functions. `f`'s parameter is named `g`
exactly as the original's variable is, so inside the body `g` is that
parameter and `g(x)` is `($g $x)`, the variable-head application; the `g`
defined above it is a different thing with the same name, which is what the
original means too. `repra` is an engine function named through the static
namespace, `fn.repra`, which reads and autocompletes without the engine having
to be running.

The two type declarations are written as the atoms they are. Annotations are
the decorator's own declaration door, but they emit ONE arrow per definition
and this head carries two, so no annotation says it. The residue table records
that against P14.9.
"""

from metta import Atom, S, arrow, fn, typed

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 6885 to 6902, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 6902 to 6913, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 6913 to 6845, on the release tree:
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
#: RE-PINNED 2026-08-25, 6845 to 6855, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 6855


def twin(m):
    """Declare two arrows for one head, specialize it, and find both on the copy."""

    @m.define
    def g(x):
        # (= (g $x) $x)
        return x

    # (: f (-> Atom Number Atom)) and (: f (-> Atom String Atom))
    # rung: below the ANNOTATION door, both declarations: this head carries two
    #   arrows and a Python signature emits one (residue, P14.9)
    m += typed(S.f, arrow(Atom, int, Atom))
    m += typed(S.f, arrow(Atom, str, Atom))

    @m.define
    def f(g, x):
        # (= (f $g $x) (repra ($g $x)))
        return fn.repra(g(x))

    # !(f g 42), the call that specializes it. A call answers a LAZY view and
    # creating one performs no engine work, so the answer has to be READ for
    # the specialization to happen at all; `.one()` reads it and states its
    # cardinality in the same breath.
    assert f(S.g, 42) == [S.repra(S.g(42))]

    specialized = S["f_Spec_[g]"]
    assert m[typed(specialized, arrow(Atom, int, Atom))]
    assert m[typed(specialized, arrow(Atom, str, Atom))]
