"""The Python twin of examples/data/holfunctions_intrinsicop.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 10337


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (mymap $f ()) ())
    m += expr(S["="], expr(S["mymap"], V["f"], expr()), expr())

    # (= (mymap $f (cons $x $xs)) (cons ($f $x) (mymap $f $xs)))
    m += expr(
        S["="],
        expr(S["mymap"], V["f"], expr(S["cons"], V["x"], V["xs"])),
        expr(S["cons"], expr(V["f"], V["x"]), expr(S["mymap"], V["f"], V["xs"])),
    )

    # (= (eq $a $b) (== $a $b))
    m += expr(S["="], expr(S["eq"], V["a"], V["b"]), expr(S["=="], V["a"], V["b"]))

    # !(test (mymap (== 1) (1 2 3)) (mymap (eq 1) (1 2 3)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["mymap"], expr(S["=="], 1), expr(1, 2, 3)),
            expr(S["mymap"], expr(S["eq"], 1), expr(1, 2, 3)),
        )
    )

    yield from ()
