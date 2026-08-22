"""The Python twin of examples/translation/translatorrule_refusal.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 4725


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (: strength (-> Atom Atom %Undefined%))
    m += expr(S[":"], S["strength"], expr(S["->"], S["Atom"], S["Atom"], S["%Undefined%"]))

    # (= (strength (dose $n) (unit mg))
    #    (if (> $n 1000)
    #        (refuse "a dose above 1000 is not a milligram strength")
    #        (noeval (mg $n))))
    m += expr(
        S["="],
        expr(S["strength"], expr(S["dose"], V["n"]), expr(S["unit"], S["mg"])),
        expr(
            S["if"],
            expr(S[">"], V["n"], 1000),
            expr(S["refuse"], val("a dose above 1000 is not a milligram strength")),
            expr(S["noeval"], expr(S["mg"], V["n"])),
        ),
    )

    # (= (strength (dose $n) (unit mg))
    #    (noeval (grams (/ $n 1000))))
    m += expr(
        S["="],
        expr(S["strength"], expr(S["dose"], V["n"]), expr(S["unit"], S["mg"])),
        expr(S["noeval"], expr(S["grams"], expr(S["/"], V["n"], 1000))),
    )

    # !(add-translator-rule! strength)
    yield m.eval(expr(S["add-translator-rule!"], S["strength"]))

    # !(test (strength (dose 250) (unit mg)) (mg 250))
    yield m.eval(
        expr(
            S["test"],
            expr(S["strength"], expr(S["dose"], 250), expr(S["unit"], S["mg"])),
            expr(S["mg"], 250),
        )
    )

    # !(test (strength (dose 5000) (unit mg)) (grams 5))
    yield m.eval(
        expr(
            S["test"],
            expr(S["strength"], expr(S["dose"], 5000), expr(S["unit"], S["mg"])),
            expr(S["grams"], 5),
        )
    )

    # !(test (match &petta (translator-rule-refusal strength $why) $why)
    #        "a dose above 1000 is not a milligram strength")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["translator-rule-refusal"], S["strength"], V["why"]),
                V["why"],
            ),
            val("a dose above 1000 is not a milligram strength"),
        )
    )

    yield from ()
