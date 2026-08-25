"""examples/functions/partialdef.metta in Python: a definition answering a partial.

`(mp)` answers `(+)`, which takes both its arguments later, so `(mp 1 1)` is
2. `..` composes two partial applications, and `(plus1times2)` answers that
composition, so `(plus1times2 1)` is `(1 + 1) * 2`.

All three definitions are decorated Python functions. `..` carries its MeTTa
name through `name=".."`, because `..` is not a Python identifier, while its
BODY is ordinary Python: `f1(f2(arg))` applies two parameters in turn, which
is the variable-head application the subset already reads.

The other two bodies are partial applications of heads Python's operators
cannot reach. `(+)`, `(* 2)` and `(+ 1)` have no operator spelling, because
`+` needs both operands to be an operator at all, so they are written by
CALLING the word-table symbols: `S.add()` is `(+)` and `S.mul(2)` is `(* 2)`.
The decorated `compose` object carries its exact MeTTa head `..` when another
compiled body mentions it.
"""

from metta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 8622 to 8660, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 8660 to 8668, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 8668 to 8637, on the release tree:
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
BUDGET = 8637


def twin(m):
    """Answer a partial application from a definition, then compose two."""

    @m.define
    def mp():
        # (= (mp) (+))
        return S.add()

    assert m.eval(S.mp(1, 1)) == [2]

    @m.define(name="..")
    def compose(f1, f2, arg):
        # (= (.. $f1 $f2 $arg) ($f1 ($f2 $arg)))
        return f1(f2(arg))

    @m.define
    def plus1times2():
        # (= (plus1times2) (.. (* 2) (+ 1)))
        return compose(S.mul(2), S.add(1))

    assert m.eval(S.plus1times2(1)) == [4]
