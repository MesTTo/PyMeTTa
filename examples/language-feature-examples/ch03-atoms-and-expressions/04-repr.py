"""Purpose: examples/ch03-atoms-and-expressions/04-repr.metta in Python: how an atom prints.

`repr` answers the engine's own text for an atom, and in Python that text is
what `str` answers: `str(S.A(S.B(S.C)))` is `(A (B C))`. So the six claims are
six `str` calls over atoms built at the `S.` door, and the loop under them
states the seam claim the six rest on, that the engine's `repr` says the same
thing about the same atoms.

Expected printed output is Python text. The atom being printed still crosses
through `ground` when it is a MeTTa String value.

Two spellings are worth naming. A plain Python tuple builds an expression, so
`(, B , C ,)` is `(S[","], S.B, S[","], S.C, S[","])`, five children under no
head; the subscript is there because `,` is not a Python identifier, which is
the only thing that form is for. And `()` is the empty expression, which
Python's own empty tuple already encodes to.

What no Python program here can say is the other half of a round trip: that
the TEXT `2025_12_12` READS as a symbol rather than as a number. That half is
the reader, whose input is MeTTa source, so it is residue against P14.1, the
same wall ch03-atoms-and-expressions/05-parse.metta's first five forms meet.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

from metta import S, ground

#: Every atom of the original, beside the text `repr` prints it as.
PRINTED = [
    (ground(42), "42"),
    (ground("42"), '"42"'),
    (S.A(S.B(S.C)), "(A (B C))"),
    (S.A((S[","], S.B, S[","], S.C, S[","])), "(A (, B , C ,))"),
    (S["2025_12_12"], "2025_12_12"),
    ((), "()"),
]


def twin(m):
    """Print six atoms, and check the engine prints them the same way."""
    number, text, nested, commas, underscores, unit = (atom for atom, _ in PRINTED)

    # !(test (repr 42) "42")
    assert str(number) == "42"
    # A string atom prints WITH its quotes, which is what makes the text read
    # back as the same string rather than as a symbol.
    # !(test (repr "42") "\"42\"")
    assert str(text) == '"42"'
    # !(test (repr (A (B C))) "(A (B C))")
    assert str(nested) == "(A (B C))"
    # !(test (repr (A (, B , C ,))) "(A (, B , C ,))")
    assert str(commas) == "(A (, B , C ,))"
    # A symbol that looks like a date is a symbol, and prints unchanged.
    # !(test (repr 2025_12_12) "2025_12_12")
    assert str(underscores) == "2025_12_12"
    # !(test (repr ()) "()")
    assert str(unit) == "()"

    # Python's `str` is the engine's `repr`: the same atom, the same text,
    # either side of the seam.
    assert [m.fn.repr(atom).one() for atom, _ in PRINTED] == [text for _, text in PRINTED]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 2107 to 2221, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 2221 to 2222, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 2222 to 2234, on the release tree:
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
#: RE-PINNED 2026-09-01, 2234 to 2463 (+229), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 2463 to 2451 (-12), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 2451
