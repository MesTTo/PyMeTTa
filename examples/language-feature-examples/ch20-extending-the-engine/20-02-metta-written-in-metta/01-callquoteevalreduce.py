"""Purpose: examples/ch20-extending-the-engine/20-02-metta-written-in-metta/01-callquoteevalreduce.metta in Python: the same four, timed.

`call`, `quote`, `eval` and `reduce` around `(fib 5)`, asked three times: before
`fib` exists, from inside the definition that installs it, and after. What each
one answers depends on whether the compiler had seen `fib` when the wrapper was
compiled, which is the whole file.

Every definition compiles. `fib` does not exist when the `before-*` wrappers
are written, so their inner call is mentioned rather than called; the four
outer heads carry hyphens and no equations, so they are mentioned too.

`compilefib` is the interesting one and it compiles whole. Its body installs an
equation from inside itself, which is `add-atom` at the function namespace
taking the handle it was given, and the original's `let` around that write is a
Python assignment to a name the body then ignores. The equation being installed
is built in place, `if` and all. `fn.lt`, `fn.add`, and `fn.sub` explicitly
name its stored relations because the equation is data here rather than the
control flow of `compilefib` itself.
"""

from metta import Expression, S, V, fn


def twin(m):
    """Install wrappers around a dynamically installed Fibonacci definition."""
    fib5 = S.fib(5)

    @m.define
    def before_call():  # (= (before-call) (call-before (call (fib 5))))
        return S.call_before(S.call(S.fib(5)))

    @m.define
    def before_quote():  # (= (before-quote) (quote-before (quote (fib 5))))
        return S.quote_before(S.quote(S.fib(5)))

    @m.define
    def before_eval():  # (= (before-eval) (eval-before (eval (fib 5))))
        return S.eval_before(S.eval(S.fib(5)))

    @m.define
    def before_reduce():  # (= (before-reduce) (reduce-before (reduce (fib 5))))
        return S.reduce_before(S.reduce(S.fib(5)))

    # With no fib to reduce, all three control frames DISSOLVE at
    # evaluation and each wrapper holds the bare payload: quote's arrives
    # unevaluated by the barrier, and eval's and reduce's arrive unreduced
    # for want of a fib. `before-call` is left out because it errors,
    # which is what the original's head says in as many words.
    assert m.eval(
        S.before_call_errors_ofc(S.before_quote(), S.before_eval(), S.before_reduce())
    ) == [
        S.before_call_errors_ofc(
            S.quote_before(fib5),
            S.eval_before(fib5),
            S.reduce_before(fib5),
        )
    ]

    @m.define
    def compilefib():
        # (= (compilefib) (let $temp (add-atom &self (= (fib $N) (if (< $N 2) $N
        #      (+ (fib (- $N 1)) (fib (- $N 2)))))) ((within (fib 5)) ...)))
        _temp = fn.add_atom(
            m,
            S["="](
                S.fib(V.n),
                V.n if fn.lt(V.n, 2) else fn.add(S.fib(fn.sub(V.n, 1)), S.fib(fn.sub(V.n, 2))),
            ),
        )
        return (
            S.within(S.fib(5)),
            S.call_within(S.call(S.fib(5))),
            S.quote_within(S.quote(S.fib(5))),
            S.eval_within(S.eval(S.fib(5))),
            S.reduce_within(S.reduce(S.fib(5))),
        )

    # The five inside were compiled before the add-atom ran, so `within` still
    # holds an unevaluated call while the four wrappers reduce.
    assert compilefib().one() == Expression(
        (
            S.within(fib5),
            S.call_within(5),
            # The barrier dissolves here too: the payload arrives bare.
            S.quote_within(fib5),
            S.eval_within(5),
            S.reduce_within(5),
        )
    )

    @m.define
    def after_call():  # (= (after-call) (call-after (call (fib 5))))
        return S.call_after(S.call(S.fib(5)))

    @m.define
    def after_quote():  # (= (after-quote) (quote-after (quote (fib 5))))
        return S.quote_after(S.quote(S.fib(5)))

    @m.define
    def after_eval():  # (= (after-eval) (eval-after (eval (fib 5))))
        return S.eval_after(S.eval(S.fib(5)))

    @m.define
    def after_reduce():  # (= (after-reduce) (reduce-after (reduce (fib 5))))
        return S.reduce_after(S.reduce(S.fib(5)))

    # fib exists now, so the four wrappers written BEFORE it reduce too.
    assert m.eval(
        Expression((S.before_call(), S.before_quote(), S.before_eval(), S.before_reduce()))
    ) == [
        Expression(
            (
                S.call_before(5),
                S.quote_before(fib5),
                S.eval_before(5),
                S.reduce_before(5),
            )
        )
    ]

    assert m.eval(
        Expression((S.after_call(), S.after_quote(), S.after_eval(), S.after_reduce()))
    ) == [
        Expression(
            (
                S.call_after(5),
                S.quote_after(fib5),
                S.eval_after(5),
                S.reduce_after(5),
            )
        )
    ]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: RE-PINNED 2026-08-25, 1 to 102651, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 102651 to 102557, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 102557 to 102532, on the release tree:
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
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-PINNED 2026-09-01 on the operator-protocol tree. Ten fresh full-lane
#: observations had no spread, and the serial min-of-three confirmed the point
#: [measured: twin minimum 68038 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch20-extending-the-engine/20-02-metta-written-in-metta/01-callquoteevalreduce.metta;
#: fixture=operator-protocol tree after python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10; commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 68038 to 68738 (+700), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 68738 to 68822 (+84), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 68822 to 68832 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 68832 to 67384 (-1448), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 67384 to 68121 (+737), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 68121 to 68173 (+52), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 68173 to 67674 (-499), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 67674 to 67669 (-5), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 67669 to 67711 (+42), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 67669 to 67777 (+108), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 67777 to 67787 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 67711 to 67764 (+53), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 67764 to 67827 (+63), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 67827 to 67855 (+28), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 67787 to 69946 (+2159), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 69946 to 69886 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 69886 to 69997 (+111), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 67787 to 67891 (+104), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 67891 to 67919 (+28), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 67919 to 70032 (+2113), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +35 against the trunk's own pin of 69997 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +2078 is what
#: landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 70032 to 70092 (+60), a library's Prolog half compiles
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
#: extensions/python/tools/twin_coverage.py --repin; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-PINNED 2026-09-09, 70092 to 70102 (+10), engine/qlf_boot.pl gained the
#: hermetic child that writes the engine's own artifact set and every library
#: half's (qlf_child/2, qlf_regenerate_aside/1, qlf_child_boot/0,
#: qlf_shell_words/2), so no process's flags, initialisation file or packs
#: shape an artifact the tree shares; the boot file's added predicates move the
#: first definition's warm-up by ten, the load-structure movement its header
#: records for any boot-content change, and the lane's authoring constant moves
#: with it (warmup 1482); a twin importing a half pays the claim's freshness
#: check besides; measured on this tree with the artifacts warm, against the
#: pins of f26de01fb [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 70102

#: DIVERGED 2026-09-07, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 1 atom the example does not (1 =): the twin is an ordinary Python
#: program and its body lowers to the engine's own forms: a match statement is
#: ONE equation whose body is a case tower where the example writes one clause
#: per arm, a named intermediate is a let* the original does not have, a Python
#: truth test wraps its condition in py-truthy, and the annotations and
#: docstrings that come with it are stored beside them [measured 2026-09-07:
#: the two stored-atom surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "3809dfff68c94dec8912ab24cf1ed8da35ef1b4a7d29424ae53c82cc67b38094"
