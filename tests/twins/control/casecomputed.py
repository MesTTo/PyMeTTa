"""The Python twin of examples/control/casecomputed.metta: cases as a value.

The cases of a `case` are usually written out, and then they are syntax. They
do not have to be: a cases argument that arrives as a VALUE is compiled when it
arrives, so the branches can be decided while the program runs, and that is
what lets a program give `case` another name.

Every equation here is written at the container door and one reason covers all
four. `case` is what Python's `match` statement would spell and the compiled
subset has no lowering for one, which the residue table records against P14.4;
`numbered-cases` additionally names `cons-atom`, and a compiled body resolves a
free name EXACTLY, so a hyphenated engine function cannot be reached from one
(wave one recorded that for `fibsmart`).
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 11131


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (switch $value $cases) (case $value $cases))
    m += S["="](S.switch(V.value, V.cases), S["case"](V.value, V.cases))

    # !(test (switch 2 ((1 one) (2 two))) two)
    yield m.eval(
        S.test(
            S.switch(2, expr(expr(1, S.one), expr(2, S.two))),
            S.two,
        )
    )

    # Handed over or written out, the same cases answer the same thing.
    # !(test (case 2 ((1 one) (2 two))) two)
    yield m.eval(
        S.test(
            S["case"](2, expr(expr(1, S.one), expr(2, S.two))),
            S.two,
        )
    )

    # Cases the program builds are cases too.
    # (= (numbered-cases) (cons-atom (1 one) ((2 two))))
    m += S["="](
        S["numbered-cases"](),
        S["cons-atom"](expr(1, S.one), expr(expr(2, S.two))),
    )

    # !(test (switch 1 (numbered-cases)) one)
    yield m.eval(S.test(S.switch(1, S["numbered-cases"]()), S.one))
    # !(test (switch 2 (numbered-cases)) two)
    yield m.eval(S.test(S.switch(2, S["numbered-cases"]()), S.two))

    # `Empty` is the branch a key with NO ANSWERS takes, and it means that
    # on both paths. Here the key is `(empty)`, so the default answers.
    # (= (key-of-nothing $cases) (case (empty) $cases))
    m += S["="](
        S["key-of-nothing"](V.cases), S["case"](S["empty"](), V.cases)
    )

    # !(test (key-of-nothing ((1 one) (Empty none))) none)
    yield m.eval(
        S.test(
            S["key-of-nothing"](expr(expr(1, S.one), expr(S.Empty, S.none))),
            S.none,
        )
    )
    # !(test (case (empty) ((1 one) (Empty none))) none)
    yield m.eval(
        S.test(
            S["case"](
                S["empty"](), expr(expr(1, S.one), expr(S.Empty, S.none))
            ),
            S.none,
        )
    )

    # A key that answers but matches no branch is a different thing, and it
    # answers nothing whether an `Empty` branch is there or not.
    # !(test (collapse (switch 9 ((1 one) (Empty none)))) ())
    yield m.eval(
        S.test(
            S["collapse"](
                S.switch(9, expr(expr(1, S.one), expr(S.Empty, S.none)))
            ),
            expr(),
        )
    )
    # !(test (collapse (case 9 ((1 one) (Empty none)))) ())
    yield m.eval(
        S.test(
            S["collapse"](
                S["case"](9, expr(expr(1, S.one), expr(S.Empty, S.none)))
            ),
            expr(),
        )
    )

    # One case pair handed over on its own is a pair too, and the definition
    # keeps the head it was written with.
    # (= (one-case $pair) (case 1 ($pair)))
    m += S["="](S["one-case"](V.pair), S["case"](1, expr(V.pair)))

    # !(test (one-case (1 hit)) hit)
    yield m.eval(S.test(S["one-case"](expr(1, S.hit)), S.hit))

    # Cases are checked when they arrive, because nothing after that point
    # can check them.
    # !(test (car-atom (catch (switch 1 foo))) Error)
    yield m.eval(
        S.test(S["car-atom"](S["catch"](S.switch(1, S.foo))), S.Error)
    )

    # Written out, `(case 1 foo)` is not a case with bad cases, it is a
    # program using the name as data, and it still reduces to itself.
    # !(test (case 1 foo) (case 1 foo))
    yield m.eval(S.test(S["case"](1, S.foo), S["case"](1, S.foo)))
