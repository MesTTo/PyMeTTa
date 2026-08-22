"""The Python twin of examples/libraries/derived_forms.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 15606


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (once (superpose (1 2 3))) 1)
    yield m.eval(expr(S["test"], expr(S["once"], expr(S["superpose"], expr(1, 2, 3))), 1))

    # !(import! &self (library lib_derived))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_derived"])))

    # !(test (once (superpose (1 2 3))) 1)
    yield m.eval(expr(S["test"], expr(S["once"], expr(S["superpose"], expr(1, 2, 3))), 1))

    # !(test (collapse (once (superpose (1 2 3)))) (1))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["once"], expr(S["superpose"], expr(1, 2, 3)))),
            expr(1),
        )
    )

    # !(test (collapse (once (empty))) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["once"], expr(S["empty"]))), expr()))

    # !(bind! &seen (new-space))
    yield m.eval(expr(S["bind!"], S["&seen"], expr(S["new-space"])))

    # (= (noisy $x) (let $_ (add-atom &seen (saw $x)) $x))
    m += expr(
        S["="],
        expr(S["noisy"], V["x"]),
        expr(S["let"], V["_1210"], expr(S["add-atom"], S["&seen"], expr(S["saw"], V["x"])), V["x"]),
    )

    # !(test (once (superpose ((noisy a) (noisy b)))) a)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["once"],
                expr(S["superpose"], expr(expr(S["noisy"], S["a"]), expr(S["noisy"], S["b"]))),
            ),
            S["a"],
        )
    )

    # !(test (collapse (get-atoms &seen)) ((saw a)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["get-atoms"], S["&seen"])),
            expr(expr(S["saw"], S["a"])),
        )
    )

    # !(remove-translator-rule! once)
    yield m.eval(expr(S["remove-translator-rule!"], S["once"]))

    # !(test (once (superpose (1 2 3))) 1)
    yield m.eval(expr(S["test"], expr(S["once"], expr(S["superpose"], expr(1, 2, 3))), 1))

    yield from ()
