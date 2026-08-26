"""examples/libraries/derived_forms.metta in Python: swapping a fused form for its expansion.

The engine fuses `once` into the compiler, and lib_derived writes the same form
as an ordinary MeTTa equation that rewrites the call into `(take 1 ...)`. This
file swaps one for the other in a live session and shows the answers do not
move, so `once` is the subject throughout and stays named.

`noisy` is an ordinary compiled definition, and both halves of its body have a
spelling now. The write is `fn.add_atom(seen, S.saw(x))`: the STATIC namespace
is what a compiled body reads for a hyphenated engine function, and the space
it writes to is the HANDLE, encoded into the equation at decoration time, so no
space is ever named as a symbol. Binding that call to `_` and answering `x` is
Python's own way of saying `(let $_ <effect> $x)`, which is the sequencing the
example writes; `seen += S.saw(x)` is the write door everywhere else and a
compiled nested body refuses it because Python's own augmented-assignment rule
would make `seen` an unbound local rather than a closure cell.
"""

import metta
from metta import S, fn, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 10186 to 10224, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 10224 to 10230, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 10230 to 10201, on the release tree:
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
#: RE-PINNED 2026-08-25, 10201 to 10204, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 10204 to 11233 (+1029), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 11233 to 11253 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 11253
def twin(m):
    """Answer with the compiler's `once`, then the library's, then the compiler's."""
    once = m.fn.once

    # Before the import, `once` is the compiler's own clause.
    assert once(S.superpose((1, 2, 3))) == [1]

    m += lib.derived

    # After it, `once` is an ordinary MeTTa equation, and it answers the same.
    assert once(S.superpose((1, 2, 3))) == [1]
    assert list(once(S.superpose((1, 2, 3)))) == [1]
    assert list(once(S.empty())) == []

    # It is still the FIRST answer of a generator with side effects, so the
    # rest of the generator does not run.
    seen = metta.space(S.seen)

    @m.define
    def noisy(x):
        # (= (noisy $x) (let $_ (add-atom &seen (saw $x)) $x))
        _ = fn.add_atom(seen, S.saw(x))
        return x

    assert once(S.superpose((S.noisy(S.a), S.noisy(S.b)))) == [S.a]
    assert list(seen) == [S.saw(S.a)]

    # The swap is a session decision, not a per-call one: registering is
    # global, and removing puts the compiler's own clause back in charge.
    m.fn.remove_translator_rule(S.once)

    assert once(S.superpose((1, 2, 3))) == [1]
