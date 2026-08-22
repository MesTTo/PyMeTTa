"""The Python twin of examples/libraries/thread_linda.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 157993


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_thread))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_thread"])))

    # (= (inc $x) (+ $x 1))
    m += expr(S["="], expr(S["inc"], V["x"]), expr(S["+"], V["x"], 1))

    # !(add-atom &jobs (job 7))
    yield m.eval(expr(S["add-atom"], S["&jobs"], expr(S["job"], 7)))

    # !(test (peek-atom &jobs (job $n)) (job 7))
    yield m.eval(
        expr(S["test"], expr(S["peek-atom"], S["&jobs"], expr(S["job"], V["n"])), expr(S["job"], 7))
    )

    # !(test (peek-atom &jobs (job $n)) (job 7))
    yield m.eval(
        expr(S["test"], expr(S["peek-atom"], S["&jobs"], expr(S["job"], V["n"])), expr(S["job"], 7))
    )

    # !(test (await-atom &jobs (job $n)) (job 7))
    yield m.eval(
        expr(
            S["test"], expr(S["await-atom"], S["&jobs"], expr(S["job"], V["n"])), expr(S["job"], 7)
        )
    )

    # !(test (take-atom &jobs (job $n)) (job 7))
    yield m.eval(
        expr(S["test"], expr(S["take-atom"], S["&jobs"], expr(S["job"], V["n"])), expr(S["job"], 7))
    )

    # !(test (collapse (take-atom &jobs (job $n) 0.05)) ())
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["take-atom"], S["&jobs"], expr(S["job"], V["n"]), 0.05)),
            expr(),
        )
    )

    # !(test (collapse (get-atoms &jobs)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["get-atoms"], S["&jobs"])), expr()))

    # !(add-atom &work (job 1))
    yield m.eval(expr(S["add-atom"], S["&work"], expr(S["job"], 1)))

    # !(add-atom &work (job 2))
    yield m.eval(expr(S["add-atom"], S["&work"], expr(S["job"], 2)))

    # !(test (let $x (take-atom &work (job $a) 1)
    #          (let $y (take-atom &work (job $b) 1)
    #            (+ $a $b)))
    #        3)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["x"],
                expr(S["take-atom"], S["&work"], expr(S["job"], V["a"]), 1),
                expr(
                    S["let"],
                    V["y"],
                    expr(S["take-atom"], S["&work"], expr(S["job"], V["b"]), 1),
                    expr(S["+"], V["a"], V["b"]),
                ),
            ),
            3,
        )
    )

    # !(test (collapse (get-atoms &work)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["get-atoms"], S["&work"])), expr()))

    # !(test (let $w (spawn (add-atom &inbox (msg hello)))
    #          (let $seen (take-atom &inbox (msg $what) 10)
    #            (let $_ (await $w) $seen)))
    #        (msg hello))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["w"],
                expr(S["spawn"], expr(S["add-atom"], S["&inbox"], expr(S["msg"], S["hello"]))),
                expr(
                    S["let"],
                    V["seen"],
                    expr(S["take-atom"], S["&inbox"], expr(S["msg"], V["what"]), 10),
                    expr(S["let"], V["_2882"], expr(S["await"], V["w"]), V["seen"]),
                ),
            ),
            expr(S["msg"], S["hello"]),
        )
    )

    # !(test (collapse (get-atoms &inbox)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["get-atoms"], S["&inbox"])), expr()))

    yield from ()
