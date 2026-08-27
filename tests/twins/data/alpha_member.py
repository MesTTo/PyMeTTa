"""examples/data/alpha_member.metta in Python: membership modulo renaming.

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
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 19099
