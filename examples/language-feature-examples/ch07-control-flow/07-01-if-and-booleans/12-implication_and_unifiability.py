"""examples/ch07-control-flow/07-01-if-and-booleans/12-implication_and_unifiability.metta in Python: three questions about two atoms.

`implies` is the connective `and`, `or` and `not` leave out. `=?` asks
whether two atoms COULD be made equal without making them so, and
`if-equal2` asks whether they already agree up to a renaming: two different
questions, and the pair that separates them is `(f $x)` against `(f 1)`.

The four relations are a `@m.rules` bundle rather than stacked `@m.define`
clauses, because `age` and `registered?` each have two clauses that COEXIST
and a stacked define reads as first-match. `registered?` and `adult?` and
`may-vote?` carry a `?` Python cannot spell, so they come through the exact
subscript door, which is rung 5 and the one the ladder keeps for a head
outside identifier grammar.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, S, V, equation, fn


def twin(m):
    """Material implication, unifiability, and alpha-equivalence."""
    # Each handle is resolved ONCE: `m.fn[...]` asks the engine on every
    # access, about 1,200 inferences a name, which is most of a small twin.
    implies, unifiable = m.fn.implies, m.fn["=?"]
    renamed_or_not = m.fn.if_equal2

    # False implies anything, and only a true antecedent with a false
    # consequent is False.
    assert implies(FALSE, FALSE) == [True]
    assert implies(FALSE, TRUE) == [True]
    assert implies(TRUE, TRUE) == [True]
    assert implies(TRUE, FALSE) == [False]

    # Three bundles, one per relation, because `@m.rules` is the door for
    # equations that COEXIST: stacked `@m.define` clauses read as first-match,
    # which would make the second age and the second registration unreachable.
    @m.rules
    def ages():
        """(= (age ann) 30) and (= (age bo) 12)."""
        yield equation(S.age(S.ann)).to(30)
        yield equation(S.age(S.bo)).to(12)

    @m.rules
    def registrations():
        """(= (registered? ann) True) and (= (registered? bo) True)."""
        yield equation(S["registered?"](S.ann)).to(TRUE)
        yield equation(S["registered?"](S.bo)).to(TRUE)

    @m.rules
    def eligibility(person):
        """The guard shape "if this holds then that must too", written once."""
        # (= (adult? $p) (> (age $p) 17))
        yield equation(S["adult?"](person)).to(S.age(person).gt(17))
        # (= (may-vote? $p) (implies (registered? $p) (adult? $p)))
        yield equation(S["may-vote?"](person)).to(
            fn.implies(S["registered?"](person), S["adult?"](person))
        )

    # Resolved after the bundle, because a handle names a function that
    # exists.
    may_vote = m.fn["may-vote?"]
    assert may_vote(S.ann) == [True]
    assert may_vote(S.bo) == [False]

    # `=?` answers whether two atoms COULD be made equal, and binds neither.
    assert unifiable(S.f(V.x), S.f(1)) == [True]
    assert unifiable(S.f(2), S.f(1)) == [False]
    assert unifiable(V.a, V.b) == [True]
    assert unifiable(S.f(V.x), S.g(V.x)) == [False]

    # Nothing is bound, so the same variable answers True against two atoms
    # that cannot both be true of it.
    assert unifiable(S.f(V.x), S.f(1)) == [True] and unifiable(S.f(V.x), S.f(2)) == [True]

    # `if-equal2` is alpha-equivalence rather than unifiability.
    assert renamed_or_not(S.f(V.x), S.f(V.y), S.renamed, S.different) == [S.renamed]
    assert renamed_or_not(S.f(V.x), S.f(1), S.renamed, S.different) == [S.different]
    assert renamed_or_not(S.f(V.x, V.x), S.f(V.y, V.z), S.renamed, S.different) == [S.different]

    # So the two are genuinely different questions, and this is the pair that
    # separates them: (f $x) and (f 1) unify, and are not alpha-equivalent.
    assert unifiable(S.f(V.x), S.f(1)) == [True]
    assert renamed_or_not(S.f(V.x), S.f(1), S.renamed, S.different) == [S.different]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 12664 inferences, 0.7714x the example's 16417; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 12664
