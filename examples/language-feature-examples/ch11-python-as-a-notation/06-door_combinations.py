"""examples/ch11-python-as-a-notation/06-door_combinations.metta in Python: the nesting matrix.

The example proves the engine half of the matrix; this side carries the host
half, cell by cell, in the design's own frame: a DEFINE body is LOWERED
(references become terms), a RULES body is EXECUTED (references act now
unless they stage), an OP body is HOST (references are plain Python unless
they deliberately cross). The staging split is asserted STRUCTURALLY, by
matching the stored equation bodies, because the law is about what the law
HOLDS, not only what it answers: a call carrying a rule variable stages to
its call term, a ground defined call runs at construction and embeds its one
result, a ground op call fires its effect exactly once at construction, and
an op call staged into a law crosses the host per application.
"""

from metta import G, S, V, fn, rules
from metta import equation as eq


def twin(m):
    """Walk the matrix: each definition kind inside each body kind."""
    # ---- inside a DEFINE body (lowered) ----

    @m.define
    def dc_twice(x: int) -> int:         # (= (dc-twice $x) (+ $x $x))
        return x + x

    @m.define
    def dc_quad(x):                      # a define inside a define: the
        return dc_twice(dc_twice(x))     # ordinary call term, engine-only

    assert dc_quad(5) == [20]

    @m.define
    def dc_upper(s):                     # a grounded operation inside a
        return fn.py_call(S[".upper"](s))  # define: one host crossing per call

    assert m.eval(S.dc_upper(G("ab"))) == [S.AB]

    # Writing equations FROM a body: add-atom of an (= ...) atom, the
    # self-modification face. The body runs, the space gains the equation,
    # and the new name answers.
    @m.define
    def dc_install():
        return fn.add_atom(fn.context_space(), S["="](S.dc_nine(), 9))

    m.eval(S.dc_install())
    assert m.eval(S.dc_nine()) == [9]

    # Equations are ordinary atoms, so a program can MATCH one: the meta
    # face that makes rules-over-rules lawful.
    assert [row.body for row in m[S["="](S.dc_nine(), V.body)]] == [9]

    # ---- inside a RULES body (executed, with the staging split) ----

    fired = []

    @m.writes
    def dc_stamp(x: int) -> int:
        fired.append(x)
        return x * 10

    @m.define
    def dc_fib(n: int) -> int:
        if n <= 1:
            return n
        return dc_fib(n - 1) + dc_fib(n - 2)

    @rules
    def dc_cells(value):
        # a defined call with a RULE VARIABLE stages: the law holds the term
        yield eq(S.dc_stage(value)).to(dc_twice(value))
        # a GROUND defined call runs at construction and embeds its result
        yield eq(S.dc_fold()).to(dc_fib(10))
        # an op call with a rule variable stages the OP-CALL TERM, so the
        # law crosses the host per application and no effect fires here
        yield eq(S.dc_op_stage(value)).to(dc_stamp(value))
        # a ground op call runs NOW: the effect fires once, at construction
        yield eq(S.dc_op_ground()).to(dc_stamp(4))

    m += dc_cells

    # The construction-time record: exactly one effect, the ground one.
    assert fired == [4]

    # The stored bodies say which side of the split each call took,
    # asserted the structural way: the law itself is matched as a pattern.
    assert len(m[S["="](S.dc_stage(V.v), S.dc_twice(V.w))]) == 1
    assert m[S["="](S.dc_fold(), V.b)][0].b == 55
    assert len(m[S["="](S.dc_op_stage(V.v), S.dc_stamp(V.w))]) == 1
    assert m[S["="](S.dc_op_ground(), V.b)][0].b == 40

    # And every law answers.
    assert m.eval(S.dc_stage(6)) == [12]
    assert m.eval(S.dc_fold()) == [55]
    assert m.eval(S.dc_op_stage(6)) == [60]
    assert m.eval(S.dc_op_ground()) == [40]
    # The staged op crossed the host at APPLICATION time, with the bound value.
    assert fired == [4, 6]

    # ---- inside an OP body (host) ----

    @m.reads
    def dc_reenter(x: int) -> int:
        # a define inside an op RE-ENTERS the engine, a full driving-lane
        # call from within a callback
        [answer] = dc_twice(x)
        return answer

    assert m.eval(S.dc_reenter(21)) == [42]

    @m.writes
    def dc_hostside(x: int) -> int:
        # an op inside an op stays in host: plain Python, zero crossings
        return dc_stamp(x) + 1

    assert m.eval(S.dc_hostside(2)) == [21]
    assert fired == [4, 6, 2]


#: Inferences this twin spends, its own tripwire.
#: PRICED 2026-08-25 on landing, tools/twin_coverage.py on the pair;
#: the release measure re-prices with the corpus.
#: RE-PINNED 2026-08-25, 63350 to 63326, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: ENVELOPED 2026-08-26 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-PINNED 2026-09-01 on the operator-protocol tree. Ten fresh full-lane
#: observations had no spread, and the serial min-of-three confirmed the point
#: [measured: twin minimum 46113 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch11-python-as-a-notation/06-door_combinations.metta;
#: fixture=operator-protocol tree after python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10; commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 46113 to 49921 (+3808), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 49921 to 51017 (+1096), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 51017 to 51151 (+134), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 51151 to 51161 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 51161 to 47679 (-3482), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 47679 to 48289 (+610), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 48289 to 48358 (+69), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 48358 to 48110 (-248), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 48110 to 48099 (-11), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 48099 to 48138 (+39), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 48099 to 48568 (+469), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 48568 to 48418 (-150), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 48418 to 48479 (+61), the module boundary merged with
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
#: RE-PINNED 2026-09-08, 48138 to 48213 (+75), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 48213 to 48539 (+326), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
BUDGET = 48539

#: OVERRUN 2026-09-07, 27600: it proves seventeen claims where the example
#: states four: the example's own comment leaves the HOST half of the nesting
#: matrix to this side, and that half is the rules bundle, the op bodies and
#: the construction-time fold. Measured 48289 against a ceiling of 20724; a
#: minimal twin of this example costs 8007, inside the ceiling's 20724, so the
#: distance is this twin's own program [measured 2026-09-07: one fresh process
#: per side; command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-08, 27600 to 27742 (+142): the module boundary merged with
#: trunk (refactor/engine-and-libraries-as-modules at b64291369): the twin's
#: host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine; every
#: crossing this twin makes pays it and the example pays none. Measured 48479
#: against a ceiling of 48337; a minimal twin costs 7956 against the band's
#: 20737, within that ceiling, so the rest is this twin's own program
#: [measured 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: OVERRUN 2026-09-09, 27742 to 27803 (+61): the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved; every crossing this twin makes pays it and
#: the example pays none. Measured 48539 against a ceiling of 48478; a minimal
#: twin costs 7954 against the band's 20736, within that ceiling, so the rest
#: is this twin's own program [measured 2026-09-09: one fresh process per
#: side; command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
OVERRUN = 27803

#: DIVERGED 2026-09-07, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 17 the example does not (5 :, 6 =, 6 annotation): the twin is
#: an ordinary Python program and its body lowers to the engine's own forms: a
#: match statement is ONE equation whose body is a case tower where the example
#: writes one clause per arm, a named intermediate is a let* the original does
#: not have, a Python truth test wraps its condition in py-truthy, and the
#: annotations and docstrings that come with it are stored beside them
#: [measured 2026-09-07: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "522dd623c9129b776ac46ad0e3f1d6a2071ed06beee8bb19e9ad8b811b002e34"
