"""Purpose: sets as ordered expressions, from Python.

A set is an expression, so it comes back as one and a tuple goes in as one;
`len` is the cardinality and `==` the equality, because the representation is
canonical. A refusal is what `if-error` reads, so it is caught as the error it is.

Guarantees: the same claims as 23-sets_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/23-sets_lib.metta; commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, lib
from metta._errors.errors import MettaError


def twin(m):
    """Build, ask, insert, remove, merge, compare and refuse."""
    m += lib.sets
    m += lib.functional

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def elements(answers):
        """One answer's expression, as a list."""
        return list(answers.one())

    set_of, is_set = m.fn.set_of, m.fn.set_is
    member, insert, remove = m.fn.set_member, m.fn.set_insert, m.fn.set_remove
    union, intersection = m.fn.set_union, m.fn.set_intersection
    difference, symmetric = m.fn.set_difference, m.fn.set_symmetric_difference
    subset, disjoint = m.fn.set_subset, m.fn.set_disjoint

    # A set is an expression in the standard order of terms with no duplicates,
    # so set-of sorts and deduplicates once and the answer is an ordinary
    # expression: len counts it, == compares it and () is the empty set.
    assert elements(set_of((3, 1, 2, 1))) == [1, 2, 3]
    assert elements(set_of(())) == []
    assert len(set_of((S.b, S.a, S.b)).one()) == 2
    assert set_of((2, 1)).one() == set_of((1, 2, 2)).one()
    # Numbers sort before symbols in the standard order, and a symbol before an
    # expression, so a mixed set has a fixed shape whatever order it was written in.
    assert elements(set_of((S.b, (S.x,), 2, S.a, 1))) == [1, 2, S.a, S.b, S.x()]

    # set-is asks whether an expression already is one: ordered and without
    # duplicates. Every other head asks the same question before it merges.
    assert is_set((1, 2, 3)) == [True]
    assert is_set((2, 1)) == [False]
    assert is_set((1, 1)) == [False]
    assert is_set(3) == [False]

    # Membership compares TERMS rather than unifying, so a variable is not a
    # member of a set of numbers, where a match would have bound it to the first.
    assert member((1, 2, 3), 2) == [True]
    assert member((1, 2, 3), 4) == [False]
    assert member((1, 2, 3), V.x) == [False]

    # Insertion and removal answer a new set and leave the input alone; adding
    # what is there and removing what is not both answer the set unchanged.
    assert elements(insert((1, 3), 2)) == [1, 2, 3]
    assert elements(insert((1, 3), 3)) == [1, 3]
    assert elements(remove((1, 2, 3), 2)) == [1, 3]
    assert elements(remove((1, 2, 3), 9)) == [1, 2, 3]
    primes = set_of((2, 3, 5)).one()
    assert elements(insert(primes, 7)) == [2, 3, 5, 7]
    assert list(primes) == [2, 3, 5]

    # The four combinations preserve the canonical representation.
    assert elements(union((1, 3), (2, 3))) == [1, 2, 3]
    assert elements(intersection((1, 2, 3), (2, 3, 4))) == [2, 3]
    assert elements(difference((1, 2, 3), (2, 3, 4))) == [1]
    assert elements(difference((2, 3, 4), (1, 2, 3))) == [4]
    assert elements(symmetric((1, 2, 3), (2, 3, 4))) == [1, 4]
    assert elements(union((), ())) == []
    assert elements(intersection((1, 2), (3, 4))) == []

    # The same operations take any number of sets. Union has an empty identity;
    # intersection requires a set to supply its universe.
    assert elements(union((1, 2), (2, 3), (5,))) == [1, 2, 3, 5]
    assert elements(union()) == []
    assert elements(intersection((1, 2, 3), (2, 3, 4), (3, 4, 5))) == [3]
    assert refused(S.set_intersection())

    # The two questions between sets. A set is a subset of itself, the empty set
    # is a subset of everything and disjoint from everything, itself included.
    assert subset((1, 2), (1, 2, 3)) == [True]
    assert subset((1, 2, 3), (1, 2)) == [False]
    assert subset((), (1,)) == [True]
    assert subset((1, 2), (1, 2)) == [True]
    assert disjoint((1, 2), (3, 4)) == [True]
    assert disjoint((1, 2), (2, 3)) == [False]
    assert disjoint((), ()) == [True]

    # The laws hold because the representation is canonical: a union is the same
    # set whichever way round, and De Morgan's law is an equality of expressions.
    assert union((1, 2), (3,)).one() == union((3,), (1, 2)).one()
    universe = (1, 2, 3, 4)
    assert difference(universe, union((1,), (2,)).one()).one() == intersection(
        difference(universe, (1,)).one(), difference(universe, (2,)).one()
    ).one()

    # An argument that is not a set is refused rather than merged into nonsense:
    # the host's own merge over an unordered list answers (2 1 1) with nothing
    # said, which is the wrong answer with no symptom this library exists to remove.
    assert refused(S.set_union((2, 1), (1,)))
    assert refused(S.set_member((1, 1), 1))
    assert refused(S.set_union((1,), (2, 1)))

    arithmetic, error_data = S["+"](1, 2), S.Error(S.a, S.b)
    assert set_of(S.quote((arithmetic, error_data, arithmetic))) == [(arithmetic, error_data)]
    assert is_set(S.quote(error_data)) == [True]
    # Iteration keeps Error-headed collections as data, as it does any answer.
    assert list(union(S.quote(error_data), (S.a, S.c))) == [S.Error(S.a, S.b, S.c)]
    assert list(intersection(S.quote(error_data), S.quote(S.Error(S.a)))) == [S.Error(S.a)]
    assert member(S.quote((V.x,)), V.x) == [True]
    assert len(set_of((1, 1.0)).one()) == 2
    assert is_set(V.x) == [False]
    assert refused(S.set_intersection((2, 1)))

    assert elements(union((1, 2))) == [1, 2]
    assert elements(intersection((1, 2))) == [1, 2]
    assert elements(union((1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,))) == list(range(1, 10))
    assert elements(m.fn.apply_to(S.set_union, S.quote(((1, 2), (2, 3), (4,))))) == [1, 2, 3, 4]
    assert elements(m.fn.apply_to(S.set_intersection, S.quote(((1, 2, 3), (2, 3, 4), (3,))))) == [3]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 41 claims cover the thirteen heads, the laws and
#: the refusals; the example pays 63,725 inferences for the same work
#: [measured 2026-09-12: 71496 inferences, minimum of three serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/23-sets_lib.metta;
#: fixture=lib_sets at its functional commit, artifacts purged before the run;
#: commit=e3e8c891065765765ee8fe567c5eb6864e79b652].
#: RE-PINNED 2026-09-13, 71496 to 366379: collection operations now compose
#: MeTTa matching, folds and application; segment continuations are protected
#: compiler helpers. The example measures 348761 for the same claims
#: [measured: 366379 inferences; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/23-sets_lib.metta;
#: fixture=minimum of three serial fresh processes after purging engine/lib QLF;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 366379 to 367716 (+1337), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 367716 to 363631 (-4085), Math and Statistics derive
#: their recipes from MeTTa equations; Statistics consolidates finite laws and
#: adds reflective claims. Their collection dependencies share the proper
#: finite expression boundary in lib/_support/collections_data.pl [measured
#: 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6fa571d1b7059b610f73e9feed657711414251e5].
#: RE-PINNED 2026-09-13, 363631 to 363653 (+22), Vector, Math and the shared
#: collection boundary declare their native effects. The engine reads late
#: provider declarations and retains definition analysis for computed function
#: heads [measured 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=1d0b78a359f58de49f2f98bed50a6480d56cd5f6].
BUDGET = 363653

#: OVERRUN 2026-09-12, 1399: the example nests its law claims in one evaluation
#: each, where Python reads them as separate calls whose intermediate sets cross
#: into the host and back: the two equalities, De Morgan's five calls and the
#: bound primes are eight evaluations the example makes as three. Measured
#: 71496 against a ceiling of 70097.5, and the distance is those crossings
#: [measured 2026-09-12: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/23-sets_lib.metta;
#: commit=e3e8c891065765765ee8fe567c5eb6864e79b652].
#: RETIRED 2026-09-13: the new 366379 cost is within the example's 10% band;
#: the measured composition above needs no additional allowance.
