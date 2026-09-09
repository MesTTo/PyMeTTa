"""Purpose: classify a false MeTTa claim separately from an engine fault.

``AssertionFailure`` carries the failed form and its observed values, so a
test harness can report a red program assertion without misdiagnosing the
interpreter beneath it.
"""

from _common import check, done

from metta import MeTTa, S, V
from metta._errors.errors import AssertionFailure, MettaResultError

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

    space.add('(log failed (Error (job 1) "boom"))', "(log ok fine)")
    clean = space.match(S.log(S.ok, V.value))
    check("clean rows chain through the error bridge", clean.raise_for_errors() is clean)
    try:
        space.match(S.log(S.failed, V.value)).raise_for_errors()
    except MettaResultError as failure:
        check("stored error data raises on request", str(failure.culprit), "(job 1)")
    else:
        msg = "raise_for_errors left an Error cell as data"
        raise AssertionError(msg)

done("error_handling")
