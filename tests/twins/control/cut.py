"""The Python twin of examples/control/cut.metta: committing to one answer.

`(foo 1)` and `(foo 2)` both match, and `cut` inside the `let*` throws away
the second, so only `(bar 1)` is ever stored.

`match-single` is written at the container door because its body applies
`match` to a SPACE, a PATTERN and a TEMPLATE that are all parameters. The
compiled subset's own `match(...)` takes a literal space name and a structural
pattern read as syntax, so a definition parameterised over all three has no
compiled spelling; the residue table records that against P14.4. once.metta is
the same definition with `once` in place of `cut`, and it makes the same
choice for the same reason.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 2560


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (foo 1)
    m += S.foo(1)
    # (foo 2)
    m += S.foo(2)

    # (= (match-single $space $pat $ret)
    #    (let* (($x (match $space $pat $ret))
    #           ($temp (cut)))
    #          $x))
    m += S["="](
        S["match-single"](V.space, V.pat, V.ret),
        S["let*"](
            expr(
                expr(V.x, S["match"](V.space, V.pat, V.ret)),
                expr(V.temp, S["cut"]()),
            ),
            V.x,
        ),
    )

    # !(let $x (match-single &self (foo $1) $1) (add-atom &self (bar $x)))
    # answers (())
    yield m.eval(
        S["let"](
            V.x,
            S["match-single"](S["&self"], S.foo(V.one), V.one),
            S["add-atom"](S["&self"], S.bar(V.x)),
        )
    )

    # !(test (collapse (match &self (bar $1) (bar $1))) ((bar 1)))
    yield m.eval(
        S.test(
            S["collapse"](
                S["match"](S["&self"], S.bar(V.one), S.bar(V.one))
            ),
            expr(S.bar(1)),
        )
    )
