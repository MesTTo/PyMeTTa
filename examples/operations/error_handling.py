"""Purpose: classify a false MeTTa claim separately from an engine fault.

``AssertionFailure`` carries the failed form and its observed values, so a
test harness can report a red program assertion without misdiagnosing the
interpreter beneath it.
"""

from _common import check, done

from metta import MeTTa
from metta.errors import AssertionFailure

with MeTTa() as context:
    space = context.space()
    try:
        space.run("!(test (+ 1 1) 3)")
    except AssertionFailure as failure:
        check("the failed form is structured", failure.operation, "test")
        check("the actual result is structured", failure.actual, 2)
        check("the expected result is structured", failure.expected, 3)
    else:
        msg = "a false MeTTa test did not raise AssertionFailure"
        raise AssertionError(msg)

done("error_handling")
