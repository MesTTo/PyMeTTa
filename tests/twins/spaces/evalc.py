"""Purpose: examples/spaces/evalc.metta in Python: naming the space you evaluate in.

Each space compiles its own equations into its own module, so `distance` means
feet in `&self` and metres in `&metric`, and `evalc` is how you reach the other
one. `space.eval(term)` IS evalc, to the letter: its signature is a term plus a
space, and the space is the handle it hangs off. So the whole example reads as
two handles and the same term asked of each.

`bind! &metric (new-space)` is `petta.space("&metric")`, because binding a name
to a space is Python's own name binding and a space exists from its first
write. All three definitions arrive through the decorator, and the third is the
one that used to need the container door: `(= (preferred-space) &metric)`
answers a bare space name, which the mention door now spells as
`S["&metric"]`. The removal is `-=` on the equation atom, and it takes the
compiled clause with it, so the last question sees the inherited `&self`
answer.

Three terms here are arithmetic over two GROUND operands, `(+ 5 5)` twice and
`(+ 1 1)` once, and they name their head at the `S["+"]` door rather than using
Python's `+`. That is deliberate: on a grounded number Python's operators are
that number's own arithmetic, so `ground(5) + 5` is 10 rather than the term
`(+ 5 5)`, and only inside a compiled body does `+` BUILD one (residue, P14.4).
PERFECT: one lifted operand stages the term, `ground(5) + 5` building `(+ 5 5)`
the way the guide's `G(1) + 2` does.

Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import petta
from petta import S, V, equation
from petta.errors import MettaOperationError

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1


def twin(m):
    """Give one name two meanings, one per space, and ask each of them."""
    metric = petta.space("&metric")
    evalc = m.fn["evalc"]

    @metric.define(name="distance")
    def metric_distance(x):
        return x * 1000

    @m.define
    def distance(x):
        return x * 5280

    # The ambient space answers in feet, the named one in metres.
    assert distance(2) == [10560]
    assert metric.eval(S.distance(2)) == [2000]

    # &self names the ambient space, so evalc there is eval, and the two doors
    # say so: this handle's own eval, and the engine's `eval` by name.
    assert m.eval(S["+"](5, 5)) == [10]
    assert m.fn["eval"](S["+"](5, 5)).one() == 10

    # The expression is handed over unevaluated. Were it not, it would already
    # have been reduced here before the space argument could select another.
    assert metric.eval(S.distance(S["+"](1, 1))) == [2000]

    # context-space, read inside evalc, reports the space evalc selected, and
    # it answers the HANDLE, so the claim compares handles rather than names.
    assert m.fn["context-space"]().one() == m
    assert metric.fn["context-space"]().one() == metric

    # The space argument is evaluated, so a function answering a space name can
    # name it, and that call is not a handle: it goes to `evalc` by name.
    @m.define(name="preferred-space")
    def preferred_space():
        return S["&metric"]  # rung: the example's subject is a function that answers a space NAME, where a handle is a host value a body cannot close over

    assert evalc(S.distance(2), S["preferred-space"]()).one() == 2000

    # A space is an atom beginning with &; anything else is refused with a
    # sentence rather than read as a silently empty space.
    refusal = None
    try:
        evalc(S.distance(2), 7).one()
    except MettaOperationError as error:
        refusal = error
    assert str(refusal) == "evalc: SpaceType expected, found 7"

    # The removal funnel owns the stored equation and its compiled clause, so
    # the metric answer leaves and the inherited &self one becomes visible.
    metric -= equation(S.distance(V.x)).to(V.x * 1000)
    assert metric.eval(S.distance(2)) == [10560]
