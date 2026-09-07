"""Purpose: examples/ch09-types/01-types.metta in Python: what a type is and where it lives.

Three groups of claims. Concrete types are declarations about SYMBOLS, so they
are atoms written into the space: there is no Python signature that says
`(: a A)`, because `a` is not a function, and `typed(x, T)` is the builder for
that declaration term. Function types are arrows, and the type variable in
`(-> $a $a)` is what Python's own type parameter says, so `mid` and `testf` are
ordinary generic functions and `@m.define` publishes the arrow their signatures
name.

`space.type(atom)` is the get-type accessor and answers the FIRST type, which
is every claim here but one: `x` is declared twice, and the whole answer set is
the form itself, evaluated.

Both function bodies select on a STRUCTURE, and Python's `match` statement is
MeTTa's own `case`: `mid` keeps only an argument shaped `(a b)` and `testf`
keeps only the symbol `at`. Measured on this engine, `case` unifies both ways,
so `mid(($a b))` answers `(a b)` exactly as the original's `let` does.
"""

from metta import Expression, S, V, Variable, arrow, ground, typed

#: The unconstrained type. Python's grammar cannot spell `%Undefined%`, so the
#: name takes the bracket; `Any` is its image in a DECLARING position, where
#: `typed` and `arrow` read it through the annotation table.
#:
#: The table is one-way, which is friction against P14.9: a twin comparing an
#: ANSWER against a type atom has no Python-type spelling for it, so the marked
#: name is written out. It should read `assert m.type(S.c) == Any`, with the
#: same table reading `Any` on the right of an equality as it already reads it
#: inside `arrow(...)` and `typed(...)`.
UNDEFINED = S["%Undefined%"]


def twin(m):
    """Declare, then ask, then declare a function and ask about its answers."""
    # Concrete types. Each declaration is a fact about a symbol.
    # (: a A) (: b B) (: A Type) (: x Letter) (: x Buchstabe)
    m += typed(S.a, S.A)
    m += typed(S.b, S.B)
    m += typed(S.A, S.Type)
    m += typed(S.x, S.Letter)
    m += typed(S.x, S.Buchstabe)

    # The type of an unbound variable is itself unknown: another variable.
    # !(test (get-type $a) $z)
    assert type(m.type(V.a)) is Variable
    # !(test (get-type a) A)
    assert m.type(S.a) == S.A
    # !(test (get-type b) B)
    assert m.type(S.b) == S.B
    # !(test (get-type c) %Undefined%)
    assert m.type(S.c) == UNDEFINED
    # !(test (get-type A) Type)
    assert m.type(S.A) == S.Type
    # !(test (get-type B) %Undefined%)
    assert m.type(S.B) == UNDEFINED

    # An expression's type is the expression of its parts' types, and a ground
    # value carries its own.
    # !(test (get-type (a b)) (A B))
    assert m.type(S.a(S.b)) == S.A(S.B)
    # !(test (get-type 42) Number)
    assert m.type(42) == S.Number
    # !(test (get-type "42") String)
    assert m.type(ground("42")) == S.String

    # Two declarations, two answers, so this one calls the relation: the
    # accessor answers the first type and the example collapses every one.
    # !(test (collapse (get-type x)) (Letter Buchstabe))
    assert m.fn.get_type(S.x) == [S.Letter, S.Buchstabe]

    @m.define
    def mid[T](x: T) -> T:
        """(: mid (-> $a $a)), and a body that keeps only an `(a b)`."""
        match x:
            case (S.a, S.b):
                return x

    # !(test (mid ($a b)) (a b))
    assert mid(Expression((V.a, S.b))) == [S.a(S.b)]

    # `testx` is a declaration and nothing else: no equation defines it, so
    # the arrow is the whole of what the file says about it.
    # (: testx (-> $a $b $a))
    m += typed(S.testx, arrow(V.a, V.b, V.a))
    # !(test (get-type (testx 1 "f")) Number)
    assert m.type(S.testx(1, ground("f"))) == S.Number

    # Nondeterministic types: `at` is both an A and a T, so a function
    # declared (-> $a $a) accepts it and answers a T.
    # (: at A) (: at T) (: t T)
    m += typed(S.at, S.A)
    m += typed(S.at, S.T)
    m += typed(S.t, S.T)

    @m.define
    def testf[T](x: T) -> T:
        """(: testf (-> $a $a)), and a body that answers only for `at`."""
        match x:
            case S.at:
                return S.t

    # !(test (testf at) t)
    assert testf(S.at) == [S.t]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11902 to 15626, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 15626 to 15639, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 15639 to 15569, on the release tree:
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
#: RE-PINNED 2026-08-25, 15569 to 15589, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 15589 to 15755 (+166), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 15755 to 15775 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 15775 to 14929 (-846), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 14929 to 14892 (-37), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 14892 to 14912 (+20), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 14912 to 15227 (+315), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 15227 to 15235 (+8), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 15235 to 15245 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 15245 to 14198 (-1047), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 14198 to 14594 (+396), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 14594 to 14637 (+43), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 14637 to 14568 (-69), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 14568 to 14558 (-10), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 14558

#: DIVERGED 2026-09-07, the example holds 2 atoms the twin does not (2 =) and
#: the twin holds 4 the example does not (2 =, 2 @doc): the twin is an ordinary
#: Python program and its body lowers to the engine's own forms: a match
#: statement is ONE equation whose body is a case tower where the example
#: writes one clause per arm, a named intermediate is a let* the original does
#: not have, a Python truth test wraps its condition in py-truthy, and the
#: annotations and docstrings that come with it are stored beside them
#: [measured 2026-09-07: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "4f06b3b0b63d4ce482888d911ea957db7add5eb9b29f5e028c321411051a6a3e"
