"""Purpose: occurrence sampling, distribution values and seeded answer streams.

Guarantees: the same 59 claims as 36-random_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/36-random_lib.metta; commit=505b45e1d9184608c818a8a4fdba5cf6406bf3e7].
"""

from metta import FALSE, TRUE, G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Select occurrences and draw reproducible distribution samples."""
    m += lib.random

    def refused(call):
        """Read a native refusal through the evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    seed = m.fn.with_seed
    choice, shuffle, sample = S["random-choice!"], S["random-shuffle!"], S["random-sample!"]
    draw, draw_term = m.fn["random-draw!"], S["random-draw!"]

    def drawn(spec, count=1, seed_value=11):
        """Evaluate a held distribution in the existing seed scope."""
        return seed(seed_value, draw_term(spec, count))

    assert len(m.fn.random_distributions().one()) == 10
    assert m.fn.random_distributions().one()[0] == S.random_distribution(S.uniform, (G("low"), G("high")))
    assert m.fn["random-choice!"]((G("only"),)) == [G("only")]
    assert len(m.fn["random-choice!"]((S["+"](1, 2),)).one()) == 3
    assert tuple(m.fn["random-shuffle!"](()).one()) == ()
    assert tuple(seed(42, S.sort_atom(shuffle((1, 1, 2, 3)))).one()) == (1, 1, 2, 3)
    assert seed(42, shuffle((1, 2, 3, 4))) == seed(42, shuffle((1, 2, 3, 4)))
    assert tuple(m.fn["random-sample!"]((), 0, TRUE).one()) == ()
    assert tuple(m.fn["random-sample!"]((), 0, FALSE).one()) == ()
    assert tuple(seed(42, S.sort_atom(sample((1, 1, 2, 3), 4, FALSE))).one()) == (1, 1, 2, 3)
    assert tuple(seed(42, sample((G("x"),), 3, TRUE)).one()) == (G("x"), G("x"), G("x"))
    assert len(seed(42, sample((1, 2, 3, 4, 5), 3, FALSE)).one()) == 3
    assert tuple(seed(42, sample((G("x"), G("x")), 2, FALSE)).one()) == (G("x"), G("x"))
    assert seed(9, choice((1, 2, 3, 4))) == seed(9, choice((1, 2, 3, 4)))

    assert list(draw(S.normal(0, 1), 0)) == []
    assert draw(S.uniform(4, 4), 3) == [4.0, 4.0, 4.0]
    assert draw(S.normal(7, 0), 1) == [7.0]
    assert draw(S.lognormal(0, 0), 1) == [1.0]
    assert draw(S.triangular(3, 3, 3), 1) == [3.0]
    assert draw(S.bernoulli(0), 2) == [False, False]
    assert draw(S.bernoulli(1), 2) == [True, True]
    assert len(drawn(S.normal(0, 1), 5, 42)) == 5
    assert drawn(S.normal(0, 1), 4, 42) == drawn(S.normal(0, 1), 4, 42)
    assert seed(42, S.once(draw_term(S.normal(0, 1), 100))) == drawn(S.normal(0, 1), 1, 42)
    # Indexing keeps the native rational atom; one() decodes its Python payload.
    mean = m.fn.math_rational(1, 2)[0]
    assert draw(S.normal(mean, 0), 1) == [0.5]

    uniform = drawn(S.uniform(-4, 9)).one()
    assert -4 <= uniform <= 9
    assert m.fn.math_class(drawn(S.normal(0, 1)).one()) == [S.normal]
    assert drawn(S.lognormal(0, 1)).one() > 0
    assert drawn(S.exponential(2)).one() > 0
    triangular = drawn(S.triangular(-4, 9, 2)).one()
    assert -4 <= triangular <= 9
    assert drawn(S.gamma(2, 3)).one() > 0
    beta = drawn(S.beta(2, 5)).one()
    assert 0 < beta < 1
    assert m.fn.get_type(drawn(S.bernoulli(0.25)).one()) == [S.Bool]
    assert drawn(S.pareto(3)).one() >= 1
    assert drawn(S.weibull(2, 3)).one() > 0
    assert drawn(S.gamma(1.0e308, 1), 1, 42) == [1.0e308]
    assert drawn(S.beta(1.0e308, 1.0e308), 1, 42) == [0.5]
    assert drawn(S.gamma(0.001, 1), 1, 2) == [0.0]
    assert drawn(S.gamma(0.001, 1.0e300), 1, 2).one() > 0
    assert drawn(S.weibull(1.0e308, 1.0e308), 1, 42) == [1.0e308]
    assert m.fn.math_class(draw_term(S.lognormal(1000, 0), 1)) == [S.infinite]

    assert refused(choice(()))
    assert refused(shuffle(G("text")))
    assert refused(sample((), 1, TRUE))
    assert refused(sample((1, 2), 3, FALSE))
    assert refused(sample((1,), -1, TRUE))
    assert refused(draw_term(S.missing(1), 0))
    assert refused(draw_term(S.normal(0), 1))
    assert refused(draw_term(S.normal(0, -1), 1))
    assert refused(draw_term(S.uniform(2, 1), 1))
    assert refused(draw_term(S.triangular(0, 1, 2), 1))
    assert refused(draw_term(S.exponential(0), 1))
    assert refused(draw_term(S.gamma(-1, 2), 1))
    assert refused(draw_term(S.beta(2, 0), 1))
    assert refused(draw_term(S.bernoulli(1.1), 1))
    assert refused(draw_term(S.pareto(0), 1))
    assert refused(draw_term(S.weibull(0, 1), 1))
    assert refused(draw_term(S.normal(G("x"), 1), 1))
    assert refused(draw_term(S.normal(0, 1), -1))


#: MEASURED: all 59 claims, with every nondegenerate draw under an explicit
#: seed. The example pays 122535 inferences.
#: [measured 2026-09-12: 117876 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/36-random_lib.metta;
#: fixture=lib_random at its functional commit with engine/lib QLF artifacts purged;
#: commit=505b45e1d9184608c818a8a4fdba5cf6406bf3e7].
#: RE-PINNED 2026-09-12, 117876 to 117883 (+7), Vector now exports its existing
#: fraction_sqrt native service; the additional module export moves each
#: measured library import by seven inferences while the numerical
#: implementations and MeTTa heads stay unchanged [measured 2026-09-12: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=84824f5cf870f5cd7ac89d6580093d0459d91a9b].
#: RE-PINNED 2026-09-13, 117883 to 123955 (+6072), Combinatorics, Functional,
#: Pairs and Sets now derive collection operations through MeTTa equations,
#: segments and folds. This example imports the changed provider directly or
#: through its library dependencies [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 123955 to 125298 (+1343), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 125298 to 135480 (+10182), Math and Statistics derive
#: their recipes from MeTTa equations; Statistics consolidates finite laws and
#: adds reflective claims. Their collection dependencies share the proper
#: finite expression boundary in lib/_support/collections_data.pl [measured
#: 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 135480
