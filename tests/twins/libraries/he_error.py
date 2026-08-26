"""examples/libraries/he_error.metta in Python: errors as data, and the railway.

`catch`, `if-error` and `return-on-error` are HE's error algebra and the
subject here, so they stay named; the example's `let` around them is Python's
own assignment, spelled as a one-element unpacking so the twin says out loud
that exactly one answer is expected.

Iterating the answer view is what hands an error atom over AS DATA. The scalar
doors take the loud reading and raise, which is right for a caller that wanted
a value and wrong for this file, whose claims are about the error atoms
themselves; unpacking iterates, so it keeps them.

Every arithmetic term is built by its operator WORD, `S.add` for `+` and
`S.truediv` for `/`, because these calls are terms handed to `catch` and
`if-error` rather than sums to compute.

Four kinds of nothing-went-right are drawn apart here. An operand whose type
RULES THE CALL OUT is already an error atom, so if-error sees one with no catch
in between; an operand whose type merely does not DECIDE is not an error, and
the call is left as written, which is upstream's NoReduce; a HOST error, the
kind the language has no atom for, needs the catch; and integer division by
zero already is error data.
"""

from metta import G, S, V, lib, typed

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass after the conformance
#: answer updates: tools/twin_coverage.py --measure min-of-3, identical
#: across two fresh rounds on p14-integration at the store-wave merge.
#: RE-PINNED 2026-08-25, 37310 to 37481, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 37481 to 37466, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 37466 to 37484, on the release tree:
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
#: RE-PINNED 2026-08-25, 37484 to 37521, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 37521 to 29260 (-8261), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=WORKTREE].
BUDGET = 29260


#: The error atom the last three claims are about.
BAD_TYPE = S.Error(5, S.BadType)


def twin(m):
    """Catch what needs catching, then route four answers through if-error."""
    m += lib.he

    if_error = m.fn.if_error

    [caught] = m.fn.catch(S.add(40, 2))
    assert if_error(caught, S.Error, caught) == [42]

    # An operand whose type RULES THE CALL OUT is an error atom already: `a` is
    # declared a String and the arrow says Number.
    m += typed(S.a, S.String)
    assert if_error(S.add(40, S.a), S.Error, S.fine) == [S.Error]

    # An operand whose type merely does not DECIDE is not an error. The call is
    # left as written, so if-error takes its second branch.
    assert if_error(S.add(40, S.undeclared_operand), S.Error, S.fine) == [S.fine]

    # catch is for a HOST error, the kind the language has no atom for. Two
    # unbound arithmetic operands are one.
    [host] = m.fn.catch(S.add(V.left, V.right))
    assert if_error(host, S.Error, host) == [S.Error]

    # Integer division by zero already is Error data, so it needs no catch.
    assert if_error(S.truediv(40, 0), S.Error, S.fine) == [S.Error]

    assert if_error(BAD_TYPE, G("Error!"), G("No error")) == [G("Error!")]

    # return-on-error KEEPS one `return` around a passed-through error for
    # an enclosing function frame to consume — the reference's own body,
    # conformance increment 2 — and answers its second argument for
    # anything else.
    return_on_error = m.fn.return_on_error
    assert return_on_error(BAD_TYPE, 6) == [S["return"](BAD_TYPE)]
    assert return_on_error(5, 6) == [6]
