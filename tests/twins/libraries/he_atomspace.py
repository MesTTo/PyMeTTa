"""examples/libraries/he_atomspace.metta in Python: writing, matching and typing atoms.

`add-atom` and `add-reduct` differ in one thing, which the two claims here
draw: add-atom stores the definition as written, and add-reduct reduces the
body to a VALUE first. Python spells the pair with one write door and an
explicit evaluation, which is the composition the ledger asks for rather than a
second method.

Reading them back is matching the space for `(= (addnormal) $X)`, which
`equation(...).to(...)` builds as a pattern the same way it builds an atom, so
the subscript door answers the stored body.

`get-type` is `space.type(atom)` now, the dissolution table's own door, so the
declaration's space is the receiver rather than an argument; and `(: a A)` is
`typed(a, A)`, the declaration as data.

The containment claims are Python's `in`: `(unify &self (hello world) Yes No)`
asks whether anything in the space unifies with a pattern, which is exactly
what `pattern in space` asks, so the twin answers True and False rather than
Yes and No.
"""

from metta import S, V, equation, lib, typed

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 3424 to 3839, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3839 to 3840, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3840 to 3846, on the release tree:
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
#: RE-PINNED 2026-08-26, 3846 to 3872 (+26), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 3872


def twin(m):
    """Write one definition each way, read both back, then type and unify."""
    m += lib.he

    m += equation(S.addnormal()).to(S.add(1, 3))
    m += equation(S.addreduct()).to(m.answers(S.add(1, 3)).one())

    # The stored body, as written.
    assert [row.body for row in m[equation(S.addnormal()).to(V.body)]] == [S.add(1, 3)]
    # And reduced, because add-reduct's Python spelling evaluates first.
    assert [row.body for row in m[equation(S.addreduct()).to(V.body)]] == [4]

    # A declared type is an ordinary atom, and the space that holds it is the
    # receiver: which space you ask is what decides the answer.
    m += typed(S.a, S.A)
    assert m.type(S.a) == S.A

    # Containment is a match, so it is Python's `in`.
    m += S.hello(S.world)
    assert S.hello(S.world) in m
    assert S.hello(S.dream) not in m
