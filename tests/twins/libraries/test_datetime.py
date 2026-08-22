"""examples/libraries/test_datetime.metta in Python: clocks and calendars.

`now`, `day-of-week` and `format-date` are lib_datetime's own and the subject
of the file, so the twin names them. Everything around them is Python: the
example's `let` and `let*` bindings are assignments, its comparison of two
readings is Python's `==`, and its bare demonstration forms print.

What is checkable about a clock is that it runs forward from a date already
past and that formatting one reading twice is stable; the fixed timestamps
check `format-date`'s output itself.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 43618 to 37448, -6170 (-14.15%), by the idiomatic
#: rewrite: five `test` wrappers, three `let*` chains and the timestamp
#: subtraction left the engine for `assert`, assignment and Python's own
#: arithmetic; the clock, the calendar and the formatter still run there.
#: Measured min-of-three with the MORK backend linked into this worktree,
#: which the earlier figure may not have been. Prior: 43618 was the last
#: figure for the generator twin that yielded `m.eval(S.test(...))` once per
#: runnable form.
BUDGET = 37448

#: 2025-01-01T00:00:00Z, a date already past, so a live clock is after it.
NEW_YEAR_2025 = 1735689600


def twin(m):
    """Read the clock, then format and name three fixed timestamps."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_datetime)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    assert m.fn("now")() > NEW_YEAR_2025

    # One reading, formatted twice: a live clock is stable within one reading
    # and would not be across two.
    format_date = m.fn("format-date")
    reading = m.fn("now")()
    assert format_date(reading, val("%Y-%m-%d")) == format_date(reading, val("%Y-%m-%d"))

    day_of_week = m.fn("day-of-week")
    stamp = 1766188800
    print(day_of_week(stamp))
    assert day_of_week(stamp) == S.Saturday

    # A week apart, which is arithmetic and therefore Python's.
    week = 1736294400 - NEW_YEAR_2025
    print(week)
    assert week == 604800

    print(format_date(1735725045, val("%H:%M:%S")))
    assert format_date(NEW_YEAR_2025, val("%B")) == S.January
