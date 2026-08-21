"""The Python twin of examples/control/if_branch_binding.metta: arms bind alone.

A conditional arm whose value collapses to a clause parameter must not capture
the clause's output at translate time; the other arm still runs its own
unification. The original found this by differential fuzzing of compiled
programs, and every equation in it is exactly what a Python `if` statement
with an assignment in one arm compiles to:

    if a < a:          -->  (if (< $a $a)
        _c = a         -->      (let* (($_c $a)) $a)
        return a
    return b           -->      $b)

so three of the four are written that way and read the same in both languages.
The binding is named `_c` rather than `c` because Python calls a bound name
nothing reads a dead store, and it is not one here: it is the `let*` pair the
defect lives in. `case-else` is the same shape through `case`, which Python's
`match` statement would spell and the compiled subset has no lowering for yet
(P14.4), so that one equation is written at the container door.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 9810


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define(name="pick-else")
    def pick_else(a, b):
        # (= (pick-else $a $b) (if (< $a $a) (let* (($c $a)) $a) $b))
        if a < a:  # noqa: PLR0124 -- comparing the parameter with itself is the fixture: the then arm must never run, and the else arm must still unify its own output
            _c = a
            return a
        return b

    # !(test (pick-else 1 2) 2)
    yield m.eval(S.test(pick_else(1, 2), 2))

    @m.define(name="pick-then")
    def pick_then(a, b):
        # (= (pick-then $a $b) (if (> $a 0) (let* (($c $a)) $a) $b))
        if a > 0:
            _c = a
            return a
        return b

    # !(test (pick-then 1 2) 1)
    yield m.eval(S.test(pick_then(1, 2), 1))

    # (= (case-else $a $b) (case (< $a $a) ((True (let* (($c $a)) $a)) (False $b))))
    m += S["="](
        S["case-else"](V.a, V.b),
        S["case"](
            S["<"](V.a, V.a),
            expr(
                expr(TRUE, S["let*"](expr(expr(V.c, V.a)), V.a)),
                expr(FALSE, V.b),
            ),
        ),
    )

    # !(test (case-else 3 4) 4)
    yield m.eval(S.test(S["case-else"](3, 4), 4))

    @m.define
    def both(a, b):
        # (= (both $a $b) (if (> $a $b) (let* (($c 1)) $a) (let* (($d 1)) $b)))
        if a > b:
            _c = 1
            return a
        _d = 1
        return b

    # !(test (both 5 2) 5)
    yield m.eval(S.test(both(5, 2), 5))
    # !(test (both 2 5) 5)
    yield m.eval(S.test(both(2, 5), 5))
