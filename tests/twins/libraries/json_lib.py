"""The Python twin of examples/libraries/json_lib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 94061


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_json))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_json"])))

    # !(test (let $d (json-decode "{\"a\":1,\"b\":2}") (collapse (get-keys $d)))
    #        (a b))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["d"],
                expr(S["json-decode"], val('{"a":1,"b":2}')),
                expr(S["collapse"], expr(S["get-keys"], V["d"])),
            ),
            expr(S["a"], S["b"]),
        )
    )

    # !(test (let $d (json-decode "{\"a\":1,\"b\":2}") (get-value $d a)) 1)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["d"],
                expr(S["json-decode"], val('{"a":1,"b":2}')),
                expr(S["get-value"], V["d"], S["a"]),
            ),
            1,
        )
    )

    # !(test (let $d (json-decode "{\"a\":1}") (collapse (get-value $d missing))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["d"],
                expr(S["json-decode"], val('{"a":1}')),
                expr(S["collapse"], expr(S["get-value"], V["d"], S["missing"])),
            ),
            expr(),
        )
    )

    # !(test (json-decode "[1,2,3]") (1 2 3))
    yield m.eval(expr(S["test"], expr(S["json-decode"], val("[1,2,3]")), expr(1, 2, 3)))

    # !(test (json-decode "\"plain\"") "plain")
    yield m.eval(expr(S["test"], expr(S["json-decode"], val('"plain"')), val("plain")))

    # !(test (json-decode "42") 42)
    yield m.eval(expr(S["test"], expr(S["json-decode"], val("42")), 42))

    # !(test (json-decode "true") True)
    yield m.eval(expr(S["test"], expr(S["json-decode"], val("true")), val(value=True)))

    # !(test (json-decode "null") Null)
    yield m.eval(expr(S["test"], expr(S["json-decode"], val("null")), S["Null"]))

    # !(test (let $outer (json-decode "{\"c\":{\"d\":2}}")
    #          (let $inner (get-value $outer c) (get-value $inner d)))
    #        2)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["outer"],
                expr(S["json-decode"], val('{"c":{"d":2}}')),
                expr(
                    S["let"],
                    V["inner"],
                    expr(S["get-value"], V["outer"], S["c"]),
                    expr(S["get-value"], V["inner"], S["d"]),
                ),
            ),
            2,
        )
    )

    # !(test (json-decode (json-encode (1 2 3))) (1 2 3))
    yield m.eval(
        expr(
            S["test"], expr(S["json-decode"], expr(S["json-encode"], expr(1, 2, 3))), expr(1, 2, 3)
        )
    )

    # !(test (json-decode (json-encode "text")) "text")
    yield m.eval(
        expr(S["test"], expr(S["json-decode"], expr(S["json-encode"], val("text"))), val("text"))
    )

    # !(test (let $d (json-decode (json-encode (dict-space ((k 1))))) (get-value $d k))
    #        1)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["d"],
                expr(
                    S["json-decode"],
                    expr(S["json-encode"], expr(S["dict-space"], expr(expr(S["k"], 1)))),
                ),
                expr(S["get-value"], V["d"], S["k"]),
            ),
            1,
        )
    )

    # !(test (let $d (dict-space ((name "ann") (age 3))) (get-value $d name)) "ann")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["d"],
                expr(S["dict-space"], expr(expr(S["name"], val("ann")), expr(S["age"], 3))),
                expr(S["get-value"], V["d"], S["name"]),
            ),
            val("ann"),
        )
    )

    yield from ()
