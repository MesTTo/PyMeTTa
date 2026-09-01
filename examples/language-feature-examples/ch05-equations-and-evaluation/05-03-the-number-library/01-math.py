"""Purpose: examples/ch05-equations-and-evaluation/05-03-the-number-library/01-math.metta in Python: the numeric surface.

Every `-math` operation is an engine function, so the space's own function
namespace names it once and it is then an ordinary Python callable: `sqrt(9)`
is `(sqrt-math 9)` evaluated, and its answers are `[3.0]`. An operation that
refuses answers an Error ATOM rather than raising, which is why the refusals
below are compared as data, and comparing the whole answer list states the
cardinality as well as the value.

Two namespaces, one split, and this file uses both on purpose. `m.fn.<name>`
is the BOUND namespace: its members evaluate in this space when called.
Package-level `fn.<name>` is the STATIC one: its members are the symbols
themselves, which is what a NESTED argument needs, since `(isnan-math
(sqrt-math -1))` is one term to evaluate once rather than two crossings.

The bound function namespace's operator-word attributes name the relational
comparisons and arithmetic calls. Python's numeric protocol reaches the four
integral conversions directly: `math.floor(G(5.8))` builds `(floor-math 5.8)`
and `round(G(5.6))` builds `(round-math 5.6)`.

`min-atom` and `max-atom` dissolve: an expression is a sequence, so Python's
own `min` and `max` read it with no engine crossing at all.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import math

from metta import Expression, G, S, fn, ground

#: The six numbers `min-atom` and `max-atom` are asked about.
NUMBERS = Expression((2, 6, 7, 4, 9, 3))


def twin(m):
    """Ask every numeric operation what it answers, refusals included."""
    equal, unequal = m.fn.eq, m.fn.ne
    divide, remainder = m.fn.truediv, m.fn.mod
    sqrt, power, log = m.fn.sqrt_math, m.fn.pow_math, m.fn.log_math
    isnan, isinf = m.fn.isnan_math, m.fn.isinf_math
    absolute = m.fn.abs_math
    sin, asin, cos, acos = (
        m.fn.sin_math, m.fn.asin_math, m.fn.cos_math, m.fn.acos_math
    )
    tan, atan = m.fn.tan_math, m.fn.atan_math

    # The engine's == is exact across numeric KINDS: an integer and a
    # float are different atoms even at the same value. Python's own
    # value-comparing == is the compiled bodies' py-eq, not this head.
    # !(test (== 1 1.0) False)
    assert equal(1, 1.0) == [False]
    assert unequal(1.0, 1) == [True]

    # Division and remainder by zero answer contained error atoms, and an
    # error is an ordinary ANSWER: the answer list holds it where a scalar
    # door would raise, and the form after it still runs.
    assert divide(7, 0) == [S.Error(G(7) / 0, S.DivisionByZero)]
    assert remainder(7, 0) == [S.Error(G(7) % 0, S.DivisionByZero)]
    # (collapse (/ 7 0)) adds the cardinality: exactly one answer, and it is
    # that error. `len()` is the size question over the answers a collapse
    # would have built.
    assert len(divide(7, 0)) == 1

    @m.define
    def math_string():
        # (= (math-string) "s")
        return "s"

    # A COMPUTED string reaches the operation's own guard and is refused
    # there, before the host can treat one character as its code.
    assert sqrt(S.math_string()) == [
        S.Error(fn.sqrt_math(ground("s")), S.BadArgType(1, S.Number, S.String))
    ]

    assert power(2, 3) == [8]
    assert isnan(fn.sqrt_math(-1)) == [True]
    # Integer zero to a negative power is exact division by zero, Error
    # data; the FLOAT form rides binary64 to an infinity.
    # !(test (pow-math 0 -1) (noeval (Error (pow-math 0 -1) DivisionByZero)))
    # !(test (isinf-math (pow-math 0.0 -1.0)) True)
    assert power(0, -1) == [S.Error(fn.pow_math(0, -1), S.DivisionByZero)]
    assert isinf(fn.pow_math(0.0, -1.0)) == [True]
    # An integer exponent is bounded to signed i32; a float one is not.
    assert power(2, 2147483648) == [
        S.Error(
            fn.pow_math(2, 2147483648),
            ground("power argument is too big, try using float value"),
        )
    ]
    # SWI's own 1 ** big-float is the integer 1, kind-preserved.
    # !(test (pow-math 1 2147483648.0) 1)
    assert power(1, 2147483648.0) == [1]

    # Real-valued operations promote integer operands to Float.
    assert sqrt(9) == [3.0]
    assert absolute(-5) == [5]
    assert log(10, 100) == [2.0]
    assert m.eval(math.trunc(G(5.6))) == [5]
    assert m.eval(math.ceil(G(5.2))) == [6]
    assert m.eval(math.floor(G(5.8))) == [5]
    assert m.eval(round(G(5.4))) == [5]
    assert m.eval(round(G(5.6))) == [6]
    assert sin(0) == [0.0]
    assert asin(0) == [0.0]
    assert cos(0) == [1.0]
    assert acos(1) == [0.0]
    assert tan(0) == [0.0]
    assert atan(0) == [0.0]
    assert isnan(0.0) == [False]
    assert isinf(0.0) == [False]

    # (min-atom (2 6 7 4 9 3)) and (max-atom ...): an expression IS a
    # sequence, so these are Python's own, at no engine cost.
    assert min(NUMBERS) == 2
    assert max(NUMBERS) == 9

    assert isinf(S.inf) == [True]
    assert isnan(S.nan) == [True]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 7828 to 8379, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 8379 to 8390, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 8390 to 8380, on the release tree:
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
#: RE-PINNED 2026-08-25, 8380 to 8413, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 8413 to 8558 (+145), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 8558 to 8578 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 8578 to 9916 (+1338), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 9916 to 9845 (-71), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 9845
