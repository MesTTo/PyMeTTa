"""The Python twin of examples/control/letlet.metta: a destructuring binding.

The equation is written at the container door because its `let*` binding is a
PATTERN, `(($f1 $c1 3) (1 2 $d1))`: three variables and a literal on the left
meeting three values on the right, binding in both directions at once. Python
spells that `f1, c1, _ = 1, 2, d1`, and a compiled body refuses a tuple target
("a compiled body binds plain names; destructuring and attribute assignment
have no let* form"). The residue table records that against P14.4.

So the ladder's other rung carries it: `m += S["="](head, body)` lands exactly
the atom the file lands, with no string anywhere.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1681


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (f) (let* ((($f1 $c1 3) (1 2 $d1))) ($f1 $c1 $d1)))
    m += S["="](
        S.f(),
        S["let*"](
            expr(expr(expr(V.f1, V.c1, 3), expr(1, 2, V.d1))),
            expr(V.f1, V.c1, V.d1),
        ),
    )

    # !(test (f) (1 2 3))
    yield m.eval(S.test(S.f(), expr(1, 2, 3)))
