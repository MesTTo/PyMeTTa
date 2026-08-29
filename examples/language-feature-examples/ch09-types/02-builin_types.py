"""Purpose: examples/ch09-types/02-builin_types.metta in Python: the library's declared types.

Thirty-six names, imported from `lib_builtin_types` and read back. Nothing is
defined here, only asked, so every claim is one line: `space.type(atom)` is the
get-type accessor, and the arrow it should answer is built from PYTHON TYPES
through the one conversion table, `arrow(int, int, int)` for
`(-> Number Number Number)`, so the numeric surface is one shape said many
times and no type atom is spelled by hand.

The heads being asked about are the operators themselves, and the operator WORD
table names each one at the attribute door: `S.add` IS `+` and `S.le` IS `<=`,
which is rung 4 of the descent ladder rather than rung 5's bracket. Three heads
have no word and keep the bracket, because `and`, `or` and `not` are Python
keywords the factory cannot spell as attributes. `truediv` is the roster's one
flagged pair (appendix 13), and it is the shipped word for `/`.

Two of the arrows carry a type VARIABLE, `(-> $a $a Bool)` for `==` and `!=`,
which is what says both arguments share one type. A variable's identity is
fresh on every answer, so those two are compared with `alpha_eq`, the relation
the law itself uses for answer equivalence, rather than with `==`.

The import itself is an evaluated directive, and its space argument is the
handle: a space crosses a term position as itself, so no `&self` symbol
appears. There is still no Python verb for importing a library (friction,
P14.13).
"""

from metta import S, V, arrow, lib


def twin(m):
    """Import the library, then read every arrow it declares."""
    binary = arrow(int, int, int)
    unary = arrow(int, int)
    compare = arrow(int, int, bool)
    predicate = arrow(int, bool)
    one_type = arrow(V.a, V.a, bool)
    over_expression = arrow(V.a, int)
    logical = arrow(bool, bool, bool)

    # !(import! &self (library lib_builtin_types))
    m += lib.builtin_types

    # Arithmetic: five heads, one arrow.
    # !(test (get-type +) (-> Number Number Number)), and four of the same shape
    assert m.type(S.add) == binary
    assert m.type(S.sub) == binary
    assert m.type(S.mul) == binary
    assert m.type(S.truediv) == binary
    assert m.type(S.mod) == binary

    # Comparison: four heads, one arrow.
    # !(test (get-type <) (-> Number Number Bool)), and three of the same shape
    assert m.type(S.lt) == compare
    assert m.type(S.le) == compare
    assert m.type(S.gt) == compare
    assert m.type(S.ge) == compare

    # ONE type variable, twice: == compares two things of one type, and
    # refuses two of different KNOWN types.
    # !(test (get-type ==) (-> $a $a Bool))
    # !(test (get-type !=) (-> $a $a Bool))
    assert m.type(S.eq).alpha_eq(one_type)
    assert m.type(S.ne).alpha_eq(one_type)

    # Mathematics: the hyphenated names take rung 4's underscore map.
    # !(test (get-type pow-math) (-> Number Number Number)), and eighteen more
    assert m.type(S.pow) == binary
    assert m.type(S.sqrt_math) == unary
    assert m.type(S.abs_math) == unary
    assert m.type(S.log_math) == binary
    assert m.type(S.trunc_math) == unary
    assert m.type(S.ceil_math) == unary
    assert m.type(S.floor_math) == unary
    assert m.type(S.round_math) == unary
    assert m.type(S.sin_math) == unary
    assert m.type(S.asin_math) == unary
    assert m.type(S.cos_math) == unary
    assert m.type(S.acos_math) == unary
    assert m.type(S.tan_math) == unary
    assert m.type(S.atan_math) == unary
    assert m.type(S.min_atom).alpha_eq(over_expression)
    assert m.type(S.max_atom).alpha_eq(over_expression)
    assert m.type(S.min) == binary
    assert m.type(S.max) == binary
    assert m.type(S.exp) == unary

    # The float predicates.
    # !(test (get-type isnan-math) (-> Number Bool))
    # !(test (get-type isinf-math) (-> Number Bool))
    assert m.type(S.isnan_math) == predicate
    assert m.type(S.isinf_math) == predicate

    # The boolean operators. Three of the four are Python keywords, so they
    # take rung 5's bracket; `xor` is an ordinary name with no operator word.
    # !(test (get-type and) (-> Bool Bool Bool)), and three more
    assert m.type(S["and"]) == logical
    assert m.type(S["or"]) == logical
    assert m.type(S["not"]) == arrow(bool, bool)
    assert m.type(S.xor) == logical


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 51121 to 51752, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 51752 to 51753, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 51753 to 51755, on the release tree:
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
#: RE-PINNED 2026-08-26, 51755 to 52951 (+1196), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 52951
