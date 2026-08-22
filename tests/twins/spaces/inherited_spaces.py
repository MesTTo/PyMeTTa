"""The Python twin of examples/spaces/inherited_spaces.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 6327


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &family-parent (edge a b))
    yield m.eval(expr(S["add-atom"], S["&family-parent"], expr(S["edge"], S["a"], S["b"])))

    # !(add-atom &family-parent (parent-only kept))
    yield m.eval(expr(S["add-atom"], S["&family-parent"], expr(S["parent-only"], S["kept"])))

    # !(add-atom &family-parent (layer parent))
    yield m.eval(expr(S["add-atom"], S["&family-parent"], expr(S["layer"], S["parent"])))

    # !(new-space &family-child (inherits &family-parent))
    yield m.eval(expr(S["new-space"], S["&family-child"], expr(S["inherits"], S["&family-parent"])))

    # !(add-atom &family-child (edge b c))
    yield m.eval(expr(S["add-atom"], S["&family-child"], expr(S["edge"], S["b"], S["c"])))

    # !(add-atom &family-child (child-only local))
    yield m.eval(expr(S["add-atom"], S["&family-child"], expr(S["child-only"], S["local"])))

    # !(add-atom &family-child (layer child))
    yield m.eval(expr(S["add-atom"], S["&family-child"], expr(S["layer"], S["child"])))

    # !(test (collapse (match &family-child
    #                          (, (edge $x $y) (edge $y $z))
    #                          ($x $z)))
    #        ((a c)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"],
                    S["&family-child"],
                    expr(S[","], expr(S["edge"], V["x"], V["y"]), expr(S["edge"], V["y"], V["z"])),
                    expr(V["x"], V["z"]),
                ),
            ),
            expr(expr(S["a"], S["c"])),
        )
    )

    # !(test (collapse (match &family-child (layer $x) $x)) (child parent))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["match"], S["&family-child"], expr(S["layer"], V["x"]), V["x"]),
            ),
            expr(S["child"], S["parent"]),
        )
    )

    # !(test (space-atom-count &family-child) 3)
    yield m.eval(expr(S["test"], expr(S["space-atom-count"], S["&family-child"]), 3))

    # !(test (collapse (match &family-parent (parent-only $x) $x)) (kept))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["match"], S["&family-parent"], expr(S["parent-only"], V["x"]), V["x"]),
            ),
            expr(S["kept"]),
        )
    )

    # !(test (collapse (match &family-child (parent-only $x) $x)) (kept))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["match"], S["&family-child"], expr(S["parent-only"], V["x"]), V["x"]),
            ),
            expr(S["kept"]),
        )
    )

    # !(test (collapse (match &family-parent (child-only $x) $x)) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["match"], S["&family-parent"], expr(S["child-only"], V["x"]), V["x"]),
            ),
            expr(),
        )
    )

    yield from ()
