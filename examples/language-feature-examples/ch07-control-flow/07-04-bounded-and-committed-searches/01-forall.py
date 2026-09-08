"""Purpose: examples/ch07-control-flow/07-04-bounded-and-committed-searches/01-forall.metta in Python: a check over every answer.

`forall` runs its check on every answer its generator gives and stops at the
first one that fails. Both slots take a function name, a call with an unbound
argument, or a lambda, and the file walks every combination of the two.

The generator and the check are ordinary definitions and are written as ones:
`g`'s two clauses stack, because a literal default IS the head pattern for
that position, and `f`'s two clauses fix nothing at all, which stacking reads
as redefinition, so `f` goes through `@rules` instead. `P` is a computation
and compiles.

The lambdas are terms. A Python lambda inside a compiled body does lower to
the engine's own `|->`, but a definition whose BODY is a lambda cannot hand
one out as data: the lambda's parameter folds into the head's arity, so
`(below 2)` answers `(partial below (2))` and `arities("below")` is `[3]`
[re-measured 2026-08-24; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. Filed as residue against P14.4. So
the two lambdas are built at the term door, once each, and the `let` and `let*`
that bind them are Python name bindings, which is what a `let` is.

The comparison inside a built lambda is built by its WORD, `S.lt(V.v, limit)`,
because Python's four rich comparisons are the engine's total ORDER over two
atoms: none of them builds a term, and one against a Python int raises. The
wrapped check is `if_`, the keyword builder for stored code, which has the
arity the engine's `if` has.
Guarantees:
  - TRUE used here is a package value rather than a local reconstruction
    [tested: test_the_canonical_atoms_are_public_values; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, S, V, equation, if_, rules

#: `(|-> ($x) (g $x))`, the generator lambda the original writes inline.
GENERATOR = S["|->"]((V.x,), S.g(V.x))

#: `(|-> ($x) (* 100 (g $x)))`, the generator that scales what it gives.
SCALED = S["|->"]((V.x,), 100 * S.g(V.x))


def below(limit):
    """`(|-> ($v) (< $v <limit>))`, the check the original writes inline.

    The top rung builds the comparison with the operator, `V.v < limit`, and
    hands the lambda out of a definition:

        @m.define
        def below(limit):
            return lambda v: v < limit

    Neither works. The four rich comparisons are the engine's total ORDER
    over two atoms, so `V.v < 2` raises `'<' not supported between instances
    of 'Variable' and 'int'` instead of building `(< $v 2)`, and the term is
    built by its operator WORD instead. And a definition whose body IS a
    lambda folds the lambda's parameter into the head's arity, so `(below 2)`
    answers `(partial below (2))` and `arities("below")` is `[3]`.
    Residue: P14.4.
    """
    return S["|->"]((V.v,), S.lt(V.v, limit))


def twin(m):
    """Check every answer of a generator, nine ways of naming the two."""

    # The top rung stacks two clauses under one head, the way `g` does below:
    #
    #     @m.define(name="f")
    #     def f_one(): return 1
    #     @m.define(name="f")
    #     def f_two(): return 2
    #
    # A literal DEFAULT is what makes stacked clauses stack, so two clauses
    # fixing nothing have no `@m.define` spelling at all. Re-measured
    # 2026-08-24: rebinding one Python name under one MeTTa name stores only
    # the LAST equation, and two different Python functions carrying one
    # `name=` raise `IndexError: list assignment index out of range` from
    # `metta/_define_twins.py` `replace_twin_clause`. The crash is a defect on
    # its own. `@rules` is the door that writes a clause set without deriving a
    # first-match guard; what it cannot do is take Python SYNTAX for its
    # bodies. Residue: P14.4.
    @rules
    def f():
        # (= (f) 1) (= (f) 2)
        yield equation(S.f()).to(1)
        yield equation(S.f()).to(2)

    m += f

    # A literal default is the head PATTERN for that position, so the
    # parameter itself never appears in the equation and the underscore says
    # so to a Python reader as well. Both clauses name the head, because one
    # head with two clauses needs two Python functions and only one of them
    # could carry the name implicitly.
    @m.define(name="g")
    def g_one(_n=1):
        # (= (g 1) 1)
        return 1

    @m.define(name="g")
    def g_two(_n=2):
        # (= (g 2) 2)
        return 2

    # The def's own name IS the head, so `name=` is for heads Python cannot
    # spell, and a CAPITALISED function head is one of them here: `def P`
    # trips the N family, whose burn-down maximum is full, so the identifier
    # this repository's gate accepts is the lowercase one and the head is
    # named [measured 2026-08-24: `GATE_ONLY=1 sh check.sh` failed with
    # "P0.13 suppression burn-down increased (observed, maximum): {'N': (37, 35)}";
    # commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
    @m.define(name="P")
    def below_two(x: int) -> bool:
        # (= (P $X) (< $X 2))
        return x < 2

    # Arg-free generator function plus check function.
    # !(test (forall (f) P) false)
    assert m.eval(S.forall(S.f(), S.P)) == [False]

    # Arg-ful generator function plus check function.
    # !(test (forall (g $x) P) false)
    assert m.eval(S.forall(S.g(V.x), S.P)) == [False]

    # Arg-ful generator lambda plus check function. The `let` that names the
    # lambda is a Python name binding, which is what a `let` is.
    # !(test (let $genlambda (|-> ($x) (g $x)) (forall ($genlambda $z) P)) false)
    genlambda = GENERATOR
    assert m.eval(S.forall((genlambda, V.z), S.P)) == [False]

    # Arg-ful generator function plus check lambda.
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    checklambda = below(2)
    assert m.eval(S.forall(S.g(2), checklambda)) == [False]
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 1) $checklambda)) true)
    assert m.eval(S.forall(S.g(1), checklambda)) == [True]
    # !(test (let $checklambda (|-> ($v) (< $v 2)) (forall (g 2) $checklambda)) false)
    assert m.eval(S.forall(S.g(2), below(2))) == [False]

    # Arg-ful generator lambda plus check lambda; a `let*` is two bindings.
    # !(test (let* (($checklambda (|-> ($v) (< $v 2)))
    #               ($genlambda (|-> ($x) (g $x))))
    #              (forall ($genlambda $z) $checklambda))
    #        false)
    assert m.eval(S.forall((genlambda, V.z), checklambda)) == [False]

    # Lambdas as arguments directly.
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 2))) false)
    assert m.eval(S.forall((GENERATOR, V.z), below(2))) == [False]
    # !(test (forall ((|-> ($x) (g $x)) $z) (|-> ($v) (< $v 20))) true)
    assert m.eval(S.forall((GENERATOR, V.z), below(20))) == [True]

    # A lambda wrapped in a syntactic construct is still a lambda.
    wrapped_2 = if_(TRUE, below(2), 42)
    wrapped_20 = if_(TRUE, below(20), 42)
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 2)) 42)) false)
    assert m.eval(S.forall((GENERATOR, V.z), wrapped_2)) == [False]
    # !(test (forall ((|-> ($x) (g $x)) $z) (if True (|-> ($v) (< $v 20)) 42)) true)
    assert m.eval(S.forall((GENERATOR, V.z), wrapped_20)) == [True]
    # !(test (forall ((|-> ($x) (* 100 (g $x))) $z) (if True (|-> ($v) (< $v 20)) 42)) false)
    assert m.eval(S.forall((SCALED, V.z), wrapped_20)) == [False]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 52958 to 51945, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 51945 to 51875, on the release tree:
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
#: RE-PINNED 2026-08-25, 51875 to 51631, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 51631 to 52689 (+1058), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 52689 to 51941 (-748), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 51941 to 51429 (-512), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 51429 to 27725 (-23704), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 27725 to 27481 (-244), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 27481 to 27513 (+32), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 27513 to 27647 (+134), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 27647 to 27336 (-311), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 27336 to 27560 (+224), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 27560 to 27814 (+254), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 27814 to 21781 (-6033), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 21781 to 21989 (+208), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 21989 to 22032 (+43), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 22032 to 21968 (-64), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 21968 to 21988 (+20), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 21968 to 22031 (+63), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 22031 to 22041 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 22041 to 22009 (-32), the module boundary merged with
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
#: RE-PINNED 2026-09-08, 21988 to 22021 (+33), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 22021 to 22027 (+6), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 22027 to 22037 (+10), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 22009 to 22684 (+675), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 22684 to 22624 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 22624 to 22697 (+73), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 22009 to 22203 (+194), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 22203 to 22822 (+619), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 22822 to 23415 (+593), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +718 against the trunk's own pin of 22697 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining -125 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 23415

#: DIVERGED 2026-09-07, the example holds 0 atoms the twin does not (none) and
#: the twin holds 1 atom the example does not (1 :): a Python annotation IS a (:
#: name (-> ...)) row and a docstring on a compiled function IS an (@doc name
#: ...) row, so the twin's space carries the declarations and the documentation
#: its own file states where the example leaves both unsaid [measured
#: 2026-09-07: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "1bd292927fedefa2ff4c74c881063fdc8d7dbe53e3c3e52f1b2fbf415ed9108d"
