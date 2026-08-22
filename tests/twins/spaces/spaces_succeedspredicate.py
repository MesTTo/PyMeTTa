"""The Python twin of examples/spaces/spaces_succeedspredicate.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 19938


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_spaces))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_spaces"])))

    # !(test (succeedsPredicate (&self friend tim tom))
    #        False)
    yield m.eval(
        expr(
            S["test"],
            expr(S["succeedsPredicate"], expr(S["&self"], S["friend"], S["tim"], S["tom"])),
            val(value=False),
        )
    )

    # (friend a b)
    m += expr(S["friend"], S["a"], S["b"])

    # !(test (if (succeedsPredicate (&self friend $a $b))
    #            ($a $b)
    #            NotFound)
    #        (a b))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if"],
                expr(S["succeedsPredicate"], expr(S["&self"], S["friend"], V["a"], V["b"])),
                expr(V["a"], V["b"]),
                S["NotFound"],
            ),
            expr(S["a"], S["b"]),
        )
    )

    yield from ()
