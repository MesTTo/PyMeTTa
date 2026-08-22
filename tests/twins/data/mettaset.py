"""The Python twin of examples/data/mettaset.metta: a superposition of facts.

One `add-atom` adds EIGHT atoms, because its argument is a superposition: the
`cons` builds `(set $x $y)` for every combination the two nested superpositions
answer, and each answer is added. The second form collapses a match over them
back into one expression, so the eight are readable in source order.

Both forms are the term door, which is where a runnable form lives: `let`
binds inside the FORM rather than in a function body, so there is no Python
statement position to spell it in.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
BUDGET = 3573


def twin(m):
    """One answer group per runnable form of the original, in source order.

    The first form answers the atoms it added; the second answers the
    collapsed match.
    """
    # !(let $x (cons set (superpose ((1 (superpose (a b c)))
    #                                (2 (superpose (d e f)))
    #                                (3 (superpose (a b))))))
    #       (add-atom &self $x))
    yield m.eval(
        S.let(
            V.x,
            S.cons(
                S.set,
                S.superpose(
                    (
                        (1, S.superpose((S.a, S.b, S.c))),
                        (2, S.superpose((S.d, S.e, S.f))),
                        (3, S.superpose((S.a, S.b))),
                    )
                ),
            ),
            S["add-atom"](S["&self"], V.x),
        )
    )

    # !(test (collapse (match &self (set $x $y) (set $x $y)))
    #        ((set 1 a) (set 1 b) (set 1 c) (set 2 d) (set 2 e) (set 2 f)
    #         (set 3 a) (set 3 b)))
    yield m.eval(
        S.test(
            S.collapse(S.match(S["&self"], S.set(V.x, V.y), S.set(V.x, V.y))),
            (
                S.set(1, S.a),
                S.set(1, S.b),
                S.set(1, S.c),
                S.set(2, S.d),
                S.set(2, S.e),
                S.set(2, S.f),
                S.set(3, S.a),
                S.set(3, S.b),
            ),
        )
    )
