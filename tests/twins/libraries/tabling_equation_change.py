"""examples/libraries/tabling_equation_change.metta in Python: a table goes stale, and knows.

A table answers from the equations compiled when it was built, so changing an
equation makes it stale. The engine's own change funnel drops the tables and the
next call rebuilds them, which is what the four claims here watch.

The first clause is an ordinary compiled definition whose body is the lowercase
symbol `one`, which the `S` factory says inside a body as readily as outside
one. The SECOND clause cannot join it: a second decoration of the same head
replaces the first rather than stacking, so the alternative is written at the
container door, and the removal takes it away from there too. That is the
residue entry this file carries, and it is the shape the example needs, because
the program removes one of the two atoms later.

The third claim is sorted, because a TABLED function does not answer in clause
order: answers come out of the answer trie, and SWI says so plainly, "Tabling
effectively inverts the execution order for this case". Which order you get
depends on the trie's layout, so it moves when anything unrelated moves. The
answer SET is what tabling preserves; that is what this asserts. Sorting takes
no key, because atoms carry the engine's standard order of terms.
"""

from metta import S, V, equation, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 54113 to 54245, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 54245 to 54719, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 54719 to 54025, on the release tree:
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
#: RE-PINNED 2026-08-25, 54025 to 54057, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 54057


def twin(m):
    """Table one equation, add a second, remove the first, watch the answers move."""
    m += lib.tabling

    @m.define
    def pick(x):  # noqa: ARG001  -- the head variable is the example's own, and its body ignores it
        # (= (pick $x) one)
        return S.one

    m.eval(S.tabled(S.pick(V.x)))

    assert pick(S.a) == [S.one]
    assert pick(S.a) == [S.one]

    # A second equation for the same function. Without invalidation the table
    # would keep answering [one].
    m += equation(S.pick(V.x)).to(S.two)
    assert sorted(pick(S.a)) == [S.one, S.two]

    # Removing one again.
    m -= equation(S.pick(V.x)).to(S.one)
    assert pick(S.a) == [S.two]
