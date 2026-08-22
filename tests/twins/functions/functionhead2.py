"""The Python twin of examples/functions/functionhead2.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 11639


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &petta (dispatch-policy small NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["small"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # (= (living garfield) True)
    m += expr(S["="], expr(S["living"], S["garfield"]), val(value=True))

    # (= (being garfield) True)
    m += expr(S["="], expr(S["being"], S["garfield"]), val(value=True))

    # (= (small garfield) True)
    m += expr(S["="], expr(S["small"], S["garfield"]), val(value=True))

    # (= (living snoopy) True)
    m += expr(S["="], expr(S["living"], S["snoopy"]), val(value=True))

    # (= (being snoopy) True)
    m += expr(S["="], expr(S["being"], S["snoopy"]), val(value=True))

    # (= (being roomba) True)
    m += expr(S["="], expr(S["being"], S["roomba"]), val(value=True))

    # (= (small roomba) True)
    m += expr(S["="], expr(S["small"], S["roomba"]), val(value=True))

    # (= (living cat42) True)
    m += expr(S["="], expr(S["living"], S["cat42"]), val(value=True))

    # (= (being cat42) True)
    m += expr(S["="], expr(S["being"], S["cat42"]), val(value=True))

    # (= (small cat42) True)
    m += expr(S["="], expr(S["small"], S["cat42"]), val(value=True))

    # (= (only $C $X)
    #    (let $constraint $C $X))
    m += expr(
        S["="], expr(S["only"], V["C"], V["X"]), expr(S["let"], V["constraint"], V["C"], V["X"])
    )

    # (= (animal $X)
    #    (only ((living $X) (being $X)) $X))
    m += expr(
        S["="],
        expr(S["animal"], V["X"]),
        expr(S["only"], expr(expr(S["living"], V["X"]), expr(S["being"], V["X"])), V["X"]),
    )

    # (= (cat $A)
    #    (let $A (animal $X)
    #         (only (small $X) $X)))
    m += expr(
        S["="],
        expr(S["cat"], V["A"]),
        expr(
            S["let"],
            V["A"],
            expr(S["animal"], V["X"]),
            expr(S["only"], expr(S["small"], V["X"]), V["X"]),
        ),
    )

    # !(test (msort (collapse (cat $X)))
    #        (cat42 garfield))
    yield m.eval(
        expr(
            S["test"],
            expr(S["msort"], expr(S["collapse"], expr(S["cat"], V["X"]))),
            expr(S["cat42"], S["garfield"]),
        )
    )

    yield from ()
