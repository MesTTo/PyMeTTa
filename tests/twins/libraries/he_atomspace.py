"""The Python twin of examples/libraries/he_atomspace.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 11625


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # !(add-atom &self (= (addnormal) (+ 1 3)))
    yield m.eval(
        expr(S["add-atom"], S["&self"], expr(S["="], expr(S["addnormal"]), expr(S["+"], 1, 3)))
    )

    # !(add-reduct &self (= (addreduct) (+ 1 3)))
    yield m.eval(
        expr(S["add-reduct"], S["&self"], expr(S["="], expr(S["addreduct"]), expr(S["+"], 1, 3)))
    )

    # !(test (match &self (= (addnormal) $X) $X) (noeval (+ 1 3)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["match"], S["&self"], expr(S["="], expr(S["addnormal"]), V["X"]), V["X"]),
            expr(S["noeval"], expr(S["+"], 1, 3)),
        )
    )

    # !(test (match &self (= (addreduct) $X) (noeval $X)) 4)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&self"],
                expr(S["="], expr(S["addreduct"]), V["X"]),
                expr(S["noeval"], V["X"]),
            ),
            4,
        )
    )

    # !(get-type 1)
    yield m.eval(expr(S["get-type"], 1))

    # (: a A)
    m += expr(S[":"], S["a"], S["A"])

    # !(test (get-type-space &self a) A)
    yield m.eval(expr(S["test"], expr(S["get-type-space"], S["&self"], S["a"]), S["A"]))

    # (hello world)
    m += expr(S["hello"], S["world"])

    # !(test (unify &self (hello world) Yes No) Yes)
    yield m.eval(
        expr(
            S["test"],
            expr(S["unify"], S["&self"], expr(S["hello"], S["world"]), S["Yes"], S["No"]),
            S["Yes"],
        )
    )

    # !(test (unify &self (hello dream) Yes No) No)
    yield m.eval(
        expr(
            S["test"],
            expr(S["unify"], S["&self"], expr(S["hello"], S["dream"]), S["Yes"], S["No"]),
            S["No"],
        )
    )

    yield from ()
