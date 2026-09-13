"""Purpose: exact finite descriptive statistics and explicit sample domains.

Guarantees: the same 76 claims as 37-statistics_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/37-statistics_lib.metta; commit=84824f5cf870f5cd7ac89d6580093d0459d91a9b].
"""

from metta import FALSE, TRUE, G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Reduce observations, interpolate quantiles and fit exact paired data."""
    m += lib.statistics
    fn = m.fn

    def refused(call):
        """Read an operation refusal through the public evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    assert fn.stats_sum(()) == [0]
    assert fn.stats_sum((1, 2, 3)) == [6]
    assert fn.stats_sum((1.0e308, 1, -1.0e308)) == [1.0]
    assert fn.math_class(S.stats_sum((1.0e308, 1.0e308))) == [S.infinite]
    assert fn.stats_mean((1, 2, 3)) == [2]
    assert tuple(fn.math_ratio(S.stats_mean((1, 2))).one()) == (3, 2)
    assert fn.stats_mean((1.0e308, 1.0e308)) == [1.0e308]
    assert fn.stats_mean((1.0e308, 1, -1.0e308)) == fn.math_float(S.math_rational(1, 3))
    assert fn.stats_harmonic_mean((40, 60)) == [48]
    assert fn.stats_harmonic_mean((40.0, 60)) == [48.0]
    assert fn.stats_harmonic_mean((0, 7)) == [0]
    assert fn.stats_geometric_mean((54, 24, 36)) == [36.0]
    assert fn.stats_geometric_mean((0, 7)) == [0.0]
    assert fn.stats_geometric_mean((1.0e308, 1.0e308)) == [1.0e308]
    big = fn.pow_math(2, 2000).one()
    small = fn.math_rational(1, big)[0]
    assert fn.stats_geometric_mean((big, small)) == [1.0]

    assert fn.stats_median((9, 1, 4)) == [4]
    assert tuple(fn.math_ratio(S.stats_median((1, 2))).one()) == (3, 2)
    assert fn.stats_median((9.0, 1, 4)) == [4.0]
    assert fn.stats_quantile((0, 10), 0, S.inclusive) == [0]
    assert fn.stats_quantile((0, 10), 1, S.inclusive) == [10]
    assert tuple(fn.math_ratio(S.stats_quantile((0, 10), 0.25, S.inclusive)).one()) == (5, 2)
    assert fn.stats_quantile((0, 10), 0, S.exclusive) == [-10]
    assert fn.stats_quantile((0, 10), 1, S.exclusive) == [20]
    assert tuple(fn.stats_quantiles((0, 4, 8), 4, S.inclusive).one()) == (2, 4, 6)
    assert tuple(fn.stats_quantiles((0, 4, 8), 4, S.exclusive).one()) == (0, 4, 8)
    assert tuple(fn.stats_quantiles((7,), 4, S.exclusive).one()) == (7, 7, 7)
    assert tuple(fn.stats_quantiles((7,), 1, S.inclusive).one()) == ()
    assert fn.stats_mode((G("b"), G("a"), G("b"), G("a"), G("c"))) == [G("b"), G("a")]
    assert fn.once(S.stats_mode((G("b"), G("a"), G("b"), G("a")))) == [G("b")]
    assert list(fn.stats_mode((1, 1.0))) == [G(1), G(1.0)]
    assert len(fn.stats_mode((S["+"](1, 2), S["+"](1, 2), 9)).one()) == 3

    assert fn.stats_variance((1, 2, 3), 1) == [1]
    assert tuple(fn.math_ratio(S.stats_variance((1, 2, 3), 0)).one()) == (2, 3)
    assert fn.stats_variance((1, 2, 3), 2) == [2]
    assert fn.stats_variance((1000000000.0, 1000000001.0, 1000000002.0), 1) == [1.0]
    assert fn.stats_variance((7,), 0) == [0]
    assert fn.stats_stdev((1, 2, 3), 1) == [1.0]
    assert fn.stats_stdev((1, 3), 0) == [1.0]
    assert fn.math_class(S.stats_variance((-1.0e308, 1.0e308), 0)) == [S.infinite]
    assert fn.stats_stdev((-1.0e308, 1.0e308), 0) == [1.0e308]
    assert fn.stats_variance((-1.0e-300, 1.0e-300), 0) == [0.0]
    assert fn.stats_stdev((-1.0e-300, 1.0e-300), 0) == [1.0e-300]
    assert fn.stats_covariance((1, 2, 3), (1, 3, 5), 1) == [2]
    assert tuple(fn.math_ratio(S.stats_covariance((1, 2, 3), (1, 3, 5), 0)).one()) == (4, 3)
    assert fn.stats_correlation((-1.0e308, 1.0e308), (-1.0e308, 1.0e308)) == [1.0]
    assert fn.stats_correlation((-1.0e308, 1.0e308), (1.0e308, -1.0e308)) == [-1.0]
    assert tuple(fn.stats_ranks(()).one()) == ()
    assert tuple(fn.stats_ranks((30, 10, 20)).one()) == (3, 1, 2)
    assert tuple(fn.vector_scale(S.stats_ranks((1, 1.0, 2)), 2).one()) == (3, 3, 6)
    assert fn.stats_correlation(S.stats_ranks((1, 4, 9)), S.stats_ranks((1, 2, 3))) == [1.0]
    assert fn.stats_regression((0, 1, 2), (1, 5, 9), FALSE) == [S.linear_fit(4, 1)]
    assert fn.stats_regression((0.0, 1, 2), (1, 5, 9), FALSE) == [S.linear_fit(4.0, 1.0)]
    assert fn.stats_regression((2,), (6,), TRUE) == [S.linear_fit(3, 0)]
    assert fn.stats_regression((0, 1, 2), (7, 7, 7), FALSE) == [S.linear_fit(0, 7)]

    assert refused(S.stats_mean(()))
    assert refused(S.stats_sum((1, G("bad"))))
    assert refused(S.stats_geometric_mean(()))
    assert refused(S.stats_geometric_mean((0, -1)))
    assert refused(S.stats_harmonic_mean(()))
    assert refused(S.stats_harmonic_mean((0, -1)))
    assert refused(S.stats_median(()))
    assert refused(S.stats_quantile((1,), 2, S.inclusive))
    assert refused(S.stats_quantile((1,), 0.5, S.missing))
    assert refused(S.stats_quantiles((1,), 0, S.inclusive))
    assert refused(S.stats_quantiles((1,), 1, S.missing))
    assert refused(S.stats_mode(()))
    assert refused(S.stats_variance((1,), 1))
    assert refused(S.stats_variance((1, 2), -1))
    assert refused(S.stats_stdev((), 0))
    assert refused(S.stats_covariance((1, 2), (1,), 0))
    assert refused(S.stats_correlation((1, 1), (2, 3)))
    assert refused(S.stats_correlation((1,), (2,)))
    assert refused(S.stats_regression((1, 1), (2, 3), FALSE))
    assert refused(S.stats_regression((0,), (2,), TRUE))
    assert refused(S.stats_regression((1, 2), (3,), FALSE))
    infinity = fn.math_real(S.inf, ()).one()
    assert refused(S.stats_mean((infinity,)))


#: MEASURED: all 76 claims, including exact rational results, range-preserving
#: deviations and the complete refusal paths. The example pays 141717.
#: [measured 2026-09-12: 157714 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/37-statistics_lib.metta;
#: fixture=lib_statistics with engine/lib QLF artifacts purged; commit=84824f5cf870f5cd7ac89d6580093d0459d91a9b].
#: RE-PINNED 2026-09-13, 157714 to 163787 (+6073), Combinatorics, Functional,
#: Pairs and Sets now derive collection operations through MeTTa equations,
#: segments and folds. This example imports the changed provider directly or
#: through its library dependencies [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 163787 to 165130 (+1343), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
BUDGET = 165130

#: OVERRUN: Python evaluates through fn/eval and reads numeric and collection
#: results across the boundary for its assertions. The example's test keeps
#: those results in the engine. Its let also keeps the huge reciprocal pair
#: inside one evaluation; the twin names and reinserts both values. A scoped
#: term probe costs 950 against 1145 for those three warm calls, 195 of the
#: total difference, so retain the direct Python values. Measured 157714 against
#: the 1.1 ceiling 155888.7 leaves 1825.3 inferences above the band.
#: [measured 2026-09-12: 1826 inference ceiling above the band;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/37-statistics_lib.metta;
#: fixture=the same 76 claims and ai-lib4-statistics-crossing-probe.py; commit=84824f5cf870f5cd7ac89d6580093d0459d91a9b].
OVERRUN = 1826
