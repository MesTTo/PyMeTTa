"""The Python twin of examples/spaces/event_catalog.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 6716


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (match &petta (vocabulary delivery $a $b $c) ($a $b $c))
    #        (at-most-once at-least-once per-write-exactly))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["vocabulary"], S["delivery"], V["a"], V["b"], V["c"]),
                expr(V["a"], V["b"], V["c"]),
            ),
            expr(S["at-most-once"], S["at-least-once"], S["per-write-exactly"]),
        )
    )

    # !(test (match &petta (vocabulary event-order $a $b) ($a $b))
    #        (ordered unordered))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["vocabulary"], S["event-order"], V["a"], V["b"]),
                expr(V["a"], V["b"]),
            ),
            expr(S["ordered"], S["unordered"]),
        )
    )

    # !(test (match &petta (kind events $ctx $delivery $order) $delivery)
    #        (one-of delivery))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["kind"], S["events"], V["ctx"], V["delivery"], V["order"]),
                V["delivery"],
            ),
            expr(S["one-of"], S["delivery"]),
        )
    )

    # !(test (if-error (catch (add-atom &petta (events &feed eventually)))
    #                  refused admitted)
    #        refused)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(
                    S["catch"],
                    expr(
                        S["add-atom"], S["&petta"], expr(S["events"], S["&feed"], S["eventually"])
                    ),
                ),
                S["refused"],
                S["admitted"],
            ),
            S["refused"],
        )
    )

    # !(add-atom &native-events (reading 1))
    yield m.eval(expr(S["add-atom"], S["&native-events"], expr(S["reading"], 1)))

    # !(test (collapse (match &petta (events &native-events $d $o) declared)) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"],
                    S["&petta"],
                    expr(S["events"], S["&native-events"], V["d"], V["o"]),
                    S["declared"],
                ),
            ),
            expr(),
        )
    )

    # !(test (match &petta (vocabulary agenda-policy $a $b $c $d $e) ($a $b $c $d $e))
    #        (declaration recency specificity priority user))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["vocabulary"], S["agenda-policy"], V["a"], V["b"], V["c"], V["d"], V["e"]),
                expr(V["a"], V["b"], V["c"], V["d"], V["e"]),
            ),
            expr(S["declaration"], S["recency"], S["specificity"], S["priority"], S["user"]),
        )
    )

    # !(test (match &petta (policy reaction-order $knob $default) ($knob $default))
    #        (agenda declaration))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["policy"], S["reaction-order"], V["knob"], V["default"]),
                expr(V["knob"], V["default"]),
            ),
            expr(S["agenda"], S["declaration"]),
        )
    )

    # !(test (match &petta (kind agenda $ctx $policy $fn) $policy)
    #        (one-of agenda-policy))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["kind"], S["agenda"], V["ctx"], V["policy"], V["fn"]),
                V["policy"],
            ),
            expr(S["one-of"], S["agenda-policy"]),
        )
    )

    # !(test (match &petta (kind on $ctx $pattern $op $priority) $priority)
    #        (optional integer))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["kind"], S["on"], V["ctx"], V["pattern"], V["op"], V["priority"]),
                V["priority"],
            ),
            expr(S["optional"], S["integer"]),
        )
    )

    yield from ()
