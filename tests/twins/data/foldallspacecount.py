"""The Python twin of examples/data/foldallspacecount.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 3263


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (foo 1)
    m += expr(S["foo"], 1)

    # (foo 2)
    m += expr(S["foo"], 2)

    # (foo 3)
    m += expr(S["foo"], 3)

    # (= (countitem) (let $x (match &self (foo $1) (foo $1)) 1))
    m += expr(
        S["="],
        expr(S["countitem"]),
        expr(
            S["let"],
            V["x"],
            expr(S["match"], S["&self"], expr(S["foo"], V["1"]), expr(S["foo"], V["1"])),
            1,
        ),
    )

    # (= (merge $a $b) (+ $a $b))
    m += expr(S["="], expr(S["merge"], V["a"], V["b"]), expr(S["+"], V["a"], V["b"]))

    # (= (spacecount $x) (foldall merge (countitem) 0))
    m += expr(
        S["="],
        expr(S["spacecount"], V["x"]),
        expr(S["foldall"], S["merge"], expr(S["countitem"]), 0),
    )

    # !(test (foldall merge (countitem) 0) 3)
    yield m.eval(expr(S["test"], expr(S["foldall"], S["merge"], expr(S["countitem"]), 0), 3))

    yield from ()
