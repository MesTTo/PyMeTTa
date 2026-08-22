"""The Python twin of examples/integration/import_duplicate_cycle.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 8602


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self _fixtures/imports/overhaul/duplicate)
    yield m.eval(
        expr(
            S["import!"],
            S["&self"],
            S["examples/integration/_fixtures/imports/overhaul/duplicate"],
        )
    )

    # !(import! &self ./_fixtures/imports/overhaul/./duplicate.metta)
    yield m.eval(
        expr(
            S["import!"],
            S["&self"],
            S["examples/integration/_fixtures/imports/overhaul/duplicate.metta"],
        )
    )

    # !(import! &self _fixtures/imports/overhaul/cycle_a)
    yield m.eval(
        expr(
            S["import!"],
            S["&self"],
            S["examples/integration/_fixtures/imports/overhaul/cycle_a"],
        )
    )

    # !(test (collapse (duplicate-import-result)) (loaded-once))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["duplicate-import-result"])),
            expr(S["loaded-once"]),
        )
    )

    # !(test (cycle-a) a)
    yield m.eval(expr(S["test"], expr(S["cycle-a"]), S["a"]))

    # !(test (cycle-b) b)
    yield m.eval(expr(S["test"], expr(S["cycle-b"]), S["b"]))

    yield from ()
