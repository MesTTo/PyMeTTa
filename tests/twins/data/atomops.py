"""The Python twin of examples/data/atomops.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 17624


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (cons-atom 0 (1 2 3))
    #        (0 1 2 3))
    yield m.eval(expr(S["test"], expr(S["cons-atom"], 0, expr(1, 2, 3)), expr(0, 1, 2, 3)))

    # !(test (car-atom (1 2 3))
    #        1)
    yield m.eval(expr(S["test"], expr(S["car-atom"], expr(1, 2, 3)), 1))

    # !(test (cdr-atom (1 2 3))
    #        (2 3))
    yield m.eval(expr(S["test"], expr(S["cdr-atom"], expr(1, 2, 3)), expr(2, 3)))

    # !(test (index-atom (1 2 3) 1)
    #        2)
    yield m.eval(expr(S["test"], expr(S["index-atom"], expr(1, 2, 3), 1), 2))

    # !(test (id 5) 5)
    yield m.eval(expr(S["test"], expr(S["id"], 5), 5))

    # !(test (=alpha (Father $X) (Father $Y)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["=alpha"], expr(S["Father"], V["X"]), expr(S["Father"], V["Y"])),
            val(value=True),
        )
    )

    # !(test (=alpha (Father $X) (Son $X)) False)
    yield m.eval(
        expr(
            S["test"],
            expr(S["=alpha"], expr(S["Father"], V["X"]), expr(S["Son"], V["X"])),
            val(value=False),
        )
    )

    # !(test (first-from-pair (A B)) A)
    yield m.eval(expr(S["test"], expr(S["first-from-pair"], expr(S["A"], S["B"])), S["A"]))

    # !(test (second-from-pair (A B)) B)
    yield m.eval(expr(S["test"], expr(S["second-from-pair"], expr(S["A"], S["B"])), S["B"]))

    # !(test (index-atom (1 2 3) 5) ())
    yield m.eval(expr(S["test"], expr(S["index-atom"], expr(1, 2, 3), 5), expr()))

    # !(test (index-atom (1 2 3) a) ())
    yield m.eval(expr(S["test"], expr(S["index-atom"], expr(1, 2, 3), S["a"]), expr()))

    # !(test (size-atom 5) ())
    yield m.eval(expr(S["test"], expr(S["size-atom"], 5), expr()))

    # !(test (sort-atom 5) ())
    yield m.eval(expr(S["test"], expr(S["sort-atom"], 5), expr()))

    # !(test (unique-atom 5) ())
    yield m.eval(expr(S["test"], expr(S["unique-atom"], 5), expr()))

    # !(test (alpha-unique-atom 5) ())
    yield m.eval(expr(S["test"], expr(S["alpha-unique-atom"], 5), expr()))

    # !(test (min-atom 5) (Error (min-atom 5) "Atom is not an ExpressionAtom"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["min-atom"], 5),
            expr(S["Error"], expr(S["min-atom"], 5), val("Atom is not an ExpressionAtom")),
        )
    )

    # !(test (max-atom 5) (Error (max-atom 5) "Atom is not an ExpressionAtom"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["max-atom"], 5),
            expr(S["Error"], expr(S["max-atom"], 5), val("Atom is not an ExpressionAtom")),
        )
    )

    # !(test (intersection-atom 5 (a)) ())
    yield m.eval(expr(S["test"], expr(S["intersection-atom"], 5, expr(S["a"])), expr()))

    # !(test (if-error (catch (car-atom $unbound)) refused answered) refused)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(S["catch"], expr(S["car-atom"], V["unbound"])),
                S["refused"],
                S["answered"],
            ),
            S["refused"],
        )
    )

    # !(test (if-error (catch (size-atom $unbound)) refused answered) refused)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(S["catch"], expr(S["size-atom"], V["unbound"])),
                S["refused"],
                S["answered"],
            ),
            S["refused"],
        )
    )

    # !(test (if-error (catch (sort-atom $unbound)) refused answered) refused)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(S["catch"], expr(S["sort-atom"], V["unbound"])),
                S["refused"],
                S["answered"],
            ),
            S["refused"],
        )
    )

    # !(test (if-error (catch (index-atom $unbound 0)) refused answered) refused)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(S["catch"], expr(S["index-atom"], V["unbound"], 0)),
                S["refused"],
                S["answered"],
            ),
            S["refused"],
        )
    )

    # !(test (if-error (catch (subtraction-atom $unbound (a b))) refused answered)
    #        refused)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(S["catch"], expr(S["subtraction-atom"], V["unbound"], expr(S["a"], S["b"]))),
                S["refused"],
                S["answered"],
            ),
            S["refused"],
        )
    )

    # !(test (if-error (catch (car-atom (1 2))) refused answered) answered)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(S["catch"], expr(S["car-atom"], expr(1, 2))),
                S["refused"],
                S["answered"],
            ),
            S["answered"],
        )
    )

    # !(test (car-atom (1 2)) 1)
    yield m.eval(expr(S["test"], expr(S["car-atom"], expr(1, 2)), 1))

    # !(test (collapse (index-atom (a b c) $i)) (a b c))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["index-atom"], expr(S["a"], S["b"], S["c"]), V["i"])),
            expr(S["a"], S["b"], S["c"]),
        )
    )

    yield from ()
