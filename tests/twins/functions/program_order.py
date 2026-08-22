"""The Python twin of examples/functions/program_order.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1223


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(p121-example-respond me)
    yield m.eval(expr(S["p121-example-respond"], S["me"]))

    # (= (p121-example-respond me) hello)
    m += expr(S["="], expr(S["p121-example-respond"], S["me"]), S["hello"])

    # !(test (p121-example-respond me) hello)
    yield m.eval(expr(S["test"], expr(S["p121-example-respond"], S["me"]), S["hello"]))

    yield from ()
