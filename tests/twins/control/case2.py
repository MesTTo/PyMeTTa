"""The Python twin of examples/control/case2.metta: a branch may fork.

One branch, whose pattern is a bare variable so everything reaches it, and
whose VALUE is a superposition: a `case` answers whatever its branch answers,
which is two things here.

The equation is written at the container door for the reason case.metta gives:
a `case` is Python's `match` and the compiled subset has no lowering for one
(P14.4). Inside a compiled body `superpose(What, What2)` would spell the
branch value, so the hole is the statement, not the fork.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1518


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (compile $stmt)
    #    (case $stmt
    #          (($stmt (superpose (what what2))))))
    m += S["="](
        S.compile(V.stmt),
        S["case"](
            V.stmt,
            expr(expr(V.stmt, S["superpose"](expr(S.what, S.what2)))),
        ),
    )

    # !(test (collapse (compile wat)) (what what2))
    yield m.eval(
        S.test(S["collapse"](S.compile(S.wat)), expr(S.what, S.what2))
    )
