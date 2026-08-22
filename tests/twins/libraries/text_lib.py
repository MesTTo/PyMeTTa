"""The Python twin of examples/libraries/text_lib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 117082


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_string))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_string"])))

    # !(import! &self (library lib_file))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_file"])))

    # !(test (string-length "hello") 5)
    yield m.eval(expr(S["test"], expr(S["string-length"], val("hello")), 5))

    # !(test (string-slice "hello world" 0 5) "hello")
    yield m.eval(expr(S["test"], expr(S["string-slice"], val("hello world"), 0, 5), val("hello")))

    # !(test (string-slice "hello" 3 999) "lo")
    yield m.eval(expr(S["test"], expr(S["string-slice"], val("hello"), 3, 999), val("lo")))

    # !(test (string-slice "hello" 99 120) "")
    yield m.eval(expr(S["test"], expr(S["string-slice"], val("hello"), 99, 120), val("")))

    # !(test (string-split "," "a,b,c") ("a" "b" "c"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["string-split"], val(","), val("a,b,c")),
            expr(val("a"), val("b"), val("c")),
        )
    )

    # !(test (string-join ", " ("a" "b" "c")) "a, b, c")
    yield m.eval(
        expr(
            S["test"],
            expr(S["string-join"], val(", "), expr(val("a"), val("b"), val("c"))),
            val("a, b, c"),
        )
    )

    # !(test (string-trim "  padded  ") "padded")
    yield m.eval(expr(S["test"], expr(S["string-trim"], val("  padded  ")), val("padded")))

    # !(test (string-upper "shout") "SHOUT")
    yield m.eval(expr(S["test"], expr(S["string-upper"], val("shout")), val("SHOUT")))

    # !(test (string-lower "QUIET") "quiet")
    yield m.eval(expr(S["test"], expr(S["string-lower"], val("QUIET")), val("quiet")))

    # !(test (string-starts-with "hello" "he") True)
    yield m.eval(
        expr(S["test"], expr(S["string-starts-with"], val("hello"), val("he")), val(value=True))
    )

    # !(test (string-ends-with "hello" "lo") True)
    yield m.eval(
        expr(S["test"], expr(S["string-ends-with"], val("hello"), val("lo")), val(value=True))
    )

    # !(test (string-contains "hello" "ell") True)
    yield m.eval(
        expr(S["test"], expr(S["string-contains"], val("hello"), val("ell")), val(value=True))
    )

    # !(test (string-contains "hello" "zzz") False)
    yield m.eval(
        expr(S["test"], expr(S["string-contains"], val("hello"), val("zzz")), val(value=False))
    )

    # !(test (string-index-of "hello" "l") 2)
    yield m.eval(expr(S["test"], expr(S["string-index-of"], val("hello"), val("l")), 2))

    # !(test (string-index-of "hello" "z") -1)
    yield m.eval(expr(S["test"], expr(S["string-index-of"], val("hello"), val("z")), -1))

    # !(test (string-replace "banana" "a" "X") "bXnXnX")
    yield m.eval(
        expr(S["test"], expr(S["string-replace"], val("banana"), val("a"), val("X")), val("bXnXnX"))
    )

    # !(test (string-chars "abc") ("a" "b" "c"))
    yield m.eval(
        expr(S["test"], expr(S["string-chars"], val("abc")), expr(val("a"), val("b"), val("c")))
    )

    # !(test (string-from-chars ("a" "b" "c")) "abc")
    yield m.eval(
        expr(
            S["test"], expr(S["string-from-chars"], expr(val("a"), val("b"), val("c"))), val("abc")
        )
    )

    # !(test (string-repeat "ab" 3) "ababab")
    yield m.eval(expr(S["test"], expr(S["string-repeat"], val("ab"), 3), val("ababab")))

    # !(test (string-pad-left "7" 3 "0") "007")
    yield m.eval(expr(S["test"], expr(S["string-pad-left"], val("7"), 3, val("0")), val("007")))

    # !(test (string-pad-right "7" 3 ".") "7..")
    yield m.eval(expr(S["test"], expr(S["string-pad-right"], val("7"), 3, val(".")), val("7..")))

    # !(test (format-args "Probability of {} is {}%" (head 50))
    #        "Probability of head is 50%")
    yield m.eval(
        expr(
            S["test"],
            expr(S["format-args"], val("Probability of {} is {}%"), expr(S["head"], 50)),
            val("Probability of head is 50%"),
        )
    )

    # !(test (format-args "{} and {}" (only)) "only and ")
    yield m.eval(
        expr(S["test"], expr(S["format-args"], val("{} and {}"), expr(S["only"])), val("only and "))
    )

    # !(test (sort-strings ("pear" "apple" "fig")) ("apple" "fig" "pear"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["sort-strings"], expr(val("pear"), val("apple"), val("fig"))),
            expr(val("apple"), val("fig"), val("pear")),
        )
    )

    # !(test (parse-number "42") 42)
    yield m.eval(expr(S["test"], expr(S["parse-number"], val("42")), 42))

    # !(test (number-to-string 42) "42")
    yield m.eval(expr(S["test"], expr(S["number-to-string"], 42), val("42")))

    # !(test (string-length hello) 5)
    yield m.eval(expr(S["test"], expr(S["string-length"], S["hello"]), 5))

    # !(test (string-upper hello) "HELLO")
    yield m.eval(expr(S["test"], expr(S["string-upper"], S["hello"]), val("HELLO")))

    # !(test (write-file! "/tmp/petta-text-example.txt" "one\ntwo\nthree\n") True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["write-file!"], val("/tmp/petta-text-example.txt"), val("one\ntwo\nthree\n")),
            val(value=True),
        )
    )

    # !(test (read-file! "/tmp/petta-text-example.txt") "one\ntwo\nthree\n")
    yield m.eval(
        expr(
            S["test"],
            expr(S["read-file!"], val("/tmp/petta-text-example.txt")),
            val("one\ntwo\nthree\n"),
        )
    )

    # !(test (file-lines! "/tmp/petta-text-example.txt") ("one" "two" "three"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["file-lines!"], val("/tmp/petta-text-example.txt")),
            expr(val("one"), val("two"), val("three")),
        )
    )

    # !(test (append-file! "/tmp/petta-text-example.txt" "four\n") True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["append-file!"], val("/tmp/petta-text-example.txt"), val("four\n")),
            val(value=True),
        )
    )

    # !(test (file-lines! "/tmp/petta-text-example.txt") ("one" "two" "three" "four"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["file-lines!"], val("/tmp/petta-text-example.txt")),
            expr(val("one"), val("two"), val("three"), val("four")),
        )
    )

    # !(test (let $h (file-open! "/tmp/petta-text-example.txt" "r")
    #          (let $head (file-read-exact! $h 3)
    #            (let $_ (file-close! $h) $head)))
    #        "one")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["h"],
                expr(S["file-open!"], val("/tmp/petta-text-example.txt"), val("r")),
                expr(
                    S["let"],
                    V["head"],
                    expr(S["file-read-exact!"], V["h"], 3),
                    expr(S["let"], V["_2652"], expr(S["file-close!"], V["h"]), V["head"]),
                ),
            ),
            val("one"),
        )
    )

    # !(test (let $log (file-space! "/tmp/petta-text-example.txt")
    #          (collapse (match $log (line $n $t) ($n $t))))
    #        ((1 "one") (2 "two") (3 "three") (4 "four")))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["log"],
                expr(S["file-space!"], val("/tmp/petta-text-example.txt")),
                expr(
                    S["collapse"],
                    expr(
                        S["match"], V["log"], expr(S["line"], V["n"], V["t"]), expr(V["n"], V["t"])
                    ),
                ),
            ),
            expr(
                expr(1, val("one")),
                expr(2, val("two")),
                expr(3, val("three")),
                expr(4, val("four")),
            ),
        )
    )

    # !(test (let $log (file-space! "/tmp/petta-text-example.txt")
    #          (collapse (match $log (line 2 $t) $t)))
    #        ("two"))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["log"],
                expr(S["file-space!"], val("/tmp/petta-text-example.txt")),
                expr(S["collapse"], expr(S["match"], V["log"], expr(S["line"], 2, V["t"]), V["t"])),
            ),
            expr(val("two")),
        )
    )

    # !(test (delete-file! "/tmp/petta-text-example.txt") True)
    yield m.eval(
        expr(
            S["test"], expr(S["delete-file!"], val("/tmp/petta-text-example.txt")), val(value=True)
        )
    )

    yield from ()
