"""The Python twin of examples/spaces/selfprog.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 3282


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (function1) OK)
    m += expr(S["="], expr(S["function1"]), S["OK"])

    # !(remove-atom &self (= (function1) OK))
    yield m.eval(expr(S["remove-atom"], S["&self"], expr(S["="], expr(S["function1"]), S["OK"])))

    # !(test (repr (function1)) "(function1)")
    yield m.eval(expr(S["test"], expr(S["repr"], expr(S["function1"])), val("(function1)")))

    # !(add-atom &self (= (function1) (OK)))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["="], expr(S["function1"]), expr(S["OK"]))))

    # !(test (repr (function1)) "(OK)")
    yield m.eval(expr(S["test"], expr(S["repr"], expr(S["function1"])), val("(OK)")))

    yield from ()
