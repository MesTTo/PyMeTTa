"""Purpose: a failing MeTTa assertion is its own kind of exception, so a
harness can tell "the program said something false" from "the engine broke"
by type rather than by reading a sentence.
Guarantees:
  - a failing (test ...) and a failing (assert ...) raise AssertionFailure,
    and an engine fault raises EngineError, and neither is an instance of the
    other [tested test_a_failing_assertion_is_a_different_exception_from_an_engine_fault]
  - the raised AssertionFailure carries the form, the actual value and the
    expected value as data [tested test_an_assertion_failure_carries_its_parts]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa, MettaError
from metta.errors import AssertionFailure, EngineError


def test_a_failing_assertion_is_a_different_exception_from_an_engine_fault():
    """A program that asserts something false and an engine that breaks are
    different events. Before this they were the same Python type, so a
    harness could only tell them apart by parsing the message.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa().self

    with pytest.raises(AssertionFailure) as failed_test:
        m.run("!(test (+ 1 1) 3)")
    with pytest.raises(AssertionFailure) as failed_assert:
        m.run("!(assert (== 1 2))")

    # An engine fault: a host exception crossing back out of an operation.
    # Whatever else it is, it must not be an assertion failure.
    def boom():
        msg = "the op broke"
        raise RuntimeError(msg)

    m.op(boom, name="petta-broken-op", effect="pureStructural")
    with pytest.raises(EngineError) as fault:
        m.run("!(petta-broken-op)")

    assert not isinstance(fault.value, AssertionFailure)
    assert not isinstance(failed_test.value, EngineError)
    assert not isinstance(failed_assert.value, EngineError)
    # Both remain catchable by the one base a caller wraps a whole run in.
    for caught in (failed_test.value, failed_assert.value, fault.value):
        assert isinstance(caught, MettaError)


def test_an_assertion_failure_carries_its_parts():
    """The parts arrive as data, so a harness reports them without parsing
    the sentence: which form failed, what it got, what it wanted.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa().self

    with pytest.raises(AssertionFailure) as caught:
        m.run("!(test (+ 1 1) 3)")
    assert caught.value.operation == "test"
    assert caught.value.actual == 2
    assert caught.value.expected == 3

    with pytest.raises(AssertionFailure) as caught:
        m.run("!(assert (== 1 2))")
    assert caught.value.operation == "assert"

    with pytest.raises(AssertionFailure) as caught:
        m.run("!(test (empty) 3)")
    assert caught.value.operation == "test"
    assert caught.value.actual is None
