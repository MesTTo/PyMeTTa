"""The Python twin of examples/data/nestedcons.metta: a nested head pattern.

`f` reads the SECOND element of a list by matching two cons cells in its head,
which is the whole example: `(a b c d)` is `(cons a (cons b (c d)))` and the
pattern names `$b`.

The clause stays at the container door because its head argument is a
PATTERN. A compiled definition spells a head pattern as a literal default,
`def fib(n=0)`, so a structural one has no `def` spelling, and the residue
table records that against P14.4.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
BUDGET = 1252


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # (= (f (cons $a (cons $b $L))) $b)
    m += equation(S.f(S.cons(V.a, S.cons(V.b, V.L)))).to(V.b)

    # !(test (f (a b c d)) b)
    yield m.eval(S.test(S.f((S.a, S.b, S.c, S.d)), S.b))
