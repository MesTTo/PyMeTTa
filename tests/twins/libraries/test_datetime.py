"""The Python twin of examples/libraries/test_datetime.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 43618


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_datetime))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_datetime"])))

    # !(test (let $ts (now) (< 1735689600 $ts)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["let"], V["ts"], expr(S["now"]), expr(S["<"], 1735689600, V["ts"])),
            val(value=True),
        )
    )

    # !(test (let $ts (now)
    #          (== (format-date $ts "%Y-%m-%d") (format-date $ts "%Y-%m-%d")))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["ts"],
                expr(S["now"]),
                expr(
                    S["=="],
                    expr(S["format-date"], V["ts"], val("%Y-%m-%d")),
                    expr(S["format-date"], V["ts"], val("%Y-%m-%d")),
                ),
            ),
            val(value=True),
        )
    )

    # !(let* (($ts 1766188800)
    #         ($dow (day-of-week $ts)))
    #     ($dow))
    yield m.eval(
        expr(
            S["let*"],
            expr(expr(V["ts"], 1766188800), expr(V["dow"], expr(S["day-of-week"], V["ts"]))),
            expr(V["dow"]),
        )
    )

    # !(test (day-of-week 1766188800) Saturday)
    yield m.eval(expr(S["test"], expr(S["day-of-week"], 1766188800), S["Saturday"]))

    # !(let* (($ts1 1735689600)
    #         ($ts2 1736294400)
    #         ($diff (- $ts2 $ts1)))
    #     ($diff))
    yield m.eval(
        expr(
            S["let*"],
            expr(
                expr(V["ts1"], 1735689600),
                expr(V["ts2"], 1736294400),
                expr(V["diff"], expr(S["-"], V["ts2"], V["ts1"])),
            ),
            expr(V["diff"]),
        )
    )

    # !(test (- 1736294400 1735689600) 604800)
    yield m.eval(expr(S["test"], expr(S["-"], 1736294400, 1735689600), 604800))

    # !(let* (($ts 1735725045)
    #         ($time-only (format-date $ts "%H:%M:%S")))
    #     ($time-only))
    yield m.eval(
        expr(
            S["let*"],
            expr(
                expr(V["ts"], 1735725045),
                expr(V["time-only"], expr(S["format-date"], V["ts"], val("%H:%M:%S"))),
            ),
            expr(V["time-only"]),
        )
    )

    # !(test (format-date 1735689600 "%B") January)
    yield m.eval(expr(S["test"], expr(S["format-date"], 1735689600, val("%B")), S["January"]))

    yield from ()
