"""Purpose: control signals cross the evaluator whole. The engine's
recovery catches (reduce, the type probes, the specializer, a program's
own (catch ...)) rethrow limits, alarms, and interrupts instead of eating
them, so a bound or a cancellation cannot be defused by the very
evaluation it is bounding.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import errors
from metta.errors import EngineError, InferenceLimitError, TimeLimitError


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def test_control_signals_pass_through_recovery_catches(m):
    """A swallowed limit signal DISARMED the budget before the fix,
    measured as six million inferences spent under a thousand-step bound
    when the raise landed inside a recovery catch mid-translation.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (deep-spin $n) (if (== $n 0) done (deep-spin (- $n 1))))")
    with pytest.raises(InferenceLimitError):
        m.eval("(== (deep-spin 3000000) done)", inferences=1_000)
    with pytest.raises(TimeLimitError):
        # The depth bound is raised for this one probe so WALL CLOCK is what
        # ends it. Since P14.8 gave m.eval the fuel scope a runnable form has,
        # a hundred-million-step recursion answers (Error ... StackOverflow)
        # after the default 100,000 reductions, which is far inside 0.05s, and
        # the timeout this line exists to observe would never arrive.
        m.eval(
            "(with-pragma! ((max-stack-depth 100000000)) (progn (deep-spin 100000000)))",
            timeout=0.05,
        )
    with pytest.raises(InferenceLimitError):
        # A program's own (catch ...) cannot eat the signal either, the
        # KeyboardInterrupt-outside-Exception design.
        m.eval("(catch (deep-spin 3000000))", inferences=1_000)
    # Real host errors still take the recovery: catch answers its Error term.
    # Integer division by zero is already an Error answer and needs no catch.
    (answer,) = m.eval("(catch (+ $left $right))")
    assert str(answer).startswith("(Error ")


@pytest.mark.parametrize(
    ("kind", "error_name"),
    [
        ("syntax", "MettaSyntaxError"),
        ("time_limit", "TimeLimitError"),
        ("inference_limit", "InferenceLimitError"),
        ("interrupted", "Interrupted"),
    ],
)
def test_reserved_exception_shape_maps_by_kind(m, kind, error_name):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    error_type = getattr(errors, error_name)
    with pytest.raises(error_type):
        m.runtime.must("metta_py_raise(Kind, detail)", Kind=kind)


@pytest.mark.parametrize(
    "sentinel",
    [
        "metta_syntax_error",
        "metta_py_time_limit",
        "metta_py_inference_limit",
        "metta_host_interrupted",
    ],
)
def test_exception_names_nested_in_other_terms_stay_engine_errors(m, sentinel):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError) as failure:
        m.runtime.must(f"throw(error(type_error({sentinel}, oops), none))")
    assert type(failure.value) is EngineError
