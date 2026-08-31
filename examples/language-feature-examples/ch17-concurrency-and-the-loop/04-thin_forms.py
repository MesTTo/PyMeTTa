"""Purpose: examples/ch17-concurrency-and-the-loop/04-thin_forms.metta in Python: the forms almost nothing uses.

This file exists because of `sealed`. It had ZERO uses anywhere in the tree,
it was broken, and nothing said so, so a low usage count is a warning rather
than a statistic. Each form here is exercised for the property that makes it a
special form rather than a function.

Most of them keep MeTTa's name, because a special form is exactly a thing
whose arguments Python would have evaluated before the call. What does move
into Python is everything around them: an arithmetic TERM is the grounded lift
`G(1) + 1`, `size-atom` is `len`, `msort` is `sorted` (atoms carry the
engine's own order, so the two agree by construction), a match is the
subscript door, a `let` that only names an intermediate result is an
assignment, `(let ($v $s) ...)` over an answer already in hand is tuple
unpacking, `(timeout 5 ...)` is `m.eval(term, timeout=5)`, `once` is
`first(default=...)` over the lazy answer view, and every `transaction` is
`m.transaction(term)`, the door that keeps the engine's own empty-answer
rollback.

One place where the dissolution table's `collapse` is `list()` does not hold,
filed against P14.4: collapsing gathers the answers into one ATOM, so the
collapse of no answers is `()` while the list of no answers is `[]`, which is
the distinction the first three claims are about; `Expression(answers)` is the
ordered atom form, and the three assertions below are the check
[tested: the first three asserts of twin(); commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. And
`(let $b (tx-body) (transaction $b))` binds the body so the special form sees a
VARIABLE holding a value; substituting the term in Python instead would hand
`transaction` the term itself, and it would run rather than come back unrun.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
  - UNIT used here is a package value rather than a local reconstruction
    [tested: test_the_canonical_atoms_are_public_values; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import UNIT, Expression, G, S, V, equation, fn, rules, superpose


def twin(m):
    """Exercise nine special forms, one property each."""
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
    assert m.eval(S.prog1(G(1) + 1, G(2) + 2, G(3) + 3)) == [2]
    # !(test (progn (+ 1 1) (+ 2 2) (+ 3 3)) 6)
    # rung: a statement sequence IS progn, and three expressions with no effect are no statements
    assert m.eval(S.progn(G(1) + 1, G(2) + 2, G(3) + 3)) == [6]

    # ----------------------------------------------------- transaction
    # Every write inside is undone when the body fails, which is what a
    # transaction is FOR and what a plain progn does not give. The handle is
    # the space operand, so no symbol names it.
    # !(test (collapse (transaction (progn (add-atom &self (tx-rolled a))
    #                                      (superpose ()))))
    #        ())
    # The top rung is a scope, with the ordinary write door inside it:
    #
    #     with m.transaction():
    #         m += S.tx_rolled(S.a)
    #         ...                        # answering nothing rolls it back
    #
    # `transaction` takes a callable or a term, and an open `with` scope is
    # appendix stamp 4, unruled: a callable rolls back on a Python EXCEPTION,
    # and this file's claim is a body that simply answers nothing.
    rolls_back = S.progn(S.add_atom(m, S.tx_rolled(S.a)), nothing)  # rung: the write has to be inside the engine's transaction, and `space += atom` is a statement over a handle
    assert m.transaction(rolls_back) == []
    # !(test (collapse (match &self (tx-rolled $x) $x)) ())
    assert m[S.tx_rolled(V.x)].x == []

    # A body that succeeds keeps its writes. The transaction answers whatever
    # its body did, and add-atom answers the unit value.
    # !(test (collapse (transaction (add-atom &self (tx-kept a)))) (()))
    keeps = S.add_atom(m, S.tx_kept(S.a))  # rung: the same, for the committing case
    assert m.transaction(keeps) == [Expression(())]
    # !(test (collapse (match &self (tx-kept $x) $x)) (a))
    assert m[S.tx_kept(V.x)].x == [S.a]

    # "whatever its body did" means EVERY answer, not the first one. Until
    # 2026-08-19 this answered (1), because SWI's transaction/1 runs its goal
    # as once/1.
    @rules
    def three():
        # (= (tx-three) 1) (= (tx-three) 2) (= (tx-three) 3)
        yield equation(S.tx_three()).to(1)
        yield equation(S.tx_three()).to(2)
        yield equation(S.tx_three()).to(3)

    m += three

    # !(test (collapse (transaction (tx-three))) (1 2 3))
    assert m.transaction(S.tx_three()) == [1, 2, 3]
    # !(test (collapse (transaction (superpose ((add-atom &self (tx-each 1))
    #                                           (add-atom &self (tx-each 2))))))
    #        (() ()))
    each = S.superpose((S.add_atom(m, S.tx_each(1)), S.add_atom(m, S.tx_each(2))))  # rung: two writes inside one transaction, and a write is a statement over a handle
    assert m.transaction(each) == [Expression(()), Expression(())]
    # !(test (collapse (match &self (tx-each $x) $x)) (1 2))
    assert m[S.tx_each(V.x)].x == [1, 2]

    # ----------------------------------------------------- atomically
    # The same operation under the name the concurrency vocabulary uses, and
    # sugar over transaction so the guarantees cannot drift.
    # !(test (collapse (atomically (tx-three))) (1 2 3))
    assert m.eval(S.atomically(S.tx_three())) == [1, 2, 3]

    # What it does that transaction cannot: transaction is a special form and
    # compiles its body into the call site, so a variable there is a value and
    # the term comes back unrun; atomically takes its body as an unreduced
    # Atom and evaluates it, so the body can be a term the program computed.
    @m.define
    def tx_body():
        # (= (tx-body) (noeval (superpose ((+ 1 1) (+ 2 2)))))
        return fn.noeval(superpose(1 + 1, 2 + 2))

    computed = S.tx_body()
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
    value, seconds = m.eval(S.elapsed(G(1) + 2))[0]
    assert value == 3
    # !(test (let ($v $s) (elapsed (+ 1 2)) (< $s 60)) True)
    # The carried scalar, because `<` between atoms is the engine's total
    # ORDER rather than arithmetic, and this claim is about a duration.
    assert seconds.value < 60

    # ----------------------------------------------------- timeout
    # A bound that does not fire leaves the answer alone. The firing case
    # cannot be an assertion here: a resource bound is a CONTROL exception, so
    # a program's own (catch ...) deliberately cannot eat it and the run stops.
    @m.define
    def spin(n):
        # (= (spin $n) (if (== $n 0) done (spin (- $n 1))))
        return S.done if n == 0 else spin(n - 1)

    # !(test (timeout 5 (spin 10)) done)
    assert m.eval(S.spin(10), timeout=5) == [S.done]

    # ----------------------------------------------------- with_mutex
    # Named, so two different names do not serialise against each other. The
    # form's own name really has an underscore, and the factory's attribute
    # map is total, so it takes the bracket: `S.with_mutex` would be
    # `with-mutex`. The two lock names are hyphenated and take the attribute.
    # !(test (with_mutex thin-lock-a (+ 1 2)) 3)
    assert m.eval(S["with_mutex"](S.thin_lock_a, G(1) + 2)) == [3]
    # !(test (with_mutex thin-lock-b (+ 2 2)) 4)
    assert m.eval(S["with_mutex"](S.thin_lock_b, G(2) + 2)) == [4]

    # ----------------------------------------------------- hyperpose
    # Runs its branches concurrently, so `once` over an expensive branch and a
    # cheap one answers as soon as the cheap one is done.
    # !(test (once (hyperpose ((spin 3000000) (spin 3)))) done)
    branches = S.parallel((S.spin(3_000_000), S.spin(3)))
    assert m.answers(branches).first(default=UNIT) == S.done
    #
    # Both branches ran and both answers came back, which is what collapsing
    # over hyperpose observes. The sort is the assertion's, not the form's:
    # answers arrive in COMPLETION order, so (4 2) is as correct as (2 4).
    # !(test (msort (collapse (hyperpose ((+ 1 1) (+ 2 2))))) (2 4))
    assert sorted(m.parallel(G(1) + 1, G(2) + 2)) == [2, 4]

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


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 31548 to 31570, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 31570 to 31581, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 31581 to 31513, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 31513 to 31523, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 31523 to 31650 (+127), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 31650 to 31676 (+26), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 31676
