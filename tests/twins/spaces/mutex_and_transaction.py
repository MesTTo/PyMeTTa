"""The Python twin of examples/spaces/mutex_and_transaction.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 5311


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &temp (cnt 37))
    yield m.eval(expr(S["add-atom"], S["&temp"], expr(S["cnt"], 37)))

    # (= (sloppyinc)
    #    (match &temp (cnt $x)
    #           ((remove-atom &temp (cnt $x))
    #            (let $inc (+ $x 1)
    #                      (add-atom &temp (cnt $inc))))))
    m += expr(
        S["="],
        expr(S["sloppyinc"]),
        expr(
            S["match"],
            S["&temp"],
            expr(S["cnt"], V["x"]),
            expr(
                expr(S["remove-atom"], S["&temp"], expr(S["cnt"], V["x"])),
                expr(
                    S["let"],
                    V["inc"],
                    expr(S["+"], V["x"], 1),
                    expr(S["add-atom"], S["&temp"], expr(S["cnt"], V["inc"])),
                ),
            ),
        ),
    )

    # (= (mutexinc)
    #    (with_mutex testmutex
    #                (match &temp (cnt $x)
    #                       ((remove-atom &temp (cnt $x))
    #                        (let $inc (+ $x 1)
    #                             (add-atom &temp (cnt $inc)))))))
    m += expr(
        S["="],
        expr(S["mutexinc"]),
        expr(
            S["with_mutex"],
            S["testmutex"],
            expr(
                S["match"],
                S["&temp"],
                expr(S["cnt"], V["x"]),
                expr(
                    expr(S["remove-atom"], S["&temp"], expr(S["cnt"], V["x"])),
                    expr(
                        S["let"],
                        V["inc"],
                        expr(S["+"], V["x"], 1),
                        expr(S["add-atom"], S["&temp"], expr(S["cnt"], V["inc"])),
                    ),
                ),
            ),
        ),
    )

    # (= (Transaction_rollback_fail_to_inc)
    #    (transaction (match &temp (cnt $x)
    #                        ((remove-atom &temp (cnt $x))
    #                         (let $inc (+ $x 1)
    #                              (add-atom &temp (cnt $inc)))
    #                         (empty)))))
    m += expr(
        S["="],
        expr(S["Transaction_rollback_fail_to_inc"]),
        expr(
            S["transaction"],
            expr(
                S["match"],
                S["&temp"],
                expr(S["cnt"], V["x"]),
                expr(
                    expr(S["remove-atom"], S["&temp"], expr(S["cnt"], V["x"])),
                    expr(
                        S["let"],
                        V["inc"],
                        expr(S["+"], V["x"], 1),
                        expr(S["add-atom"], S["&temp"], expr(S["cnt"], V["inc"])),
                    ),
                    expr(S["empty"]),
                ),
            ),
        ),
    )

    # !(hyperpose ((mutexinc) (mutexinc) (mutexinc) (mutexinc) (mutexinc)))
    yield None

    # !(test (collapse (get-atoms &temp)) ((cnt 42)))
    yield None

    # !(Transaction_rollback_fail_to_inc)
    yield m.eval(expr(S["Transaction_rollback_fail_to_inc"]))

    # !(test (collapse (get-atoms &temp)) ((cnt 42)))
    yield None

    yield from ()
