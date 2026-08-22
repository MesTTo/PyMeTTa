"""The Python twin of examples/spaces/evalc.metta: naming the space you evaluate in.

Each space compiles its own equations into its own module, so `distance` means
feet in `&self` and metres in `&metric`, and `evalc` is how you reach the other
one. Removing the named space's equation removes its compiled answer too, so the
last assertion sees the inherited `&self` one.

`bind! &metric (new-space)` is `m.space("&metric")`: naming a space IS Python's
own name binding, and the space exists from its first write. Both definitions
arrive through `@<space>.define`, so the twin shows the same name meaning two
different functions in two spaces, and the removal is `-=` on the equation atom.

Three of this file's terms are arithmetic over two GROUND operands, `(+ 5 5)`
twice and `(+ 1 1)` once, and those name their head at the `S["+"]` door rather
than using Python's `+`. That is the deliberate spelling and not a dropped rung:
on a grounded number Python's operators are that number's own arithmetic, so
`val(5) + 5` is 10 rather than the term `(+ 5 5)`, and only inside a compiled
body does `+` BUILD one. basics/math.py records the same rule for the same
reason.
"""

from petta import S, V, equation, expr, val

#: The answer group a write form contributes: `bind!`, `add-atom` and
#: `remove-atom` each answer the unit, which is what Python's own None means at
#: this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11267 to 11798, +531 (+4.7%), by the P14 twin-style
#: rewrite, whose causes pull opposite ways and were split by re-measuring this
#: file with only the decorator change reverted: 10,034, twice. The three
#: write forms moved to their Python doors, `m.space("&metric")` for the bind!,
#: `metric += equation(...)` for the add and `metric -= equation(...)` for the
#: removal, worth -1233 between them. Both equations then moved to the
#: decorator door, worth +1764 for two, one of them into a NAMED space, which
#: is the same order as the +1629-plus-193 measured for two in &self. The ten
#: assertions are the same terms spelled with named symbols and did not move.
#: Prior: ADDED 2026-08-22 at 11267 by the wave-3 spaces baseline.
BUDGET = 11798


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    evalc, context = S.evalc, S["context-space"]
    here = S[m.space_name]

    # !(bind! &metric (new-space))
    metric = m.space("&metric")
    at_metric = S[metric.space_name]
    yield WROTE

    # !(add-atom &metric (= (distance $x) (* $x 1000)))
    @metric.define(name="distance")
    def metric_distance(x):
        return x * 1000

    yield WROTE

    # (= (distance $x) (* $x 5280))
    @m.define
    def distance(x):
        return x * 5280

    # The ambient space answers in feet, the named one in metres.
    # !(test (distance 2) 10560)
    yield m.eval(S.test(S.distance(2), 10560))
    # !(test (evalc (distance 2) &metric) 2000)
    yield m.eval(S.test(evalc(S.distance(2), at_metric), 2000))

    # &self names the ambient space, so evalc there is eval.
    # !(test (evalc (+ 5 5) &self) 10)
    yield m.eval(S.test(evalc(S["+"](5, 5), here), 10))
    # !(test (eval (+ 5 5)) 10)
    yield m.eval(S.test(S.eval(S["+"](5, 5)), 10))

    # The expression is handed over unevaluated: were it not, it would already
    # have been reduced here before the space argument could select another one.
    # !(test (evalc (distance (+ 1 1)) &metric) 2000)
    yield m.eval(S.test(evalc(S.distance(S["+"](1, 1)), at_metric), 2000))

    # context-space, read inside evalc, reports the space evalc selected.
    # !(test (context-space) &self)
    yield m.eval(S.test(context(), here))
    # !(test (evalc (context-space) &metric) &metric)
    yield m.eval(S.test(evalc(context(), at_metric), at_metric))

    # The space argument is evaluated, so a function answering a space name can
    # name it.
    # (= (preferred-space) &metric)
    m += equation(S["preferred-space"]()).to(at_metric)
    # !(test (evalc (distance 2) (preferred-space)) 2000)
    yield m.eval(
        S.test(evalc(S.distance(2), S["preferred-space"]()), 2000)
    )

    # A space is an atom beginning with &; anything else is a type error rather
    # than a silently empty space.
    # !(test (repr (catch (evalc (distance 2) 7)))
    #        "(Error (type_error SpaceType 7) (context evalc invalid MeTTa operation argument))")
    yield m.eval(
        S.test(
            S.repr(S.catch(evalc(S.distance(2), 7))),
            val(
                "(Error (type_error SpaceType 7) (context evalc invalid "
                "MeTTa operation argument))"
            ),
        )
    )

    # The removal funnel owns the stored equation and its compiled clause, so
    # the named 2000 answer leaves and the inherited &self equation is visible.
    # !(remove-atom &metric (= (distance $x) (* $x 1000)))
    metric -= equation(S.distance(V.x)).to(V.x * 1000)
    yield WROTE

    # !(test (evalc (distance 2) &metric) 10560)
    yield m.eval(S.test(evalc(S.distance(2), at_metric), 10560))
