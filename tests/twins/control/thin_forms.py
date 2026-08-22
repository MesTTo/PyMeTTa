"""The Python twin of examples/control/thin_forms.metta: the forms nobody calls.

The special forms almost nothing used, each exercised for the property that
makes it a special form rather than a function. A form nobody calls is a form
nobody would notice breaking, which is why the file exists; every one of them
takes its argument UNEVALUATED, and a built term is unevaluated by
construction, so the term door is what the whole file is written with.

Two equations are written at the container door for reasons wave one already
recorded against P14.4. `tx-three` has three clauses that fix nothing, which
stacked Python clauses read as first-match while the file's whole point is
that all three answer. `spin` answers the lowercase SYMBOL `done`, and a
compiled body resolves a lowercase free name as a function and reads a
capitalised one as a constructor, so it has no spelling for that atom.
`tx-body` is a computation and is written as one: `noeval` is an ordinary
engine name a body can call, and `superpose(a, b)` spells alternatives written
out.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 32760 to 33994, +1234, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 32760 by 47554fc's control/types twin baseline.
BUDGET = 33994


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    noeval, superpose = m.fn("noeval"), m.fn("superpose")

    # ------------------------------------------------- test-no-answer
    # It distinguishes NO ANSWER from ONE ANSWER THAT IS THE EMPTY
    # EXPRESSION, which is the whole reason it is not just (== x ()).
    # !(test-no-answer (superpose ())) answers (True)
    yield m.eval(S["test-no-answer"](S["superpose"](expr())))
    # !(test (collapse (superpose ())) ())
    yield m.eval(
        S.test(S["collapse"](S["superpose"](expr())), expr())
    )
    # !(test (collapse ()) (()))
    yield m.eval(S.test(S["collapse"](expr()), expr(expr())))

    # ------------------------------------------------- prog1 and progn
    # Both run every form; they differ in which one they answer.
    # !(test (prog1 (+ 1 1) (+ 2 2) (+ 3 3)) 2)
    yield m.eval(
        S.test(
            S["prog1"](S["+"](1, 1), S["+"](2, 2), S["+"](3, 3)), 2
        )
    )
    # !(test (progn (+ 1 1) (+ 2 2) (+ 3 3)) 6)
    yield m.eval(
        S.test(
            S["progn"](S["+"](1, 1), S["+"](2, 2), S["+"](3, 3)), 6
        )
    )

    # ------------------------------------------------- transaction
    # Every write inside is undone when the body fails, which is what a
    # transaction is FOR and what a plain progn does not give.
    # !(test (collapse (transaction (progn (add-atom &self (tx-rolled a))
    #                                      (superpose ()))))
    #        ())
    yield m.eval(
        S.test(
            S["collapse"](
                S["transaction"](
                    S["progn"](
                        S["add-atom"](
                            S["&self"], S["tx-rolled"](S.a)
                        ),
                        S["superpose"](expr()),
                    )
                )
            ),
            expr(),
        )
    )
    # !(test (collapse (match &self (tx-rolled $x) $x)) ())
    yield m.eval(
        S.test(
            S["collapse"](
                S["match"](
                    S["&self"], S["tx-rolled"](V.x), V.x
                )
            ),
            expr(),
        )
    )

    # A body that succeeds keeps its writes, and add-atom answers the unit
    # value the specification types it with.
    # !(test (collapse (transaction (add-atom &self (tx-kept a)))) (()))
    yield m.eval(
        S.test(
            S["collapse"](
                S["transaction"](
                    S["add-atom"](S["&self"], S["tx-kept"](S.a))
                )
            ),
            expr(expr()),
        )
    )
    # !(test (collapse (match &self (tx-kept $x) $x)) (a))
    yield m.eval(
        S.test(
            S["collapse"](
                S["match"](S["&self"], S["tx-kept"](V.x), V.x)
            ),
            expr(S.a),
        )
    )

    # "whatever its body did" means EVERY answer, not the first one.
    # (= (tx-three) 1)
    m += S["="](S["tx-three"](), 1)
    # (= (tx-three) 2)
    m += S["="](S["tx-three"](), 2)
    # (= (tx-three) 3)
    m += S["="](S["tx-three"](), 3)

    # !(test (collapse (transaction (tx-three))) (1 2 3))
    yield m.eval(
        S.test(
            S["collapse"](S["transaction"](S["tx-three"]())),
            expr(1, 2, 3),
        )
    )
    # !(test (collapse (transaction (superpose ((add-atom &self (tx-each 1))
    #                                           (add-atom &self (tx-each 2))))))
    #        (() ()))
    yield m.eval(
        S.test(
            S["collapse"](
                S["transaction"](
                    S["superpose"](
                        expr(
                            S["add-atom"](
                                S["&self"], S["tx-each"](1)
                            ),
                            S["add-atom"](
                                S["&self"], S["tx-each"](2)
                            ),
                        )
                    )
                )
            ),
            expr(expr(), expr()),
        )
    )
    # !(test (collapse (match &self (tx-each $x) $x)) (1 2))
    yield m.eval(
        S.test(
            S["collapse"](
                S["match"](S["&self"], S["tx-each"](V.x), V.x)
            ),
            expr(1, 2),
        )
    )

    # ------------------------------------------------- atomically
    # The same operation under the name the concurrency vocabulary uses.
    # !(test (collapse (atomically (tx-three))) (1 2 3))
    yield m.eval(
        S.test(
            S["collapse"](S["atomically"](S["tx-three"]())),
            expr(1, 2, 3),
        )
    )

    # What it does that transaction cannot: transaction compiles its body
    # into the call site, so a variable there is a value and the term comes
    # back unrun; atomically takes its body as an unreduced Atom and
    # evaluates it.
    @m.define(name="tx-body")
    def tx_body():
        # (= (tx-body) (noeval (superpose ((+ 1 1) (+ 2 2)))))
        return noeval(superpose(1 + 1, 2 + 2))

    # !(test (collapse (let $b (tx-body) (atomically $b))) (2 4))
    yield m.eval(
        S.test(
            S["collapse"](
                S["let"](
                    V.b, tx_body(), S["atomically"](V.b)
                )
            ),
            expr(2, 4),
        )
    )
    # !(test (size-atom (collapse (let $b (tx-body) (atomically $b)))) 2)
    yield m.eval(
        S.test(
            S["size-atom"](
                S["collapse"](
                    S["let"](
                        V.b, tx_body(), S["atomically"](V.b)
                    )
                )
            ),
            2,
        )
    )
    # !(test (size-atom (collapse (let $b (tx-body) (transaction $b)))) 1)
    yield m.eval(
        S.test(
            S["size-atom"](
                S["collapse"](
                    S["let"](
                        V.b, tx_body(), S["transaction"](V.b)
                    )
                )
            ),
            1,
        )
    )

    # ------------------------------------------------- elapsed
    # Answers the value AND the seconds it took, as a pair, so the value is
    # still usable rather than being replaced by a measurement.
    # !(test (let ($v $s) (elapsed (+ 1 2)) $v) 3)
    yield m.eval(
        S.test(
            S["let"](
                expr(V.v, V.s), S["elapsed"](S["+"](1, 2)), V.v
            ),
            3,
        )
    )
    # !(test (let ($v $s) (elapsed (+ 1 2)) (< $s 60)) True)
    yield m.eval(
        S.test(
            S["let"](
                expr(V.v, V.s),
                S["elapsed"](S["+"](1, 2)),
                S["<"](V.s, 60),
            ),
            TRUE,
        )
    )

    # ------------------------------------------------- timeout
    # A bound that does not fire leaves the answer alone.
    # (= (spin $n) (if (== $n 0) done (spin (- $n 1))))
    m += S["="](
        S.spin(V.n),
        S["if"](
            S["=="](V.n, 0), S.done, S.spin(S["-"](V.n, 1))
        ),
    )
    # !(test (timeout 5 (spin 10)) done)
    yield m.eval(S.test(S["timeout"](5, S.spin(10)), S.done))

    # ------------------------------------------------- with_mutex
    # Named, so two different names do not serialise against each other.
    # !(test (with_mutex thin-lock-a (+ 1 2)) 3)
    yield m.eval(
        S.test(
            S["with_mutex"](S["thin-lock-a"], S["+"](1, 2)), 3
        )
    )
    # !(test (with_mutex thin-lock-b (+ 2 2)) 4)
    yield m.eval(
        S.test(
            S["with_mutex"](S["thin-lock-b"], S["+"](2, 2)), 4
        )
    )

    # ------------------------------------------------- hyperpose
    # Runs its branches concurrently, so `once` over an expensive branch and
    # a cheap one answers as soon as the cheap one is done.
    # !(test (once (hyperpose ((spin 3000000) (spin 3)))) done)
    # DECLINED: the form ANSWERS correctly, and it cannot be PRICED. The
    # branches RACE, and how far the three-million-step branch gets before
    # `once` cuts it is what the race decides: measured over six fresh
    # processes the original costs 60,275-62,013 inferences and a twin that
    # runs the form costs 34,138-35,851, against the lane's allowance of 4.
    # The residue table routes that to P14.14, which owns the budget law.
    yield None
    # Answers arrive in COMPLETION order, so the msort is the assertion's,
    # not the form's.
    # !(test (msort (collapse (hyperpose ((+ 1 1) (+ 2 2))))) (2 4))
    yield m.eval(
        S.test(
            S["msort"](
                S["collapse"](
                    S["hyperpose"](
                        expr(S["+"](1, 1), S["+"](2, 2))
                    )
                )
            ),
            expr(2, 4),
        )
    )

    # ------------------------------------------------- call
    # Reaches a Prolog predicate with no registration at all, which is the
    # point: msort/2 is SWI's and nothing here imported it.
    # !(test (call (msort (3 1 2))) (1 2 3))
    yield m.eval(
        S.test(
            S["call"](S.msort(expr(3, 1, 2))), expr(1, 2, 3)
        )
    )

    # ------------------------------------------------- translatePredicate
    # Compiles ONE goal inline. It is a statement rather than a value, so it
    # is written inside a progn whose last form is the variable the goal
    # bound.
    # !(test (progn (translatePredicate (msort (3 1 2) $s)) $s) (1 2 3))
    yield m.eval(
        S.test(
            S["progn"](
                S["translatePredicate"](
                    S.msort(expr(3, 1, 2), V.s)
                ),
                V.s,
            ),
            expr(1, 2, 3),
        )
    )
