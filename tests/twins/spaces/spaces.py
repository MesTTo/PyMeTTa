"""The Python twin of examples/spaces/spaces.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 2220


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (matchtrickery)
    #    (let* (($t1 (add-atom &self (foo a)))
    #           ($t2 (add-atom &self (foo b))))
    #          (match &self (foo $1) (bar $1))))
    m += expr(
        S["="],
        expr(S["matchtrickery"]),
        expr(
            S["let*"],
            expr(
                expr(V["t1"], expr(S["add-atom"], S["&self"], expr(S["foo"], S["a"]))),
                expr(V["t2"], expr(S["add-atom"], S["&self"], expr(S["foo"], S["b"]))),
            ),
            expr(S["match"], S["&self"], expr(S["foo"], V["1"]), expr(S["bar"], V["1"])),
        ),
    )

    # !(test (collapse (matchtrickery))
    #        ((bar a) (bar b)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["matchtrickery"])),
            expr(expr(S["bar"], S["a"]), expr(S["bar"], S["b"])),
        )
    )

    yield from ()
