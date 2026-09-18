"""Purpose: a tagged rule's `where` guard is its side condition over the premise tags.

Guarantees:
  - a rule stored with `(where G)` derives an instance only where G over
    the premise tags answers True, on the derived route and on the engine's
    fixpoint alike, and a callable guard registers under its own name
    [tested: test_a_guard_keeps_only_the_instances_it_admits,
    test_a_callable_guard_registers_under_its_name; commit=WORKTREE].
  - the retained derivation shows the guard that held, and a guarded
    instance is not reinterpreted under another carrier, since it exists
    because its guard held over the tags of the carrier it ran under
    [tested: test_a_derivation_shows_its_guard_and_is_not_reinterpreted;
    commit=WORKTREE].
  - a guard that answers no truth value is refused by name on both routes
    [tested: test_a_guard_that_answers_no_truth_value_is_refused; commit=WORKTREE].
  - a guard reads the labels of the carrier the program is asked in: under
    counting every fact is one, so a probability threshold admits every
    instance, derived rather than counted by the proof-tree shortcut, and
    the witnesses of a tabled answer follow the answer's own carrier
    [tested: test_counting_on_a_guarded_program_reads_countings_own_labels;
    commit=WORKTREE].
"""

import pytest

import metta.algebra as algebra_module
from metta import S, V
from metta.algebra import AlgebraEvaluationError, AlgebraOperationError, evaluate


def _scored(space):
    space.add_tagged_fact(0.6, S.score(S.a))
    space.add_tagged_fact(0.3, S.score(S.b))
    space.add(S["="](S["above-half"](V.s), S[">"](V.s, 0.5)))


def test_a_guard_keeps_only_the_instances_it_admits(metta):
    """The guard is a function of the premise tags in order, answering True or False."""
    with metta._new_space() as space:
        _scored(space)
        stored = space.add_tagged_rule(1, S.trusted(V.x), S.score(V.x), where=S["above-half"])
        assert stored.children[4] == S.where(S["above-half"])
        for derivations in (True, False):
            answers = evaluate(space, S.trusted(V.x), algebra="prob", derivations=derivations).answers
            assert [(answer.value, answer.annotation) for answer in answers] == [(S.trusted(S.a), pytest.approx(0.6))]


def test_a_callable_guard_registers_under_its_name(metta):
    """A Python guard registers like a callable tag and the rule stores its name."""
    with metta._new_space() as space:
        _scored(space)

        def strong(score):
            return score > 0.5

        stored = space.add_tagged_rule(1, S.trusted(V.x), S.score(V.x), where=strong)
        assert stored.children[4] == S.where(S["rule-strong"])
        answers = evaluate(space, S.trusted(V.x), algebra="prob").answers
        assert [answer.value for answer in answers] == [S.trusted(S.a)]


def test_a_derivation_shows_its_guard_and_is_not_reinterpreted(metta):
    """why() names the guard that held; under() refuses a guarded instance by name."""
    with metta._new_space() as space:
        _scored(space)
        space.add_tagged_rule(1, S.trusted(V.x), S.score(V.x), where=S["above-half"])
        answer = space.match(S.trusted(S.a), under=algebra_module.prob).one()
        assert "where (above-half 0.6) held" in str(answer.why())
        with pytest.raises(AlgebraEvaluationError, match="guard_not_reinterpretable"):
            answer.under(algebra_module.tropical)


def test_counting_on_a_guarded_program_reads_countings_own_labels(metta):
    """A guard reads the labels of the carrier the program is asked in.

    Under counting every fact is one, so a threshold written for
    probabilities admits both scores; the count is the derived instances,
    not the proof-tree shortcut, which never computes the tags a guard
    reads. The witnesses under prob are what the threshold meant.
    """
    with metta._new_space() as space:
        _scored(space)
        space.add_tagged_rule(1, S.trusted(V.x), S.score(V.x), where=S["above-half"])
        assert space.match(S.trusted(V.x), under=algebra_module.counting).one().annotation == 2
        admitted = space.match(S.trusted(V.x), under=algebra_module.prob, derivations=False)
        assert [answer.value for answer in admitted] == [S.trusted(S.a)]
        assert len(admitted.one().why().alternatives) == 1


def test_a_guard_that_answers_no_truth_value_is_refused(metta):
    """A guard is a side condition, not a weight: a number is refused by name."""
    with metta._new_space() as space:
        _scored(space)
        space.add(S["="](S.doubled(V.s), S["*"](V.s, 2)))
        space.add_tagged_rule(1, S.trusted(V.x), S.score(V.x), where=S.doubled)
        with pytest.raises(AlgebraOperationError, match="guard_not_boolean"):
            evaluate(space, S.trusted(V.x), algebra="prob", derivations=True)
        with pytest.raises(Exception, match="guard_not_boolean"):
            evaluate(space, S.trusted(V.x), algebra="prob", derivations=False)
