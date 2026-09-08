"""Purpose: examples/ch14-seeing-your-program/01-time_and_pragmas.metta in Python: bounds, time and pragmas.

Three of the four bounding forms have a Python door and take it. `timeout` and
`inferences` are per-call keywords, so `(timeout 30 (spin 100))` is
`m.eval(S.spin(100), timeout=30)`; `with-pragma!` scopes settings to a region,
so it is `with m.limits(...)`, which is the same shape and the same undo. The
fourth, `pragma!`, sets a process-wide interpreter setting and is the bound
`m.fn.pragma` effect call. `car-atom` dissolves as well:
`elapsed` answers `(Value Seconds)` and Python reads the value as `[0]`.

`metta/3` takes the space as an operand and a space HANDLE is a grounded atom,
so the handle goes straight in and no `&self` symbol appears; `evalc` is
`m.eval` on the same handle, which is why the two forms sit side by side here.

`spin` is an ordinary decorated function now: its body answers the lowercase
symbol `done`, and `S.done` is the mention door for exactly that, a lowercase
name a compiled body reads as data rather than as a call it cannot resolve.

`bounded-factorial` needs the definitional door that derives NO first-match
guard: its two clauses are non-exclusive and both apply at 0, which is what
makes the runaway branch reachable at all. `@m.define` would emit
`(if (== $n 0) (empty) ...)` and prune it, so `@m.rules` is the door, and the
bound decorator writes the bundle and lands it in one act.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import UNIT, S, V, equation, fn


def twin(m):
    """Bound four evaluations, set seven pragmas, then invert arithmetic."""

    @m.define
    def spin(n: int):
        # (= (spin $n) (if (> $n 0) (spin (- $n 1)) done))
        return spin(n - 1) if n > 0 else S.done

    # A bound that is not reached is invisible.
    assert m.eval(S.spin(100), timeout=30) == [S.done]
    assert m.eval(S.add(1, 2), timeout=30) == [3]

    # Bounding an expression does NOT collapse it to one answer: the whole
    # answer set computes under the bound.
    assert m.eval(S.superpose((1, 2, 3)), timeout=30) == [1, 2, 3]

    # elapsed answers (Value Seconds), so timing a call does not mean writing
    # the clock by hand. Only the value is asserted; the duration is real but
    # not reproducible enough to assert on.
    assert m.answers(S.elapsed(S.spin(100))).one()[0] == S.done

    # sleep answers True, so it sequences with anything else.
    assert m.fn.sleep(0.01).one() is True

    # metta/3 interprets an atom in a space it is HANDED; MeTTa's evalc
    # already is that, since MeTTa's eval is full evaluation rather than one
    # rewriting step, so the two agree.
    assert m.eval(S.metta(S.add(1, 2), S["%Undefined%"], m)) == [3]
    assert m.eval(S.add(1, 2)) == [3]

    # Pragmas. Each answers the unit value, the way add-atom and print do.
    # Every key must be in the interpreter registry, and a bound's value is
    # checked before it replaces a working setting.
    pragma = m.fn.pragma
    assert pragma(S.max_time, 30) == [UNIT]
    assert pragma(S.max_inferences, 100_000_000) == [UNIT]
    # Passing none clears a bound again.
    assert pragma(S.max_time, S.none) == [UNIT]
    assert pragma(S.max_inferences, S.none) == [UNIT]

    # max-stack-depth answers its own error rather than raising: the count it
    # requires is checked in the answer, so the program that wrote it runs on.
    assert pragma(S.max_stack_depth, 0) == [UNIT]
    assert pragma(S.max_stack_depth, -1) == [
        S.Error(fn.pragma(S.max_stack_depth, -1), S.UnsignedIntegerIsExpected)
    ]
    assert pragma(S.max_stack_depth, S.none) == [UNIT]

    # A positive stack-depth setting caps the evaluator's branch-local fuel,
    # and a finite sibling survives when an overlapping recursive branch runs
    # out.
    pragma(S.max_stack_depth, 20).one()

    @m.rules
    def bounded_factorial(n):
        # (= (bounded-factorial 0) 1)
        yield equation(S.bounded_factorial(0)).to(1)
        # (= (bounded-factorial $n) (* $n (bounded-factorial (- $n 1))))
        yield equation(S.bounded_factorial(n)).to(n * S.bounded_factorial(n - 1))

    assert m.eval(S.bounded_factorial(5)) == [120, S.Error(-3, S.StackOverflow)]

    pragma(S.max_stack_depth, S.none).one()

    # (inferences $n $expr) is timeout's deterministic twin: the bound stops
    # at the same step on every machine, and it is the same keyword.
    assert m.eval(S.spin(100), inferences=100000) == [S.done]
    assert m.eval(S.superpose((1, 2, 3)), inferences=100000) == [1, 2, 3]

    # with-pragma! scopes settings to ONE expression; a with-block scopes them
    # to a region, and the previous values come back on every exit path.
    with m.limits(inferences=100000):
        assert m.eval(S.add(20, 22)) == [42]
    with m.limits(timeout=30, inferences=100000):
        assert m.eval(S.spin(100)) == [S.done]
    assert m.eval(S.spin(2000)) == [S.done]

    # verify-specializations runs each generated higher-order call beside its
    # generic form on first use. A compiled parameter applied to itself is the
    # same `($f ($f $x))` the example writes, so the twin exercises the mode on
    # the same specialization; turning the pragma off reports the tally. The
    # value is `S.true`/`S.false`, the symbols the example writes, rather than
    # Python booleans that would only happen to compare unequal to `false`.
    assert pragma(S.verify_specializations, S.true) == [UNIT]

    @m.define
    def verified_inc(x: int):
        # (= (verified-inc $x) (+ $x 1)). The annotation is what makes the
        # body the engine's own `+` rather than the host `py-operator add`;
        # it costs the twin-only declaration `spin` already carries.
        return x + 1

    @m.define
    def verified_twice(f, x):
        # (= (verified-twice $f $x) ($f ($f $x)))
        return f(f(x))

    assert m.eval(S.verified_twice(S.verified_inc, 20)) == [22]
    assert pragma(S.verify_specializations, S.false) == [UNIT]

    # Relational integer arithmetic: one unbound argument among integers
    # solves for it. Exactness is honest, so a branch with no integer answer
    # answers nothing rather than something approximate.
    assert m.solve(4, V.x - 1).x == 5
    assert m.solve(10, V.x + 3).x == 7
    assert m.solve(6, V.x * 2).x == 3
    assert m.solve(3, V.x / 2).x == 6
    assert m.solve(7, V.x * 2).x == []


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 47686 to 48047, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 48047 to 48058, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 48058 to 48026, on the release tree:
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
#: RE-PINNED 2026-08-25, 48026 to 48036, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 48036 to 48119 (+83), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 48119 to 48139 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 48139 to 37197 (-10942), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 37197 to 37132 (-65), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 37132 to 37940 (+808), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 37940 to 43813 (+5873), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 43813 to 44429 (+616), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 44429 to 44445 (+16), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 44445 to 44455 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 44455 to 49767 (+5312), the twin gained the verify-
#: specializations block its example gained: two definitions, one higher-order
#: call that specializes, and the mode's own first-use comparison of the
#: generated clause against the generic one. The move is work the example now
#: does too, not layout [measured 2026-09-06: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=694dff934a11dbc2ee99267b60f39564053baf87].
#: RE-PINNED 2026-09-06, 49767 to 49757 (-10), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 49757 to 50242 (+485), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 50242 to 50284 (+42), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 50284 to 50137 (-147), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 50137 to 48434 (-1703), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 48434 to 48458 (+24), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 48434 to 48555 (+121), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 48555 to 48565 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 48565 to 48746 (+181), the module boundary merged with
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
#: RE-PINNED 2026-09-08, 48458 to 48539 (+81), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 48539 to 48784 (+245), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 48784

#: DIVERGED 2026-09-07, the example holds 0 atoms the twin does not (none) and
#: the twin holds 2 the example does not (2 :): a Python annotation IS a (:
#: name (-> ...)) row and a docstring on a compiled function IS an (@doc name
#: ...) row, so the twin's space carries the declarations and the documentation
#: its own file states where the example leaves both unsaid [measured
#: 2026-09-07: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "7712923adefafa31335329b2ef6b7dba06f9d218411c1df85bb08fe503d89201"
