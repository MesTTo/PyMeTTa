"""The Python twin of examples/spaces/state.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 3971


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(bind! state (new-state rest))
    state = m.eval(expr(S["new-state"], S["rest"]))[0]
    yield [expr()]

    # !(test (get-state state) rest)
    yield m.eval(expr(S["test"], expr(S["get-state"], state), S["rest"]))

    # !(test (get-state (change-state! state active)) active)
    yield m.eval(
        expr(
            S["test"],
            expr(S["get-state"], expr(S["change-state!"], state, S["active"])),
            S["active"],
        )
    )

    # !(test (get-state state) active)
    yield m.eval(expr(S["test"], expr(S["get-state"], state), S["active"]))

    # !(test (get-type (new-state 5)) (StateMonad Number))
    yield m.eval(
        expr(
            S["test"],
            expr(S["get-type"], expr(S["new-state"], 5)),
            expr(S["StateMonad"], S["Number"]),
        )
    )

    # !(test (get-type (new-state "hi")) (StateMonad String))
    yield m.eval(
        expr(
            S["test"],
            expr(S["get-type"], expr(S["new-state"], val("hi"))),
            expr(S["StateMonad"], S["String"]),
        )
    )

    # !(test (get-state (change-state! (new-state 1) 2)) 2)
    yield m.eval(
        expr(
            S["test"], expr(S["get-state"], expr(S["change-state!"], expr(S["new-state"], 1), 2)), 2
        )
    )

    yield from ()
