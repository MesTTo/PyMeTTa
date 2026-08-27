"""Purpose: examples/types/matchtypes.metta in Python: types compared as ordinary atoms.

`match-types` takes two TYPES and two branches and answers one of them. Nothing
about it is special: a type is an atom, `==` compares atoms, and the whole
function is one conditional. `match-type-or` is built on top and answers True
when the two types agree and its own value otherwise.

Both are `@m.rules` equations rather than `@m.define` functions, because this
engine already answers both names (`match-types` at arity 5, `match-type-or` at
arity 3) and the definitional decorator refuses a name the space answers.
`@m.rules` is the door that lands bare coexisting equations deliberately, the
parameters ARE the equations' variables, and a rules body EXECUTES, so its
terms are built rather than lowered.

The equality is therefore built by its WORD, `S.eq(a, b)` for `(== $A $B)`,
where Python's own `==` between two atoms is a structural test that answers a
bool. `if_` is the keyword builder for a stored `if`, and it takes the arity
the engine's `if` has.
"""

from metta import FALSE, TRUE, S, equation, if_


def twin(m):
    """Define the two functions, then compare four pairs of types."""

    @m.rules
    def comparison(left, right, then, otherwise, value):
        """The example's two equations, over five shared rule variables."""
        # (= (match-types $A $B $Then $Else) (if (== $A $B) $Then $Else))
        yield equation(S.match_types(left, right, then, otherwise)).to(
            if_(S.eq(left, right), then, otherwise)
        )
        # (= (match-type-or $value $type1 $type2)
        #    (match-types $type1 $type2 True $value))
        yield equation(S.match_type_or(value, left, right)).to(
            S.match_types(left, right, TRUE, value)
        )

    # !(match-types Atom Atom "Matched!" "Didn't match")
    assert m.fn.match_types(S.Atom, S.Atom, S.yes, S.no) == [S.yes]
    # !(match-types Atom Number "Matched!" "Didn't match")
    assert m.fn.match_types(S.Atom, S.Number, S.yes, S.no) == [S.no]

    # The two types agree, so the value never gets a say; when they differ it
    # is the answer.
    # !(test (match-type-or True Number Number) True)
    assert m.fn.match_type_or(TRUE, S.Number, S.Number) == [True]
    # !(test (match-type-or False Number Number) True)
    assert m.fn.match_type_or(FALSE, S.Number, S.Number) == [True]
    # !(test (match-type-or True Number Bool) True)
    assert m.fn.match_type_or(TRUE, S.Number, S.Bool) == [True]
    # !(test (match-type-or False Number Bool) False)
    assert m.fn.match_type_or(FALSE, S.Number, S.Bool) == [False]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 9950 to 10064, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 10064 to 10067, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 10067 to 10079, on the release tree:
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
#: RE-PINNED 2026-08-25, 10079 to 10091, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 10091 to 10096 (+5), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 10096
