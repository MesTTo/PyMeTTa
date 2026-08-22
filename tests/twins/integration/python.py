"""The Python twin of examples/integration/python.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 7591


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (make-object) (py-call (types.SimpleNamespace)))
    m += expr(S["="], expr(S["make-object"]), expr(S["py-call"], expr(S["types.SimpleNamespace"])))

    # (= (get-attribute $obj $name) (py-call (getattr $obj $name)))
    m += expr(
        S["="],
        expr(S["get-attribute"], V["obj"], V["name"]),
        expr(S["py-call"], expr(S["getattr"], V["obj"], V["name"])),
    )

    # (= (set-attribute $obj $name $value) (py-call (setattr $obj $name $value)))
    m += expr(
        S["="],
        expr(S["set-attribute"], V["obj"], V["name"], V["value"]),
        expr(S["py-call"], expr(S["setattr"], V["obj"], V["name"], V["value"])),
    )

    # (= (import $name) (py-call (importlib.import_module $name)))
    m += expr(
        S["="],
        expr(S["import"], V["name"]),
        expr(S["py-call"], expr(S["importlib.import_module"], V["name"])),
    )

    # (= (math.pi) (get-attribute (import math) pi))
    m += expr(
        S["="], expr(S["math.pi"]), expr(S["get-attribute"], expr(S["import"], S["math"]), S["pi"])
    )

    # !(test (let* (($obj (make-object))
    #               ($temp (set-attribute $obj foo (math.pi))))
    #              (get-attribute $obj foo))
    #        3.141592653589793)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let*"],
                expr(
                    expr(V["obj"], expr(S["make-object"])),
                    expr(
                        V["temp"], expr(S["set-attribute"], V["obj"], S["foo"], expr(S["math.pi"]))
                    ),
                ),
                expr(S["get-attribute"], V["obj"], S["foo"]),
            ),
            3.141592653589793,
        )
    )

    # !(test (py-call (.upper "abc")) ABC)
    yield m.eval(expr(S["test"], expr(S["py-call"], expr(S[".upper"], val("abc"))), S["ABC"]))

    # !(test (py-call (.__add__ 5 3)) 8)
    yield m.eval(expr(S["test"], expr(S["py-call"], expr(S[".__add__"], 5, 3)), 8))

    yield from ()
