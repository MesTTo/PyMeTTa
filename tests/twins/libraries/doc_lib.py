"""The Python twin of examples/libraries/doc_lib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 11626


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_doc))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_doc"])))

    # (@doc greet (@desc "Greets somebody by name"))
    m += expr(S["@doc"], S["greet"], expr(S["@desc"], val("Greets somebody by name")))

    # (= (greet $who) $who)
    m += expr(S["="], expr(S["greet"], V["who"]), V["who"])

    # (@doc add-two
    #       (@desc "Adds two numbers")
    #       (@params ((@param "the first") (@param "the second")))
    #       (@return "their sum"))
    m += expr(
        S["@doc"],
        S["add-two"],
        expr(S["@desc"], val("Adds two numbers")),
        expr(
            S["@params"],
            expr(expr(S["@param"], val("the first")), expr(S["@param"], val("the second"))),
        ),
        expr(S["@return"], val("their sum")),
    )

    # (= (add-two $a $b) (+ $a $b))
    m += expr(S["="], expr(S["add-two"], V["a"], V["b"]), expr(S["+"], V["a"], V["b"]))

    # !(test (get-doc greet) (@doc greet (@desc "Greets somebody by name")))
    yield m.eval(
        expr(
            S["test"],
            expr(S["get-doc"], S["greet"]),
            expr(S["@doc"], S["greet"], expr(S["@desc"], val("Greets somebody by name"))),
        )
    )

    # !(test (get-doc add-two)
    #        (@doc add-two
    #              (@desc "Adds two numbers")
    #              (@params ((@param "the first") (@param "the second")))
    #              (@return "their sum")))
    yield m.eval(
        expr(
            S["test"],
            expr(S["get-doc"], S["add-two"]),
            expr(
                S["@doc"],
                S["add-two"],
                expr(S["@desc"], val("Adds two numbers")),
                expr(
                    S["@params"],
                    expr(expr(S["@param"], val("the first")), expr(S["@param"], val("the second"))),
                ),
                expr(S["@return"], val("their sum")),
            ),
        )
    )

    # !(test (collapse (get-doc greet-nobody)) ())
    yield m.eval(
        expr(S["test"], expr(S["collapse"], expr(S["get-doc"], S["greet-nobody"])), expr())
    )

    # !(test (collapse (get-doc missing)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["get-doc"], S["missing"])), expr()))

    # !(test (collapse (undocumented)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["undocumented"])), expr()))

    yield from ()
