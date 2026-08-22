"""The Python twin of examples/integration/import_relative_nested.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 8459


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self _fixtures/imports/relative/root)
    yield m.eval(
        expr(
            S["import!"],
            S["&self"],
            S["examples/integration/_fixtures/imports/relative/root"],
        )
    )

    # !(test (from-sibling) 42)
    yield m.eval(expr(S["test"], expr(S["from-sibling"]), 42))

    # !(test (from-second) 7)
    yield m.eval(expr(S["test"], expr(S["from-second"]), 7))

    yield from ()
