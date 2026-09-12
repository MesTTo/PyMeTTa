"""Purpose: finite generators, counted answer-bag assertions and first witnesses.

Guarantees: the same 48 claims as 43-testing_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/43-testing_lib.metta; commit=a283d39342d891aae0edc58949e2ccbb48911cd8].
"""

from metta import FALSE, TRUE, G, S, V, lib
from metta._errors.errors import AssertionFailure, MettaError


def twin(m):
    """Enumerate finite families and retain the engine's quantified verdicts."""
    m += lib.combinatorics
    m += lib.testing

    def unary(body):
        """A held one-input function whose parameter is x."""
        return S["|->"]((V.x,), body)

    def refused(call):
        """Return the native refusal, or None when the complete call succeeds."""
        try:
            list(m.eval(call))
        except MettaError as error:
            return error
        return None

    integers, choices, lists = m.fn.test_integers, m.fn.test_choices, m.fn.test_lists
    check, witness = m.fn.test_forall, m.fn.test_witness
    x = V.x
    identity = unary(x)
    population = S.test_integers(0, 1)

    assert m.fn.cartesian_power((S.a, S.b), 1) == [(S.a,), (S.b,)]
    assert integers(-2, 2) == [-2, -1, 0, 1, 2]
    assert integers(3, 3) == [3]
    assert integers(3, 2) == []
    assert integers(10**20, 10**20 + 2) == [10**20, 10**20 + 1, 10**20 + 2]
    assert choices((S.a, S.a, G("π"))) == [S.a, S.a, G("π")]
    assert choices(()) == []
    assert len(choices((S["+"](1, 2),))[0]) == 3
    assert choices(((),)) == [()]
    assert choices(tuple(integers(1, 3))) == [1, 2, 3]
    assert lists(population, 0, 2) == [(), (0,), (1,), (0, 0), (0, 1), (1, 0), (1, 1)]
    assert lists(S.test_choices((S.a, S.a)), 2, 2) == [(S.a, S.a)] * 4
    assert lists(S.test_choices(()), 0, 4) == [()]
    assert lists(S.test_choices(()), 1, 4) == []
    assert lists(population, 2, 1) == []
    assert lists(S.test_integers(S.bad, S.bounds), 0, 0) == [()]
    assert lists(S.test_lists(S.test_choices((S.a,)), 0, 1), 1, 1) == [((),), ((S.a,),)]
    pair = lists(S.test_choices((S.row(x, x),)), 2, 2)[0]
    assert m.fn["=alpha"](pair, (S.row(V.a, V.a), S.row(V.b, V.b))) == [True]

    assert check(S.test_integers(-3, 3), unary(S[">="](S["*"](x, x), 0)), (TRUE,)) == [7]
    assert check(S.test_lists(population, 0, 3),
                 unary(S["=="](S.reverse(S.reverse(x)), x)), (TRUE,)) == [15]
    assert check(S.test_integers(0, 4), S["<="](0), (TRUE,)) == [5]
    assert check(S.test_choices((S.a, S.a, S.b)), unary(TRUE), (TRUE,)) == [3]
    assert check(S.test_choices(()), unary(FALSE), (TRUE,)) == [0]
    assert check(S.test_integers(1, 2), unary(S.superpose((2, 1, 1))), (1, 2, 1)) == [2]
    assert check(S.test_integers(1, 2), unary(S.empty()), ()) == [2]
    assert check(S.test_choices((S["+"](1, 2),)), identity, (S["+"](1, 2),)) == [1]
    alpha = S["|->"]((V.value,), S["=alpha"](V.value, S.row(V.y, V.y)))
    assert check(S.test_choices((S.row(x, x),)), alpha, (TRUE,)) == [1]

    at_least_three = unary(S[">="](x, 3))
    assert witness(S.test_integers(0, 5), at_least_three, (TRUE,)) == [3]
    assert tuple(witness(S.test_integers(0, 5), at_least_three, (TRUE,))) == (3,)
    assert witness(S.test_integers(0, 2), at_least_three, (TRUE,)) == []
    assert witness(S.test_choices(()), unary(TRUE), (TRUE,)) == []
    assert witness(S.test_integers(0, 5), unary(S.superpose((2, 1, 1))), (1, 1, 2)) == [0]
    assert len(witness(S.test_choices((S["+"](1, 2),)), identity, (S["+"](1, 2),))[0]) == 3
    assert witness(S.test_choices(((), (S.a,))), S.size_atom, (0,)) == [()]
    nested = unary(S["=="](S.test_witness(S.test_integers(0, 2), S["=="](x), (TRUE,)), x))
    assert check(S.test_integers(0, 2), nested, (TRUE,)) == [3]

    error = refused(S.test_forall(S.test_integers(0, 3), unary(S["<"](x, 2)), (TRUE,)))
    assert (isinstance(error, AssertionFailure) and error.missing == (TRUE,)
            and error.excess == (FALSE,) and "(quote 2)" in str(error))
    assert refused(S.test_forall(S.test_choices((S.a,)), unary(7), (TRUE,))) is not None
    assert refused(S.test_forall(S.test_choices((S.a,)), unary(S.empty()), (TRUE,))) is not None
    assert refused(S.test_forall(S.test_choices((S.a,)), unary(S.superpose((TRUE, TRUE))), (TRUE,))) is not None
    assert refused(S.test_integers(1.5, 2)) is not None
    assert refused(S.test_integers(1, S.inf)) is not None
    assert refused(S.test_choices(S.a)) is not None
    assert refused(S.test_lists(S.test_choices((S.a,)), -1, 2)) is not None
    assert refused(S.test_lists(S.test_choices((S.a,)), 0, 1.5)) is not None
    assert refused(S.test_forall(S.test_choices(()), unary(TRUE), TRUE)) is not None
    assert refused(S.test_witness(S.test_choices(()), unary(TRUE), TRUE)) is not None
    assert refused(S.test_lists(S.test_integers(S.bad, 3), 1, 1)) is not None
    assert refused(S.test_forall(S.test_choices((S.a,)), unary(S.test_integers(S.bad, 3)), (TRUE,))) is not None


#: MEASURED: all 48 claims, including literal generators and failed bag checks.
#: The example pays 174886 inferences.
#: [measured: 175727 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/43-testing_lib.metta;
#: fixture=lib_testing with engine/lib QLF artifacts purged; commit=a283d39342d891aae0edc58949e2ccbb48911cd8].
BUDGET = 175727
