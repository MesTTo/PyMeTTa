"""Purpose: examples/spaces/evalc.metta in Python: naming the space you evaluate in.

Each space compiles its own equations into its own module, so `distance` means
feet in `&self` and metres in `&metric`, and `evalc` is how you reach the other
one. `space.eval(term)` IS evalc, to the letter: its signature is a term plus a
space, and the space is the handle it hangs off. So the whole example reads as
two handles and the same term asked of each.

`bind! &metric (new-space)` is `m.space("&metric")`, because binding a name to
a space is Python's own name binding and a space exists from its first write.
Both definitions arrive through the decorator, one per space, which is what
makes the same name two different functions. The removal is `-=` on the
equation atom, and it takes the compiled clause with it, so the last question
sees the inherited `&self` answer.

Three terms here are arithmetic over two GROUND operands, `(+ 5 5)` twice and
`(+ 1 1)` once, and they name their head at the `S["+"]` door rather than using
Python's `+`. That is deliberate: on a grounded number Python's operators are
that number's own arithmetic, so `val(5) + 5` is 10 rather than the term
`(+ 5 5)`, and only inside a compiled body does `+` BUILD one (residue, P14.4).
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import MettaOperationError, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11798 to 7462, -4336 (-36.8%), by the twin contract
#: change: ten `(test ...)` terms became ten Python `assert`s, so the `test`
#: wrapper left the engine ten times over, and the type-error form dropped its
#: `catch` and `repr` as well because a refusal at the Python door is an
#: exception with a sentence. What did NOT move is the two definitions, the two
#: writes, the removal and every evaluation. Against the example's 21008 the
#: ratio is 0.3552.
#: Prior: 11798, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 7462


def twin(m):
    """Give one name two meanings, one per space, and ask each of them."""
    metric = m.space("&metric")

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
    assert m.fn("eval")(S["+"](5, 5)) == 10

    # The expression is handed over unevaluated. Were it not, it would already
    # have been reduced here before the space argument could select another.
    assert metric.eval(S.distance(S["+"](1, 1))) == [2000]

    # context-space, read inside evalc, reports the space evalc selected, and
    # the handle it was asked through is where that name comes from.
    assert str(m.fn("context-space")()) == m.space_name
    assert str(metric.fn("context-space")()) == metric.space_name

    # The space argument is evaluated, so a function answering a space name can
    # name it, and that call is not a handle: it goes to `evalc` by name.
    m += equation(S["preferred-space"]()).to(S[metric.space_name])
    assert m.fn("evalc")(S.distance(2), S["preferred-space"]()) == 2000

    # A space is an atom beginning with &; anything else is refused with a
    # sentence rather than read as a silently empty space.
    refusal = None
    try:
        m.fn("evalc")(S.distance(2), 7)
    except MettaOperationError as error:
        refusal = error
    assert str(refusal) == "evalc: SpaceType expected, found 7"

    # The removal funnel owns the stored equation and its compiled clause, so
    # the metric answer leaves and the inherited &self one becomes visible.
    metric -= equation(S.distance(V.x)).to(V.x * 1000)
    assert metric.eval(S.distance(2)) == [10560]
