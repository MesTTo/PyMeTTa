"""The Python twin of examples/spaces/match_snapshot.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 7027


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (link A B)
    m += expr(S["link"], S["A"], S["B"])

    # (link B C)
    m += expr(S["link"], S["B"], S["C"])

    # (link C A)
    m += expr(S["link"], S["C"], S["A"])

    # (link C E)
    m += expr(S["link"], S["C"], S["E"])

    # !(test (collapse (match &self (, (link $x $y)
    #                                 (link $y $z)
    #                                 (link $z $x))
    #                              (let () (remove-atom &self (link $x $y))
    #                                      (add-atom &self (link $y $x)))))
    #        (() () ()))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"],
                    S["&self"],
                    expr(
                        S[","],
                        expr(S["link"], V["x"], V["y"]),
                        expr(S["link"], V["y"], V["z"]),
                        expr(S["link"], V["z"], V["x"]),
                    ),
                    expr(
                        S["let"],
                        expr(),
                        expr(S["remove-atom"], S["&self"], expr(S["link"], V["x"], V["y"])),
                        expr(S["add-atom"], S["&self"], expr(S["link"], V["y"], V["x"])),
                    ),
                ),
            ),
            expr(expr(), expr(), expr()),
        )
    )

    # !(test (collapse (match &self (link $x $y) ($x $y))) ((C E) (B A) (C B) (A C)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["match"], S["&self"], expr(S["link"], V["x"], V["y"]), expr(V["x"], V["y"])),
            ),
            expr(
                expr(S["C"], S["E"]),
                expr(S["B"], S["A"]),
                expr(S["C"], S["B"]),
                expr(S["A"], S["C"]),
            ),
        )
    )

    # !(bind! &snapshot (new-space))
    yield m.eval(expr(S["bind!"], S["&snapshot"], expr(S["new-space"])))

    # !(add-atom &snapshot (item alpha))
    yield m.eval(expr(S["add-atom"], S["&snapshot"], expr(S["item"], S["alpha"])))

    # !(add-atom &snapshot (item beta))
    yield m.eval(expr(S["add-atom"], S["&snapshot"], expr(S["item"], S["beta"])))

    # (= (visit alpha) (let () (remove-atom &snapshot (item beta)) alpha))
    m += expr(
        S["="],
        expr(S["visit"], S["alpha"]),
        expr(
            S["let"],
            expr(),
            expr(S["remove-atom"], S["&snapshot"], expr(S["item"], S["beta"])),
            S["alpha"],
        ),
    )

    # (= (visit beta) (let () (remove-atom &snapshot (item alpha)) beta))
    m += expr(
        S["="],
        expr(S["visit"], S["beta"]),
        expr(
            S["let"],
            expr(),
            expr(S["remove-atom"], S["&snapshot"], expr(S["item"], S["alpha"])),
            S["beta"],
        ),
    )

    # !(test (collapse (match &snapshot (item $x) (visit $x))) (alpha beta))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["match"], S["&snapshot"], expr(S["item"], V["x"]), expr(S["visit"], V["x"])),
            ),
            expr(S["alpha"], S["beta"]),
        )
    )

    # !(test (collapse (get-atoms &snapshot)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["get-atoms"], S["&snapshot"])), expr()))

    yield from ()
