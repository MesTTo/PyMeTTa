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
#: RE-PINNED 2026-08-26, 6855 to 8687 (+1832), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 8687 to 8707 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=WORKTREE].
#: RE-PINNED 2026-08-26, 8707 to 7228 (-1479), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 7228
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
