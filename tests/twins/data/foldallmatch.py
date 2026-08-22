"""The Python twin of examples/data/foldallmatch.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4216


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (kb 1)
    m += expr(S["kb"], 1)

    # (kb 2)
    m += expr(S["kb"], 2)

    # !(test (foldall + (match &self (kb $n) (+ $n 1)) 0)
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["foldall"],
                S["+"],
                expr(S["match"], S["&self"], expr(S["kb"], V["n"]), expr(S["+"], V["n"], 1)),
                0,
            ),
            5,
        )
    )

    # (= (f) 1)
    m += expr(S["="], expr(S["f"]), 1)

    # (= (f) 2)
    m += expr(S["="], expr(S["f"]), 2)

    # !(test (foldall + (let $x (f) (+ 1 $x)) 0)
    #         5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["foldall"],
                S["+"],
                expr(S["let"], V["x"], expr(S["f"]), expr(S["+"], 1, V["x"])),
                0,
            ),
            5,
        )
    )

    yield from ()
