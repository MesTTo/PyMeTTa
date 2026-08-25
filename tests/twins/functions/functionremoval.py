"""examples/functions/functionremoval.metta in Python: equations move.

An equation is an ATOM, so it can be taken out of the space and put back, and
the function answers differently while it is gone. When both clauses are gone
`(f g)` matches nothing and answers itself.

Both definitions are decorated Python functions. `g` is a computation. `f`'s
two clauses are ALTERNATIVES that both answer, and a generator body says
exactly that: each independent yield stores one equation under the one head,
so the pair is two atoms rather than a first-match ladder.

The point of the file then writes itself, because an equation is a VALUE:
`equation(head).to(body)` builds the same atom the decorator stored, and `-=`
and `+=` take it as the atom it is.

The last claim reads through the engine's own reducer rather than `m.eval`,
for the reason examples/functions/dispatch_policies.metta's twin measures:
with both clauses gone the call is not reducible, and `m.eval` drops that
answer where a runnable form keeps it.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass after the conformance
#: answer updates: tools/twin_coverage.py --measure min-of-3, identical
#: across two fresh rounds on p14-integration at the store-wave merge.
#: RE-PINNED 2026-08-25, 15690 to 15749, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 15749 to 15760, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 15760 to 15696, on the release tree:
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
#: RE-PINNED 2026-08-25, 15696 to 15706, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 15706


def twin(m):
    """Take one clause out, put it back, take the other, then both."""

    @m.define
    def g(x):
        # (= (g $x) (+ $x 1))
        return x + 1

    @m.define
    def f(g):
        # (= (f $g) ($g 1))
        yield (g, 1)
        # (= (f $g) 42)
        yield 42

    call = equation(S.f(V.g)).to((V.g, 1))
    const = equation(S.f(V.g)).to(42)

    assert m.eval(S.f(S.g)) == [2, 42]

    m -= const
    assert m.eval(S.f(S.g)) == [2]

    m += const
    m -= call
    assert m.eval(S.f(S.g)) == [42]

    m -= const
    # !(test (collapse (f g)) ((f g))) — with every equation removed the
    # call is retained as written, the boundary protocol's own answer;
    # `reduce` now retains its OWN written frame, so the plain eval is the
    # spelling that mirrors the example's collapse row.
    assert m.eval(S.f(S.g)) == [S.f(S.g)]
