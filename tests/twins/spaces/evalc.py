"""Purpose: examples/spaces/evalc.metta in Python: naming the space you evaluate in.

Each space compiles its own equations into its own module, so `distance` means
feet in `&self` and metres in `&metric`, and `evalc` is how you reach the other
one. `space.eval(term)` IS evalc, to the letter: its signature is a term plus a
space, and the space is the handle it hangs off. So the whole example reads as
two handles and the same term asked of each.

`bind! &metric (new-space)` is `metta.space(S.metric)`, because binding a name
to a space is Python's own name binding and a space exists from its first
write. All three definitions arrive through the decorator, the third included:
`(= (preferred-space) &metric)` answers a space, and a compiled body reads a
Python name bound to one as the grounded atom a handle already is, so the
equation stores `&metric` without any symbol spelling of a space
[measured 2026-08-24: a `@m.define`d body returning a handle stores the space
operand itself; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. The removal is `-=` on the equation atom, and
it takes the compiled clause with it, so the last question sees the inherited
`&self` answer.

Three terms here are arithmetic over two GROUND operands, `(+ 5 5)` twice and
`(+ 1 1)` once, and each is written with the guide's lift: one grounded operand
STAGES its operator, so `G(5) + 5` is the term `(+ 5 5)` rather than 10.

Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import G, S, V, equation
from metta.errors import MettaOperationError


def twin(m):
    """Give one name two meanings, one per space, and ask each of them."""
    metric = metta.space(S.metric)

    @metric.define
    def distance(x):
        return x * 1000

    assert distance(2) == [2000]
    del distance

    @m.define
    def distance(x):
        return x * 5280

    # The ambient space answers in feet, the named one in metres.
    assert distance(2) == [10560]
    assert metric.eval(S.distance(2)) == [2000]

    # &self names the ambient space, so evalc there is eval, and the two doors
    # say so: this handle's own eval, and the engine's `eval` by name.
    assert m.eval(G(5) + 5) == [10]
    assert m.fn.eval(G(5) + 5) == [10]

    # The expression is handed over unevaluated. Were it not, it would already
    # have been reduced here before the space argument could select another.
    assert metric.eval(S.distance(G(1) + 1)) == [2000]

    # context-space, read inside evalc, reports the space evalc selected, and
    # it answers the HANDLE, so the claim compares handles rather than names.
    assert m.fn.context_space() == [m]
    assert metric.fn.context_space() == [metric]

    # The space argument is evaluated, so a function answering a space can name
    # it, and that call is not a handle: it goes to `evalc` by name.
    @m.define
    def preferred_space():
        return metric

    assert m.fn.evalc(S.distance(2), S.preferred_space()) == [2000]

    # A space is an atom beginning with &; anything else is refused with a
    # sentence rather than read as a silently empty space.
    refusal = None
    try:
        m.fn.evalc(S.distance(2), 7).one()
    except MettaOperationError as error:
        refusal = error
    assert str(refusal) == "evalc: SpaceType expected, found 7"

    # The removal funnel owns the stored equation and its compiled clause, so
    # the metric answer leaves and the inherited &self one becomes visible.
    metric -= equation(S.distance(V.x)).to(V.x * 1000)
    assert metric.eval(S.distance(2)) == [10560]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 9484 to 9730, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 9730 to 9744, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 9744 to 9692, on the release tree:
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
#: RE-PINNED 2026-08-25, 9692 to 9702, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 9702 to 9680 (-22), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 9680 to 9700 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 9700
