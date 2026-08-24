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

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1


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
    assert m.fn.eval(G(5) + 5).one() == 10

    # The expression is handed over unevaluated. Were it not, it would already
    # have been reduced here before the space argument could select another.
    assert metric.eval(S.distance(G(1) + 1)) == [2000]

    # context-space, read inside evalc, reports the space evalc selected, and
    # it answers the HANDLE, so the claim compares handles rather than names.
    assert m.fn.context_space().one() == m
    assert metric.fn.context_space().one() == metric

    # The space argument is evaluated, so a function answering a space can name
    # it, and that call is not a handle: it goes to `evalc` by name.
    @m.define
    def preferred_space():
        return metric

    assert m.fn.evalc(S.distance(2), S.preferred_space()).one() == 2000

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
