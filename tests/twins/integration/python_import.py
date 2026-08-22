"""The Python twin of examples/integration/python_import.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 2081


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self "_fixtures/python_import_file.py")
    yield m.eval(
        expr(
            S["import!"],
            S["&self"],
            val("examples/integration/_fixtures/python_import_file.py"),
        )
    )

    # !(test (repr (py-call (python_import_file.greet "PeTTa User"))) "Hello, PeTTa User from Python!")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["repr"],
                expr(S["py-call"], expr(S["python_import_file.greet"], val("PeTTa User"))),
            ),
            val("Hello, PeTTa User from Python!"),
        )
    )

    # !(test (py-call (python_import_file.add 10 20)) 30)
    yield m.eval(expr(S["test"], expr(S["py-call"], expr(S["python_import_file.add"], 10, 20)), 30))

    yield from ()
