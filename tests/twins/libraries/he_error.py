"""The Python twin of examples/libraries/he_error.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 17863


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # !(test (let $result (catch (+ 40 2))
    #        (if-error $result
    #            Error
    #            $result))
    #        42)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["result"],
                expr(S["catch"], expr(S["+"], 40, 2)),
                expr(S["if-error"], V["result"], S["Error"], V["result"]),
            ),
            42,
        )
    )

    # (: a String)
    m += expr(S[":"], S["a"], S["String"])

    # !(test (if-error (+ 40 a) Error fine) Error)
    yield m.eval(
        expr(
            S["test"],
            expr(S["if-error"], expr(S["+"], 40, S["a"]), S["Error"], S["fine"]),
            S["Error"],
        )
    )

    # !(test (if-error (+ 40 undeclared-operand) Error fine) fine)
    yield m.eval(
        expr(
            S["test"],
            expr(S["if-error"], expr(S["+"], 40, S["undeclared-operand"]), S["Error"], S["fine"]),
            S["fine"],
        )
    )

    # !(test (let $result (catch (+ $left $right))
    #             (if-error $result
    #                 Error
    #                 $result))
    #        Error)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["result"],
                expr(S["catch"], expr(S["+"], V["left"], V["right"])),
                expr(S["if-error"], V["result"], S["Error"], V["result"]),
            ),
            S["Error"],
        )
    )

    # !(test (if-error (/ 40 0) Error fine) Error)
    yield m.eval(
        expr(S["test"], expr(S["if-error"], expr(S["/"], 40, 0), S["Error"], S["fine"]), S["Error"])
    )

    # !(test (if-error (Error 5 BadType) "Error!" "No error")
    #        "Error!")
    yield m.eval(
        expr(
            S["test"],
            expr(S["if-error"], expr(S["Error"], 5, S["BadType"]), val("Error!"), val("No error")),
            val("Error!"),
        )
    )

    # !(test (return-on-error (Error 5 BadType) 6)
    #        (Error 5 BadType))
    yield m.eval(
        expr(
            S["test"],
            expr(S["return-on-error"], expr(S["Error"], 5, S["BadType"]), 6),
            expr(S["Error"], 5, S["BadType"]),
        )
    )

    # !(test (return-on-error 5 6) 6)
    yield m.eval(expr(S["test"], expr(S["return-on-error"], 5, 6), 6))

    yield from ()
