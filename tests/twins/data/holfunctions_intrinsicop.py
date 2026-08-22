"""The Python twin of examples/data/holfunctions_intrinsicop.metta.

`mymap` maps a function over a cons list, and the example checks that mapping
the PARTIALLY APPLIED builtin `(== 1)` agrees with mapping `eq`, the
one-equation wrapper around the same builtin. Both arguments are partial
applications, which is why both are written as a head applied to one argument:
`equals(1)` and `S.eq(1)`.

`==` is named rather than reached through Python's operator because Python's
`==` is BINARY and taken by structural equality on atoms; the library's binary
spelling is the `a.eq(b)` method, which `eq`'s own equation uses below. A
CURRIED comparison has no operator or method spelling, so the symbol is named
the way a Python author names any function they are about to apply partially,
and the residue table records the missing spelling against P14.4.

`mymap`'s two clauses stay at the container door because their second head
argument is a PATTERN, `()` and `(cons $x $xs)`. A compiled definition spells
a head pattern as a literal default, `def fib(n=0)`, so a structural one has
no `def` spelling; the residue table records that against P14.4 as well.
"""

from petta import S, V, equation

#: The builtin the example curries, named because a curried operator has no
#: operator spelling: `==` is binary in Python and taken by structural
#: equality on atoms, so `equals(1)` is what `(== 1)` reads as.
equals = S["=="]

#: Inferences this twin spends, its own tripwire.
BUDGET = 10337


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # (= (mymap $f ()) ())
    m += equation(S.mymap(V.f, ())).to(())
    # (= (mymap $f (cons $x $xs)) (cons ($f $x) (mymap $f $xs)))
    m += equation(S.mymap(V.f, S.cons(V.x, V.xs))).to(
        S.cons((V.f, V.x), S.mymap(V.f, V.xs))
    )

    # (= (eq $a $b) (== $a $b))
    m += equation(S.eq(V.a, V.b)).to(V.a.eq(V.b))

    # !(test (mymap (== 1) (1 2 3)) (mymap (eq 1) (1 2 3)))
    yield m.eval(
        S.test(
            S.mymap(equals(1), (1, 2, 3)),
            S.mymap(S.eq(1), (1, 2, 3)),
        )
    )
