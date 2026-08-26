"""examples/translation/translatorrule_cost.metta in Python: cost, and a joined head.

A bidirectional rule says two forms are equivalent, and a COST is what decides
which one the compiler emits: a rewrite fires only when it lowers the total,
and a form's cost is its node count unless a rule declares one for its head.
Declared at 10, `pow2` is expensive enough that squaring a small argument
expands and squaring a big one collapses, and the file's first three claims are
that turn.

The second half is a CONJUNCTIVE left side. `unit-of` has no equation at all;
the rule itself names the call it rewrites and a second pattern matched against
the space, so `$q` joins the two and `$u` carries the answer out. That is why
its type declaration is data rather than an annotation: there is no def to
annotate.

`pow2` is an ordinary compiled function whose parameter is annotated `Atom`, so
the argument arrives unreduced, which is what the original's own type
declaration says. Its body names `mul`, and that name takes the bracket: the
operator word table owns `S.mul` and makes it `*`, where this `mul` is a plain
data head with no equations behind it and multiplying two expressions is not
what the rule means.
"""

from typing import Any

from metta import Atom, Expression, S, V, arrow, equation, typed


def twin(m):
    """Register the costed and conjunctive rules, then exercise every case."""

    @m.define
    def pow2(x: Atom) -> Any:            # (: pow2 (-> Atom %Undefined%))
        return S.noeval(S["mul"](x, x))  # rung: the word table owns S.mul, which is *, and this mul is a data head

    m.fn.add_translator_rule(            # (add-translator-rule! pow2
        S.pow2,                          #   ((direction bidirectional) (cost 10)))
        Expression((S.direction(S.bidirectional), S.cost(10))),
    )

    # (pow2 3) costs 10 for the head plus 1 for the argument, and (mul 3 3) is
    # three nodes, so the squaring is expanded.
    assert pow2(3) == [S["mul"](3, 3)]   # rung: as above, the exact door for a data head the word table has taken

    # The same declaration collapses the multiplication back when the argument
    # is big enough to make writing it twice the more expensive side. The
    # bound namespace keeps a bracket exact for the same reason.
    large = S.a(S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert m.fn["mul"](large, large) == [S.pow2(large)]

    # A CONJUNCTIVE left side names several patterns that must all match: the
    # first is the call the rule rewrites and the rest are matched against the
    # space, so a rule can look at the program around the call.
    m += [(S.unit, S.mass, S.kg), (S.unit, S.length, S.m)]
    m += typed(S.unit_of, arrow(Atom, Any))

    m.fn.add_translator_rule(            # (add-translator-rule! unit-of
        S.unit_of,                       #   ((left ((unit-of $q) (unit $q $u)))
        Expression((                     #    (right (in $u))))
            S.left(Expression((S.unit_of(V.q), S.unit(V.q, V.u)))),
            S.right(S["in"](V.u)),
        )),
    )

    assert m.fn.unit_of(S.mass) == [S["in"](S.kg)]
    assert m.fn.unit_of(S.length) == [S["in"](S.m)]

    # A call whose conjuncts do not match is a rule miss like any other, so it
    # has no answer rather than bringing the translation down.
    assert m.fn.unit_of(S.time) == []

    # The rule compiles to the equation an author would have written by hand,
    # with the conjuncts as a `match` chain: the engine's own conjunctive query
    # does the join.
    compiled = m[equation(S.unit_of(V.q)).to(V.body)]
    assert [row.body[0] for row in compiled] == [S.match]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 12646 to 13239, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 13239 to 13245, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 13245 to 13228, on the release tree:
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
BUDGET = {
    # Widened to 13220..13257 by a second ten-round full-lane
    # observe pass; observations count both passes.
    "minimum": 13220,
    "maximum": 13257,
    "observations": 20,
    "protocol": "full-lane/219/workers=32",
}
