"""examples/libraries/datetime.metta in Python: clocks and calendars.

`now`, `day-of-week` and `format-date` are lib_datetime's own and the subject
of the file, so the twin names them. Everything around them is Python: the
example's `let` and `let*` bindings are assignments and its comparison of two
readings is Python's `==`.

Two of the example's three bare demonstration forms bind an intermediate name
and hand it to the claim written just below them, so the Python that says both
is the claim itself, with the `let*` it translates on the line. The third has
no claim under it and reads the clock in local time, so it PRINTS, which is
what a top-level `!` form does in the example's own run.

What is checkable about a clock is that it runs forward from a date already
past and that formatting one reading twice is stable; the fixed timestamps
check `format-date`'s output itself.
"""

from metta import G, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1

#: 2025-01-01T00:00:00Z, a date already past, so a live clock is after it.
NEW_YEAR_2025 = 1735689600

#: strftime patterns are text, and text is what a string is for.
ISO_DAY, CLOCK, MONTH_NAME = G("%Y-%m-%d"), G("%H:%M:%S"), G("%B")


def twin(m):
    """Read the clock, then format and name three fixed timestamps."""
    m.fn["import!"](m, S.library(S["lib_datetime"]))

    now = m.fn.now
    # (let $ts (now) (< 1735689600 $ts))
    assert now().one() > NEW_YEAR_2025

    # One reading, formatted twice: a live clock is stable within one reading
    # and would not be across two.
    format_date = m.fn.format_date
    reading = now().one()
    assert format_date(reading, ISO_DAY).one() == format_date(reading, ISO_DAY).one()

    # (let* (($ts 1766188800) ($dow (day-of-week $ts))) ($dow))
    a_saturday = 1766188800
    assert m.fn.day_of_week(a_saturday) == [S.Saturday]

    # (let* (($ts1 ...) ($ts2 ...) ($diff (- $ts2 $ts1))) ($diff)): both
    # operands are ground, so the subtraction is Python's own.
    assert 1736294400 - NEW_YEAR_2025 == 604800

    # (let* (($ts 1735725045) ($time-only (format-date $ts "%H:%M:%S"))) ($time-only)):
    # a wall-clock reading, so what it prints moves with the machine's zone.
    print(format_date(1735725045, CLOCK))

    assert format_date(NEW_YEAR_2025, MONTH_NAME) == [S.January]
