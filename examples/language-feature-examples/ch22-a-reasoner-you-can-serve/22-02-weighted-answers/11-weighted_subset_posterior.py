"""Purpose: prove exact additive conditioning and inspect its MeTTa recipe.

Guarantees: the example's exact masses, marginals, literal identities and
alternative rows have matching answers and stored content [tested: twin;
commit=e1be99ea1c08f70444c1c35cada441e089777906].
"""

from metta import S, V, lib


def twin(m):
    """Use Statistics for exact laws and ordinary matching for their recipes."""
    m += lib.statistics
    mass = m.fn.weighted_subset_mass_independent
    posterior = m.fn.weighted_subset_posterior_independent

    assert posterior((S.candidate(S.pump_a, 2, S.ratio(1, 2)),
                      S.candidate(S.pump_b, 3, S.ratio(1, 4))), 2) == [
        S.subset_posterior(S.ratio(3, 8),
                          (S.candidate_posterior(S.pump_a, S.ratio(1, 1)),
                           S.candidate_posterior(S.pump_b, S.ratio(0, 1))))]
    assert posterior((S.candidate(S.left, 1, S.ratio(1, 2)),
                      S.candidate(S.right, 1, S.ratio(1, 2))), 1) == [
        S.subset_posterior(S.ratio(1, 2),
                          (S.candidate_posterior(S.left, S.ratio(1, 2)),
                           S.candidate_posterior(S.right, S.ratio(1, 2))))]
    assert posterior((S.candidate(S.metadata_flag, 0, S.ratio(1, 3)),
                      S.candidate(S.failing_part, 2, S.ratio(1, 2))), 2) == [
        S.subset_posterior(S.ratio(1, 2),
                          (S.candidate_posterior(S.metadata_flag, S.ratio(1, 3)),
                           S.candidate_posterior(S.failing_part, S.ratio(1, 1))))]
    assert mass((S.candidate(S.absent, 5, S.ratio(0, 1)),), 5) == [S.ratio(0, 1)]
    assert mass((S.candidate(S.scaled_loss, 125, S.ratio(2, 5)),), 125) == [S.ratio(2, 5)]
    assert posterior((), 0) == [S.subset_posterior(S.ratio(1, 1), ())]
    assert posterior((S.candidate(1, 0, S.ratio(1, 2)),
                      S.candidate(1.0, 0, S.ratio(1, 3))), 0) == [
        S.subset_posterior(S.ratio(1, 1),
                          (S.candidate_posterior(1, S.ratio(1, 2)),
                           S.candidate_posterior(1.0, S.ratio(1, 3))))]
    assert posterior((S.candidate(S["+"](1, 2), 0, S.ratio(1, 2)),
                      S.candidate(S.Error(S.a, S.b), 0, S.ratio(1, 3))), 0) == [
        S.subset_posterior(S.ratio(1, 1),
                          (S.candidate_posterior(S["+"](1, 2), S.ratio(1, 2)),
                           S.candidate_posterior(S.Error(S.a, S.b), S.ratio(1, 3))))]
    laws = ((S.candidate(S.a, 1, S.ratio(1, 2)),),
            (S.candidate(S.a, 1, S.ratio(1, 2)),),
            (S.candidate(S.b, 1, S.ratio(1, 3)),))
    assert [answer for rows in laws for answer in mass(rows, 1)] == [
        S.ratio(1, 2), S.ratio(1, 2), S.ratio(1, 3)]

    row = m.match(S["="](S.weighted_subset_mass_independent(V.rows, V.target), V.body)).one()
    recipe = m.eval(S["|->"]((row.rows, row.target), row.body))[0]
    assert m.eval((recipe, S.quote((S.candidate(S.a, 1, S.ratio(1, 3)),)), 1)) == [S.ratio(1, 3)]

    m += S.subset_event(S.from_space, 2, S.ratio(1, 3))
    m += S.subset_event(S.other, 3, S.ratio(1, 4))
    rows = tuple(S.candidate(row.id, row.loss, row.prior)
                 for row in m.match(S.subset_event(V.id, V.loss, V.prior)))
    assert mass(rows, 2) == [S.ratio(1, 4)]


#: The eleven claims exercise exact masses, inclusion marginals, literal IDs,
#: alternative candidate rows and reconstruction of a stored MeTTa equation.
#: [measured: 1755787 inferences against example1749167, minimum of three
#: serial fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --measure --rounds 3 examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/11-weighted_subset_posterior.metta;
#: fixture=Statistics MeTTa coefficient rows, QLFs purged before measurement;
#: commit=e1be99ea1c08f70444c1c35cada441e089777906].
#: RE-PINNED 2026-09-14, 1755787 to 1757926 (+2139), Vector derives fill,
#: random construction and normalized-dot through MeTTa equations;
#: Combinatorics supplies ranges, literal validation folds once before core
#: seeded draws, and the Vector example adds nine construction and refusal
#: claims. Native Math also imports the shared Vector kernels, so every MeTTa
#: and native consumer is renewed [measured 2026-09-14: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c7bacead4feb29b9761d026b52b952e91b26b10b].
BUDGET = 1757926
