"""Purpose: examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/02-spaces2.metta in Python: what is stored and what is only run.

Four facts are stored, two `!(bar ...)` forms are only EVALUATED, and the last
claim collects everything the space actually holds. `(bar 42)` is nowhere,
because evaluating a form never stores it, and that is the whole distinction
the example draws.

The facts are plain tuples, which is the knowledge front's own shape: `(foo 42
42)` reads as `(S.foo, 42, 42)` and nests, so `(foo (42 42))` is
`(S.foo, (42, 42))`.

The original sorts before comparing, and so does this file: `sorted(atoms)`
is `msort`, because atoms carry the engine's own elementwise order. That was
not true when this twin was first written, when the shipped key compared an
expression's LENGTH first and disagreed with `msort` whenever one expression
was a longer version of another, which is exactly the pair below; the twin
counted with `Counter` to avoid the question. `Atom.__lt__` now reads the
engine's order, so the ordinary spelling is the correct one again
[measured 2026-08-23: `sorted` and `msort` both answer
`((foo 42 42) (foo (42 42)))` for this file's own atoms; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
"""

from metta import S, V


def twin(m):
    """Store four facts, run two forms, then collect what the space holds."""
    m += (S.foo, 1)
    m += (S.foo, 2)
    m += (S.foo, 42, 42)
    m += (S.foo, (42, 42))

    # Nothing defines bar, so each form answers itself, and neither is stored.
    assert m.eval(S.bar(42)) == [S.bar(42)]
    assert m.eval(S.bar(43)) == [S.bar(43)]

    @m.define
    def answer():
        return 42

    held = (
        [S.foo(row.x) for row in m[S.foo(V.x)]]
        + [S.foo(row.x, row.y) for row in m[S.foo(V.x, V.y)]]
        + [S.bar(row.x) for row in m[S.bar(V.x)]]
    )
    assert sorted(held) == [S.foo(1), S.foo(2), S.foo(42, 42), S.foo((42, 42))]
    assert answer() == [42]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 2810 to 2829, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 2829 to 2840, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 2840 to 2774, on the release tree:
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
#: RE-PINNED 2026-08-25, 2774 to 2784, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 2784 to 2793 (+9), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2793 to 2813 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 2813 to 2661 (-152), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 2661 to 2654 (-7), the subtract-atom primitive and the
#: Counter grain for -=: a new engine head shifts every twin's load structure,
#: and the removal doors changed meaning where a twin spells one [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 2654
