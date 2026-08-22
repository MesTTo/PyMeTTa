"""The Python twin of examples/performance/holbenchmark.metta: four million-step kernels.

Every definition stays at the container door, and the reasons are the four this
corpus keeps meeting:

- `map-flat` and `fold-nested` destructure in the HEAD (`(cons $x $xs)`, `()`),
  and a compiled head pattern must be a literal;
- `map-flat`, `fold-nested`, `apply-many` and `poly` APPLY a parameter
  (`($f $x)`), and a compiled body calls a plain name, never a variable;
- `range`, `deep-nest`, `apply-many` and `poly` test `(== $n 0)` in their inner
  loop, and Python's `==` in a compiled body lowers to the prelude's `py-eq`
  rather than MeTTa's `==`, which superpose_primes measures at +71.6% on a
  search of this shape;
- `fold-nested` names `is-expr`, which is not a Python identifier either.

Each is a residue entry against P14.4. What the term door does reach is written
as Python: `V.n.eq(0)` is the equality TERM, `V.n - 1` is `(- $n 1)`, `($f $n)`
is the tuple `(V.f, V.n)` and `(+ ($f $n) (poly ...))` is that tuple plus the
call, because a tuple on the left of `+` reflects into the term builder.
"""

from petta import S, V, equation

#: `(+ 1)`, the partially applied increment the four kernels are driven with.
#: A one-argument application has no operator spelling, so it is the tuple MeTTa
#: writes it as.
INC = (S["+"], 1)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 139184129 across the term-door rewrite: `equation(...).to(...)`,
#: `.eq`, `-`, the `INC` tuple and the tuple-plus-Expr addition build the same
#: atoms the hand-nested `expr` calls built, which the atom-level differential
#: confirms byte-for-byte. Prior: ADDED 2026-08-22 at 139184129 by the wave-3
#: twin baseline.
BUDGET = 139184129


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (map-flat $f ()) ())
    m += equation(S["map-flat"](V.f, ())).to(())

    # (= (map-flat $f (cons $x $xs)) (cons ($f $x) (map-flat $f $xs)))
    m += equation(S["map-flat"](V.f, S.cons(V.x, V.xs))).to(
        S.cons((V.f, V.x), S["map-flat"](V.f, V.xs))
    )

    # (= (range $n)
    #    (if (== $n 0) ()
    #        (cons $n (range (- $n 1)))))
    m += equation(S.range(V.n)).to(S["if"](V.n.eq(0),
            (),
            S.cons(V.n, S.range(V.n - 1))))

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (let $temp (map-flat (+ 1) (range 1000000))
    #                           (length $temp)))
    #        1000000)
    yield m.eval(
        S.test(S["with-pragma!"]((S["max-stack-depth"](100000000),),
                S.let(V.temp,
                    S["map-flat"](INC, S.range(1000000)),
                    S.length(V.temp))),
            1000000)
    )

    # (= (fold-nested $f $init ()) $init)
    m += equation(S["fold-nested"](V.f, V.init, ())).to(V.init)

    # (= (fold-nested $f $init (cons $x $xs))
    #       (if (is-expr $x)
    #         (fold-nested $f (fold-nested $f $init $x) $xs)
    #         (fold-nested $f ($f $init $x) $xs)))
    m += equation(S["fold-nested"](V.f, V.init, S.cons(V.x, V.xs))).to(S["if"](S["is-expr"](V.x),
            S["fold-nested"](V.f, S["fold-nested"](V.f, V.init, V.x), V.xs),
            S["fold-nested"](V.f, (V.f, V.init, V.x), V.xs)))

    # (= (deep-nest $n)
    #    (if (== $n 0) ()
    #        (cons (range 50) (deep-nest (- $n 1)))))
    m += equation(S["deep-nest"](V.n)).to(S["if"](V.n.eq(0),
            (),
            S.cons(S.range(50), S["deep-nest"](V.n - 1))))

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (fold-nested + 0 (deep-nest 20000)))
    #        25500000)
    yield m.eval(
        S.test(S["with-pragma!"]((S["max-stack-depth"](100000000),),
                S["fold-nested"](S["+"], 0, S["deep-nest"](20000))),
            25500000)
    )

    # (= (apply-many $f $n $x)
    #    (if (== $n 0) $x
    #        (apply-many $f (- $n 1) ($f $x))))
    m += equation(S["apply-many"](V.f, V.n, V.x)).to(S["if"](V.n.eq(0),
            V.x,
            S["apply-many"](V.f, V.n - 1, (V.f, V.x))))

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (apply-many (+ 1) 100000 0))
    #        100000)
    yield m.eval(
        S.test(S["with-pragma!"]((S["max-stack-depth"](100000000),),
                S["apply-many"](INC, 100000, 0)),
            100000)
    )

    # (= (poly $f $n)
    #    (if (== $n 0) 0
    #        (+ ($f $n) (poly $f (- $n 1)))))
    m += equation(S.poly(V.f, V.n)).to(S["if"](V.n.eq(0),
            0,
            (V.f, V.n) + S.poly(V.f, V.n - 1)))  # noqa: RUF005  -- not tuple concatenation: the right operand is an Expr, so this is Expr.__radd__ building (+ ($f $n) (poly ...))

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (poly (+ 1) 1000000))
    #        500001500000)
    yield m.eval(
        S.test(S["with-pragma!"]((S["max-stack-depth"](100000000),),
                S.poly(INC, 1000000)),
            500001500000)
    )
