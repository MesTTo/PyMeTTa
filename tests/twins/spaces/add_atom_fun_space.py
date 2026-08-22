"""The Python twin of examples/spaces/add_atom_fun_space.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1826


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (space) &my_space_name)
    m += expr(S["="], expr(S["space"]), S["&my_space_name"])

    # !(add-atom (space) (my test atom))
    yield m.eval(expr(S["add-atom"], expr(S["space"]), expr(S["my"], S["test"], S["atom"])))

    # !(test (match (space) $a $a) (my test atom))
    yield m.eval(
        expr(
            S["test"],
            expr(S["match"], expr(S["space"]), V["a"], V["a"]),
            expr(S["my"], S["test"], S["atom"]),
        )
    )

    yield from ()
