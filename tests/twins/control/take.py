"""The Python twin of examples/control/take.metta: at most k answers.

`once` takes one and `collapse` takes all; `take` is the bound between them,
applied OUTSIDE the producer so it cuts one that would not stop on its own.

`from` is that producer, and it is where a Python generator says exactly what
MeTTa says: **each `yield` is one answer, which is what `superpose` spells.**
The Python is named `count_up` because `from` is a Python keyword, and
`name="from"` puts the MeTTa name on the equation; recursion inside the body
resolves to the equation's own name either way.

The recursive call is `yield count_up(n + 1)`, not `yield from count_up(n + 1)`.
That is MeTTa's own reading, where an element of a superposition contributes
its own answers, and it is NOT Python's, where `yield f()` would answer a
generator object. `yield from` is the spelling a Python author reaches for and
it compiles wrongly here, silently: the residue table records that against
P14.4 with its reproducer.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8650 to 9052, +402, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 8650 by 47554fc's control/types twin baseline.
BUDGET = 9052


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (collapse (take 3 (superpose (a b c d e)))) (a b c))
    yield m.eval(
        S.test(
            S["collapse"](
                S["take"](3, S["superpose"](expr(S.a, S.b, S.c, S.d, S.e)))
            ),
            expr(S.a, S.b, S.c),
        )
    )

    # Fewer answers than the bound is not an error, and a bound of zero
    # answers nothing, which is what "at most" means.
    # !(test (collapse (take 9 (superpose (a b)))) (a b))
    yield m.eval(
        S.test(
            S["collapse"](S["take"](9, S["superpose"](expr(S.a, S.b)))),
            expr(S.a, S.b),
        )
    )
    # !(test (collapse (take 0 (superpose (a b)))) ())
    yield m.eval(
        S.test(
            S["collapse"](S["take"](0, S["superpose"](expr(S.a, S.b)))),
            expr(),
        )
    )

    @m.define(name="from")
    def count_up(n):
        # (= (from $n) (superpose ($n (from (+ $n 1)))))
        yield n
        yield count_up(n + 1)

    # This counts up forever and take ends it.
    # !(test (collapse (take 4 (from 0))) (0 1 2 3))
    yield m.eval(
        S.test(S["collapse"](S["take"](4, count_up(0))), expr(0, 1, 2, 3))
    )

    # A count that is not a whole number is a mistake rather than an empty
    # answer, because failing into "there is nothing there" sends you
    # looking at your data.
    # !(test (car-atom (catch (take foo (superpose (a b))))) Error)
    yield m.eval(
        S.test(
            S["car-atom"](
                S["catch"](S["take"](S.foo, S["superpose"](expr(S.a, S.b))))
            ),
            S.Error,
        )
    )

    # For a FOREIGN space the bound also reaches the provider. That happens
    # when the expression is exactly one match over one space, which is the
    # first shape below; across a join it does not, and the answers are
    # bounded either way.
    # (edge a b) (edge b c) (edge c d)
    m += S.edge(S.a, S.b)
    m += S.edge(S.b, S.c)
    m += S.edge(S.c, S.d)

    # !(test (collapse (take 2 (match &self (edge $x $y) (edge $x $y))))
    #        ((edge a b) (edge b c)))
    yield m.eval(
        S.test(
            S["collapse"](
                S["take"](
                    2,
                    S["match"](
                        S["&self"],
                        S.edge(V.x, V.y),
                        S.edge(V.x, V.y),
                    ),
                )
            ),
            expr(S.edge(S.a, S.b), S.edge(S.b, S.c)),
        )
    )
    # !(test (collapse (take 2 (match &self (, (edge $x $y) (edge $y $z)) ($x $z))))
    #        ((a c) (b d)))
    yield m.eval(
        S.test(
            S["collapse"](
                S["take"](
                    2,
                    S["match"](
                        S["&self"],
                        S[","](S.edge(V.x, V.y), S.edge(V.y, V.z)),
                        expr(V.x, V.z),
                    ),
                )
            ),
            expr(expr(S.a, S.c), expr(S.b, S.d)),
        )
    )
