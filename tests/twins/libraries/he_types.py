"""The Python twin of examples/libraries/he_types.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 18997


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # !(test (is-function (-> Atom Atom)) True)
    yield m.eval(
        expr(
            S["test"], expr(S["is-function"], expr(S["->"], S["Atom"], S["Atom"])), val(value=True)
        )
    )

    # !(test (is-function Atom) False)
    yield m.eval(expr(S["test"], expr(S["is-function"], S["Atom"]), val(value=False)))

    # (: type1 Type)
    m += expr(S[":"], S["type1"], S["Type"])

    # (: A type1)
    m += expr(S[":"], S["A"], S["type1"])

    # !(test (type-cast A type1 &self) A)
    yield m.eval(expr(S["test"], expr(S["type-cast"], S["A"], S["type1"], S["&self"]), S["A"]))

    # !(test (type-cast 1 type1 &self) (Error 1 BadType))
    yield m.eval(
        expr(
            S["test"],
            expr(S["type-cast"], 1, S["type1"], S["&self"]),
            expr(S["Error"], 1, S["BadType"]),
        )
    )

    # !(test (type-cast A Symbol &self) A)
    yield m.eval(expr(S["test"], expr(S["type-cast"], S["A"], S["Symbol"], S["&self"]), S["A"]))

    # !(test (type-cast 1 Number &self) 1)
    yield m.eval(expr(S["test"], expr(S["type-cast"], 1, S["Number"], S["&self"]), 1))

    # !(test (type-cast B type1 &self) B)
    yield m.eval(expr(S["test"], expr(S["type-cast"], S["B"], S["type1"], S["&self"]), S["B"]))

    # !(test (match-types Atom Atom "Matched!" "Didn't match") "Matched!")
    yield m.eval(
        expr(
            S["test"],
            expr(S["match-types"], S["Atom"], S["Atom"], val("Matched!"), val("Didn't match")),
            val("Matched!"),
        )
    )

    # !(test (match-types Atom Number "Matched!" "Didn't match") "Matched!")
    yield m.eval(
        expr(
            S["test"],
            expr(S["match-types"], S["Atom"], S["Number"], val("Matched!"), val("Didn't match")),
            val("Matched!"),
        )
    )

    # !(test (match-types Bool Number "Matched!" "Didn't match") "Didn't match")
    yield m.eval(
        expr(
            S["test"],
            expr(S["match-types"], S["Bool"], S["Number"], val("Matched!"), val("Didn't match")),
            val("Didn't match"),
        )
    )

    # !(test (match-types (List $x) (List Number) "Matched!" "Didn't match") "Matched!")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match-types"],
                expr(S["List"], V["x"]),
                expr(S["List"], S["Number"]),
                val("Matched!"),
                val("Didn't match"),
            ),
            val("Matched!"),
        )
    )

    # !(test (first-from-pair (A B)) A)
    yield m.eval(expr(S["test"], expr(S["first-from-pair"], expr(S["A"], S["B"])), S["A"]))

    # !(test (second-from-pair (A B)) B)
    yield m.eval(expr(S["test"], expr(S["second-from-pair"], expr(S["A"], S["B"])), S["B"]))

    # !(test (match-type-or True Number Bool) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["match-type-or"], val(value=True), S["Number"], S["Bool"]),
            val(value=True),
        )
    )

    yield from ()
