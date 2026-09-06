"""Purpose: charge carrier predicates to the tagged evaluation's resource quota.

Guarantees:
  - initial tags and operation inputs/results share one inference and time budget
    [tested: this module; commit=WORKTREE]
Owns resources: each test drops its temporary declaration space.
"""

from collections import Counter

import pytest

from metta import S
from metta.algebra import AlgebraOperationError, evaluate
from metta.errors import EngineError, InferenceLimitError, TimeLimitError


@pytest.mark.parametrize("phase", ["fact", "rule", "input", "result"])
def test_carrier_predicate_inferences_are_bounded_at_every_phase(metta, phase):
    """The predicate's finite recursive work must stop inside its own check."""
    trigger, occurrence = {"fact": (2, 1), "rule": (3, 1), "input": (3, 2), "result": (6, 1)}[phase]
    with metta._new_space() as space:
        space.run("(= (carrier-spin $n) (if (== $n 0) True (carrier-spin (- $n 1))))")
        calls = Counter()

        def admits(value):
            calls[value] += 1
            if value == trigger and calls[value] == occurrence:
                assert space.eval(S.carrier_spin(20000)) == [True]
            return isinstance(value, int)

        space.algebra("bounded-carrier", combine="max", extend="*", zero=0, one=1, type=admits)
        space.add_tagged_fact(2, S.base(S.a))
        space.add_tagged_rule(3, S.result(S.a), S.base(S.a))
        with pytest.raises(InferenceLimitError, match="the 20000 inference limit was reached"):
            evaluate(space, S.result(S.a), algebra="bounded-carrier", inferences=20_000)
        assert calls[trigger] == occurrence
        assert space.eval(S["+"](1, 2)) == [3]


def test_carrier_checks_debit_one_quota_across_initial_facts(metta):
    """Many cheap checks cannot each restart the evaluation's allowance."""
    with metta._new_space() as space:
        checked = []

        def admits(value):
            checked.append(value)
            return isinstance(value, int)

        space.algebra("many-carrier-checks", combine="max", extend="*", zero=0, one=1, type=admits)
        for value in range(80):
            space.add_tagged_fact(value, S.base(value))
        checked.clear()
        with pytest.raises(InferenceLimitError, match="the 5000 inference limit was reached"):
            evaluate(space, S.base(S.missing), algebra="many-carrier-checks", inferences=5000)
        assert 0 < len(checked) < 80


def test_carrier_predicate_respects_the_enclosing_time_limit(metta):
    """A type predicate's nested engine work inherits the outer deadline."""
    with metta._new_space() as space:
        space.run("(= (carrier-spin $n) (if (== $n 0) True (carrier-spin (- $n 1))))")
        finished = []

        def admits(value):
            if value == 2:
                assert space.eval(S.carrier_spin(2000000)) == [True]
                finished.append(value)
            return isinstance(value, int)

        space.algebra("timed-carrier", combine="max", extend="*", zero=0, one=1, type=admits)
        space.add_tagged_fact(2, S.base(S.a))
        with pytest.raises(TimeLimitError, match=r"the 0\.1 second time limit was reached"):
            evaluate(space, S.base(S.a), algebra="timed-carrier", timeout=0.1)
        assert not finished
        assert space.eval(S["+"](1, 2)) == [3]


def test_carrier_failure_text_cannot_impersonate_a_resource_signal(metta):
    """Only the raw engine term classifies a callback failure as exhaustion."""
    with metta._new_space() as space:
        def admits(value):
            if value == 2:
                message = "Time limit exceeded"
                raise EngineError(message)
            return isinstance(value, int)

        space.algebra("failing-carrier", combine="max", extend="*", zero=0, one=1, type=admits)
        space.add_tagged_fact(2, S.base(S.a))
        with pytest.raises(AlgebraOperationError, match="Time limit exceeded"):
            evaluate(space, S.base(S.a), algebra="failing-carrier", timeout=1.0)
