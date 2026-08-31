"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/09-he_types.metta in Python: the type judgment, asked directly.

The HE type vocabulary is part of the core engine now, so this file's import is
a no-op and stays only to show that. Its subject is the judgment itself, which
is why every function here is named: `is-function` observes an arrow,
`type-cast` admits or refuses, `match-types` unifies with wildcards, and the
pair accessors and `match-type-or` are the rest of that vocabulary.

The arrow it observes is built by `arrow(...)`, the `->` form as DATA, which is
the same character Python writes in a signature and the builder the surface
keeps for the rare case where the arrow itself has to be handed to something.
A declaration is `typed(a, T)`, the `(: a T)` form as data.

`type-cast` takes the space it asks as an ARGUMENT, and a space crosses a term
position as a grounded operand, so the receiver is handed over rather than
named.

`type-cast` is asked through the engine rather than through `m.cast`, and that
is a measured decision, not a habit: `m.cast(S.B, S.type1)` RAISES CastError
where the engine answers B, because an atom nobody declared has type
`%Undefined%`, which the language's own rule treats as a wildcard that matches
any requested type. The divergence is recorded in the residue table.

The refusal is an Error ATOM, and iterating the answer view keeps it as data
where the scalar doors take the loud reading and raise.
"""

from metta import G, S, V, arrow, lib, typed


def twin(m):
    """Observe arrows, cast five atoms, unify four type pairs, take two halves."""
    m += lib.he

    is_function = m.fn.is_function
    assert is_function(arrow(S.Atom, S.Atom)) == [True]
    assert is_function(S.Atom) == [False]

    # type-cast answers the atom when it has the type and (Error $atom BadType)
    # when it does not. Three ways to have it: the type is the atom's metatype,
    # a declared type matches it, or the atom has no declaration at all, which
    # the engine answers as %Undefined%, a wildcard matching any type.
    m += typed(S.type1, S.Type)
    m += typed(S.A, S.type1)

    cast = m.fn.type_cast
    assert cast(S.A, S.type1, m) == [S.A]
    assert cast(1, S.type1, m) == [S.Error(1, S.BadType)]

    # A metatype counts, so any symbol casts to Symbol and any number to Number.
    assert cast(S.A, S.Symbol, m) == [S.A]
    assert cast(1, S.Number, m) == [1]
    # An atom nobody declared is not the wrong type.
    assert cast(S.B, S.type1, m) == [S.B]

    # match-types is unification with wildcards, Hyperon's own contract:
    # %Undefined% and Atom on EITHER side match anything, and otherwise the two
    # types unify, so a type carrying a variable matches its instance.
    match_types = m.fn.match_types
    matched, missed = G("Matched!"), G("Didn't match")
    assert match_types(S.Atom, S.Atom, matched, missed) == [matched]
    assert match_types(S.Atom, S.Number, matched, missed) == [matched]
    assert match_types(S.Bool, S.Number, matched, missed) == [missed]
    assert match_types(S.List(V.x), S.List(S.Number), matched, missed) == [matched]

    assert m.fn.first_from_pair((S.A, S.B)) == [S.A]
    assert m.fn.second_from_pair((S.A, S.B)) == [S.B]
    assert m.fn.match_type_or(True, S.Number, S.Bool) == [True]  # noqa: FBT003  -- True is the folded accumulator this call carries, an ordinary atom, not a flag


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 39149 to 40155, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 40155 to 40156, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 40156 to 40182, on the release tree:
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
#: RE-PINNED 2026-08-25, 40182 to 40192, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 40192 to 35166 (-5026), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 35166 to 88277 (+53111), one corpus pricing pass on
#: the merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 88277
