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
    rolls_back = S.progn(
        S.add_atom(m, S.tx_rolled(S.a)), nothing
    )  # rung: the write has to be inside the engine's transaction, and `space += atom` is a statement over a handle
    assert m.transaction(rolls_back) == []
    # !(test (collapse (match &self (tx-rolled $x) $x)) ())
    assert m[S.tx_rolled(V.x)].x == []

    # A body that succeeds keeps its writes. The transaction answers whatever
    # its body did, and add-atom answers `true`, the effect family's answer.
    # !(test (collapse (transaction (add-atom &self (tx-kept a)))) (true))
    keeps = S.add_atom(m, S.tx_kept(S.a))  # rung: the same, for the committing case
    assert m.transaction(keeps) == [True]
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
    #        (true true))
    each = S.superpose(
        (S.add_atom(m, S.tx_each(1)), S.add_atom(m, S.tx_each(2)))
    )  # rung: two writes inside one transaction, and a write is a statement over a handle
    assert m.transaction(each) == [True, True]
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
    assert m.eval(S.let(V.b, computed, S.atomically(V.b))) == [
        2,
        4,
    ]  # rung: the binding IS the claim: it is what makes the argument a variable holding a value
    # !(test (size-atom (collapse (let $b (tx-body) (atomically $b)))) 2)
    assert len(m.eval(S.let(V.b, computed, S.atomically(V.b)))) == 2  # rung: the same binding
    # !(test (size-atom (collapse (let $b (tx-body) (transaction $b)))) 1)
    assert (
        len(m.eval(S.let(V.b, computed, S.transaction(V.b)))) == 1
    )  # rung: the same binding, and the contrast this file is making

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
    def spin(n: int):
        # (= (spin $n) (if (== $n 0) done (spin (- $n 1))))
        return S.done if fn.eq(n, 0) else spin(n - 1)  # engine equality is intentional

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
    branches = S.hyperpose((S.spin(3_000_000), S.spin(3)))
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
#: RE-PINNED 2026-09-01, 31676 to 28216 (-3460), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 28216 to 28181 (-35), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 28181 to 28918 (+737), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 28918 to 30494 (+1576), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 30494 to 31132 (+638), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 31132 to 31152 (+20), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 31152 to 31178 (+26), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 31178 to 30180 (-998), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 30180 to 30481 (+301), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 30481 to 30523 (+42), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 30523 to 30405 (-118), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 30405 to 30411 (+6), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 30411 to 30432 (+21), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 30411 to 30740 (+329), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 30740 to 30750 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 30750 to 30769 (+19), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 30432 to 30478 (+46), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 30478 to 30797 (+319), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 30797 to 30876 (+79), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 30769 to 31309 (+540), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 31309 to 31249 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 31249 to 31401 (+152), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 30769 to 30784 (+15), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 30784 to 30768 (-16), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 30768 to 31305 (+537), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, -96 against the trunk's own pin of 31401 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +633 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 31305 to 31365 (+60), a library's Prolog half compiles
#: beside itself on its first import and loads from the artifact after
#: (metta_load_source/2, seam:compiled_source/1): a twin whose example imports
#: a library with a Prolog half pays the artifact load where both sides paid
#: the source consult and its compile-time expansion in every process,
#: lib_thread's import 278,309 to 5,925 inferences; every import now resolves
#: its spec and asks the boot's claim, about 180 inferences an import, and the
#: boot's content moved (the door, the seam and the three library imports the
#: tokens, receipts and seed units gained), which shifts clause layout by tens;
#: measured on this tree with the artifacts warm [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 31365

#: DIVERGED 2026-09-07, the example holds 0 atoms the twin does not (none) and
#: the twin holds 1 atom the example does not (1 :): a Python annotation IS a (:
#: name (-> ...)) row and a docstring on a compiled function IS an (@doc name
#: ...) row, so the twin's space carries the declarations and the documentation
#: its own file states where the example leaves both unsaid [measured
#: 2026-09-07: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "d7ab69e9f2229d2be651bd994cfb195aafbe3a8084a7ce3119178019f74e23c5"
