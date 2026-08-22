"""The Python twin of examples/data/listhead.metta: matching a list's head.

`len` walks a cons list by matching `(cons $Head $Tail)` in its head, and the
first form shows the same match written as a `let`: a pattern on the left of a
binding is unification, so `(cons $Head $Tail)` against `(1 2 3 4 5 6)` binds
the head and the rest.

Both clauses stay at the container door because their head arguments are
PATTERNS, `()` and `(cons $Head $Tail)`. A compiled definition spells a head
pattern as a literal default, `def fib(n=0)`, so a structural one has no `def`
spelling and the residue table records that against P14.4. The name would
collide with Python's own `len` besides.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
BUDGET = 4655


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # (= (len ()) 0)
    m += equation(S.len(())).to(0)
    # (= (len (cons $Head $Tail)) (let $N0 (len $Tail) (+ $N0 1)))
    m += equation(S.len(S.cons(V.Head, V.Tail))).to(
        S.let(V.N0, S.len(V.Tail), V.N0 + 1)
    )

    # !(test (let (cons $Head $Tail) (1 2 3 4 5 6) ($Head $Tail))
    #        (1 (2 3 4 5 6)))
    yield m.eval(
        S.test(
            S.let(
                S.cons(V.Head, V.Tail),
                (1, 2, 3, 4, 5, 6),
                (V.Head, V.Tail),
            ),
            (1, (2, 3, 4, 5, 6)),
        )
    )
    # !(test (len (1 2 3)) 3)
    yield m.eval(S.test(S.len((1, 2, 3)), 3))
    # !(test (cons 42 ()) (42))
    yield m.eval(S.test(S.cons(42, ()), (42,)))
