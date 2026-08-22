r"""The Python twin of examples/libraries/regex_lib.metta.

PCRE2 regular expressions through lib_regex: boolean guards, nondeterministic
match enumeration, typed named captures, split, and replace.

Every pattern and subject is a MeTTa STRING, so each is carried whole through
`val(...)`, which is the door for a Python value that is data rather than a
name. A MeTTa string reads `\\` as one backslash, so `"\\d"` spells the regex
`\d`, the same convention as Python's non-raw strings, and the twin keeps the
source's own spelling rather than a raw-string equivalent. This docstring is
itself raw so the backslashes above are the ones you would type.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 60456 to 60456, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 60456 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 60456


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_regex))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_regex)))

    # !(test (re-match "(?i)^needle" "Needle in a haystack") True)
    yield m.eval(
        S.test(
            S["re-match"](val("(?i)^needle"), val("Needle in a haystack")), TRUE
        )
    )
    # !(test (re-match "^x" "abc") False)
    yield m.eval(S.test(S["re-match"](val("^x"), val("abc")), FALSE))

    # !(test (collapse (re-find "\\d+" "a1 b22 c333")) ("1" "22" "333"))
    yield m.eval(
        S.test(
            S.collapse(S["re-find"](val("\\d+"), val("a1 b22 c333"))),
            (val("1"), val("22"), val("333")),
        )
    )

    # !(test (re-captures "(?<year_I>\\d\\d\\d\\d)-(?<month_I>\\d\\d)" "2017-04-20")
    #        ((0 "2017-04") (month 4) (year 2017)))
    yield m.eval(
        S.test(
            S["re-captures"](
                val("(?<year_I>\\d\\d\\d\\d)-(?<month_I>\\d\\d)"),
                val("2017-04-20"),
            ),
            ((0, val("2017-04")), (S.month, 4), (S.year, 2017)),
        )
    )

    # !(test (re-split ":\\s*" "Age: 33") ("Age" ": " "33"))
    yield m.eval(
        S.test(
            S["re-split"](val(":\\s*"), val("Age: 33")),
            (val("Age"), val(": "), val("33")),
        )
    )

    # !(test (re-replace-all "a+" "X" "banana") "bXnXnX")
    yield m.eval(
        S.test(
            S["re-replace-all"](val("a+"), val("X"), val("banana")),
            val("bXnXnX"),
        )
    )
    # !(test (re-replace "(?<y>\\d+)" "[$y]" "n 42 n") "n [42] n")
    yield m.eval(
        S.test(
            S["re-replace"](val("(?<y>\\d+)"), val("[$y]"), val("n 42 n")),
            val("n [42] n"),
        )
    )
