"""The Python twin of examples/libraries/regex_lib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 60456


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_regex))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_regex"])))

    # !(test (re-match "(?i)^needle" "Needle in a haystack") True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["re-match"], val("(?i)^needle"), val("Needle in a haystack")),
            val(value=True),
        )
    )

    # !(test (re-match "^x" "abc") False)
    yield m.eval(expr(S["test"], expr(S["re-match"], val("^x"), val("abc")), val(value=False)))

    # !(test (collapse (re-find "\\d+" "a1 b22 c333")) ("1" "22" "333"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["re-find"], val("\\d+"), val("a1 b22 c333"))),
            expr(val("1"), val("22"), val("333")),
        )
    )

    # !(test (re-captures "(?<year_I>\\d\\d\\d\\d)-(?<month_I>\\d\\d)" "2017-04-20")
    #        ((0 "2017-04") (month 4) (year 2017)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["re-captures"],
                val("(?<year_I>\\d\\d\\d\\d)-(?<month_I>\\d\\d)"),
                val("2017-04-20"),
            ),
            expr(expr(0, val("2017-04")), expr(S["month"], 4), expr(S["year"], 2017)),
        )
    )

    # !(test (re-split ":\\s*" "Age: 33") ("Age" ": " "33"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["re-split"], val(":\\s*"), val("Age: 33")),
            expr(val("Age"), val(": "), val("33")),
        )
    )

    # !(test (re-replace-all "a+" "X" "banana") "bXnXnX")
    yield m.eval(
        expr(
            S["test"], expr(S["re-replace-all"], val("a+"), val("X"), val("banana")), val("bXnXnX")
        )
    )

    # !(test (re-replace "(?<y>\\d+)" "[$y]" "n 42 n") "n [42] n")
    yield m.eval(
        expr(
            S["test"],
            expr(S["re-replace"], val("(?<y>\\d+)"), val("[$y]"), val("n 42 n")),
            val("n [42] n"),
        )
    )

    yield from ()
