"""The Python twin of examples/integration/c_extension/handle.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 105529


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_import))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_import"])))

    # !(import! &self (library lib_file))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_file"])))

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (import_prolog_functions_from_file
    #         "./examples/integration/c_extension/handle_loader.pl"
    #         (vector-new vector-nth vector-bump vector-length))
    #      (println! "SKIPPED handle: handle.so is not built, see the README beside this file"))
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/handle.so")),
            expr(
                S["import_prolog_functions_from_file"],
                val("./examples/integration/c_extension/handle_loader.pl"),
                expr(S["vector-new"], S["vector-nth"], S["vector-bump"], S["vector-length"]),
            ),
            expr(
                S["println!"],
                val("SKIPPED handle: handle.so is not built, see the README beside this file"),
            ),
        )
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (vector-length (vector-new 1000))) 1000)
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/handle.so")),
            expr(
                S["test"],
                expr(S["eval"], expr(S["vector-length"], expr(S["vector-new"], 1000))),
                1000,
            ),
            val(value=True),
        )
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (vector-nth (vector-new 1000) 700)) 700)
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/handle.so")),
            expr(
                S["test"],
                expr(S["eval"], expr(S["vector-nth"], expr(S["vector-new"], 1000), 700)),
                700,
            ),
            val(value=True),
        )
    )

    # (= (bump-thrice)
    #    (let $v (vector-new 4)
    #         (progn (vector-bump $v 0) (vector-bump $v 0) (vector-bump $v 0))))
    m += expr(
        S["="],
        expr(S["bump-thrice"]),
        expr(
            S["let"],
            V["v"],
            expr(S["vector-new"], 4),
            expr(
                S["progn"],
                expr(S["vector-bump"], V["v"], 0),
                expr(S["vector-bump"], V["v"], 0),
                expr(S["vector-bump"], V["v"], 0),
            ),
        ),
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (bump-thrice)) 3)
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/handle.so")),
            expr(S["test"], expr(S["eval"], expr(S["bump-thrice"])), 3),
            val(value=True),
        )
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (let $vector (vector-new 1) (get-metatype $vector)) Grounded)
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/handle.so")),
            expr(
                S["test"],
                expr(
                    S["let"],
                    V["vector"],
                    expr(S["vector-new"], 1),
                    expr(S["get-metatype"], V["vector"]),
                ),
                S["Grounded"],
            ),
            val(value=True),
        )
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (let $v (vector-new 1) (== $v $v))) True)
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_extension/handle.so")),
            expr(
                S["test"],
                expr(
                    S["eval"],
                    expr(S["let"], V["v"], expr(S["vector-new"], 1), expr(S["=="], V["v"], V["v"])),
                ),
                val(value=True),
            ),
            val(value=True),
        )
    )

    yield from ()
