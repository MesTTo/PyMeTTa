"""The Python twin of examples/reasoning/scallop_readme.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 43276


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (sc-edge 0 1)
    m += expr(S["sc-edge"], 0, 1)

    # (sc-edge 1 2)
    m += expr(S["sc-edge"], 1, 2)

    # (= (sc-edge-to $a)
    #    (match (context-space) (sc-edge $a $b) $b))
    m += expr(
        S["="],
        expr(S["sc-edge-to"], V["a"]),
        expr(S["match"], expr(S["context-space"]), expr(S["sc-edge"], V["a"], V["b"]), V["b"]),
    )

    # (= (sc-path-to $a) (sc-edge-to $a))
    m += expr(S["="], expr(S["sc-path-to"], V["a"]), expr(S["sc-edge-to"], V["a"]))

    # (= (sc-path-to $a)
    #    (let $b (sc-edge-to $a) (sc-path-to $b)))
    m += expr(
        S["="],
        expr(S["sc-path-to"], V["a"]),
        expr(S["let"], V["b"], expr(S["sc-edge-to"], V["a"]), expr(S["sc-path-to"], V["b"])),
    )

    # (= (sc-paths)
    #    (collapse
    #       (let $a (match (context-space) (sc-edge $a $_) $a)
    #         (let $b (sc-path-to $a) ($a $b)))))
    m += expr(
        S["="],
        expr(S["sc-paths"]),
        expr(
            S["collapse"],
            expr(
                S["let"],
                V["a"],
                expr(
                    S["match"],
                    expr(S["context-space"]),
                    expr(S["sc-edge"], V["a"], V["_1646"]),
                    V["a"],
                ),
                expr(S["let"], V["b"], expr(S["sc-path-to"], V["a"]), expr(V["a"], V["b"])),
            ),
        ),
    )

    # !(test (sc-paths) ((0 1) (0 2) (1 2)))
    yield m.eval(expr(S["test"], expr(S["sc-paths"]), expr(expr(0, 1), expr(0, 2), expr(1, 2))))

    # (sc-number 0)
    m += expr(S["sc-number"], 0)

    # (sc-number 1)
    m += expr(S["sc-number"], 1)

    # (sc-number 2)
    m += expr(S["sc-number"], 2)

    # (sc-number 3)
    m += expr(S["sc-number"], 3)

    # (sc-number 4)
    m += expr(S["sc-number"], 4)

    # (sc-number 5)
    m += expr(S["sc-number"], 5)

    # (sc-number 6)
    m += expr(S["sc-number"], 6)

    # (sc-number 7)
    m += expr(S["sc-number"], 7)

    # (sc-number 8)
    m += expr(S["sc-number"], 8)

    # (sc-number 9)
    m += expr(S["sc-number"], 9)

    # (sc-number 10)
    m += expr(S["sc-number"], 10)

    # (= (sc-odd? 1) True)
    m += expr(S["="], expr(S["sc-odd?"], 1), val(value=True))

    # (= (sc-odd? $x)
    #    (let $n (match (context-space) (sc-number $x) $x)
    #      (sc-odd? (- $n 2))))
    m += expr(
        S["="],
        expr(S["sc-odd?"], V["x"]),
        expr(
            S["let"],
            V["n"],
            expr(S["match"], expr(S["context-space"]), expr(S["sc-number"], V["x"]), V["x"]),
            expr(S["sc-odd?"], expr(S["-"], V["n"], 2)),
        ),
    )

    # (= (sc-evens)
    #    (collapse
    #       (let $y (match (context-space) (sc-number $y) $y)
    #         (let True (not-provable (sc-odd? $y)) $y))))
    m += expr(
        S["="],
        expr(S["sc-evens"]),
        expr(
            S["collapse"],
            expr(
                S["let"],
                V["y"],
                expr(S["match"], expr(S["context-space"]), expr(S["sc-number"], V["y"]), V["y"]),
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["sc-odd?"], V["y"])),
                    V["y"],
                ),
            ),
        ),
    )

    # !(test (sc-evens) (0 2 4 6 8 10))
    yield m.eval(expr(S["test"], expr(S["sc-evens"]), expr(0, 2, 4, 6, 8, 10)))

    # (sc-object-color 0 "blue")
    m += expr(S["sc-object-color"], 0, val("blue"))

    # (sc-object-color 1 "green")
    m += expr(S["sc-object-color"], 1, val("green"))

    # (sc-object-color 2 "blue")
    m += expr(S["sc-object-color"], 2, val("blue"))

    # (= (sc-one-color $c)
    #    (let $o (match (context-space) (sc-object-color $o $c) $o) 1))
    m += expr(
        S["="],
        expr(S["sc-one-color"], V["c"]),
        expr(
            S["let"],
            V["o"],
            expr(
                S["match"],
                expr(S["context-space"]),
                expr(S["sc-object-color"], V["o"], V["c"]),
                V["o"],
            ),
            1,
        ),
    )

    # (= (sc-color-count $c) (foldall + (sc-one-color $c) 0))
    m += expr(
        S["="],
        expr(S["sc-color-count"], V["c"]),
        expr(S["foldall"], S["+"], expr(S["sc-one-color"], V["c"]), 0),
    )

    # (= (sc-color-counts)
    #    (collapse
    #       (let $c (superpose ("blue" "green"))
    #         ($c (sc-color-count $c)))))
    m += expr(
        S["="],
        expr(S["sc-color-counts"]),
        expr(
            S["collapse"],
            expr(
                S["let"],
                V["c"],
                expr(S["superpose"], expr(val("blue"), val("green"))),
                expr(V["c"], expr(S["sc-color-count"], V["c"])),
            ),
        ),
    )

    # !(test (sc-color-counts) (("blue" 2) ("green" 1)))
    yield m.eval(
        expr(
            S["test"], expr(S["sc-color-counts"]), expr(expr(val("blue"), 2), expr(val("green"), 1))
        )
    )

    # (sc-class-student-grade 0 "tom" 50)
    m += expr(S["sc-class-student-grade"], 0, val("tom"), 50)

    # (sc-class-student-grade 0 "jerry" 70)
    m += expr(S["sc-class-student-grade"], 0, val("jerry"), 70)

    # (sc-class-student-grade 0 "alice" 60)
    m += expr(S["sc-class-student-grade"], 0, val("alice"), 60)

    # (sc-class-student-grade 1 "bob" 80)
    m += expr(S["sc-class-student-grade"], 1, val("bob"), 80)

    # (sc-class-student-grade 1 "sherry" 90)
    m += expr(S["sc-class-student-grade"], 1, val("sherry"), 90)

    # (sc-class-student-grade 1 "frank" 30)
    m += expr(S["sc-class-student-grade"], 1, val("frank"), 30)

    # (= (sc-pick-max $a $b) (if (> $a $b) $a $b))
    m += expr(
        S["="],
        expr(S["sc-pick-max"], V["a"], V["b"]),
        expr(S["if"], expr(S[">"], V["a"], V["b"]), V["a"], V["b"]),
    )

    # (= (sc-class-max $c)
    #    (foldall sc-pick-max
    #             (match (context-space)
    #                    (sc-class-student-grade $c $_ $g)
    #                    $g)
    #             -1))
    m += expr(
        S["="],
        expr(S["sc-class-max"], V["c"]),
        expr(
            S["foldall"],
            S["sc-pick-max"],
            expr(
                S["match"],
                expr(S["context-space"]),
                expr(S["sc-class-student-grade"], V["c"], V["_2064"], V["g"]),
                V["g"],
            ),
            -1,
        ),
    )

    # (= (sc-class-top)
    #    (collapse
    #       (let $c (superpose (0 1))
    #         (let $g (sc-class-max $c)
    #           (let $s
    #             (match (context-space)
    #                    (sc-class-student-grade $c $s $g)
    #                    $s)
    #             ($c $s))))))
    m += expr(
        S["="],
        expr(S["sc-class-top"]),
        expr(
            S["collapse"],
            expr(
                S["let"],
                V["c"],
                expr(S["superpose"], expr(0, 1)),
                expr(
                    S["let"],
                    V["g"],
                    expr(S["sc-class-max"], V["c"]),
                    expr(
                        S["let"],
                        V["s"],
                        expr(
                            S["match"],
                            expr(S["context-space"]),
                            expr(S["sc-class-student-grade"], V["c"], V["s"], V["g"]),
                            V["s"],
                        ),
                        expr(V["c"], V["s"]),
                    ),
                ),
            ),
        ),
    )

    # !(test (sc-class-top) ((0 "jerry") (1 "sherry")))
    yield m.eval(
        expr(
            S["test"], expr(S["sc-class-top"]), expr(expr(0, val("jerry")), expr(1, val("sherry")))
        )
    )

    # (sc-is-a giraffe mammal)
    m += expr(S["sc-is-a"], S["giraffe"], S["mammal"])

    # (sc-is-a tiger mammal)
    m += expr(S["sc-is-a"], S["tiger"], S["mammal"])

    # (sc-is-a mammal animal)
    m += expr(S["sc-is-a"], S["mammal"], S["animal"])

    # (sc-name 1 giraffe)
    m += expr(S["sc-name"], 1, S["giraffe"])

    # (sc-name 1 tiger)
    m += expr(S["sc-name"], 1, S["tiger"])

    # (sc-name 2 giraffe)
    m += expr(S["sc-name"], 2, S["giraffe"])

    # (sc-name 2 tiger)
    m += expr(S["sc-name"], 2, S["tiger"])

    # (= (sc-parent-kind $x)
    #    (match (context-space) (sc-is-a $x $y) $y))
    m += expr(
        S["="],
        expr(S["sc-parent-kind"], V["x"]),
        expr(S["match"], expr(S["context-space"]), expr(S["sc-is-a"], V["x"], V["y"]), V["y"]),
    )

    # (= (sc-ancestor-kind $x) (sc-parent-kind $x))
    m += expr(S["="], expr(S["sc-ancestor-kind"], V["x"]), expr(S["sc-parent-kind"], V["x"]))

    # (= (sc-ancestor-kind $x)
    #    (let $y (sc-parent-kind $x) (sc-ancestor-kind $y)))
    m += expr(
        S["="],
        expr(S["sc-ancestor-kind"], V["x"]),
        expr(
            S["let"], V["y"], expr(S["sc-parent-kind"], V["x"]), expr(S["sc-ancestor-kind"], V["y"])
        ),
    )

    # (= (sc-animal-object)
    #    (let ($o $kind)
    #      (match (context-space) (sc-name $o $kind) ($o $kind))
    #      (let $ancestor (sc-ancestor-kind $kind)
    #        (if (== $ancestor animal) $o (empty)))))
    m += expr(
        S["="],
        expr(S["sc-animal-object"]),
        expr(
            S["let"],
            expr(V["o"], V["kind"]),
            expr(
                S["match"],
                expr(S["context-space"]),
                expr(S["sc-name"], V["o"], V["kind"]),
                expr(V["o"], V["kind"]),
            ),
            expr(
                S["let"],
                V["ancestor"],
                expr(S["sc-ancestor-kind"], V["kind"]),
                expr(S["if"], expr(S["=="], V["ancestor"], S["animal"]), V["o"], expr(S["empty"])),
            ),
        ),
    )

    # (= (sc-one-animal)
    #    (let $o (unique (sc-animal-object)) 1))
    m += expr(
        S["="],
        expr(S["sc-one-animal"]),
        expr(S["let"], V["o"], expr(S["unique"], expr(S["sc-animal-object"])), 1),
    )

    # (= (sc-animal-count) (foldall + (sc-one-animal) 0))
    m += expr(
        S["="], expr(S["sc-animal-count"]), expr(S["foldall"], S["+"], expr(S["sc-one-animal"]), 0)
    )

    # !(test (sc-animal-count) 2)
    yield m.eval(expr(S["test"], expr(S["sc-animal-count"]), 2))

    yield from ()
