"""Purpose: examples/spaces/matchsingle.metta in Python: two ways to take one match.

`(a b)` and `(a c)` both match, and both definitions answer only the first: one
cuts after the match, one wraps it in `once`.

Both equations are written at the container door, and one blocker is left of
the two this file used to carry. A compiled body resolves a free name against
the engine's FUNCTION REGISTRY, and neither `cut` nor `once` is in it: both are
forms the translator handles, so `is_function` answers False and a body naming
either is refused (residue, P14.4). PERFECT: `cut` and `once` join the function
registry, so a `@m.define`d body names them like any other callee. What is no
longer a blocker is the space:
a compiled `match` takes its space through a PARAMETER now that a handle is an
ordinary term operand [measured 2026-08-23: a `@m.define`d body whose first
parameter is the space compiles and answers; commit=WORKTREE].

The facts above them are ordinary tuples, and the two calls are terms the
engine evaluates, with the handle itself in the space position.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Store two matching facts, then take one match two ways."""
    m += (S.a, S.b)
    m += (S.a, S.c)

    # (= (match-single-via-cut $space $pattern $outPattern)
    #    (let* (($x (match $space $pattern $outPattern))
    #           ($temp (cut)))
    #          $x))
    m += equation(S["match-single-via-cut"](V.space, V.pattern, V.out)).to(
        S["let*"](  # rung: `cut` is a translator form, not a registry function, so no compiled body names it
            (
                (V.found, S.match(V.space, V.pattern, V.out)),  # rung: the stored body of an equation the decorator cannot compile
                (V.stop, S.cut()),
            ),
            V.found,
        )
    )

    # (= (match-single-via-once $space $pattern $outPattern)
    #    (once (match $space $pattern $outPattern)))
    m += equation(S["match-single-via-once"](V.space, V.pattern, V.out)).to(
        S.once(S.match(V.space, V.pattern, V.out))  # rung: as above, with `once` in place of `cut`
    )

    # Each call carries the caller's own $x, so its answers are rows and the
    # claim reads the projection: one solution, bound to the first fact.
    assert m.fn["match-single-via-cut"](m, S.a(V.x), S.a(V.x)).x == [S.b]
    assert m.fn["match-single-via-once"](m, S.a(V.x), S.a(V.x)).x == [S.b]
