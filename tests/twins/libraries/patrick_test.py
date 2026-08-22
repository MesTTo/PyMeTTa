"""The Python twin of examples/libraries/patrick_test.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 28309


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_patrick))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_patrick"])))

    # (= (mirror $A)
    #    (let $A (@ $L (cons $head $tail))
    #         (append (reverse $L) $tail)))
    m += expr(
        S["="],
        expr(S["mirror"], V["A"]),
        expr(
            S["let"],
            V["A"],
            expr(S["@"], V["L"], expr(S["cons"], V["head"], V["tail"])),
            expr(S["append"], expr(S["reverse"], V["L"]), V["tail"]),
        ),
    )

    # !(test (mirror (h a n n e s)) (s e n n a h a n n e s))
    yield m.eval(
        expr(
            S["test"],
            expr(S["mirror"], expr(S["h"], S["a"], S["n"], S["n"], S["e"], S["s"])),
            expr(
                S["s"],
                S["e"],
                S["n"],
                S["n"],
                S["a"],
                S["h"],
                S["a"],
                S["n"],
                S["n"],
                S["e"],
                S["s"],
            ),
        )
    )

    # !(test (collapse (for $x (1 2 3 4 5 6)
    #                       (if (> $x 3) $x)))
    #        (4 5 6))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["for"],
                    V["x"],
                    expr(1, 2, 3, 4, 5, 6),
                    expr(S["if"], expr(S[">"], V["x"], 3), V["x"]),
                ),
            ),
            expr(4, 5, 6),
        )
    )

    # !(test (iterate 0 10
    #                 1 (|-> ($i $x)
    #                        (+ $x $i)))
    #        46)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["iterate"],
                0,
                10,
                1,
                expr(S["|->"], expr(V["i"], V["x"]), expr(S["+"], V["x"], V["i"])),
            ),
            46,
        )
    )

    yield from ()
