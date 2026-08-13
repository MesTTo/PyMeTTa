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


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def test_control_signals_pass_through_recovery_catches(m):
    """A swallowed limit signal DISARMED the budget before the fix,
    measured as six million inferences spent under a thousand-step bound
    when the raise landed inside a recovery catch mid-translation."""
    from petta import InferenceLimitError, TimeLimitError

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
