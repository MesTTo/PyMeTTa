"""examples/libraries/test_datetime.metta in Python: clocks and calendars.

`now`, `day-of-week` and `format-date` are lib_datetime's own and the subject
of the file, so the twin names them. Everything around them is Python: the
example's `let` and `let*` bindings are assignments, its comparison of two
readings is Python's `==`, and its bare demonstration forms print.

What is checkable about a clock is that it runs forward from a date already
past and that formatting one reading twice is stable; the fixed timestamps
check `format-date`'s output itself.
"""

from petta import G, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1

#: 2025-01-01T00:00:00Z, a date already past, so a live clock is after it.
NEW_YEAR_2025 = 1735689600


def twin(m):
    """Read the clock, then format and name three fixed timestamps."""
    m.fn["import!"](m, S.library(S["lib_datetime"]))

    now = m.fn.now
    assert now().one() > NEW_YEAR_2025

    # One reading, formatted twice: a live clock is stable within one reading
    # and would not be across two.
    format_date = m.fn.format_date
    reading = now().one()
    assert format_date(reading, G("%Y-%m-%d")).one() == format_date(reading, G("%Y-%m-%d")).one()

    day_of_week = m.fn.day_of_week
    stamp = 1766188800
    print(day_of_week(stamp))
    assert day_of_week(stamp) == [S.Saturday]

    # A week apart, which is arithmetic and therefore Python's.
    week = 1736294400 - NEW_YEAR_2025
    print(week)
    assert week == 604800

    print(format_date(1735725045, G("%H:%M:%S")))
    assert format_date(NEW_YEAR_2025, G("%B")) == [S.January]
