"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/13-strategy_internals.metta in Python: lib_strategy from the inside.

A strategy is a NAME, so `S.mark` is what every operation here is handed:
applying one lowers to a MeTTa call and never installs a host callback, which
is the library's whole claim and the reason a Python callable would be the
wrong argument.

The typed operations take a SORT, so the declarations below are the ordinary
`typed` and `arrow` doors and the term's own type is what decides whether the
strategy runs.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, arrow, lib, typed


def declined(answers):
    """Whether a strategy answered nothing, `Empty` being how it says so."""
    return [answer for answer in answers if answer != S.Empty] == []


def twin(m):
    """Application, the two traversals, and the three typed operations."""
    m += lib.strategy

    @m.define
    def mark(x):
        # (= (mark $x) (marked $x))
        return S.marked(x)

    evaluate, everywhere = m.fn["strategy-eval"], m.fn["strategy-all"]
    tail, one = m.fn["strategy-all-tail"], m.fn["strategy-one"]

    # Application itself: a strategy NAME and a term. Every combinator
    # bottoms out here.
    assert evaluate(S.mark, S.a) == [S.marked(S.a)]
    assert evaluate(S.id, S.a) == [S.a]
    assert evaluate(S.mark, S.a) == m.fn["strategy-apply"](S.mark, S.a)

    # `all`: the strategy at every immediate child, INCLUDING the written
    # expression head, because a head is a child in MeTTa's flat term model.
    assert everywhere(S.mark, S.h(S.a, S.b)) == [
        Expression((S.marked(S.h), S.marked(S.a), S.marked(S.b)))
    ]
    assert everywhere(S.mark, S.leaf) == [S.leaf]
    assert everywhere(S.mark, ()) == [()]

    # The recursion inside it: `strategy-all` takes the head off and hands
    # the TAIL to this one, so the two agree on an expression and differ on
    # everything else.
    assert tail(S.mark, (S.a, S.b)) == [(S.marked(S.a), S.marked(S.b))]
    assert tail(S.mark, ()) == [()]
    assert tail(S.mark, (S.a, S.b)) == [everywhere(S.mark, S.h(S.a, S.b))[0][1:]]
    assert declined(tail(S.mark, S.leaf))
    assert everywhere(S.mark, S.leaf) == [S.leaf]

    # `one`: every successful single-child rewrite, left to right, as
    # separate answers rather than one term with every child rewritten.
    # The `Empty` a declining position answers is a sentinel the original's
    # `collapse` prunes; a Python answer list keeps it, so it is filtered by
    # name rather than pretended away.
    rewrites = [answer for answer in one(S.mark, S.h(S.a)) if answer != S.Empty]
    assert rewrites == [Expression((S.marked(S.h), S.a)), S.h(S.marked(S.a))]
    assert declined(one(S.mark, S.leaf))

    # The three typed operations under the application operator. A
    # type-preserving strategy has the same sort on both sides, and
    # `strategy-typed-tp` finds that sort by MATCHING the declaration.
    m += typed(S.DA, S.Type)
    m += typed(S.DS, S.Type)
    m += typed(S.da, S.DA)
    m += typed(S.preserve, arrow(S.DA, S.DA))

    @m.define
    def preserve(x):
        # (= (preserve $x) (kept $x))
        return S.kept(x)

    assert m.fn["strategy-typed-tp"](S.preserve, S.da) == [S.kept(S.da)]
    assert declined(m.fn["strategy-typed-tp"](S.preserve, 1))

    # The type-unifying scheme takes the RESULT sort instead.
    m += typed(S.summarize, arrow(S.DA, S.DS))

    @m.define
    def summarize(x):
        # (= (summarize $x) (sum $x))
        return S.sum(x)

    assert m.fn["strategy-typed-tu"](S.summarize, S.DS, S.da) == [S.sum(S.da)]
    assert declined(m.fn["strategy-typed-tu"](S.summarize, S.DA, S.da))

    # Both hand the sort they selected to the one gradual type check.
    apply_typed = m.fn["strategy-typed-apply"]
    assert apply_typed(S.preserve, S.DA, S.da) == [S.kept(S.da)]
    assert declined(apply_typed(S.preserve, S.DA, 1))
    assert apply_typed(S.preserve, S.DA, S.da) == m.fn["◁"](S.preserve, S.TP, S.da)

    # An ill-typed subject reports its OWN error rather than being silently
    # declined, so a term that cannot be typed at all is a different answer
    # from a term whose type does not fit.
    assert apply_typed(S.preserve, S.DA, S.undeclared_name()) == [
        S.kept(S.undeclared_name())
    ]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 422964 inferences, 0.9520x the example's 444306; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 422964
