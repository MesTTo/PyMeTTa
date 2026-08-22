"""The Python twin of examples/reasoning/constructive_negation.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 95562


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &petta (dispatch-policy penguin NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["penguin"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy bird NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["bird"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy student NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["student"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy married NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["married"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy invalid NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["invalid"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy over-65 NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["over-65"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy paid-up NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["paid-up"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy marks NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["marks"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy edge NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["edge"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # (= (bird tweety) True)
    m += expr(S["="], expr(S["bird"], S["tweety"]), val(value=True))

    # (= (bird polly) True)
    m += expr(S["="], expr(S["bird"], S["polly"]), val(value=True))

    # (= (penguin polly) True)
    m += expr(S["="], expr(S["penguin"], S["polly"]), val(value=True))

    # !(test (collapse (not (penguin tweety))) ())
    yield m.eval(
        expr(
            S["test"], expr(S["collapse"], expr(S["not"], expr(S["penguin"], S["tweety"]))), expr()
        )
    )

    # !(test (not-provable (penguin tweety)) True)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["penguin"], S["tweety"])), val(value=True))
    )

    # !(test (not-provable (penguin polly)) False)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["penguin"], S["polly"])), val(value=False))
    )

    # (= (flies $x) (and (bird $x) (not-provable (penguin $x))))
    m += expr(
        S["="],
        expr(S["flies"], V["x"]),
        expr(
            S["and"], expr(S["bird"], V["x"]), expr(S["not-provable"], expr(S["penguin"], V["x"]))
        ),
    )

    # !(test (collapse (let True (flies $x) $x)) (tweety))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["let"], val(value=True), expr(S["flies"], V["x"]), V["x"])),
            expr(S["tweety"]),
        )
    )

    # (= (student bill) True)
    m += expr(S["="], expr(S["student"], S["bill"]), val(value=True))

    # (= (married joe) True)
    m += expr(S["="], expr(S["married"], S["joe"]), val(value=True))

    # (= (unmarried-student $x)
    #    (and (not-provable (married $x)) (student $x)))
    m += expr(
        S["="],
        expr(S["unmarried-student"], V["x"]),
        expr(
            S["and"],
            expr(S["not-provable"], expr(S["married"], V["x"])),
            expr(S["student"], V["x"]),
        ),
    )

    # !(test (collapse (let True (unmarried-student $x) $x)) (bill))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["let"], val(value=True), expr(S["unmarried-student"], V["x"]), V["x"]),
            ),
            expr(S["bill"]),
        )
    )

    # (= (two-but-not-one $x)
    #    (and (not-provable (== $x 1)) (let $x 2 True)))
    m += expr(
        S["="],
        expr(S["two-but-not-one"], V["x"]),
        expr(
            S["and"],
            expr(S["not-provable"], expr(S["=="], V["x"], 1)),
            expr(S["let"], V["x"], 2, val(value=True)),
        ),
    )

    # !(test (collapse (let True (two-but-not-one $x) $x)) (2))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["let"], val(value=True), expr(S["two-but-not-one"], V["x"]), V["x"]),
            ),
            expr(2),
        )
    )

    # (= (invalid mc-tavish) True)
    m += expr(S["="], expr(S["invalid"], S["mc-tavish"]), val(value=True))

    # (= (over-65 mc-tavish) True)
    m += expr(S["="], expr(S["over-65"], S["mc-tavish"]), val(value=True))

    # (= (over-65 mc-donald) True)
    m += expr(S["="], expr(S["over-65"], S["mc-donald"]), val(value=True))

    # (= (over-65 mc-duff) True)
    m += expr(S["="], expr(S["over-65"], S["mc-duff"]), val(value=True))

    # (= (paid-up mc-tavish) True)
    m += expr(S["="], expr(S["paid-up"], S["mc-tavish"]), val(value=True))

    # (= (paid-up mc-donald) True)
    m += expr(S["="], expr(S["paid-up"], S["mc-donald"]), val(value=True))

    # (= (pension $p invalid-pension) (invalid $p))
    m += expr(S["="], expr(S["pension"], V["p"], S["invalid-pension"]), expr(S["invalid"], V["p"]))

    # (= (pension $p old-age-pension) (and (over-65 $p) (paid-up $p)))
    m += expr(
        S["="],
        expr(S["pension"], V["p"], S["old-age-pension"]),
        expr(S["and"], expr(S["over-65"], V["p"]), expr(S["paid-up"], V["p"])),
    )

    # (= (pension $p supplementary-benefit) (over-65 $p))
    m += expr(
        S["="], expr(S["pension"], V["p"], S["supplementary-benefit"]), expr(S["over-65"], V["p"])
    )

    # (= (entitlement $p $what) (pension $p $what))
    m += expr(
        S["="], expr(S["entitlement"], V["p"], V["what"]), expr(S["pension"], V["p"], V["what"])
    )

    # (= (entitlement $p nothing) (not-provable (pension $p $any)))
    m += expr(
        S["="],
        expr(S["entitlement"], V["p"], S["nothing"]),
        expr(S["not-provable"], expr(S["pension"], V["p"], V["any"])),
    )

    # !(test (collapse (let True (entitlement mc-tavish $w) $w))
    #        (invalid-pension old-age-pension supplementary-benefit))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["entitlement"], S["mc-tavish"], V["w"]),
                    V["w"],
                ),
            ),
            expr(S["invalid-pension"], S["old-age-pension"], S["supplementary-benefit"]),
        )
    )

    # !(test (collapse (let True (entitlement mc-duff $w) $w))
    #        (supplementary-benefit))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"], val(value=True), expr(S["entitlement"], S["mc-duff"], V["w"]), V["w"]
                ),
            ),
            expr(S["supplementary-benefit"]),
        )
    )

    # !(test (collapse (let True (entitlement someone-else $w) $w)) (nothing))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["entitlement"], S["someone-else"], V["w"]),
                    V["w"],
                ),
            ),
            expr(S["nothing"]),
        )
    )

    # (= (edge a b) True)
    m += expr(S["="], expr(S["edge"], S["a"], S["b"]), val(value=True))

    # (= (edge b c) True)
    m += expr(S["="], expr(S["edge"], S["b"], S["c"]), val(value=True))

    # (= (has-no-outgoing $x) (not-provable (edge $x $y)))
    m += expr(
        S["="],
        expr(S["has-no-outgoing"], V["x"]),
        expr(S["not-provable"], expr(S["edge"], V["x"], V["y"])),
    )

    # !(test (has-no-outgoing c) True)
    yield m.eval(expr(S["test"], expr(S["has-no-outgoing"], S["c"]), val(value=True)))

    # !(test (has-no-outgoing a) False)
    yield m.eval(expr(S["test"], expr(S["has-no-outgoing"], S["a"]), val(value=False)))

    # !(test (collapse (let True (has-no-outgoing $x) (let $x c $x))) (c))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["has-no-outgoing"], V["x"]),
                    expr(S["let"], V["x"], S["c"], V["x"]),
                ),
            ),
            expr(S["c"]),
        )
    )

    # !(test (collapse (let True (has-no-outgoing $x) (let $x zzz $x))) (zzz))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["has-no-outgoing"], V["x"]),
                    expr(S["let"], V["x"], S["zzz"], V["x"]),
                ),
            ),
            expr(S["zzz"]),
        )
    )

    # !(test (collapse (let True (has-no-outgoing $x) (let $x a $x))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["has-no-outgoing"], V["x"]),
                    expr(S["let"], V["x"], S["a"], V["x"]),
                ),
            ),
            expr(),
        )
    )

    # !(test (dif 1 2) True)
    yield m.eval(expr(S["test"], expr(S["dif"], 1, 2), val(value=True)))

    # !(test (collapse (let True (dif $q 5) (let $q 6 $q))) (6))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["dif"], V["q"], 5),
                    expr(S["let"], V["q"], 6, V["q"]),
                ),
            ),
            expr(6),
        )
    )

    # !(test (collapse (let True (dif $q 5) (let $q 5 $q))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["dif"], V["q"], 5),
                    expr(S["let"], V["q"], 5, V["q"]),
                ),
            ),
            expr(),
        )
    )

    # !(test (!= 1 2) True)
    yield m.eval(expr(S["test"], expr(S["!="], 1, 2), val(value=True)))

    # !(test (!= 1 1) False)
    yield m.eval(expr(S["test"], expr(S["!="], 1, 1), val(value=False)))

    # !(test (collapse (let True (!= $r 5) (let $r 5 $r))) (5))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["!="], V["r"], 5),
                    expr(S["let"], V["r"], 5, V["r"]),
                ),
            ),
            expr(5),
        )
    )

    # (= (marks carol) 90)
    m += expr(S["="], expr(S["marks"], S["carol"]), 90)

    # (= (marks carol) 30)
    m += expr(S["="], expr(S["marks"], S["carol"]), 30)

    # (= (marks dave) 10)
    m += expr(S["="], expr(S["marks"], S["dave"]), 10)

    # (= (marks dave) 20)
    m += expr(S["="], expr(S["marks"], S["dave"]), 20)

    # (= (any-pass $w) (let $m (marks $w) (> $m 50)))
    m += expr(
        S["="],
        expr(S["any-pass"], V["w"]),
        expr(S["let"], V["m"], expr(S["marks"], V["w"]), expr(S[">"], V["m"], 50)),
    )

    # !(test (collapse (any-pass carol)) (True False))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["any-pass"], S["carol"])),
            expr(val(value=True), val(value=False)),
        )
    )

    # !(test (not-provable (any-pass carol)) False)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["any-pass"], S["carol"])), val(value=False))
    )

    # !(test (not-provable (any-pass dave)) True)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["any-pass"], S["dave"])), val(value=True))
    )

    # !(test (not-provable (any-pass nobody)) True)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["any-pass"], S["nobody"])), val(value=True))
    )

    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w dave $w)))
    #        (dave))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["any-pass"], V["w"])),
                    expr(S["let"], V["w"], S["dave"], V["w"]),
                ),
            ),
            expr(S["dave"]),
        )
    )

    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w carol $w))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["any-pass"], V["w"])),
                    expr(S["let"], V["w"], S["carol"], V["w"]),
                ),
            ),
            expr(),
        )
    )

    # !(test (collapse (let True (not-provable (any-pass $w)) (let $w erin $w)))
    #        (erin))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["any-pass"], V["w"])),
                    expr(S["let"], V["w"], S["erin"], V["w"]),
                ),
            ),
            expr(S["erin"]),
        )
    )

    # !(bind! &kin (new-space))
    yield m.eval(expr(S["bind!"], S["&kin"], expr(S["new-space"])))

    # !(add-atom &kin (parent alice bob))
    yield m.eval(expr(S["add-atom"], S["&kin"], expr(S["parent"], S["alice"], S["bob"])))

    # !(add-atom &kin (parent carol dave))
    yield m.eval(expr(S["add-atom"], S["&kin"], expr(S["parent"], S["carol"], S["dave"])))

    # (= (has-child $x) (match &kin (parent $x $y) True))
    m += expr(
        S["="],
        expr(S["has-child"], V["x"]),
        expr(S["match"], S["&kin"], expr(S["parent"], V["x"], V["y"]), val(value=True)),
    )

    # !(test (not-provable (has-child alice)) False)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["has-child"], S["alice"])), val(value=False))
    )

    # !(test (not-provable (has-child bob)) True)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["has-child"], S["bob"])), val(value=True))
    )

    # !(test (not-provable (has-child stranger)) True)
    yield m.eval(
        expr(
            S["test"], expr(S["not-provable"], expr(S["has-child"], S["stranger"])), val(value=True)
        )
    )

    # !(test (collapse (let True (not-provable (has-child $w)) (let $w bob $w)))
    #        (bob))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["has-child"], V["w"])),
                    expr(S["let"], V["w"], S["bob"], V["w"]),
                ),
            ),
            expr(S["bob"]),
        )
    )

    # !(test (collapse (let True (not-provable (has-child $w)) (let $w alice $w))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["has-child"], V["w"])),
                    expr(S["let"], V["w"], S["alice"], V["w"]),
                ),
            ),
            expr(),
        )
    )

    # !(test (collapse (let True (not-provable (has-child $w)) (let $w nobody $w)))
    #        (nobody))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["has-child"], V["w"])),
                    expr(S["let"], V["w"], S["nobody"], V["w"]),
                ),
            ),
            expr(S["nobody"]),
        )
    )

    # (= (band $n) (case $n ((90 True) (40 False))))
    m += expr(
        S["="],
        expr(S["band"], V["n"]),
        expr(S["case"], V["n"], expr(expr(90, val(value=True)), expr(40, val(value=False)))),
    )

    # !(test (not-provable (band 90)) False)
    yield m.eval(expr(S["test"], expr(S["not-provable"], expr(S["band"], 90)), val(value=False)))

    # !(test (not-provable (band 40)) True)
    yield m.eval(expr(S["test"], expr(S["not-provable"], expr(S["band"], 40)), val(value=True)))

    # !(test (not-provable (band 55)) True)
    yield m.eval(expr(S["test"], expr(S["not-provable"], expr(S["band"], 55)), val(value=True)))

    # !(test (not-provable (superpose (False True))) False)
    yield m.eval(
        expr(
            S["test"],
            expr(S["not-provable"], expr(S["superpose"], expr(val(value=False), val(value=True)))),
            val(value=False),
        )
    )

    # !(test (not-provable (superpose (False False))) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["not-provable"], expr(S["superpose"], expr(val(value=False), val(value=False)))),
            val(value=True),
        )
    )

    # !(test (not-provable (superpose ())) True)
    yield m.eval(
        expr(S["test"], expr(S["not-provable"], expr(S["superpose"], expr())), val(value=True))
    )

    # !(test (not-provable (> 1 2)) True)
    yield m.eval(expr(S["test"], expr(S["not-provable"], expr(S[">"], 1, 2)), val(value=True)))

    # !(test (not-provable (> 2 1)) False)
    yield m.eval(expr(S["test"], expr(S["not-provable"], expr(S[">"], 2, 1)), val(value=False)))

    # !(test (not-provable (== 1 1)) False)
    yield m.eval(expr(S["test"], expr(S["not-provable"], expr(S["=="], 1, 1)), val(value=False)))

    # !(test (not-provable (#< 5 1)) True)
    yield m.eval(expr(S["test"], expr(S["not-provable"], expr(S["#<"], 5, 1)), val(value=True)))

    # !(test (collapse (let True (not-provable (#< $x 5)) (let $x 7 $x))) (7))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["#<"], V["x"], 5)),
                    expr(S["let"], V["x"], 7, V["x"]),
                ),
            ),
            expr(7),
        )
    )

    # !(test (collapse (let True (not-provable (#< $x 5)) (let $x 3 $x))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["#<"], V["x"], 5)),
                    expr(S["let"], V["x"], 3, V["x"]),
                ),
            ),
            expr(),
        )
    )

    # !(test (collapse (let True (not-provable (#= $y 4)) (let $y 9 $y))) (9))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["#="], V["y"], 4)),
                    expr(S["let"], V["y"], 9, V["y"]),
                ),
            ),
            expr(9),
        )
    )

    # !(test (collapse (let True (not-provable (#= $y 4)) (let $y 4 $y))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    val(value=True),
                    expr(S["not-provable"], expr(S["#="], V["y"], 4)),
                    expr(S["let"], V["y"], 4, V["y"]),
                ),
            ),
            expr(),
        )
    )

    # (: mask-example-double (-> Number Number))
    m += expr(S[":"], S["mask-example-double"], expr(S["->"], S["Number"], S["Number"]))

    # (= (mask-example-double $x) (* $x 2))
    m += expr(S["="], expr(S["mask-example-double"], V["x"]), expr(S["*"], V["x"], 2))

    # (: mask-example-holds (-> Atom Bool))
    m += expr(S[":"], S["mask-example-holds"], expr(S["->"], S["Atom"], S["Bool"]))

    # (= (mask-example-holds 10) True)
    m += expr(S["="], expr(S["mask-example-holds"], 10), val(value=True))

    # !(add-atom &petta (dispatch-policy mask-example-holds NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["mask-example-holds"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(test (not-provable (mask-example-holds (mask-example-double 5))) True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["not-provable"], expr(S["mask-example-holds"], expr(S["mask-example-double"], 5))
            ),
            val(value=True),
        )
    )

    # !(test (not-provable (mask-example-holds 10)) False)
    yield m.eval(
        expr(
            S["test"], expr(S["not-provable"], expr(S["mask-example-holds"], 10)), val(value=False)
        )
    )

    # !(test (collapse (mask-example-holds (mask-example-double 5))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["mask-example-holds"], expr(S["mask-example-double"], 5))),
            expr(),
        )
    )

    yield from ()
