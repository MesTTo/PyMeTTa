"""The Python twin of examples/translation/translatorrule_guard.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 17296


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &petta (dispatch-policy add-pairs NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["add-pairs"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # (: add-pairs (-> Atom Atom %Undefined%))
    m += expr(S[":"], S["add-pairs"], expr(S["->"], S["Atom"], S["Atom"], S["%Undefined%"]))

    # (= (add-pairs (pair $a $b) (pair $c $d))
    #    (noeval (pair (+ $a $c) (+ $b $d))))
    m += expr(
        S["="],
        expr(S["add-pairs"], expr(S["pair"], V["a"], V["b"]), expr(S["pair"], V["c"], V["d"])),
        expr(
            S["noeval"], expr(S["pair"], expr(S["+"], V["a"], V["c"]), expr(S["+"], V["b"], V["d"]))
        ),
    )

    # !(add-translator-rule! add-pairs)
    yield m.eval(expr(S["add-translator-rule!"], S["add-pairs"]))

    # !(test (add-pairs (pair 1 2) (pair 10 20)) (pair 11 22))
    yield m.eval(
        expr(
            S["test"],
            expr(S["add-pairs"], expr(S["pair"], 1, 2), expr(S["pair"], 10, 20)),
            expr(S["pair"], 11, 22),
        )
    )

    # !(test (collapse (add-pairs 1 2)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["add-pairs"], 1, 2)), expr()))

    # (= (holds-a-miss) (add-pairs 1 2))
    m += expr(S["="], expr(S["holds-a-miss"]), expr(S["add-pairs"], 1, 2))

    # !(test (collapse (holds-a-miss)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["holds-a-miss"])), expr()))

    # (: hold-pairs (-> Atom Atom %Undefined%))
    m += expr(S[":"], S["hold-pairs"], expr(S["->"], S["Atom"], S["Atom"], S["%Undefined%"]))

    # (= (hold-pairs (pair $a $b) (pair $c $d))
    #    (noeval (pair (+ $a $c) (+ $b $d))))
    m += expr(
        S["="],
        expr(S["hold-pairs"], expr(S["pair"], V["a"], V["b"]), expr(S["pair"], V["c"], V["d"])),
        expr(
            S["noeval"], expr(S["pair"], expr(S["+"], V["a"], V["c"]), expr(S["+"], V["b"], V["d"]))
        ),
    )

    # (= (hold-pairs $a $b) (noeval (noeval (hold-pairs $a $b))))
    m += expr(
        S["="],
        expr(S["hold-pairs"], V["a"], V["b"]),
        expr(S["noeval"], expr(S["noeval"], expr(S["hold-pairs"], V["a"], V["b"]))),
    )

    # !(add-translator-rule! hold-pairs)
    yield m.eval(expr(S["add-translator-rule!"], S["hold-pairs"]))

    # !(test (hold-pairs (pair 1 2) (pair 10 20)) (pair 11 22))
    yield m.eval(
        expr(
            S["test"],
            expr(S["hold-pairs"], expr(S["pair"], 1, 2), expr(S["pair"], 10, 20)),
            expr(S["pair"], 11, 22),
        )
    )

    # !(test (hold-pairs 1 2) (hold-pairs 1 2))
    yield m.eval(expr(S["test"], expr(S["hold-pairs"], 1, 2), expr(S["hold-pairs"], 1, 2)))

    # !(test (collapse (union (superpose (1 2)) (superpose (2 3)))) (1 2 2 3))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["union"], expr(S["superpose"], expr(1, 2)), expr(S["superpose"], expr(2, 3))
                ),
            ),
            expr(1, 2, 2, 3),
        )
    )

    # !(test (union foo bar) (union foo bar))
    yield m.eval(
        expr(S["test"], expr(S["union"], S["foo"], S["bar"]), expr(S["union"], S["foo"], S["bar"]))
    )

    # (: pick (-> Atom %Undefined%))
    m += expr(S[":"], S["pick"], expr(S["->"], S["Atom"], S["%Undefined%"]))

    # (= (pick a) (empty))
    m += expr(S["="], expr(S["pick"], S["a"]), expr(S["empty"]))

    # (= (pick $x) (noeval (picked $x)))
    m += expr(S["="], expr(S["pick"], V["x"]), expr(S["noeval"], expr(S["picked"], V["x"])))

    # !(add-translator-rule! pick)
    yield m.eval(expr(S["add-translator-rule!"], S["pick"]))

    # !(test (pick a) (picked a))
    yield m.eval(expr(S["test"], expr(S["pick"], S["a"]), expr(S["picked"], S["a"])))

    # !(test (pick b) (picked b))
    yield m.eval(expr(S["test"], expr(S["pick"], S["b"]), expr(S["picked"], S["b"])))

    # (: only-a (-> Atom %Undefined%))
    m += expr(S[":"], S["only-a"], expr(S["->"], S["Atom"], S["%Undefined%"]))

    # (= (only-a a) (empty))
    m += expr(S["="], expr(S["only-a"], S["a"]), expr(S["empty"]))

    # !(add-translator-rule! only-a)
    yield m.eval(expr(S["add-translator-rule!"], S["only-a"]))

    # !(test (collapse (only-a a)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["only-a"], S["a"])), expr()))

    # (= (both-ways $x) bw-one)
    m += expr(S["="], expr(S["both-ways"], V["x"]), S["bw-one"])

    # (= (both-ways $x) bw-two)
    m += expr(S["="], expr(S["both-ways"], V["x"]), S["bw-two"])

    # !(test (collapse (both-ways q)) (bw-one bw-two))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["both-ways"], S["q"])),
            expr(S["bw-one"], S["bw-two"]),
        )
    )

    yield from ()
