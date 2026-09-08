"""Purpose: examples/ch18-performance/18-01-larger-workloads/02-holbenchmark.metta in Python: four million-step kernels.

A map over a million-long cons list, a fold over a nested one, a hundred
thousand applications of one function, and a polynomial sum. All four are
higher-order: the function being applied arrives as an argument and is called
through a variable.

Applying a parameter is Python's own call syntax now, `f(x)` lowering to
`($f $x)`, so `apply-many` and `poly` are ordinary functions under the
decorator, and so are the two list builders `range` and `deep-nest`, whose
empty-expression base case is Python's `()`.

`map-flat` and `fold-nested` stay at the container door for a blocker the
subset still has: each is two clauses that destructure in the HEAD, `()` and
`(cons $x $xs)`, and a compiled head pattern may only be a LITERAL default, so
a structural default is refused with "a default here is a head pattern, so it
must be a literal" [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT: two
`@m.define`s whose parameters carry the patterns, the way the equations do.
Residue P14.4.

The recursive list builders name every value before passing it to `cons`.
Rules-bundle bodies build the stored `let` terms; compiled bodies use plain
assignment, which lowers to `let*`.
[source: examples/ch18-performance/18-01-larger-workloads/02-holbenchmark.metta:1; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]

Each claim states its own branch allowance above the evaluator's 100000
default, which is a term because `m.limits` bounds inferences and time and not
stack depth (residue, P14.14). The exact numeric annotations keep arithmetic
and ordering on pure engine heads. Equality stays explicit as `fn.eq`, whose
declared Bool result remains bare in each recursive condition.
"""

from metta import S, V, equation, fn, if_

#: `(+ 1)`, the partially applied increment all four kernels are driven with. A
#: one-argument application has no operator spelling, so it is the tuple MeTTa
#: writes it as.
INC = S.add(1)

#: The branch allowance these million-step kernels state above the evaluator's
#: 100000 default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S.max_stack_depth(100_000_000),)


def twin(m):
    """Four higher-order kernels, each run to a million steps."""
    # A map that flattens as it goes, over a cons list built by counting down.
    m += equation(S.map_flat(V.f, ())).to(
        ()
    )  # rung: a compiled head pattern may only be a literal default
    m += equation(
        S.map_flat(V.f, S.cons(V.x, V.xs))
    ).to(  # rung: as above
        S.let(  # rung: this rules body has no Python statement position for the required binding
            V.head,
            (V.f, V.x),
            S.let(  # rung: the recursive value must be named before cons receives its Expression-typed tail
                V.rest,
                S.map_flat(V.f, V.xs),
                S.cons(V.head, V.rest),
            ),
        )
    )

    # The define door applies rung 4's underscore map like every other door,
    # so a hyphenated MeTTa name needs nothing said twice, and this one needs
    # nothing either: `range` is a Python builtin, so the def carries rung 2's
    # trailing underscore, and the map ALREADY reads `range_` as `range`.
    # `def range` would consume the gate's zero A-family headroom and report
    # `P0.13 suppression burn-down increased (observed, maximum): {'N': (37,
    # 35), 'A': (9, 8)}`; it would also redirect recursion to `py-range`.
    @m.define
    def range_(n: int):
        if fn.eq(n, 0):  # engine equality is intentional
            return ()
        rest = range_(n - 1)
        return S.cons(n, rest)

    assert m.fn.with_pragma(DEEP, S.length(S.map_flat(INC, S.range(1_000_000)))) == [1_000_000]

    # A fold that recurses into nested expressions rather than over them.
    m += equation(S.fold_nested(V.f, V.init, ())).to(V.init)  # rung: as above
    m += equation(S.fold_nested(V.f, V.init, S.cons(V.x, V.xs))).to(  # rung: as above
        if_(
            S.is_expr(V.x),  # rung: the stored body of an equation the decorator cannot compile
            S.fold_nested(V.f, S.fold_nested(V.f, V.init, V.x), V.xs),
            S.fold_nested(V.f, (V.f, V.init, V.x), V.xs),
        )
    )

    @m.define
    def deep_nest(n: int):
        if fn.eq(n, 0):  # engine equality is intentional
            return ()
        row = fn.range(50)
        rest = deep_nest(n - 1)
        return S.cons(row, rest)

    assert m.fn.with_pragma(DEEP, S.fold_nested(S.add, 0, S.deep_nest(20_000))).one() == 25_500_000

    # A hundred thousand applications of one function to one value.
    @m.define
    def apply_many(f, n: int, x):
        if fn.eq(n, 0):  # engine equality is intentional
            return x
        return apply_many(f, n - 1, f(x))

    assert m.fn.with_pragma(DEEP, S.apply_many(INC, 100_000, 0)) == [100_000]

    # And a polynomial sum, which applies the parameter inside an addition.
    @m.define
    def poly(f, n: int) -> int:
        if fn.eq(n, 0):  # engine equality is intentional
            return 0
        return fn.add(f(n), poly(f, n - 1))  # f's return type is unknown

    assert m.fn.with_pragma(DEEP, S.poly(INC, 1_000_000)) == [500_001_500_000]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 189781420 to 189781298, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 189781298 to 189781263, on the release tree:
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
#: RE-PINNED 2026-08-25, 189781263 to 189781236, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 189781236 to 189786652 (+5416), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 189786652 to 189787371 (+719), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 189787371 to 189787307 (-64), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 189787307 to 189785398 (-1909), by the
#: specializer argument-walk fix this file's own chain named as the
#: follow-up. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 189785398 to 37300388 (-152485010), the compiled-
#: language batch: try/raise/dict/set/global/type-alias compilation, engine bit
#: family builtins, prelude except/error-payload ops, variadic doors, twin
#: heals [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 37300388 to 37300359 (-29), the subtract-atom
#: primitive and Counter's grain for -=: a new engine head shifts every twin's
#: load structure, the removal doors changed meaning where a twin spells one,
#: and the quad twin stopped being a different program [measured 2026-09-01:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 37300359 to 27901918 (-9398441), generic Python
#: operators now dispatch through live protocols while source twins explicitly
#: name relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 27901918 to 34146332 (+6244414), exact numeric
#: annotations retain native operator heads, publish MeTTa type declarations,
#: and leave relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 34146332 to 34148259 (+1927), static contract
#: discharge and policy-stable recompilation [measured 2026-09-02: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 34148259 to 34148338 (+79), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 34148338 to 34148372 (+34), P43 protects both
#: generated policy-check fallbacks from space-local capture [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 34148372 to 34136479 (-11893), the one pricing pass at
#: the 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 34136479 to 34137515 (+1036), trunk's own movement
#: since each twin's pin was taken on the base its own branch had: twenty-two
#: first-parent steps between the 0.8.0 release re-pin and this tree, the
#: prelude's move into Prolog the largest of them at +39 to +115 a twin and
#: -65,806 on the error algebra, the live-views merge -45 on every twin that
#: writes, the catalog and get-type repairs +169 on the types chapter, and the
#: rest SWI clause-indexing layout as the boot image grew; this tree also
#: stores the compiled default space operand as &self rather than a (context-
#: space) call [measured 2026-09-07: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 34137515 to 34137560 (+45), the merges between this
#: lane's burn-down base (dfd5003f) and the tree that merged it, placed by a
#: first-parent ladder through the lane's own driver over ten twins at
#: f8c4b672, 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
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
#: RE-PINNED 2026-09-08, 34137560 to 34137047 (-513), metta_substitute_self/3
#: probes the term for the text &self before walking it, one C write and one C
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
#: RE-PINNED 2026-09-08, 34137047 to 34135344 (-1703), the evaluation-fuel
#: scope marker is a trailed write (fix/every-intermittent-root-caused,
#: f6e05ca9): `$metta_fuel_scope` is written open with b_setval/2 at scope open
#: and read with b_getval/2 where nb_current/2 used to answer, so an abandoned
#: scope closes itself when an exception unwinds the trail and the cleanup is
#: the fast ordinary exit, and every runnable form pays fewer inferences per
#: scope; a twin drops by about the count of its runnables, and the engine
#: bench reads evaluate and translate 1642 lower each on the same tree. Every
#: twin here re-reads its budget on the merged tree, minimum of three fresh
#: processes [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 34135344 to 34135374 (+30), boot content moved: the
#: refusal table and the typing point are modules this package did not have,
#: three convert doors became one, per-library faces are projections, and the
#: engine gained a catalog watch point, and SWI clause-indexing shape shifts a
#: twin count by tens whenever boot content moves, the mechanism every earlier
#: entry in these chains names. The watch point itself is one inference per
#: &metta write, which a twin that defines a function pays three of (2239
#: against 2236 on ch03 01-comments with the two announcement clauses taken
#: out), and the (limit ...) rows it exists for cost nothing at all: 2239
#: either way with every row-backed bound removed, because boot seeds the
#: mirror those bounds are read from [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 34135344 to 34135774 (+430), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 34135774 to 34135784 (+10), The engine and library
#: module boundaries retain explicit lookup owners, including host registration
#: and returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 34135784 to 34135816 (+32), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 34135816 to 34136610 (+794), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-08, 34136610 to 34136550 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 34136550

#: DIVERGED 2026-09-07, the example holds 6 atoms the twin does not (6 =) and
#: the twin holds 12 the example does not (6 :, 6 =): the twin is an ordinary
#: Python program and its body lowers to the engine's own forms: a match
#: statement is ONE equation whose body is a case tower where the example
#: writes one clause per arm, a named intermediate is a let* the original does
#: not have, a Python truth test wraps its condition in py-truthy, and the
#: annotations and docstrings that come with it are stored beside them
#: [measured 2026-09-07: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "24c90c96a2bda6bdbf28c255aa4cf95acef8da93c267598be1345bfa4607e150"
