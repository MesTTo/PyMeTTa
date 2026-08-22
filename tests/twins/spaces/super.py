"""The Python twin of examples/spaces/super.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 13746


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (store $atom) (stored $atom))
    m += expr(S["="], expr(S["store"], V["atom"]), expr(S["stored"], V["atom"]))

    # !(bind! &guarded (new-space))
    yield m.eval(expr(S["bind!"], S["&guarded"], expr(S["new-space"])))

    # !(add-atom &guarded (= (store $atom)
    #                        (if (== $atom bad) refused (super (store $atom)))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&guarded"],
            expr(
                S["="],
                expr(S["store"], V["atom"]),
                expr(
                    S["if"],
                    expr(S["=="], V["atom"], S["bad"]),
                    S["refused"],
                    expr(S["super"], expr(S["store"], V["atom"])),
                ),
            ),
        )
    )

    # !(test (evalc (store good) &guarded) (stored good))
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["store"], S["good"]), S["&guarded"]),
            expr(S["stored"], S["good"]),
        )
    )

    # !(test (evalc (store bad) &guarded) refused)
    yield m.eval(
        expr(S["test"], expr(S["evalc"], expr(S["store"], S["bad"]), S["&guarded"]), S["refused"])
    )

    # !(test (store bad) (stored bad))
    yield m.eval(expr(S["test"], expr(S["store"], S["bad"]), expr(S["stored"], S["bad"])))

    # !(bind! &wrapping (new-space))
    yield m.eval(expr(S["bind!"], S["&wrapping"], expr(S["new-space"])))

    # !(add-atom &wrapping (= (car-atom $expr) (wrapped (super (car-atom $expr)))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&wrapping"],
            expr(
                S["="],
                expr(S["car-atom"], V["expr"]),
                expr(S["wrapped"], expr(S["super"], expr(S["car-atom"], V["expr"]))),
            ),
        )
    )

    # !(test (evalc (car-atom (1 2 3)) &wrapping) (wrapped 1))
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["car-atom"], expr(1, 2, 3)), S["&wrapping"]),
            expr(S["wrapped"], 1),
        )
    )

    # !(test (car-atom (1 2 3)) 1)
    yield m.eval(expr(S["test"], expr(S["car-atom"], expr(1, 2, 3)), 1))

    # !(test (evalc (store good) &self) (stored good))
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["store"], S["good"]), S["&self"]),
            expr(S["stored"], S["good"]),
        )
    )

    yield from ()
