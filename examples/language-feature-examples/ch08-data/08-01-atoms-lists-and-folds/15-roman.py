"""Purpose: examples/ch08-data/08-01-atoms-lists-and-folds/15-roman.metta in Python: lib_roman, walked end to end.

Every claim here is about a lib_roman function, so every one names it. Three
families: the higher-order maps and folds, the nine set operations whose names
are drawn from the shapes of their Venn diagrams, and the composition
combinators. Then the inverses: `let` unifying a CALL against a value so the
function runs BACKWARDS, where `(let (head $x) (1 2 3) $x)` answers 1 because
head, run in reverse, says what its argument's first element must be. `solve`
is the door for that shape, and its answer template takes the variables the
PATTERN introduces as well as the subject's, which is what this reading needs.

Six of the nine set operations carry VARIABLES in their arguments, and the
call answers the resulting term all the same. Two of those answers carry a
fresh variable, which is why they are compared with `alpha_eq` rather than
`==`: the engine renames variables and the claim is about the shape, not the
name.

An engine function may be named with an ampersand, and three of these are:
`&&&`, `&^&` and the Venn family's punctuation take the bracket, which is the
exact door for a name Python's grammar cannot spell. The arithmetic the maps
and folds are GIVEN takes the other door in the same ladder: `+` and `*` have
words, so `S.add(1)` is the partial application `(+ 1)` and `S.add` alone is
the operator mentioned by name.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, lib


def twin(m):
    """Import lib_roman, then exercise its three families and its inverses."""
    m += lib.roman

    # Higher-order functions.
    assert m.fn.map_flat(S.add(1), (1, 2, 3)) == [Expression((2, 3, 4))]
    assert m.fn.map_nested(S.add(1), (1, (2, 3))) == [
        Expression((2, Expression((3, 4))))
    ]
    assert m.fn.fold_flat(S.add, 0, (1, 2, 3)) == [6]
    assert m.fn.foldr_flat(S.cons, (), (1, (2, 3), 4)) == [
        Expression((1, Expression((2, 3)), 4))
    ]
    assert m.fn.fold_nested(S.add, 0, (1, (2, 3))) == [6]

    # Set operations. The three families are intersection (/=\), difference
    # (\=) and union (\=/), each in a unifying, an equal and an alpha variant.
    #
    # Six of the nine carry a MeTTa variable in an argument, and the call
    # answers the resulting term all the same.
    assert m.fn["/=\\"]((1, 2, V.a), (2, 3, 4)) == [Expression((2, 2))]
    assert m.fn["/==\\"]((1, 2, 3), (2, 3, 4)) == [Expression((2, 3))]
    unified = m.fn["/=a\\"]((1, 2, V.a), (2, V.a, 4)).one()
    assert unified.alpha_eq(Expression((2, V.a)))

    assert m.fn["\\="]((1, 2, 3), (V.a, 3, 4)) == [Expression((2,))]
    assert m.fn["\\=="]((1, 2, 3), (2, 3, 4)) == [Expression((1,))]
    assert m.fn["\\=a"]((1, 2, V.a), (2, V.a, 4)) == [Expression((1,))]

    assert m.fn["\\=/"]((1, 2, 3), (V.a, 3, 4)) == [Expression((2, 1, 3, 4))]
    assert m.fn["\\==/"]((1, 2, 3), (2, 3, 4)) == [Expression((1, 2, 3, 4))]
    joined = m.fn["\\=a/"]((1, 2, V.a), (2, V.a, 4)).one()
    assert joined.alpha_eq(Expression((1, 2, V.a, 4)))

    # Composition.
    assert m.fn["."](S.add(1), S.mul(2), 1) == [3]
    assert m.fn[".:"](S.add(1), S.add, 2, 3) == [6]
    assert m.fn["&&&"](S.add(2), S.mul(2), 1) == [Expression((3, 2))]

    # A branch that answers nothing prunes, so the fan-out keeps one answer.
    @m.define
    def mfail(x):  # noqa: ARG001  -- the branch answers nothing whatever it is given, which is what makes it prune
        yield from ()

    assert list(m.fn["&^&"](S.add(1), S.mfail(), 1)) == [2]

    # Reverse function matching, which is `solve`: the PATTERN wins its
    # variables from what the subject produces, so the call runs backwards and
    # the bindings come back projected by name.
    taken = m.solve(S["@"](V.lst, S.cons(V.h, V.t)), (1, 2, 3))
    assert (taken.lst, taken.h, taken.t) == (Expression((1, 2, 3)), 1, Expression((2, 3)))
    assert m.solve(S.head(V.x), (1, 2, 3)).x == 1
    assert m.solve(S.tail(V.xs), (1, 2, 3)).xs == Expression((2, 3))
    assert m.solve(S.mylast(V.x), (1, 2, 3)).x == 3
    assert m.solve(S.init(V.xs), (1, 2, 3)).xs == Expression((1, 2))
    split = m.solve(S.rcons(V.xs, V.x), (1, 2, 3))
    assert (split.xs, split.x) == (Expression((1, 2)), 3)

    # prog1 answers its first form, progn its last; both run both.
    assert m.fn.prog1(S.add(1, 1), S.add(2, 2)) == [2]
    assert m.fn.progn(S.add(1, 1), S.add(2, 2)) == [4]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 763487 to 763867, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 763867 to 763366, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 763366 to 763336, on the release tree:
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
#: RE-PINNED 2026-08-25, 763336 to 763218, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 763218 to 800064 (+36846): ~30 definitions each
#: paying 5c731b03's per-translated-equation specializer bookkeeping
#: (ai-brief-p14-specializer-translation-tax), plus 6917bef7's small
#: share and layout [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 800064 to 799702 (-362), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 799702 to 799574 (-128), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 799574 to 793257 (-6317), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 793257 to 498469 (-294788), the compiled-language
#: batch: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 498469 to 498300 (-169), the subtract-atom primitive
#: and Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 498300 to 498370 (+70), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 498370 to 501255 (+2885), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 501255 to 501459 (+204), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 501459 to 501581 (+122), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 501581 to 320265 (-181316), the one pricing pass at
#: the 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 320265 to 320547 (+282), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 320547 to 320587 (+40), the merges between this lane's
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
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 320587

#: OVERRUN 2026-09-07, 17700: it names every lib_roman function at every claim
#: and runs the backwards `let` inverses beside them. Measured 320547 against a
#: ceiling of 302881; a MINIMAL twin of this example -- its own forms stored
#: and asked through the structured door, nothing else -- costs 313903 against
#: the ceiling's 302881, so no twin of it fits the band at all [measured
#: 2026-09-07: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
OVERRUN = 17700

#: DIVERGED 2026-09-07, the example holds 9 atoms the twin does not (9 =) and
#: the twin holds 9 the example does not (9 =): the twin is an ordinary Python
#: program and its body lowers to the engine's own forms: a match statement is
#: ONE equation whose body is a case tower where the example writes one clause
#: per arm, a named intermediate is a let* the original does not have, a Python
#: truth test wraps its condition in py-truthy, and the annotations and
#: docstrings that come with it are stored beside them [measured 2026-09-07:
#: the two stored-atom surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "84a06c2dd74dcee6885a630031d4a25b42a5d68fc42ef679dddfb50551eb3348"
