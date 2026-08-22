"""The Python twin of examples/translation/myinterpreter.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 5361


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (: myinterpreter (-> Atom %Undefined%))
    m += expr(S[":"], S["myinterpreter"], expr(S["->"], S["Atom"], S["%Undefined%"]))

    # (= (myinterpreter $code)
    #    (let $temp (println! ("Runtime-interpreting code" $code))
    #         (eval $code)))
    m += expr(
        S["="],
        expr(S["myinterpreter"], V["code"]),
        expr(
            S["let"],
            V["temp"],
            expr(S["println!"], expr(val("Runtime-interpreting code"), V["code"])),
            expr(S["eval"], V["code"]),
        ),
    )

    # (= (w) 42)
    m += expr(S["="], expr(S["w"]), 42)

    # (= (v) 43)
    m += expr(S["="], expr(S["v"]), 43)

    # !(test (myinterpreter (if (== 1 1) (w) (v))) 42)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["myinterpreter"], expr(S["if"], expr(S["=="], 1, 1), expr(S["w"]), expr(S["v"]))
            ),
            42,
        )
    )

    # !(test (myinterpreter (if (== 1 2) (w) (v))) 43)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["myinterpreter"], expr(S["if"], expr(S["=="], 1, 2), expr(S["w"]), expr(S["v"]))
            ),
            43,
        )
    )

    yield from ()
