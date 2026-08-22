"""The Python twin of examples/spaces/spaces_find.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 20742


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_spaces))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_spaces"])))

    # (friend a b)
    m += expr(S["friend"], S["a"], S["b"])

    # (friend b c)
    m += expr(S["friend"], S["b"], S["c"])

    # !(test (collapse (if (find &self (friend $a $b))
    #                      (if (find &self (friend $b $c))
    #                          (FoundChain $a $b $c)
    #                          (MissedSecondPiece))
    #                      (MissedAllPieces)))
    #        ((FoundChain a b c) (MissedSecondPiece)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["if"],
                    expr(S["find"], S["&self"], expr(S["friend"], V["a"], V["b"])),
                    expr(
                        S["if"],
                        expr(S["find"], S["&self"], expr(S["friend"], V["b"], V["c"])),
                        expr(S["FoundChain"], V["a"], V["b"], V["c"]),
                        expr(S["MissedSecondPiece"]),
                    ),
                    expr(S["MissedAllPieces"]),
                ),
            ),
            expr(expr(S["FoundChain"], S["a"], S["b"], S["c"]), expr(S["MissedSecondPiece"])),
        )
    )

    yield from ()
