"""The Python twin of examples/spaces/parametric_spaces.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 8400


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(new-space (cache &primary-kb 100))
    yield m.eval(expr(S["new-space"], expr(S["cache"], S["&primary-kb"], 100)))

    # !(new-space (cache &secondary-kb 10))
    yield m.eval(expr(S["new-space"], expr(S["cache"], S["&secondary-kb"], 10)))

    # !(add-atom
    #    (cache &primary-kb 100)
    #    (= (cache-config)
    #       (let (cache $base $limit)
    #            (context-space)
    #            (config $base $limit))))
    yield m.eval(
        expr(
            S["add-atom"],
            expr(S["cache"], S["&primary-kb"], 100),
            expr(
                S["="],
                expr(S["cache-config"]),
                expr(
                    S["let"],
                    expr(S["cache"], V["base"], V["limit"]),
                    expr(S["context-space"]),
                    expr(S["config"], V["base"], V["limit"]),
                ),
            ),
        )
    )

    # !(add-atom
    #    (cache &secondary-kb 10)
    #    (= (cache-config)
    #       (let (cache $base $limit)
    #            (context-space)
    #            (config $base $limit))))
    yield m.eval(
        expr(
            S["add-atom"],
            expr(S["cache"], S["&secondary-kb"], 10),
            expr(
                S["="],
                expr(S["cache-config"]),
                expr(
                    S["let"],
                    expr(S["cache"], V["base"], V["limit"]),
                    expr(S["context-space"]),
                    expr(S["config"], V["base"], V["limit"]),
                ),
            ),
        )
    )

    # !(add-atom (cache &primary-kb 100) (entry primary))
    yield m.eval(
        expr(S["add-atom"], expr(S["cache"], S["&primary-kb"], 100), expr(S["entry"], S["primary"]))
    )

    # !(add-atom (cache &secondary-kb 10) (entry secondary))
    yield m.eval(
        expr(
            S["add-atom"],
            expr(S["cache"], S["&secondary-kb"], 10),
            expr(S["entry"], S["secondary"]),
        )
    )

    # !(test
    #    (evalc (cache-config) (cache &primary-kb 100))
    #    (config &primary-kb 100))
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["cache-config"]), expr(S["cache"], S["&primary-kb"], 100)),
            expr(S["config"], S["&primary-kb"], 100),
        )
    )

    # !(test
    #    (evalc (cache-config) (cache &secondary-kb 10))
    #    (config &secondary-kb 10))
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["cache-config"]), expr(S["cache"], S["&secondary-kb"], 10)),
            expr(S["config"], S["&secondary-kb"], 10),
        )
    )

    # !(test
    #    (collapse (match (cache &primary-kb 100) (entry $which) $which))
    #    (primary))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"],
                    expr(S["cache"], S["&primary-kb"], 100),
                    expr(S["entry"], V["which"]),
                    V["which"],
                ),
            ),
            expr(S["primary"]),
        )
    )

    # !(test
    #    (collapse (match (cache &secondary-kb 10) (entry $which) $which))
    #    (secondary))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"],
                    expr(S["cache"], S["&secondary-kb"], 10),
                    expr(S["entry"], V["which"]),
                    V["which"],
                ),
            ),
            expr(S["secondary"]),
        )
    )

    # !(test (get-type (cache &primary-kb 100)) SpaceType)
    yield m.eval(
        expr(
            S["test"], expr(S["get-type"], expr(S["cache"], S["&primary-kb"], 100)), S["SpaceType"]
        )
    )

    yield from ()
