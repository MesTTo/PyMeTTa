"""Purpose: exercise forward and bidirectional translator-rule declarations.

Assumes:
  - the rule metadata and six claims mirror the direction example
    [source: examples/translation/translatorrule_direction.metta lines 8-46; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - the inverse fires only while its bidirectional declaration is installed
    [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/translatorrule_direction.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
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
    """Register both direction policies, exercise them, then withdraw one."""
    m += S[":"](S.celsius, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.celsius(S.degrees(V.c))).to(
        S.noeval(S.kelvin(V.c + 273))
    )
    # Known issue: a call through the function namespace answers a LAZY view,
    # so the perfect statement-level spelling of a directive,
    # `m.fn.add_translator_rule(head)`, REGISTERS NOTHING until something pulls
    # its answers [measured 2026-08-23: the rule fires only after list() of the
    # view]. The term door evaluates eagerly, so a directive is written that
    # way until a side-effecting call runs at statement level.
    m.eval(S["add-translator-rule!"](S.celsius, Expression((S.direction(S.forward),))))

    assert m.fn.celsius(S.degrees(27)).one() == S.kelvin(300)

    m += S[":"](S.unpack, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.unpack(S.wrap(S.box(V.x)))).to(
        S.noeval(S.twin(V.x, V.x))
    )
    m.eval(S["add-translator-rule!"](S.unpack, Expression((S.direction(S.bidirectional),))))

    small = S.twin(1, 1)
    small_unpack = S.unpack(S.wrap(S.box(1)))
    large = S.a(S.b, S.c)
    large_twin = S.twin(large, large)
    large_unpack = S.unpack(S.wrap(S.box(large)))

    assert m.eval(small_unpack) == [small]
    assert m.eval(large_twin) == [large_unpack]

    # The example writes these two as `(test (twin 1 1) (twin 1 1))` and
    # `(test (unpack (wrap (box (a b c)))) (unpack (wrap (box (a b c)))))`,
    # reading them as a form already at its cheapest being left alone. `test`
    # evaluates BOTH sides, so a rewrite of the expected side cancels out of
    # the comparison; an `assert` compares an evaluated left against a LITERAL
    # right, and the small form is in fact carried the other way. Known issue,
    # for whoever owns the extractor: `(twin 1 1)` is three nodes and
    # `(unpack (wrap (box 1)))` is four, so this rewrite RAISES the cost the
    # example's own prose says decides the direction.
    assert m.eval(small) == [small_unpack]
    assert m.eval(large_unpack) == [large_unpack]

    m.eval(S["remove-translator-rule!"](S.unpack))

    assert m.eval(large_twin) == [large_twin]
