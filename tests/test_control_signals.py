"""Purpose: control signals cross the evaluator whole. The engine's
recovery catches (reduce, the type probes, the specializer, a program's
own (catch ...)) rethrow limits, alarms, and interrupts instead of eating
them, so a bound or a cancellation cannot be defused by the very
evaluation it is bounding.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

import petta
from petta import EngineError, InferenceLimitError, TimeLimitError


@pytest.fixture()
def m(metta):
    with metta.new_space() as space:
        yield space


def test_control_signals_pass_through_recovery_catches(m):
    """A swallowed limit signal DISARMED the budget before the fix,
    measured as six million inferences spent under a thousand-step bound
    when the raise landed inside a recovery catch mid-translation."""
    m.run("(= (deep-spin $n) (if (== $n 0) done (deep-spin (- $n 1))))")
    with pytest.raises(InferenceLimitError):
        m.eval("(== (deep-spin 3000000) done)", inferences=1_000)
    with pytest.raises(TimeLimitError):
        m.eval("(progn (deep-spin 100000000))", timeout=0.05)
    with pytest.raises(InferenceLimitError):
        # A program's own (catch ...) cannot eat the signal either, the
        # KeyboardInterrupt-outside-Exception design.
        m.eval("(catch (deep-spin 3000000))", inferences=1_000)
    # Real errors still take the recovery: catch answers its Error term.
    (answer,) = m.eval("(catch (/ 1 0))")
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
def test_reserved_exception_shape_maps_by_kind(m, kind, error_name):
    error_type = getattr(petta, error_name)
    with pytest.raises(error_type):
        m.runtime.must("petta_py_raise(Kind, detail)", Kind=kind)


@pytest.mark.parametrize(
    "sentinel",
    [
        "petta_syntax_error",
        "petta_py_time_limit",
        "petta_py_inference_limit",
        "petta_py_interrupted",
    ],
)
def test_exception_names_nested_in_other_terms_stay_engine_errors(m, sentinel):
    with pytest.raises(EngineError) as failure:
        m.runtime.must(f"throw(error(type_error({sentinel}, oops), none))")
    assert type(failure.value) is EngineError
