"""The Python twin of examples/data/constanthead.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1593


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (h (justdata haha $B) $C)
    #    (+ $B $C))
    m += expr(
        S["="],
        expr(S["h"], expr(S["justdata"], S["haha"], V["B"]), V["C"]),
        expr(S["+"], V["B"], V["C"]),
    )

    # !(test (h (justdata haha 30) 40) 70)
    yield m.eval(expr(S["test"], expr(S["h"], expr(S["justdata"], S["haha"], 30), 40), 70))

    yield from ()
