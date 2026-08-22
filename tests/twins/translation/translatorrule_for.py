"""The Python twin of examples/translation/translatorrule_for.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4111


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (: for (-> Atom Atom Atom %Undefined%))
    m += expr(S[":"], S["for"], expr(S["->"], S["Atom"], S["Atom"], S["Atom"], S["%Undefined%"]))

    # (= (for $var $collection $body)
    #    (noeval (let $var (superpose $collection)
    #                      $body)))
    m += expr(
        S["="],
        expr(S["for"], V["var"], V["collection"], V["body"]),
        expr(
            S["noeval"], expr(S["let"], V["var"], expr(S["superpose"], V["collection"]), V["body"])
        ),
    )

    # !(add-translator-rule! for)
    yield m.eval(expr(S["add-translator-rule!"], S["for"]))

    # (= (myfun $L)
    #    (for $x $L
    #         (if (== (% $x 2) 0)
    #             (even $x)
    #             (odd $x))))
    m += expr(
        S["="],
        expr(S["myfun"], V["L"]),
        expr(
            S["for"],
            V["x"],
            V["L"],
            expr(
                S["if"],
                expr(S["=="], expr(S["%"], V["x"], 2), 0),
                expr(S["even"], V["x"]),
                expr(S["odd"], V["x"]),
            ),
        ),
    )

    # !(test (collapse (myfun (3 4)))
    #        ((odd 3) (even 4)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["myfun"], expr(3, 4))),
            expr(expr(S["odd"], 3), expr(S["even"], 4)),
        )
    )

    yield from ()
