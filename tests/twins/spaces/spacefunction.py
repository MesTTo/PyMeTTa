"""Purpose: examples/spaces/spacefunction.metta in Python: removing a definition.

Two identical equations under different names, one of them removed. The removal
takes the compiled answer with it, so `(f 3 4)` becomes its own answer while
`(g 3 4)` still reduces to 7, and a plain fact behaves the same way.

That is the reflectivity invariant in Python dress: a Python-authored
definition is an ordinary atom, so `-=`, the operator that removes an atom,
removes it, and `equation(head).to(body)` names which atom to remove.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 6409 to 6428, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 6428 to 6441, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 6441 to 6373, on the release tree:
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
#: RE-PINNED 2026-08-25, 6373 to 6383, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 6383


def twin(m):
    """Define two functions, remove one, and see which answers survive."""

    @m.define
    def f(x, y):
        return x + y

    @m.define
    def g(x, y):
        return x + y

    # An equation is an ordinary atom, so the operator that removes an atom
    # removes it, and the compiled clause leaves with the atom.
    m -= equation(S.f(V.x, V.y)).to(V.x + V.y)

    # With nothing left to reduce it, the call is its own answer.
    assert m.eval(S.f(3, 4)) == [S.f(3, 4)]
    assert g(3, 4) == [7]

    # A plain fact is the same story with no compilation in it.
    m += (S.my, S.test)
    m -= (S.my, S.test)
    assert (S.my, S.test) not in m
