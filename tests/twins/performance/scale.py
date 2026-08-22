"""The Python twin of examples/performance/scale.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 24314635


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (addK $K)
    #    (if (== $K 0)
    #        done
    #        (let* (($K10 (% $K 10))
    #               ($t (add-atom &self (r $K $K10))))
    #               (addK (- $K 1)))))
    m += expr(
        S["="],
        expr(S["addK"], V["K"]),
        expr(
            S["if"],
            expr(S["=="], V["K"], 0),
            S["done"],
            expr(
                S["let*"],
                expr(
                    expr(V["K10"], expr(S["%"], V["K"], 10)),
                    expr(V["t"], expr(S["add-atom"], S["&self"], expr(S["r"], V["K"], V["K10"]))),
                ),
                expr(S["addK"], expr(S["-"], V["K"], 1)),
            ),
        ),
    )

    # (= (q-all)
    #    (collapse (match &self (r $x $y) (r $x $y))))
    m += expr(
        S["="],
        expr(S["q-all"]),
        expr(
            S["collapse"],
            expr(
                S["match"], S["&self"], expr(S["r"], V["x"], V["y"]), expr(S["r"], V["x"], V["y"])
            ),
        ),
    )

    # (= (q-first $a)
    #    (collapse (match &self (r $a $y) (r $a $y))))
    m += expr(
        S["="],
        expr(S["q-first"], V["a"]),
        expr(
            S["collapse"],
            expr(
                S["match"], S["&self"], expr(S["r"], V["a"], V["y"]), expr(S["r"], V["a"], V["y"])
            ),
        ),
    )

    # (= (q-second $b)
    #    (collapse (match &self (r $x $b) (r $x $b))))
    m += expr(
        S["="],
        expr(S["q-second"], V["b"]),
        expr(
            S["collapse"],
            expr(
                S["match"], S["&self"], expr(S["r"], V["x"], V["b"]), expr(S["r"], V["x"], V["b"])
            ),
        ),
    )

    # (= (q-both $a $b)
    #    (collapse (match &self (r $a $b) (r $a $b))))
    m += expr(
        S["="],
        expr(S["q-both"], V["a"], V["b"]),
        expr(
            S["collapse"],
            expr(
                S["match"], S["&self"], expr(S["r"], V["a"], V["b"]), expr(S["r"], V["a"], V["b"])
            ),
        ),
    )

    # (= (q-rel $r)
    #    (collapse (match &self ($r 643 3) ($r 643 3))))
    m += expr(
        S["="],
        expr(S["q-rel"], V["r"]),
        expr(
            S["collapse"], expr(S["match"], S["&self"], expr(V["r"], 643, 3), expr(V["r"], 643, 3))
        ),
    )

    # (= (indexing-demo $K)
    #    (let* (($temp (addK $K))
    #           ($all (q-all))
    #           ($first (q-first 7))
    #           ($second (q-second 3))
    #           ($rel (q-rel r))
    #           ($both (q-both 42 2)))
    #          (all: (length $all) first: (length $first) second: (length $second) rel: (length $rel) both: (length $both))))
    m += expr(
        S["="],
        expr(S["indexing-demo"], V["K"]),
        expr(
            S["let*"],
            expr(
                expr(V["temp"], expr(S["addK"], V["K"])),
                expr(V["all"], expr(S["q-all"])),
                expr(V["first"], expr(S["q-first"], 7)),
                expr(V["second"], expr(S["q-second"], 3)),
                expr(V["rel"], expr(S["q-rel"], S["r"])),
                expr(V["both"], expr(S["q-both"], 42, 2)),
            ),
            expr(
                S["all:"],
                expr(S["length"], V["all"]),
                S["first:"],
                expr(S["length"], V["first"]),
                S["second:"],
                expr(S["length"], V["second"]),
                S["rel:"],
                expr(S["length"], V["rel"]),
                S["both:"],
                expr(S["length"], V["both"]),
            ),
        ),
    )

    # !(test (indexing-demo 1000000)
    #        (all: 1000000 first: 1 second: 100000 rel: 1 both: 1))
    yield m.eval(
        expr(
            S["test"],
            expr(S["indexing-demo"], 1000000),
            expr(
                S["all:"],
                1000000,
                S["first:"],
                1,
                S["second:"],
                100000,
                S["rel:"],
                1,
                S["both:"],
                1,
            ),
        )
    )

    yield from ()
