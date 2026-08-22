"""The Python twin of examples/integration/c_extension/c_extension.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 99523


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_import))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_import"])))

    # !(import! &self (library lib_file))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_file"])))

    # !(if (file-exists "./examples/integration/c_extension/cbump.so")
    #      (import_prolog_functions_from_file
    #         "./examples/integration/c_extension/loader.pl" (c-bump))
    #      (println! "SKIPPED c_extension: cbump.so is not built, see the README beside this file"))
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/cbump.so")),
            expr(
                S["import_prolog_functions_from_file"],
                val("./examples/integration/c_extension/loader.pl"),
                expr(S["c-bump"]),
            ),
            expr(
                S["println!"],
                val("SKIPPED c_extension: cbump.so is not built, see the README beside this file"),
            ),
        )
    )

    # !(if (file-exists "./examples/integration/c_extension/cbump.so")
    #      (test (eval (c-bump 41)) 42)
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/cbump.so")),
            expr(S["test"], expr(S["eval"], expr(S["c-bump"], 41)), 42),
            val(value=True),
        )
    )

    yield from ()
