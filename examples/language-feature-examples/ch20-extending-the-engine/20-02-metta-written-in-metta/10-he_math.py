"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/10-he_math.metta in Python: the engine's numeric library, checked.

Twenty-four claims about the `*-math` family and the two atom-level extrema.
Real-valued math promotes integers, `pow-math` answers a Float while enforcing
the signed-i32 bound only for integer exponents, and the nan/inf predicates are
how a caller finds out.

Six of the operations have a Python spelling and take it. `**` on a grounded
operand builds `(pow-math a b)` and `abs()` builds `(abs-math a)`, so those two
claims are written with Python's own punctuation over the lift, `G(0) ** -1`
[appendix 12: the math dunder split, protocol-backed names build live]. The
lift is what makes the second of them worth reading: Python raises
ZeroDivisionError for `0 ** -1` where the engine answers inf, and the twin
shows that difference instead of hiding it behind a head name.

`math.trunc`, `math.ceil`, `math.floor`, and both forms of `round` build the
matching engine terms. The rest of the family has no Python hook and takes
rung 4 at the function namespace, `m.fn.sqrt_math(9)`.

The two nested claims nest the way Python nests calls. An answer view crossing
into term position is an observation point, so a deterministic inner call
composes without anything written between the levels.

A name used more than once is bound once and called twice, the way a mention
is bound once for reading. The two special float symbols are what the engine
names them, `inf` and `nan`.
"""

import math

from metta import G, S


def twin(m):
    """Ask each numeric operation for its answer."""
    sqrt_math = m.fn.sqrt_math
    isnan, isinf = m.fn.isnan_math, m.fn.isinf_math

    # pow-math keeps its operands' own kinds: two integers answer the
    # integer, upstream's `Out is A ** B` law.
    assert m.answers(G(2) ** 3) == [8]
    assert isnan(sqrt_math(-1)) == [True]
    # Integer zero to a negative power is exact division by zero, Error
    # data; the float spelling rides binary64 to an infinity.
    assert m.answers(G(0) ** -1) == [S.Error(S.pow_math(0, -1), S.DivisionByZero)]
    assert isinf(m.fn.pow_math(0.0, -1.0)) == [True]
    # The signed-i32 bound is enforced only for INTEGER exponents, and
    # SWI's own 1 ** big-float is the integer 1, kind-preserved.
    assert m.answers(G(1) ** 2147483648.0) == [1]
    assert sqrt_math(9) == [3.0]
    assert m.answers(abs(G(-5))) == [5]
    assert m.fn.log_math(10, 100) == [2.0]

    assert m.eval(math.trunc(G(5.6))) == [5]
    assert m.eval(math.ceil(G(5.2))) == [6]
    assert m.eval(math.floor(G(5.8))) == [5]
    assert m.eval(round(G(5.4))) == [5]
    assert m.eval(round(G(5.6))) == [6]

    assert m.fn.sin_math(0) == [0.0]
    assert m.fn.asin_math(0) == [0.0]
    assert m.fn.cos_math(0) == [1.0]
    assert m.fn.acos_math(1) == [0.0]
    assert m.fn.tan_math(0) == [0.0]
    assert m.fn.atan_math(0) == [0.0]

    assert isnan(0.0) == [False]
    assert isinf(0.0) == [False]

    assert m.fn.min_atom((2, 6, 7, 4, 9, 3)) == [2]
    assert m.fn.max_atom((2, 6, 7, 4, 9, 3)) == [9]

    assert isinf(S.inf) == [True]
    assert isnan(S.nan) == [True]


#: Why this twin sits below the top rung: `min-atom` and `max-atom` dissolve
#: into Python's `min` and `max` everywhere else in the corpus, and here they
#: are two of the numeric operations under test, so a Python max over a Python
#: tuple would check Python rather than the engine.
RUNG = "min-atom and max-atom are two of the stdlib numeric operations this file checks, not a request to take a maximum"

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 4164 to 4639, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 4639 to 4640, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 4640 to 4690, on the release tree:
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
#: RE-PINNED 2026-08-25, 4690 to 4692, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 4692 to 4724 (+32), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 4724 to 5458 (+734), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 5458 to 5404 (-54), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 5404 to 5513 (+109), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 5513
