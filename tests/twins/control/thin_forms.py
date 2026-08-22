"""Purpose: examples/control/thin_forms.metta in Python: the forms almost nothing uses.

This file exists because of `sealed`. It had ZERO uses anywhere in the tree,
it was broken, and nothing said so, so a low usage count is a warning rather
than a statistic. Each form here is exercised for the property that makes it a
special form rather than a function.

Most of them keep MeTTa's name, because a special form is exactly a thing
whose arguments Python would have evaluated before the call. What does move
into Python is everything around them: `size-atom` is `len`, `msort` is
`sorted`, a match is the query door, a `let` that only names an intermediate
result is an assignment, `(let ($v $s) ...)` over an answer already in hand is
tuple unpacking, and `(timeout 5 ...)` is `m.eval(term, timeout=5)`, the same
bound as a keyword argument.

Two places where the dissolution table's `collapse` is `list()` does not
hold, both measured 2026-08-22 and both filed against P14.4. Collapsing
gathers the answers into one ATOM, so the collapse of no answers is `()` while
the list of no answers is `[]`, which is the distinction the first three
claims are about; `Expression(answers)` is the ordered atom form. And
`(let $b (tx-body) (transaction $b))` binds the body so the special form sees
a VARIABLE holding a value; substituting the term in Python instead would hand
`transaction` the term itself, and it would run rather than come back unrun.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation, order_key, rules

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 26649..53210 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 26649,
    "maximum": 53210,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Exercise nine special forms, one property each."""
    here = S[m.space_name]
    nothing = S.superpose(())

    # ----------------------------------------------------- test-no-answer
    # It distinguishes NO ANSWER from ONE ANSWER THAT IS THE EMPTY
    # EXPRESSION, which is the whole reason it is not just (== x ()).
    # !(test-no-answer (superpose ()))
    assert m.eval(nothing) == []
    # !(test (collapse (superpose ())) ())
    assert Expression(m.eval(nothing)) == Expression(())
    # !(test (collapse ()) (()))
    assert Expression(m.eval(Expression(()))) == Expression((Expression(()),))

    # ----------------------------------------------------- prog1 and progn
    # Both run every form; they differ in which one they answer.
    # !(test (prog1 (+ 1 1) (+ 2 2) (+ 3 3)) 2)
    # rung: `prog1` answers its first form after running the rest, and Python has no statement whose value is the first of several
    assert m.eval(S.prog1(S["+"](1, 1), S["+"](2, 2), S["+"](3, 3))) == [2]
    # !(test (progn (+ 1 1) (+ 2 2) (+ 3 3)) 6)
    # rung: a statement sequence IS progn, and three expressions with no effect are no statements
    assert m.eval(S.progn(S["+"](1, 1), S["+"](2, 2), S["+"](3, 3))) == [6]

    # ----------------------------------------------------- transaction
    # Every write inside is undone when the body fails, which is what a
    # transaction is FOR and what a plain progn does not give.
    # !(test (collapse (transaction (progn (add-atom &self (tx-rolled a))
    #                                      (superpose ()))))
    #        ())
    rolls_back = S.progn(S["add-atom"](here, S["tx-rolled"](S.a)), nothing)  # rung: the write has to be inside the engine's transaction, and `m.transaction` rolls back on a Python EXCEPTION rather than on a body with no answers
    assert m.eval(S.transaction(rolls_back)) == []
    # !(test (collapse (match &self (tx-rolled $x) $x)) ())
    assert m.query(S["tx-rolled"](V.x))["x"] == []

    # A body that succeeds keeps its writes. The transaction answers whatever
    # its body did, and add-atom answers the unit value.
    # !(test (collapse (transaction (add-atom &self (tx-kept a)))) (()))
    keeps = S["add-atom"](here, S["tx-kept"](S.a))  # rung: the same, for the committing case
    assert m.eval(S.transaction(keeps)) == [Expression(())]
    # !(test (collapse (match &self (tx-kept $x) $x)) (a))
    assert m.query(S["tx-kept"](V.x))["x"] == [S.a]

    # "whatever its body did" means EVERY answer, not the first one. Until
    # 2026-08-19 this answered (1), because SWI's transaction/1 runs its goal
    # as once/1.
    @rules
    def three():
        # (= (tx-three) 1) (= (tx-three) 2) (= (tx-three) 3)
        yield equation(S["tx-three"]()).to(1)
        yield equation(S["tx-three"]()).to(2)
        yield equation(S["tx-three"]()).to(3)

    m.add(*three)

    # !(test (collapse (transaction (tx-three))) (1 2 3))
    assert m.eval(S.transaction(S["tx-three"]())) == [1, 2, 3]
    # !(test (collapse (transaction (superpose ((add-atom &self (tx-each 1))
    #                                           (add-atom &self (tx-each 2))))))
    #        (() ()))
    each = S.superpose((S["add-atom"](here, S["tx-each"](1)), S["add-atom"](here, S["tx-each"](2))))  # rung: two writes inside one transaction, which the Python door cannot spell for the same reason
    assert m.eval(S.transaction(each)) == [Expression(()), Expression(())]
    # !(test (collapse (match &self (tx-each $x) $x)) (1 2))
    assert m.query(S["tx-each"](V.x))["x"] == [1, 2]

    # ----------------------------------------------------- atomically
    # The same operation under the name the concurrency vocabulary uses, and
    # sugar over transaction so the guarantees cannot drift.
    # !(test (collapse (atomically (tx-three))) (1 2 3))
    assert m.eval(S.atomically(S["tx-three"]())) == [1, 2, 3]

    # What it does that transaction cannot: transaction is a special form and
    # compiles its body into the call site, so a variable there is a value and
    # the term comes back unrun; atomically takes its body as an unreduced
    # Atom and evaluates it, so the body can be a term the program computed.
    noeval, superpose = m.fn("noeval"), m.fn("superpose")

    @m.define(name="tx-body")
    def tx_body():
        # (= (tx-body) (noeval (superpose ((+ 1 1) (+ 2 2)))))
        return noeval(superpose(1 + 1, 2 + 2))

    computed = S["tx-body"]()
    # !(test (collapse (let $b (tx-body) (atomically $b))) (2 4))
    assert m.eval(S.let(V.b, computed, S.atomically(V.b))) == [2, 4]  # rung: the binding IS the claim: it is what makes the argument a variable holding a value
    # !(test (size-atom (collapse (let $b (tx-body) (atomically $b)))) 2)
    assert len(m.eval(S.let(V.b, computed, S.atomically(V.b)))) == 2  # rung: the same binding
    # !(test (size-atom (collapse (let $b (tx-body) (transaction $b)))) 1)
    assert len(m.eval(S.let(V.b, computed, S.transaction(V.b)))) == 1  # rung: the same binding, and the contrast this file is making

    # ----------------------------------------------------- elapsed
    # Answers the value AND the seconds it took, as a pair, so the value is
    # still usable rather than being replaced by a measurement.
    # !(test (let ($v $s) (elapsed (+ 1 2)) $v) 3)
    value, seconds = m.eval(S.elapsed(S["+"](1, 2)))[0]
    assert value == 3
    # !(test (let ($v $s) (elapsed (+ 1 2)) (< $s 60)) True)
    assert seconds < 60

    # ----------------------------------------------------- timeout
    # A bound that does not fire leaves the answer alone. The firing case
    # cannot be an assertion here: a resource bound is a CONTROL exception, so
    # a program's own (catch ...) deliberately cannot eat it and the run stops.
    @m.define
    def spin(n):
        # (= (spin $n) (if (== $n 0) done (spin (- $n 1))))
        return Done if n == 0 else spin(n - 1)  # noqa: F821  -- a capitalised free name in a compiled body is MeTTa data, which has no Python value to bind

    # !(test (timeout 5 (spin 10)) done)
    assert m.eval(S.spin(10), timeout=5) == [S.Done]

    # ----------------------------------------------------- with_mutex
    # Named, so two different names do not serialise against each other.
    # !(test (with_mutex thin-lock-a (+ 1 2)) 3)
    assert m.eval(S.with_mutex(S["thin-lock-a"], S["+"](1, 2))) == [3]
    # !(test (with_mutex thin-lock-b (+ 2 2)) 4)
    assert m.eval(S.with_mutex(S["thin-lock-b"], S["+"](2, 2))) == [4]

    # ----------------------------------------------------- hyperpose
    # Runs its branches concurrently, so `once` over an expensive branch and a
    # cheap one answers as soon as the cheap one is done.
    # !(test (once (hyperpose ((spin 3000000) (spin 3)))) done)
    # The empirical BUDGET admits the measured scheduler envelope, while a
    # later run outside it remains a two-sided finding.
    assert m.eval(S.once(S.hyperpose((S.spin(3_000_000), S.spin(3))))) == [S.Done]
    #
    # Both branches ran and both answers came back, which is what collapsing
    # over hyperpose observes. The sort is the assertion's, not the form's:
    # answers arrive in COMPLETION order, so (4 2) is as correct as (2 4).
    # !(test (msort (collapse (hyperpose ((+ 1 1) (+ 2 2))))) (2 4))
    assert sorted(m.parallel(S["+"](1, 1), S["+"](2, 2)), key=order_key) == [2, 4]

    # ----------------------------------------------------- call
    # Reaches a Prolog predicate with no registration at all, which is the
    # point: msort/2 is SWI's and nothing here imported it.
    # !(test (call (msort (3 1 2))) (1 2 3))
    assert m.eval(S.call(S.msort((3, 1, 2)))) == [Expression((1, 2, 3))]

    # ----------------------------------------------------- translatePredicate
    # Compiles ONE goal inline. It is a statement rather than a value, so it is
    # written inside a progn whose last form is the variable the goal bound.
    # !(test (progn (translatePredicate (msort (3 1 2) $s)) $s) (1 2 3))
    inline = S.translatePredicate(S.msort((3, 1, 2), V.s))
    assert m.eval(S.progn(inline, V.s)) == [Expression((1, 2, 3))]
