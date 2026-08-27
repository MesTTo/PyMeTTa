"""examples/libraries/he_equalreduct.metta in Python: equality and reduction, HE's vocabulary.

`=alpha` is equality modulo a consistent renaming of variables, and that
relation belongs to the atom: `a.alpha_eq(b)` is the method, so the two claims
about it are ordinary Python truth tests and the twin never spells the MeTTa
head. `id` and `if-equal` are lib_he's own functions and stay named.

`(= (add 1 2) 3)` goes to the container door. Its head carries LITERAL
arguments, and a decorated Python function's parameters are always variables,
so `@m.define` would store `(= (add $x $y) 3)`, a different equation.

That head keeps the BRACKET, and this is the one place in the folder where the
choice is load-bearing. `add` is one of the operator words, so the attribute
door reads `S.add` as `+` and would store `(= (+ 1 2) 3)`, an equation about
addition instead of about the symbol the example defines. Rung 5's bracket is
the exact door, so `S["add"]` is the head literally named `add`.
"""

from metta import G, S, V, equation, lib


def twin(m):
    """Store an equation with a literal head, then ask three equality questions."""
    m += lib.he

    m += equation(S["add"](1, 2)).to(3)

    assert m.fn.id(5) == [5]

    # Alpha equality is equality up to a consistent renaming of variables.
    assert S.Father(V.X).alpha_eq(S.Father(V.Y))
    assert not S.Father(V.X).alpha_eq(S.Son(V.X))

    assert m.fn.if_equal(1, 1, G("Equal"), G("Not Equal")) == [G("Equal")]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 2291 to 3063, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3063 to 3064, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3064 to 3068, on the release tree:
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
#: RE-PINNED 2026-08-25, 3068 to 3070, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 3070 to 3083 (+13), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 3083
