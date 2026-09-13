"""Purpose: compose finite domains, traversal, assertions and first witnesses.

Guarantees: every claim in 43-testing_lib.metta uses the same ordinary primitives.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/43-testing_lib.metta; commit=7fad61bab72098722b27091a94282ff69989920e].
"""

from metta import FALSE, TRUE, G, S, V, lib
from metta._errors.errors import AssertionFailure, MettaError


def twin(m):
    """Use ordinary generators with assertions, counting and commitment."""
    m += lib.combinatorics
    m += lib.testing

    def unary(body):
        """Hold a function with the parameter x."""
        return S["|->"]((V.x,), body)

    def refused(call):
        """Return the native refusal after consuming the complete call."""
        try:
            list(m.eval(call))
        except MettaError as error:
            return error
        return None

    x = V.x
    literal = S["+"](1, 2)
    power = m.fn.cartesian_power
    assert m.fn.range(-2, 3) == [-2, -1, 0, 1, 2]
    assert m.fn.range(3, 4) == [3]
    assert m.fn.range(3, 3) == []
    assert m.fn.range(10**20, 10**20 + 3) == [10**20, 10**20 + 1, 10**20 + 2]
    assert m.fn.superpose((S.a, S.a, G("π"))) == [S.a, S.a, G("π")]
    assert m.fn.superpose(()) == []
    assert len(m.fn.index_atom(S.quote((literal,)), 0)[0]) == 3
    assert m.fn.index_atom(((),), 0) == [()]
    items = tuple(m.fn.range(1, 4))
    assert m.fn.index_atom(items, S.range(0, S.size_atom(items))) == [1, 2, 3]

    assert power((0, 1), 0) == [()]
    assert power((0, 1), 2) == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert power((S.a, S.a), 2) == [(S.a, S.a)] * 4
    assert power((), 0) == [()]
    assert power((), 2) == []
    population = tuple(m.fn.range(0, 2))
    assert power(population, S.range(0, 3)) == [(), (0,), (1,), (0, 0), (0, 1), (1, 0), (1, 1)]
    assert power((0, 1), S.range(2, 2)) == []
    choice = m.fn.index_atom((S.row(x, x),), 0).one()
    pair = m.fn.map_atom((1, 2), unary(S["copy_term"](S.quote(choice)))).one()  # rung: both variable copies must travel in one answer to compare their sharing
    assert m.fn["=alpha"](pair, (S.row(V.a, V.a), S.row(V.b, V.b))) == [True]
    assert power(((), (S.a,)), 1) == [((),), ((S.a,),)]

    for value in m.fn.range(-3, 4):
        assert value.value * value.value >= 0
    for values in power((0, 1), S.range(0, 4)):
        assert m.fn.reverse(S.reverse(values)) == [values]
    assert m.fn.forall(S.range(0, 5), S["<="](0)) == [True]
    count = S["|->"]((V.value, V.count), S["+"](V.count, 1))
    assert m.fn.foldall(count, S.superpose((S.a, S.a, S.b)), 0) == [3]
    assert m.fn.forall(S.superpose(()), unary(FALSE)) == [True]
    assert m.fn.foldall(count, S.superpose(()), 0) == [0]

    for _ in m.fn.range(1, 3):
        assert sorted(m.fn.superpose((2, 1, 1))) == [1, 1, 2]
    for _ in m.fn.range(1, 3):
        assert m.fn.empty() == []
    for value in m.fn.index_atom(S.quote((literal,)), 0):
        assert [value] == [literal]
    for value in m.fn.index_atom((S.row(x, x),), 0):
        assert m.fn["=alpha"](value, S.row(V.y, V.y)) == [True]

    assert next(value for value in m.fn.range(0, 6) if value.value >= 3) == 3
    assert (next(value for value in m.fn.range(0, 6) if value.value >= 3),) == (3,)
    assert next((value for value in m.fn.range(0, 3) if value.value >= 3), None) is None
    assert m.fn.superpose(()).first(default=None) is None
    assert next(value for value in m.fn.range(0, 6)
                if sorted(m.fn.superpose((2, 1, 1))) == [1, 1, 2]) == 0
    assert len(m.fn.index_atom(S.quote((literal,)), 0).first()) == 3
    assert next(value for value in m.fn.index_atom(((), (S.a,)), S.range(0, 2))
                if len(value) == 0) == ()
    for value in m.fn.range(0, 3):
        assert next(other for other in m.fn.range(0, 3) if value == other) == value

    checked = 0
    for value in m.fn.range(0, 3):
        assert value.value >= 0
        checked += 1
    assert checked == 3
    assert m.fn.forall(S.range(0, 2), unary(S.superpose((FALSE, TRUE)))) == [True]
    assert m.fn.forall(S.range(0, 2), unary(S.empty())) == [False]
    assert m.fn.forall(S.range(0, 2), unary(7)) == [False]

    error = refused(S.assertEqualToResult(S.superpose((1, 1)), (1, 2)))  # rung: the core assertion's own missing/excess report is the subject
    assert isinstance(error, AssertionFailure) and error.missing == (2,) and error.excess == (1,)
    assert refused(S.cartesian_power((S.a,), -1)) is not None
    assert refused(S.cartesian_power((S.a,), 1.5)) is not None
    assert m.solve(x, S.once(S.unify(x, 3, x, S.empty()))).x == 3


#: MEASURED: domain, assertion, bag, witness and refusal claims through the core.
#: The example pays 76856 inferences.
#: [measured: 74003 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/43-testing_lib.metta;
#: fixture=lib_testing with engine/lib QLF artifacts purged; commit=7fad61bab72098722b27091a94282ff69989920e].
#: RE-PINNED 2026-09-13, 74003 to 364240: collection operations now compose
#: MeTTa matching, folds and application; segment continuations are protected
#: compiler helpers. The example measures 390681 for the same claims
#: [measured: 364240 inferences; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/43-testing_lib.metta;
#: fixture=minimum of three serial fresh processes after purging engine/lib QLF;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 364240 to 365541 (+1301), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 365541 to 367992 (+2451), Math and Statistics derive
#: their recipes from MeTTa equations; Statistics consolidates finite laws and
#: adds reflective claims. Their collection dependencies share the proper
#: finite expression boundary in lib/_support/collections_data.pl [measured
#: 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6fa571d1b7059b610f73e9feed657711414251e5].
BUDGET = 367992
