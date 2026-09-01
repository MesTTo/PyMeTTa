"""Purpose: examples/ch09-types/05-meta_types.metta in Python: the metatype IS the Python class.

MeTTa's four kinds are four Python classes here, so `get-metatype` and Python's
own `type()` answer the same question, and this twin asks both of every atom the
example asks about.

One atom answers differently on the two sides, and it is the interesting one:
`+` is a Symbol as Python holds it, because a name built at the operator WORD
door is just a name, and Grounded as the engine reads it, because the engine
resolves that name to a builtin operation. The class is what the atom IS; the
metatype is what the engine MAKES of it.
"""

from metta import Expression, Grounded, S, Symbol, V, Variable, ground


def twin(m):
    """Ask both sides for the metatype of one atom of every kind."""
    metatype = m.fn.get_metatype

    # An expression, however it was built.
    # !(test (get-metatype (foo 1 2)) Expression)
    assert type(S.foo(1, 2)) is Expression
    assert metatype(S.foo(1, 2)) == [S.Expression]
    # !(test (get-metatype (a b)) Expression)
    assert type(S.a(S.b)) is Expression
    assert metatype(S.a(S.b)) == [S.Expression]

    # A ground value, a variable and a plain symbol.
    # !(test (get-metatype 1) Grounded)
    assert type(ground(1)) is Grounded
    assert metatype(ground(1)) == [S.Grounded]
    # !(test (get-metatype $x) Variable)
    assert type(V.x) is Variable
    assert metatype(V.x) == [S.Variable]
    # !(test (get-metatype a) Symbol)
    assert type(S.a) is Symbol
    assert metatype(S.a) == [S.Symbol]

    # The one disagreement, and it is not a defect on either side.
    # !(test (get-metatype +) Grounded)
    assert type(S.add) is Symbol
    assert metatype(S.add) == [S.Grounded]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 1136 to 1250, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 1250 to 1251, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 1251 to 1263, on the release tree:
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
#: RE-PINNED 2026-08-26, 1263 to 1279 (+16), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 1279 to 1446 (+167), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 1446 to 1434 (-12), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 1434 to 1463 (+29), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 1463 to 1542 (+79), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
BUDGET = 1542
