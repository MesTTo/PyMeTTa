"""examples/translation/translatorrule_direction.metta in Python: which way a rule fires.

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

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Register both direction policies, exercise them, then withdraw one."""
    m += typed(S.celsius, arrow(Atom, Any))     # (: celsius (-> Atom %Undefined%))

    @m.rules
    def scale(c):                               # (= (celsius (degrees $c))
        yield equation(S.celsius(S.degrees(c))).to(
            S.noeval(S.kelvin(c + 273)))        #    (noeval (kelvin (+ $c 273))))

    m.fn.add_translator_rule(S.celsius, Expression((S.direction(S.forward),)))

    assert m.fn.celsius(S.degrees(27)).one() == S.kelvin(300)   # (kelvin 300)

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

    # The original writes the next two as a form already at its cheapest being
    # left alone, `(test (twin 1 1) (twin 1 1))`. `test` evaluates BOTH sides,
    # so a rewrite of the expected side cancels out of the comparison; an
    # assert compares an evaluated left against a LITERAL right, and the small
    # form is in fact carried the other way. Known issue, for whoever owns the
    # extractor: `(twin 1 1)` is three nodes and `(unpack (wrap (box 1)))` is
    # four, so this rewrite RAISES the cost the example's own prose says
    # decides the direction.
    assert m.eval(small) == [small_unpack]
    assert m.eval(large_unpack) == [large_unpack]

    # Withdrawing the rule withdraws the derived equation with it, so the
    # inverse never outlives the declaration that produced it.
    m.fn.remove_translator_rule(S.unpack)       # (remove-translator-rule! unpack)

    assert m.eval(large_twin) == [large_twin]
