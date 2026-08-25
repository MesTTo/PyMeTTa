"""Purpose: examples/spaces/selfprog.metta in Python: a program editing itself.

An equation is an ordinary atom, so a running program removes one and adds
another, and the same call answers differently either side of the edit: first
`(function1)` itself, unreduced, then `(OK)`.

Both edits go through the container protocol, which is the point made in
Python: `m -= equation(...).to(...)` is the removal and `m +=` the add, the
same two operators that move any other knowledge. The original reads its
answers through `repr` because MeTTa's `test` would reduce them; here the
answers are atoms and Python compares atoms, so no printing is involved.

The definition's body says `S.OK`, the naming factory, which a compiled body
reads as syntax and lowers to the constructor atom. The earlier spelling was a
bare `OK` with an `F821` suppression under it, because the name had no Python
value; the mention door removed both the suppression and the reason for it.
"""

from metta import S, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 5257 to 5276, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 5276 to 5287, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 5287 to 5221, on the release tree:
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
#: RE-PINNED 2026-08-25, 5221 to 5231, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 5231


def twin(m):
    """Define a function, delete its equation, then give it another one."""

    @m.define
    def function1():
        return S.OK

    m -= equation(S.function1()).to(S.OK)

    # With no equation left, the call is its own answer.
    assert function1() == [S.function1()]

    m += equation(S.function1()).to(S.OK())

    assert function1() == [S.OK()]
