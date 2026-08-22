"""The Python twin of examples/libraries/test_datetime.metta.

Clock reading, weekday naming, and stable date formatting.

`now` answers the current Unix time, so a form that PRINTS it verifies nothing
and cannot be reproduced. What is checkable about a clock is that it runs
forward from a date already past and that formatting one reading is stable, so
those are the two assertions; the fixed timestamps below check `format-date`'s
output itself.

`(< 1735689600 $ts)` and `(- $ts2 $ts1)` are built by Python's own operators,
because an operand that is a variable makes the operator a builder. The other
two name their heads: `(- 1736294400 1735689600)` is over two ground numbers,
where Python's `-` answers 604800 before any term exists, and Python's `==`
between atoms is structural equality rather than a builder.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 43618 to 43618, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 43618 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 43618

#: The format strings, which are DATA the library reads rather than names.
ISO_DAY, CLOCK, MONTH = val("%Y-%m-%d"), val("%H:%M:%S"), val("%B")


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_datetime))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_datetime)))

    # !(test (let $ts (now) (< 1735689600 $ts)) True)
    yield m.eval(
        S.test(S.let(V.ts, S.now(), 1735689600 < V.ts), TRUE)
    )
    # !(test (let $ts (now)
    #          (== (format-date $ts "%Y-%m-%d") (format-date $ts "%Y-%m-%d")))
    #        True)
    yield m.eval(
        S.test(
            S.let(
                V.ts,
                S.now(),
                S["=="](
                    S["format-date"](V.ts, ISO_DAY),
                    S["format-date"](V.ts, ISO_DAY),
                ),
            ),
            TRUE,
        )
    )

    # !(let* (($ts 1766188800)
    #         ($dow (day-of-week $ts)))
    #     ($dow))
    yield m.eval(
        S["let*"](
            ((V.ts, 1766188800), (V.dow, S["day-of-week"](V.ts))),
            (V.dow,),
        )
    )
    # !(test (day-of-week 1766188800) Saturday)
    yield m.eval(S.test(S["day-of-week"](1766188800), S.Saturday))

    # !(let* (($ts1 1735689600)
    #         ($ts2 1736294400)
    #         ($diff (- $ts2 $ts1)))
    #     ($diff))
    yield m.eval(
        S["let*"](
            (
                (V.ts1, 1735689600),
                (V.ts2, 1736294400),
                (V.diff, V.ts2 - V.ts1),
            ),
            (V.diff,),
        )
    )
    # !(test (- 1736294400 1735689600) 604800)
    yield m.eval(S.test(S["-"](1736294400, 1735689600), 604800))

    # !(let* (($ts 1735725045)
    #         ($time-only (format-date $ts "%H:%M:%S")))
    #     ($time-only))
    yield m.eval(
        S["let*"](
            (
                (V.ts, 1735725045),
                (V["time-only"], S["format-date"](V.ts, CLOCK)),
            ),
            (V["time-only"],),
        )
    )
    # !(test (format-date 1735689600 "%B") January)
    yield m.eval(S.test(S["format-date"](1735689600, MONTH), S.January))
