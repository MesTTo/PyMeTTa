"""Purpose: inspect, rewrite and run sample programs through ordinary MeTTa control.

Guarantees: the same 68 claims as 36-random_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/36-random_lib.metta; commit=1d0b78a359f58de49f2f98bed50a6480d56cd5f6].
"""

from metta import G, S, V, lib
from metta._errors.errors import MettaError


def twin(m):
    """Construct sample code, then use the existing evaluation and repetition doors."""
    m += lib.random
    seed = m.fn.with_seed
    choice = m.fn.random_choice
    shuffle, sample = m.fn["random-shuffle!"], m.fn["random-sample!"]
    normal, uniform = m.fn.random_normal, m.fn.random_uniform
    lognormal, triangular = m.fn.random_lognormal, m.fn.random_triangular
    bernoulli, exponential = m.fn.random_bernoulli, m.fn.random_exponential
    gamma, beta = m.fn.random_gamma, m.fn.random_beta
    pareto, weibull = m.fn.random_pareto, m.fn.random_weibull

    def refused(call):
        """Read a refusal through the same catch and if-error boundary."""
        try:
            return m.eval(S.if_error(S.catch(call), S.refused, S.fine)) == [S.refused]
        except MettaError:
            return True

    def drawn(program, count=1, seed_value=11):
        """Use the existing seed and repeat forms on an already constructed program."""
        return seed(seed_value, S.repeat(count, program))

    assert m.fn.get_metatype(normal(0, 1)[0]) == [S.Expression]
    assert m.fn.get_type(S.random_normal) == [S["->"](S.Number, S.Number, S.Expression)]
    assert m.eval(choice((G("only"),))[0]) == [G("only")]
    assert len(m.eval(choice((S["+"](1, 2),))[0])[0]) == 3
    assert shuffle(()) == [()]
    assert tuple(seed(42, S.sort_atom(S["random-shuffle!"]((1, 1, 2, 3)))).one()) == (1, 1, 2, 3)
    assert seed(42, S["random-shuffle!"]((1, 2, 3, 4))) == seed(42, S["random-shuffle!"]((1, 2, 3, 4)))
    assert sample((), 0) == [()]
    assert tuple(seed(42, S.sort_atom(S["random-sample!"]((1, 1, 2, 3), 4))).one()) == (1, 1, 2, 3)
    assert m.fn.repeat(3, choice((G("x"),))[0]) == [G("x"), G("x"), G("x")]
    assert len(seed(42, S["random-sample!"]((1, 2, 3, 4, 5), 3)).one()) == 3
    assert tuple(seed(42, S["random-sample!"]((G("x"), G("x")), 2)).one()) == (G("x"), G("x"))
    choices = choice((1, 2, 3, 4))[0]
    assert seed(9, choices) == seed(9, choices)
    choices = choice((V.x,))[0]
    repeated = m.fn.map_atom((0, 1, 2), V.i, S.eval(choices))[0]
    assert len(repeated.vars) == 1 and tuple(repeated) == (repeated[0],) * 3
    pair = seed(42, S["random-sample!"]((V.x, V.x), 2))[0]
    assert len(pair.vars) == 1 and pair[0] == pair[1]
    assert sample((S.Error(S.data, S.code),), 1)[0] == (S.Error(S.data, S.code),)

    assert m.fn.repeat(0, normal(0, 1)[0]) == []
    assert m.fn.repeat(3, uniform(4, 4)[0]) == [4.0, 4.0, 4.0]
    assert m.eval(normal(7, 0)[0]) == [7.0]
    assert m.eval(lognormal(0, 0)[0]) == [1.0]
    assert m.eval(triangular(3, 3, 3)[0]) == [3.0]
    assert m.fn.repeat(2, bernoulli(0)[0]) == [False, False]
    assert m.fn.repeat(2, bernoulli(1)[0]) == [True, True]
    gaussian = normal(0, 1)[0]
    assert len(drawn(gaussian, 5, 42)) == 5
    assert drawn(gaussian, 4, 42) == drawn(gaussian, 4, 42)
    assert seed(42, S.once(S.repeat(100, gaussian))) == drawn(gaussian, 1, 42)
    assert m.eval(normal(m.fn.math_rational(1, 2)[0], 0)[0]) == [0.5]

    u = drawn(uniform(-4, 9)[0]).one()
    assert -4 <= u <= 9
    assert m.fn.math_class(drawn(gaussian).one()) == [S.normal]
    assert drawn(lognormal(0, 1)[0]).one() > 0
    assert drawn(exponential(2)[0]).one() > 0
    t = drawn(triangular(-4, 9, 2)[0]).one()
    assert -4 <= t <= 9
    assert drawn(gamma(2, 3)[0]).one() > 0
    b = drawn(beta(2, 5)[0]).one()
    assert 0 < b < 1
    assert m.fn.get_type(drawn(bernoulli(0.25)[0])[0]) == [S.Bool]
    assert drawn(pareto(3)[0]).one() >= 1
    assert drawn(weibull(2, 3)[0]).one() > 0
    assert drawn(gamma(1.0e308, 1)[0], seed_value=42) == [1.0e308]
    assert drawn(beta(1.0e308, 1.0e308)[0], seed_value=42) == [0.5]
    assert drawn(gamma(0.001, 1)[0], seed_value=2) == [0.0]
    assert drawn(gamma(0.001, 1.0e300)[0], seed_value=2).one() > 0
    assert drawn(weibull(1.0e308, 1.0e308)[0], seed_value=42) == [1.0e308]
    assert m.fn.math_class(m.eval(lognormal(1000, 0)[0])[0]) == [S.infinite]
    assert m.eval(lognormal(-1000, 0)[0]) == [0.0]

    m.add(S.saved_sampler(normal(12, 0)[0]))
    stored = m.match(S.saved_sampler(V.code)).one().code
    assert m.eval(stored) == [12.0]
    head, _entropy, low, high = uniform(2, 10)[0]
    assert m.eval((head, 0.25, low, high)) == [4.0]
    row = m.match(S["="](S.random_normal(V.mean, V.deviation), V.body)).one()
    constructor = m.eval(S["|->"]((row.mean, row.deviation), row.body))[0]
    assert m.eval(m.eval((constructor, 9, 0))[0]) == [9.0]
    alternatives = normal(S.superpose((1, 2)), 0)
    assert [answer for program in alternatives for answer in m.eval(program)] == [1.0, 2.0]
    assert m.fn.repeat(2, S.superpose((S.a, S.b))) == [S.a, S.b, S.a, S.b]
    a, b = normal(2, 0)[0], uniform(3, 3)[0]
    assert m.eval(S["+"](S.eval(a), S.eval(b))) == [5.0]

    assert refused(S.random_choice(()))
    assert refused(S["random-shuffle!"](G("text")))
    assert refused(S["random-sample!"]((), 1))
    assert refused(S["random-sample!"]((1, 2), 3))
    assert refused(S["random-sample!"]((1,), -1))
    assert refused(S["random-sample!"]((1,), 1.0))
    assert refused(S.random_normal(0, -1))
    assert refused(S.random_uniform(2, 1))
    assert refused(S.random_triangular(0, 1, 2))
    assert refused(S.random_exponential(0))
    assert refused(S.random_gamma(-1, 2))
    assert refused(S.random_beta(2, 0))
    assert refused(S.random_bernoulli(1.1))
    assert refused(S.random_pareto(0))
    assert refused(S.random_weibull(0, 1))
    assert refused(S.random_normal(G("x"), 1))
    assert refused(S.random_normal(S.math_real(S.inf, ()), 1))
    try:
        invalid = normal(0, -1)[0]
        m.fn.repeat(0, invalid)
    except MettaError:
        refused_before_repeat = True
    else:
        refused_before_repeat = False
    assert refused_before_repeat


#: MEASURED 2026-09-13: 68 equal claims over inspectable sample programs,
#: including variable sharing, reflection, exact extreme parameters and
#: validation before drawing. min-of-3 serial fresh processes reads
#: metta=1075529 and twin=1134846 [measured: 1134846;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/36-random_lib.metta;
#: fixture=68 Random example claims with core seeded entropy; commit=1d0b78a359f58de49f2f98bed50a6480d56cd5f6].
#: RE-PINNED 2026-09-14, 1134846 to 1148657 (+13811), Functional applies
#: finished callback arguments through reduce; Statistics derives exact
#: coefficient rows and Combinatorics retires its native probability provider
#: [measured 2026-09-14: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=e1be99ea1c08f70444c1c35cada441e089777906].
#: RE-PINNED 2026-09-14, 1148657 to 1150796 (+2139), Vector derives fill,
#: random construction and normalized-dot through MeTTa equations;
#: Combinatorics supplies ranges, literal validation folds once before core
#: seeded draws, and the Vector example adds nine construction and refusal
#: claims. Native Math also imports the shared Vector kernels, so every MeTTa
#: and native consumer is renewed [measured 2026-09-14: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c7bacead4feb29b9761d026b52b952e91b26b10b].
BUDGET = 1150796
