"""Purpose: exact number operations and native floating functions.

Guarantees: the same 74 claims as 35-math_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/35-math_lib.metta; commit=6fa571d1b7059b610f73e9feed657711414251e5].
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Compute exact numbers, stream factors and apply native floating functions."""
    m += lib.math

    def refused(call):
        """Read a native refusal through the evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    gcd, lcm = m.fn.math_gcd, m.fn.math_lcm
    ratio, rationalize = m.fn.math_ratio, m.fn.math_rationalize
    root, power = m.fn.math_integer_root, m.fn.math_power_mod
    classify, real = m.fn.math_class, m.fn.math_real

    assert m.fn.factorial(20) == [2432902008176640000]
    assert m.fn.binomial(52, 5) == [2598960]
    assert gcd(()) == [0]
    assert gcd((0, 0)) == [0]
    assert gcd((-18, 24, 30)) == [6]
    assert gcd((18446744073709551616, 36893488147419103232)) == [18446744073709551616]
    assert lcm(()) == [1]
    assert lcm((-6, 8, 15)) == [120]
    assert lcm((0, 5)) == [0]

    assert m.fn.mul(S.math_rational(1, 3), 3) == [1]
    assert tuple(ratio(S.math_rational(10, -20)).one()) == (-1, 2)
    assert classify(S.math_rational(6, 3)) == [S.integer]
    assert classify(S.math_rational(1, 3)) == [S.rational]
    assert tuple(ratio(0.1).one()) == (3602879701896397, 36028797018963968)
    assert tuple(ratio(S.math_rational(0.1)).one()) == (3602879701896397, 36028797018963968)
    assert tuple(ratio(-0.0).one()) == (0, 1)
    assert tuple(ratio(S.math_rationalize(0.1)).one()) == (1, 10)
    assert rationalize(42) == [42]
    assert tuple(ratio(S.math_rationalize(S.math_rational(2, 3))).one()) == (2, 3)

    assert tuple(root(2, 101).one()) == (10, 1)
    assert tuple(root(3, -28).one()) == (-3, -1)
    assert tuple(root(1, -42).one()) == (-42, 0)
    assert tuple(root(2, 340282366920938463463374607431768211456).one()) == (18446744073709551616, 0)
    assert power(2, 100, 1000) == [376]
    assert power(-2, 3, 5) == [2]
    assert power(42, 0, 1) == [0]
    assert [tuple(pair) for pair in m.fn.math_factor_pairs(1)] == [(1, 1)]
    assert [tuple(pair) for pair in m.fn.math_factor_pairs(36)] == [(1, 36), (2, 18), (3, 12), (4, 9), (6, 6)]
    assert tuple(m.fn.once(S.math_factor_pairs(36)).one()) == (1, 36)

    assert m.fn.math_sqrt(4) == [2.0]
    assert m.fn.math_sqrt(S.bit_shift_left(1, 2000)) == m.fn.math_float(S.bit_shift_left(1, 1000))
    assert m.fn.math_sqrt(S.math_rational(1, S.bit_shift_left(1, 2000))) == m.fn.math_float(
        S.math_rational(1, S.bit_shift_left(1, 1000)))
    assert real(S.copysign, (1.0, S.math_sqrt(-0.0))) == [-1.0]
    assert refused(S.math_sqrt(-1))
    assert refused(S.math_sqrt(S.math_real(S.inf, ())))

    assert m.fn.math_float(S.math_rational(1, 10)) == [0.1]
    assert classify(S.math_float(1)) == [S.normal]
    assert classify(S.math_float(-0.0)) == [S.zero]
    assert real(S.copysign, (1.0, S.math_float(-0.0))) == [-1.0]
    assert classify(S.math_float(S.math_rational(18014398509481985, S.bit_shift_left(1, 1129)))) == [S.subnormal]
    assert classify(S.math_float(S.bit_shift_left(1, 2000))) == [S.infinite]

    assert len(m.fn.math_real_functions().one()) == 20
    assert real(S.sinh, (0,)) == [0.0]
    assert real(S.cosh, (0,)) == [1.0]
    assert real(S.tanh, (0,)) == [0.0]
    assert real(S.asinh, (0,)) == [0.0]
    assert real(S.acosh, (1,)) == [0.0]
    assert real(S.atanh, (0,)) == [0.0]
    assert real(S.log10, (100,)) == [2.0]
    assert real(S.erf, (0,)) == [0.0]
    assert real(S.erfc, (0,)) == [1.0]
    assert real(S.lgamma, (1,)) == [0.0]
    assert real(S.atan2, (1, 1)).one() == m.fn.truediv(S.math_real(S.pi, ()), 4).one()
    assert real(S.nexttoward, (1.0, 2.0)) == [1.0000000000000002]
    assert real(S["float_integer_part"], (-1.75,)) == [-1.0]
    assert real(S["float_fractional_part"], (-1.75,)) == [-0.75]
    assert real(S.e, ()).one() > 2.7
    assert real(S.epsilon, ()) == [2.220446049250313e-16]
    assert classify(S.math_real(S.inf, ())) == [S.infinite]
    assert classify(S.math_real(S.nan, ())) == [S.nan]

    assert refused(S.math_gcd((1, 2.5)))
    assert refused(S.math_lcm((0, 2.5)))
    assert refused(S.math_rational(1, 0))
    assert refused(S.math_ratio(S.math_real(S.inf, ())))
    assert refused(S.math_rationalize(S.math_real(S.nan, ())))
    assert refused(S.math_integer_root(0, 5))
    assert refused(S.math_integer_root(2, -1))
    assert refused(S.math_power_mod(2, -1, 5))
    assert refused(S.math_power_mod(2, 3, 0))
    assert refused(S.math_factor_pairs(0))
    assert refused(S.math_real(S.missing, (1,)))
    assert refused(S.math_real(S.atan2, (1,)))
    assert refused(S.math_real(S.erf, (G("x"),)))
    assert refused(S.math_real(S.acosh, (0,)))


#: MEASURED: all 67 claims, including exact arithmetic, streamed factors,
#: native floating dispatch and refusals. The example pays 118980 inferences.
#: [measured 2026-09-12: 121592 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/35-math_lib.metta;
#: fixture=lib_math at its functional commit with engine/lib QLF artifacts purged;
#: commit=4d17f1af15fe125e3b8cd488502ba1e0e688fb3e].
#: RE-PINNED 2026-09-12, 121592 to 121599 (+7), Vector now exports its existing
#: fraction_sqrt native service; the additional module export moves each
#: measured library import by seven inferences while the numerical
#: implementations and MeTTa heads stay unchanged [measured 2026-09-12: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=84824f5cf870f5cd7ac89d6580093d0459d91a9b].
#: RE-PINNED 2026-09-13, 121599 to 192956 (+71357), Combinatorics, Functional,
#: Pairs and Sets now derive collection operations through MeTTa equations,
#: segments and folds. This example imports the changed provider directly or
#: through its library dependencies [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 192956 to 194299 (+1343), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 194299 to 361166 (+166867), Math and Statistics derive
#: their recipes from MeTTa equations; Statistics consolidates finite laws and
#: adds reflective claims. Their collection dependencies share the proper
#: finite expression boundary in lib/_support/collections_data.pl [measured
#: 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6fa571d1b7059b610f73e9feed657711414251e5].
#: RE-PINNED 2026-09-13, 361166 to 361369 (+203), Vector, Math and the shared
#: collection boundary declare their native effects. The engine reads late
#: provider declarations and retains definition analysis for computed function
#: heads [measured 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=1d0b78a359f58de49f2f98bed50a6480d56cd5f6].
#: RE-PINNED 2026-09-14, 361369 to 357368 (-4001), Functional applies finished
#: callback arguments through reduce; Statistics derives exact coefficient rows
#: and Combinatorics retires its native probability provider [measured
#: 2026-09-14: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=e1be99ea1c08f70444c1c35cada441e089777906].
#: RE-PINNED 2026-09-14, 357368 to 359493 (+2125), Vector derives fill, random
#: construction and normalized-dot through MeTTa equations; Combinatorics
#: supplies ranges, literal validation folds once before core seeded draws, and
#: the Vector example adds nine construction and refusal claims. Native Math
#: also imports the shared Vector kernels, so every MeTTa and native consumer
#: is renewed [measured 2026-09-14: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c7bacead4feb29b9761d026b52b952e91b26b10b].
BUDGET = 359493
