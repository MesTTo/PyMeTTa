"""Purpose: examples/ch04-spaces-and-matching/04-02-patterns-and-bindings/04-match_snapshot.metta in Python: the query is a snapshot.

`match` finds every row BEFORE any output template runs, so a template that
writes to the space cannot change what the match still has to answer. The
language specifies this rather than leaving it open, and the graph-rewriting
example is why: reversing links one at a time as they are found would break the
cycle after the first rewrite.

The Python door says the same thing by being an ordinary sequence.
`space[pattern]` answers a materialised view, so the three loop links are all
found before the first `-=` runs, and the comprehension at the bottom pulls
both `item` rows before the first `visit` call removes the other one. Nothing
about that is special pleading: it is what `for row in rows` means.

`visit` is one compiled definition where the original writes two equations, and
the door picked the form: two literal heads at one arity would overlap if they
were written as bare coexisting equations, so a Python `match` statement is the
spelling and it lowers to MeTTa's own case tower, exclusivity structural inside
one equation. The removals inside it are the engine's own `remove-atom` through
the mention door, with the snapshot space itself as the operand, because a
compiled body carries a handle the way a term does.
"""

from collections import Counter

import metta
from metta import S, V, fn

#: Upstream's own example, verbatim: three links form a loop, the fourth does
#: not.
LINKS = [(S.A, S.B), (S.B, S.C), (S.C, S.A), (S.C, S.E)]


def twin(m):
    """Reverse every link of a cycle, then watch two templates delete each other."""
    m += [S.link(tail, head) for tail, head in LINKS]

    # All three rows are found before the first reversal breaks the cycle, so
    # all three are reverted and (link C E) is left alone.
    loop = m[S.link(V.x, V.y), S.link(V.y, V.z), S.link(V.z, V.x)]
    assert len(loop) == 3
    for row in loop:
        m -= S.link(row.x, row.y)
        m += S.link(row.y, row.x)

    assert Counter(S.link(row.x, row.y) for row in m[S.link(V.x, V.y)]) == Counter(
        [S.link(S.C, S.E), S.link(S.B, S.A), S.link(S.C, S.B), S.link(S.A, S.C)]
    )

    # The single-pattern case, reduced to its detector: two rows, and each
    # template removes the OTHER one. A lazy query would lose the row it had
    # not reached yet and answer once.
    snapshot = metta.space(S.snapshot)
    snapshot += S.item(S.alpha)
    snapshot += S.item(S.beta)

    # (= (visit alpha) (let () (remove-atom &snapshot (item beta)) alpha))
    # (= (visit beta)  (let () (remove-atom &snapshot (item alpha)) beta))
    @m.define
    def visit(item):
        match item:
            case S.alpha:
                _gone = fn.remove_atom(snapshot, S.item(S.beta))
                return S.alpha
            case S.beta:
                _gone = fn.remove_atom(snapshot, S.item(S.alpha))
                return S.beta

    assert [visit(row.x).one() for row in snapshot[S.item(V.x)]] == [S.alpha, S.beta]

    # Both removals happened, so the space is empty: each row's template ran,
    # and ran against the space the other row's template had written to.
    assert not list(snapshot)


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 7056 to 7094, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 7094 to 7102, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 7102 to 7071, on the release tree:
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
#: RE-PINNED 2026-08-25, 7071 to 7076, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 7076 to 7108 (+32), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 7108 to 7128 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 7128 to 4998 (-2130), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4998
