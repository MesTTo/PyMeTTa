"""The Python twin of examples/spaces/matchnested2.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4670


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (hide $1) (empty))
    m += expr(S["="], expr(S["hide"], V["1"]), expr(S["empty"]))

    # !(hide ((add-atom &self (friend tim tom))
    #         (add-atom &self (friend tom tam))
    #         (add-atom &self (friend sim som))
    #         (add-atom &self (friend som sam))))
    yield m.eval(
        expr(
            S["hide"],
            expr(
                expr(S["add-atom"], S["&self"], expr(S["friend"], S["tim"], S["tom"])),
                expr(S["add-atom"], S["&self"], expr(S["friend"], S["tom"], S["tam"])),
                expr(S["add-atom"], S["&self"], expr(S["friend"], S["sim"], S["som"])),
                expr(S["add-atom"], S["&self"], expr(S["friend"], S["som"], S["sam"])),
            ),
        )
    )

    # !(hide (match &self (, (friend $1 $2) (friend $2 $3))
    #                     ((add-atom &self (transitive $1 $2 $3))
    #                      (remove-atom &self (friend $1 $2))
    #                      (remove-atom &self (friend $2 $3)))))
    yield m.eval(
        expr(
            S["hide"],
            expr(
                S["match"],
                S["&self"],
                expr(S[","], expr(S["friend"], V["1"], V["2"]), expr(S["friend"], V["2"], V["3"])),
                expr(
                    expr(S["add-atom"], S["&self"], expr(S["transitive"], V["1"], V["2"], V["3"])),
                    expr(S["remove-atom"], S["&self"], expr(S["friend"], V["1"], V["2"])),
                    expr(S["remove-atom"], S["&self"], expr(S["friend"], V["2"], V["3"])),
                ),
            ),
        )
    )

    # !(test (msort (collapse (match &self (transitive $1 $2 $3) (transitive $1 $2 $3))))
    #        ((transitive sim som sam) (transitive tim tom tam)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["msort"],
                expr(
                    S["collapse"],
                    expr(
                        S["match"],
                        S["&self"],
                        expr(S["transitive"], V["1"], V["2"], V["3"]),
                        expr(S["transitive"], V["1"], V["2"], V["3"]),
                    ),
                ),
            ),
            expr(
                expr(S["transitive"], S["sim"], S["som"], S["sam"]),
                expr(S["transitive"], S["tim"], S["tom"], S["tam"]),
            ),
        )
    )

    yield from ()
