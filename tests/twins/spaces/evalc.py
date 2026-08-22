"""The Python twin of examples/spaces/evalc.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 11267


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(bind! &metric (new-space))
    yield m.eval(expr(S["bind!"], S["&metric"], expr(S["new-space"])))

    # !(add-atom &metric (= (distance $x) (* $x 1000)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&metric"],
            expr(S["="], expr(S["distance"], V["x"]), expr(S["*"], V["x"], 1000)),
        )
    )

    # (= (distance $x) (* $x 5280))
    m += expr(S["="], expr(S["distance"], V["x"]), expr(S["*"], V["x"], 5280))

    # !(test (distance 2) 10560)
    yield m.eval(expr(S["test"], expr(S["distance"], 2), 10560))

    # !(test (evalc (distance 2) &metric) 2000)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["distance"], 2), S["&metric"]), 2000))

    # !(test (evalc (+ 5 5) &self) 10)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["+"], 5, 5), S["&self"]), 10))

    # !(test (eval (+ 5 5)) 10)
    yield m.eval(expr(S["test"], expr(S["eval"], expr(S["+"], 5, 5)), 10))

    # !(test (evalc (distance (+ 1 1)) &metric) 2000)
    yield m.eval(
        expr(
            S["test"], expr(S["evalc"], expr(S["distance"], expr(S["+"], 1, 1)), S["&metric"]), 2000
        )
    )

    # !(test (context-space) &self)
    yield m.eval(expr(S["test"], expr(S["context-space"]), S["&self"]))

    # !(test (evalc (context-space) &metric) &metric)
    yield m.eval(
        expr(S["test"], expr(S["evalc"], expr(S["context-space"]), S["&metric"]), S["&metric"])
    )

    # (= (preferred-space) &metric)
    m += expr(S["="], expr(S["preferred-space"]), S["&metric"])

    # !(test (evalc (distance 2) (preferred-space)) 2000)
    yield m.eval(
        expr(S["test"], expr(S["evalc"], expr(S["distance"], 2), expr(S["preferred-space"])), 2000)
    )

    # !(test (repr (catch (evalc (distance 2) 7)))
    #        "(Error (type_error SpaceType 7) (context evalc invalid MeTTa operation argument))")
    yield m.eval(
        expr(
            S["test"],
            expr(S["repr"], expr(S["catch"], expr(S["evalc"], expr(S["distance"], 2), 7))),
            val(
                "(Error (type_error SpaceType 7) (context evalc invalid MeTTa operation argument))"
            ),
        )
    )

    # !(remove-atom &metric (= (distance $x) (* $x 1000)))
    yield m.eval(
        expr(
            S["remove-atom"],
            S["&metric"],
            expr(S["="], expr(S["distance"], V["x"]), expr(S["*"], V["x"], 1000)),
        )
    )

    # !(test (evalc (distance 2) &metric) 10560)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["distance"], 2), S["&metric"]), 10560))

    yield from ()
