"""examples/ch08-data/08-01-atoms-lists-and-folds/08-alpha_member.metta in Python: membership modulo renaming.

`is-alpha-member` asks whether a list holds a term that is the same as the one
you have UP TO the names of its variables, so `(f $x)` is a member of
`((f $y) (g $z))` while Python's own `in`, which compares structurally, says it
is not. That difference is the whole subject, so the claims go to the operation
itself and the two spellings are put side by side once to show where they part.

Python does have the relation, as the atom's own `alpha_eq` method, so the
Python route is `any(atom.alpha_eq(needle) for atom in haystack)` and it agrees
with the operation. What Python does not have is `in` meaning that: `in` on an
expression is structural by design, because matching membership is the space
door's job.

Every question is the operation CALLED. Half of these needles carry variables
and the call still answers the verdict, because what those variables bound is
the parallel row face on the same view rather than a competing answer.

The cases walk the edges: an empty list, a variable against ground terms, a
ground term, nested structure, a repeated variable that must repeat in the
match too, differing arities, numbers, and the empty expression as a member.
"""

from metta import Expression, S, V


def twin(m):
    """Ask about membership for twenty-two shapes of needle and haystack."""

    def holds(needle, haystack):
        """Whether `haystack` holds a term alpha-equal to `needle`."""
        return m.fn.is_alpha_member(needle, haystack).one()

    letters = S.a(S.b, S.c)
    nothing = Expression(())

    assert not holds(S.x, nothing)             # (is-alpha-member x ()) is false
    assert not holds(V.x, letters)             # a variable is not one of a b c
    assert holds(S.a, letters)
    assert not holds(S.d, letters)

    # Alpha-equivalence: the variable names differ and the structure does not.
    two_shapes = Expression((S.f(V.y), S.g(V.z)))
    assert holds(S.f(V.x), two_shapes)         # (is-alpha-member (f $x) ((f $y) (g $z)))
    assert holds(S.f(V.x), Expression((S.f(V.y), S.f(V.y))))

    # The same relation, in Python: it is the atom's own method, and it agrees.
    assert any(atom.alpha_eq(S.f(V.x)) for atom in two_shapes)
    # `in` is STRUCTURAL by design, which is where the two spellings part.
    assert S.f(V.x) not in two_shapes

    # Nested structure, and a repeated variable that must repeat in the match.
    assert holds(S.f(S.g(V.x), V.y), Expression((S.f(S.g(V.a), V.b), S.h(V.c, V.d))))
    assert holds(S.f(S.g(V.x), V.x), Expression((S.f(S.g(V.a), V.b), S.f(S.g(V.c), V.c))))

    # Different arities never match.
    assert not holds(S.f(V.x), Expression((S.f(V.x, V.y), S.g(V.z))))

    numbers = Expression((1, 2, 42, 3))
    assert holds(42, numbers)
    assert not holds(99, numbers)

    assert holds(Expression((1, V.x)), Expression((Expression((1, 2)), Expression((3, 4)))))
    assert not holds(Expression((1, V.x)), Expression((Expression((2, 3)), Expression((4, 5)))))

    assert holds(S.a, S.a(S.b, S.a, S.c))      # more than one occurrence
    assert holds(S.f(V.x, V.y), Expression((S.f(V.a, V.b), S.f(V.c, V.d))))

    assert holds(S.a, S.a())                   # a single-element list
    assert not holds(S.b, S.a())

    # Every element is a variable, and so is the needle.
    assert holds(V.x, Expression((V.y, V.z, V.w)))

    assert holds(S.a(S.b(S.c(V.x))), Expression((S.a(S.b(S.c(V.d))), S.e(V.f))))
    assert not holds(S.f(V.x), Expression((S.g(V.y), S.h(V.z))))

    # The empty expression is an ordinary member.
    assert holds(nothing, Expression((nothing, S.a, S.b)))
    assert not holds(nothing, S.a(S.b, S.c))

    # The example closes by printing the pattern and the verdict for a fresh
    # needle, which is one variable against a list of three symbols.
    pattern = S.hi(S.name, S.boss)             # (println! (pattern:- $pat))
    print(pattern, holds(V.new, pattern))      # (hi name boss) True


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 18473 to 18910, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 18910 to 18911, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 18911 to 18957, on the release tree:
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
#: RE-PINNED 2026-08-25, 18957 to 18959, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 18959 to 19099 (+140), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 19099 to 22327 (+3228), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 22327 to 22281 (-46), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 22281 to 22395 (+114), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 22395 to 22827 (+432), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 22827 to 22938 (+111), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 22938 to 23710 (+772), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 23710 to 23642 (-68), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 23642 to 24060 (+418), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
BUDGET = 24060

#: OVERRUN 2026-09-07, 3600: it puts Python's own `in` beside `is-alpha-member`
#: at every claim, which is the difference the file is about. Measured 23710
#: against a ceiling of 20155; a MINIMAL twin of this example -- its own forms
#: stored and asked through the structured door, nothing else -- costs 23556
#: against the ceiling's 20155, so no twin of it fits the band at all [measured
#: 2026-09-07: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
OVERRUN = 3600
