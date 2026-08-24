"""examples/libraries/he_math.metta in Python: the engine's numeric library, checked.

Twenty-four claims about the `*-math` family and the two atom-level extrema.
Real-valued math promotes integers, `pow-math` answers a Float while enforcing
the signed-i32 bound only for integer exponents, and the nan/inf predicates are
how a caller finds out.

Two of the operations have a Python spelling and take it. `**` on a grounded
operand builds `(pow-math a b)` and `abs()` builds `(abs-math a)`, so those two
claims are written with Python's own punctuation over the lift, `G(0) ** -1`
[appendix 12: the math dunder split, protocol-backed names build live]. The
lift is what makes the second of them worth reading: Python raises
ZeroDivisionError for `0 ** -1` where the engine answers inf, and the twin
shows that difference instead of hiding it behind a head name.

The rest of the family has no Python hook and takes rung 4 at the function
namespace, `m.fn.sqrt_math(9)`, which is the guide's own answer for a
hook-less math name in live position.

The two nested claims nest the way Python nests calls. An answer view crossing
into term position is an observation point, so a deterministic inner call
composes without anything written between the levels.

A name used more than once is bound once and called twice, the way a mention
is bound once for reading. The two special float symbols are what the engine
names them, `inf` and `nan`.
"""

from metta import G, S

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
BUDGET = 1


def twin(m):
    """Ask each numeric operation for its answer."""
    sqrt_math = m.fn.sqrt_math
    isnan, isinf = m.fn.isnan_math, m.fn.isinf_math

    assert m.answers(G(2) ** 3) == [8.0]
    assert isnan(sqrt_math(-1)) == [True]
    assert isinf(G(0) ** -1) == [True]
    # The signed-i32 bound is enforced only for INTEGER exponents.
    assert m.answers(G(1) ** 2147483648.0) == [1.0]
    assert sqrt_math(9) == [3.0]
    assert m.answers(abs(G(-5))) == [5]
    assert m.fn.log_math(10, 100) == [2.0]

    assert m.fn.trunc_math(5.6) == [5]
    assert m.fn.ceil_math(5.2) == [6]
    assert m.fn.floor_math(5.8) == [5]
    round_math = m.fn.round_math
    assert round_math(5.4) == [5]
    assert round_math(5.6) == [6]

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
