"""Purpose: examples/spaces/spaces.metta in Python: writes a later match can see.

`matchtrickery` adds two atoms and matches them in one expression, and the
example's point is the ordering: `let*` binds both writes before the match
reads the space, so the match sees them.

The whole equation compiles, and every part of it is a Python spelling now. A
statement sequence inside a compiled body IS `let*`, so the two writes bind and
the match reads afterwards, in the source order the example depends on;
the local handle returned by `context-space` takes ordinary `+=` writes; and
`match(space, pattern, template)` is the ask itself, the same word Python reads
at three positions. Calling the definition and reading its answers are
ordinary Python.
"""

from metta import S, V, fn, match

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 6046 to 6065, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 6065 to 6071, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 6071 to 6040, on the release tree:
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
BUDGET = 6040


def twin(m):
    """Store one self-writing definition, then read what calling it answers."""

    # (= (matchtrickery)
    #    (let* (($t1 (add-atom &self (foo a)))
    #           ($t2 (add-atom &self (foo b))))
    #          (match &self (foo $1) (bar $1))))
    @m.define
    def matchtrickery():
        space = fn.context_space()
        space += S.foo(S.a)
        space += S.foo(S.b)
        return match(space, S.foo(V.x), S.bar(V.x))

    assert matchtrickery() == [S.bar(S.a), S.bar(S.b)]
