"""examples/ch20-extending-the-engine/20-01-translator-rules/02-translatorrule_direction.metta in Python: which way a rule fires.

A rule is left-to-right by default and saying so explicitly changes nothing. A
BIDIRECTIONAL rule is one declaration from which the engine derives the inverse
equation and registers the head it is rooted at, so nobody writes it twice.
Both sides are then rewritable, and what decides a given call is the form's
COST: a rewrite fires only when it lowers the node count.

Both rules are laws with structured heads, `(celsius (degrees $c))` and
`(unpack (wrap (box $x)))`, so both are `@m.rules` bundles: the head is the
pattern it looks like, the parameters ARE the equations' variables, and the
inverse the engine derives is rooted at the head the author wrote rather than
at whatever a lowered body would have left there. Their type declarations are
data for the same reason, since a bundle has no signature to annotate.

A bundle body EXECUTES rather than lowering, and the arithmetic on a rule
variable builds, so `c + 273` there is the term `(+ $c 273)`.
"""

from typing import Any

from metta import Atom, Expression, S, arrow, equation, typed


def twin(m):
    """Register both direction policies, exercise them, then withdraw one."""
    m += typed(S.celsius, arrow(Atom, Any))     # (: celsius (-> Atom %Undefined%))

    @m.rules
    def scale(c):                               # (= (celsius (degrees $c))
        yield equation(S.celsius(S.degrees(c))).to(
            S.noeval(S.kelvin(c + 273)))        #    (noeval (kelvin (+ $c 273))))

    m.fn.add_translator_rule(S.celsius, Expression((S.direction(S.forward),)))

    assert m.fn.celsius(S.degrees(27)) == [S.kelvin(300)]   # (kelvin 300)

    m += typed(S.unpack, arrow(Atom, Any))      # (: unpack (-> Atom %Undefined%))

    @m.rules
    def unwrapping(x):                          # (= (unpack (wrap (box $x)))
        yield equation(S.unpack(S.wrap(S.box(x)))).to(
            S.noeval(S.twin(x, x)))             #    (noeval (twin $x $x)))

    m.fn.add_translator_rule(S.unpack, Expression((S.direction(S.bidirectional),)))

    small, small_unpack = S.twin(1, 1), S.unpack(S.wrap(S.box(1)))
    large = S.a(S.b, S.c)
    large_twin, large_unpack = S.twin(large, large), S.unpack(S.wrap(S.box(large)))

    # Four nodes against three, so this call goes forwards.
    assert m.eval(small_unpack) == [small]
    # Seven against six, because the argument is written twice on one side and
    # once on the other, so this one goes back.
    assert m.eval(large_twin) == [large_unpack]

    # A form already at its cheapest is left alone, exactly as the prose
    # says: `(twin 1 1)` is three nodes and its rewrite is four, so the
    # backward direction is BLOCKED by cost, and the fixed door shows it.
    # The old pin here recorded the pre-P14.32 fast path running the
    # derived equation raw, past the orientation gate that only lives in
    # translation; a rule-owned head's call now routes through the rule.
    assert m.eval(small) == [small]
    assert m.eval(large_unpack) == [large_unpack]

    # Withdrawing the rule withdraws the derived equation with it, so the
    # inverse never outlives the declaration that produced it.
    m.fn.remove_translator_rule(S.unpack)       # (remove-translator-rule! unpack)

    assert m.eval(large_twin) == [large_twin]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 18967 to 19112, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 19112 to 19147, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 19147 to 19366, on the release tree:
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
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-PINNED 2026-09-01 on the operator-protocol tree. Ten fresh full-lane
#: observations had no spread, and the serial min-of-three confirmed the point
#: [measured: twin minimum 15562 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch20-extending-the-engine/20-01-translator-rules/02-translatorrule_direction.metta;
#: fixture=operator-protocol tree after python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10; commit=WORKTREE].
BUDGET = 15562
