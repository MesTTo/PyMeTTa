"""The Python twin of examples/functions/specialize.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 65533


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (map-flat $f ()) ())
    m += expr(S["="], expr(S["map-flat"], V["f"], expr()), expr())

    # (= (map-flat $f (cons $x $xs)) (cons ($f $x) (map-flat $f $xs)))
    m += expr(
        S["="],
        expr(S["map-flat"], V["f"], expr(S["cons"], V["x"], V["xs"])),
        expr(S["cons"], expr(V["f"], V["x"]), expr(S["map-flat"], V["f"], V["xs"])),
    )

    # !(test (map-flat (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(
        expr(S["test"], expr(S["map-flat"], expr(S["+"], 1), expr(1, 2, 3)), expr(2, 3, 4))
    )

    # (= (map-flat2 (() $f)) ())
    m += expr(S["="], expr(S["map-flat2"], expr(expr(), V["f"])), expr())

    # (= (map-flat2 ((cons $x $xs) $f)) (cons ($f $x) (map-flat2 ($xs $f))))
    m += expr(
        S["="],
        expr(S["map-flat2"], expr(expr(S["cons"], V["x"], V["xs"]), V["f"])),
        expr(S["cons"], expr(V["f"], V["x"]), expr(S["map-flat2"], expr(V["xs"], V["f"]))),
    )

    # !(test (map-flat2 ((1 2 3) (+ 1))) (2 3 4))
    yield m.eval(
        expr(S["test"], expr(S["map-flat2"], expr(expr(1, 2, 3), expr(S["+"], 1))), expr(2, 3, 4))
    )

    # (: map-flat3 (-> Atom %Undefined%))
    m += expr(S[":"], S["map-flat3"], expr(S["->"], S["Atom"], S["%Undefined%"]))

    # (= (map-flat3 ($f ())) ())
    m += expr(S["="], expr(S["map-flat3"], expr(V["f"], expr())), expr())

    # (= (map-flat3 ($f (cons $x $xs))) (cons ($f $x) (map-flat3 ($f $xs))))
    m += expr(
        S["="],
        expr(S["map-flat3"], expr(V["f"], expr(S["cons"], V["x"], V["xs"]))),
        expr(S["cons"], expr(V["f"], V["x"]), expr(S["map-flat3"], expr(V["f"], V["xs"]))),
    )

    # (= (p1 $x) (+ 1 $x))
    m += expr(S["="], expr(S["p1"], V["x"]), expr(S["+"], 1, V["x"]))

    # !(test (map-flat3 (p1 (1 2))) (2 3))
    yield m.eval(expr(S["test"], expr(S["map-flat3"], expr(S["p1"], expr(1, 2))), expr(2, 3)))

    # (: map-flat4 (-> Atom %Undefined%))
    m += expr(S[":"], S["map-flat4"], expr(S["->"], S["Atom"], S["%Undefined%"]))

    # (= (map-flat4 ($v ($f ()))) ())
    m += expr(S["="], expr(S["map-flat4"], expr(V["v"], expr(V["f"], expr()))), expr())

    # (= (map-flat4 ($v ($f (cons $x $xs)))) (cons ($f $x) (map-flat4 ($v ($f $xs)))))
    m += expr(
        S["="],
        expr(S["map-flat4"], expr(V["v"], expr(V["f"], expr(S["cons"], V["x"], V["xs"])))),
        expr(
            S["cons"],
            expr(V["f"], V["x"]),
            expr(S["map-flat4"], expr(V["v"], expr(V["f"], V["xs"]))),
        ),
    )

    # !(test (map-flat4 (x (p1 (1 2)))) (2 3))
    yield m.eval(
        expr(S["test"], expr(S["map-flat4"], expr(S["x"], expr(S["p1"], expr(1, 2)))), expr(2, 3))
    )

    # (= (wrapper $f $list) (map-flat $f $list))
    m += expr(S["="], expr(S["wrapper"], V["f"], V["list"]), expr(S["map-flat"], V["f"], V["list"]))

    # !(test (wrapper (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(expr(S["test"], expr(S["wrapper"], expr(S["+"], 1), expr(1, 2, 3)), expr(2, 3, 4)))

    # (= (wrapper2 $f) (id $f))
    m += expr(S["="], expr(S["wrapper2"], V["f"]), expr(S["id"], V["f"]))

    # !(test (wrapper2 (+ 1)) (+ 1))
    yield m.eval(expr(S["test"], expr(S["wrapper2"], expr(S["+"], 1)), expr(S["+"], 1)))

    # (= (trickyspec $f) (if (= ($f 1) 2) (trickyspec (+ 2)) ($f 1)))
    m += expr(
        S["="],
        expr(S["trickyspec"], V["f"]),
        expr(
            S["if"],
            expr(S["="], expr(V["f"], 1), 2),
            expr(S["trickyspec"], expr(S["+"], 2)),
            expr(V["f"], 1),
        ),
    )

    # !(test (trickyspec (+ 4)) 5)
    yield m.eval(expr(S["test"], expr(S["trickyspec"], expr(S["+"], 4)), 5))

    # !(test (trickyspec (+ 1)) 3)
    yield m.eval(expr(S["test"], expr(S["trickyspec"], expr(S["+"], 1)), 3))

    # (= (fold-nested $f $init ()) $init)
    m += expr(S["="], expr(S["fold-nested"], V["f"], V["init"], expr()), V["init"])

    # (= (fold-nested $f $init (cons $x $xs))
    #       (if (is-expr $x)
    #         (fold-nested $f (fold-nested $f $init $x) $xs)
    #         (fold-nested $f ($f $init $x) $xs)))
    m += expr(
        S["="],
        expr(S["fold-nested"], V["f"], V["init"], expr(S["cons"], V["x"], V["xs"])),
        expr(
            S["if"],
            expr(S["is-expr"], V["x"]),
            expr(
                S["fold-nested"], V["f"], expr(S["fold-nested"], V["f"], V["init"], V["x"]), V["xs"]
            ),
            expr(S["fold-nested"], V["f"], expr(V["f"], V["init"], V["x"]), V["xs"]),
        ),
    )

    # !(test (fold-nested + 0 (1 (2 3))) 6)
    yield m.eval(expr(S["test"], expr(S["fold-nested"], S["+"], 0, expr(1, expr(2, 3))), 6))

    # (= (higher-order-fun $a $b) (($a 1) ($b 1)))
    m += expr(
        S["="], expr(S["higher-order-fun"], V["a"], V["b"]), expr(expr(V["a"], 1), expr(V["b"], 1))
    )

    # (= (fun2) (higher-order-fun (+ 1) (* 1)))
    m += expr(
        S["="], expr(S["fun2"]), expr(S["higher-order-fun"], expr(S["+"], 1), expr(S["*"], 1))
    )

    # (= (fun3) (higher-order-fun (* 1) (+ 1)))
    m += expr(
        S["="], expr(S["fun3"]), expr(S["higher-order-fun"], expr(S["*"], 1), expr(S["+"], 1))
    )

    # !(test (fun2) (2 1))
    yield m.eval(expr(S["test"], expr(S["fun2"]), expr(2, 1)))

    # !(test (fun3) (1 2))
    yield m.eval(expr(S["test"], expr(S["fun3"]), expr(1, 2)))

    yield from ()
