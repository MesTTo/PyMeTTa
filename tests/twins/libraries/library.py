"""The Python twin of examples/libraries/library.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 151231


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_roman))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_roman"])))

    # !(test (map-flat (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(
        expr(S["test"], expr(S["map-flat"], expr(S["+"], 1), expr(1, 2, 3)), expr(2, 3, 4))
    )

    yield from ()
