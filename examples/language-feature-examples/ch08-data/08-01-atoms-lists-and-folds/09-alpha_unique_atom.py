"""examples/ch08-data/08-01-atoms-lists-and-folds/09-alpha_unique_atom.metta in Python: dedupe modulo renaming.

`alpha-unique-atom` drops a later element when an earlier one is the same term
up to the names of its variables, so three links that differ only in their
variable survive as one. Every claim compares with `alpha_eq` rather than `==`,
for the same reason the operation exists: the surviving element carries
whichever variable came first and the expected answer names a different one.

Python has the relation too, as `metta.structures.AlphaSet`, whose membership
IS that equivalence, so a four-line walk over it does what the operation does.
Each claim runs both and holds them to one answer, which is what makes the
Python structure safe to reach for.
"""

from metta import Expression, S, V
from metta.structures import AlphaSet


def twin(m):
    """Dedupe thirteen expressions modulo variable renaming, two ways each."""

    def first_of_each(items):
        """The walk in Python: AlphaSet membership IS alpha-equivalence."""
        seen, kept = AlphaSet(), []
        for atom in items:
            if atom not in seen:
                seen.add(atom)
                kept.append(atom)
        return Expression(kept)

    def dedupes(items, expected):
        """Whether both routes drop the same elements, up to renaming."""
        engine = m.fn.alpha_unique_atom(Expression(items)).one()
        return engine.alpha_eq(Expression(expected)) and first_of_each(items).alpha_eq(engine)

    link, human = S.link, S.human
    parent, child, foo, bar = S.parent, S.child, S.foo, S.bar

    # Duplicates that differ only in their variable.
    assert dedupes((link(V.x, human), link(V.y, human), link(V.z, human)),
                   (link(V.a, human),))
    assert dedupes((parent(V.x, human), parent(V.y, human), child(V.z, human)),
                   (parent(V.a, human), child(V.b, human)))

    # Different functors are all distinct.
    assert dedupes((parent(V.x, human), child(V.y, human), S.friend(V.z, human)),
                   (parent(V.a, human), child(V.b, human), S.friend(V.c, human)))
    assert dedupes((S.likes(V.x), S.hates(V.y), S.knows(V.z)),
                   (S.likes(V.a), S.hates(V.b), S.knows(V.c)))

    # Nested structure is compared all the way down.
    assert dedupes((link(foo(V.x), human), link(foo(V.y), human), link(bar(V.z), human)),
                   (link(foo(V.a), human), link(bar(V.b), human)))
    assert dedupes((parent(child(V.x), human), parent(child(V.y), human),
                    parent(child(V.x), human)),
                   (parent(child(V.a), human),))

    # A mix of unique elements and duplicates keeps the first of each.
    assert dedupes((link(V.x, human), parent(V.x, human), link(V.y, human),
                    parent(V.z, human), link(V.x, human)),
                   (link(V.a, human), parent(V.a, human)))
    assert dedupes((foo(V.x), foo(V.y), bar(V.x), foo(V.x), bar(V.y)),
                   (foo(V.a), bar(V.a)))

    # Numbers and plain symbols need no renaming at all.
    assert dedupes((1, 2, 2, 3, 1, 4, 4, 5), (1, 2, 3, 4, 5))
    assert dedupes((S.a, S.b, S.a, S.c, S.b, S.d, S.e, S.a), (S.a, S.b, S.c, S.d, S.e))

    # The empty and the single-element cases.
    assert dedupes((), ())
    assert dedupes((1,), (1,))
    assert dedupes((link(V.x, human),), (link(V.a, human),))


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 8954 to 9201, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 9201 to 9202, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 9202 to 9228, on the release tree:
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
#: RE-PINNED 2026-08-25, 9228 to 9230, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 9230 to 9186 (-44), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 9186 to 13138 (+3952), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 13138
