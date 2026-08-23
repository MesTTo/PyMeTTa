"""Purpose: exercise translator costs and conjunctive translator-rule heads.

Assumes:
  - the two declarations and six claims mirror the cost example
    [source: examples/translation/translatorrule_cost.metta lines 8-55; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - extraction follows the declared cost and the conjunctive rule joins through
    the surrounding space [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/translatorrule_cost.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Register the costed and conjunctive rules, then exercise every case."""
    m += S[":"](S.pow2, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.pow2(V.x)).to(S.noeval(S.mul(V.x, V.x)))
    # Known issue: a call through the function namespace answers a LAZY view,
    # so the perfect statement-level spelling of a directive,
    # `m.fn.add_translator_rule(head)`, REGISTERS NOTHING until something pulls
    # its answers [measured 2026-08-23: the rule fires only after list() of the
    # view]. The term door evaluates eagerly, so a directive is written that
    # way until a side-effecting call runs at statement level.
    m.eval(S["add-translator-rule!"](
        S.pow2,
        Expression((S.direction(S.bidirectional), S.cost(10))),
    ))

    assert m.fn.pow2(3).one() == S.mul(3, 3)

    large = S.a(S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert m.fn.mul(large, large).one() == S.pow2(large)

    m += S.unit(S.mass, S.kg)
    m += S.unit(S.length, S.m)
    m += S[":"](S["unit-of"], S["->"](S.Atom, S["%Undefined%"]))

    conjuncts = Expression((S["unit-of"](V.q), S.unit(V.q, V.u)))
    m.eval(S["add-translator-rule!"](
        S["unit-of"],
        Expression((S.left(conjuncts), S.right(S["in"](V.u)))),
    ))

    assert m.fn.unit_of(S.mass).one() == S["in"](S.kg)
    assert m.fn.unit_of(S.length).one() == S["in"](S.m)
    assert m.fn.unit_of(S.time) == []

    compiled = m[equation(S["unit-of"](V.q)).to(V.body)]
    assert [row.body[0] for row in compiled] == [S.match]
