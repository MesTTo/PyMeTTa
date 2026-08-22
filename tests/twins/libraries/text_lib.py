"""The Python twin of examples/libraries/text_lib.metta.

Text and files, imported the way C reaches for string.h: neither library is
loaded until you ask for it, so a program that never touches text never pays
for it.

Every string here is DATA rather than a name, so each is carried whole through
`val(...)`; the tuples of pieces are Python tuples, which is what a MeTTa
expression already is. The one thing worth noticing about the file half is that
`file-space!` is the mettafied reading of reading a file: its lines become
`(line Number Text)` atoms in a space, so the file is QUERYABLE with `match`
rather than being one long string you then have to take apart.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 117082 to 117079, -3 (-0.00%), by the P14 twin-style
#: rewrite: reading the source's own anonymous variable as one: the let that
#: closes the file handle binds $_ where the previous twin renamed it, which
#: is the same three inferences derived_forms moved by for the same reason.
#: Prior: ADDED 2026-08-22 at 117082 by the wave-3 libraries baseline, which
#: recorded no cause.
BUDGET = 117079

#: The scratch file, written under a distinctive name so the concurrent example
#: runner cannot collide with itself, and removed at the end.
PATH = val("/tmp/petta-text-example.txt")


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_string))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_string)))
    # !(import! &self (library lib_file))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_file)))

    # Measuring and slicing. string-slice is half-open, From included, To not.
    # !(test (string-length "hello") 5)
    yield m.eval(S.test(S["string-length"](val("hello")), 5))
    # !(test (string-slice "hello world" 0 5) "hello")
    yield m.eval(
        S.test(S["string-slice"](val("hello world"), 0, 5), val("hello"))
    )
    # An over-long end clamps instead of erroring, which is what every language
    # with slicing does.
    # !(test (string-slice "hello" 3 999) "lo")
    yield m.eval(
        S.test(S["string-slice"](val("hello"), 3, 999), val("lo"))
    )
    # !(test (string-slice "hello" 99 120) "")
    yield m.eval(
        S.test(S["string-slice"](val("hello"), 99, 120), val(""))
    )

    # Splitting and joining are inverses.
    # !(test (string-split "," "a,b,c") ("a" "b" "c"))
    yield m.eval(
        S.test(
            S["string-split"](val(","), val("a,b,c")),
            (val("a"), val("b"), val("c")),
        )
    )
    # !(test (string-join ", " ("a" "b" "c")) "a, b, c")
    yield m.eval(
        S.test(
            S["string-join"](val(", "), (val("a"), val("b"), val("c"))),
            val("a, b, c"),
        )
    )
    # !(test (string-trim "  padded  ") "padded")
    yield m.eval(
        S.test(S["string-trim"](val("  padded  ")), val("padded"))
    )
    # !(test (string-upper "shout") "SHOUT")
    yield m.eval(S.test(S["string-upper"](val("shout")), val("SHOUT")))
    # !(test (string-lower "QUIET") "quiet")
    yield m.eval(S.test(S["string-lower"](val("QUIET")), val("quiet")))

    # The tests answer True or False, so they guard a query.
    # !(test (string-starts-with "hello" "he") True)
    yield m.eval(
        S.test(S["string-starts-with"](val("hello"), val("he")), TRUE)
    )
    # !(test (string-ends-with "hello" "lo") True)
    yield m.eval(
        S.test(S["string-ends-with"](val("hello"), val("lo")), TRUE)
    )
    # !(test (string-contains "hello" "ell") True)
    yield m.eval(
        S.test(S["string-contains"](val("hello"), val("ell")), TRUE)
    )
    # !(test (string-contains "hello" "zzz") False)
    yield m.eval(
        S.test(S["string-contains"](val("hello"), val("zzz")), FALSE)
    )

    # index-of answers -1 rather than failing: asking "where is it" deserves an
    # answer either way.
    # !(test (string-index-of "hello" "l") 2)
    yield m.eval(S.test(S["string-index-of"](val("hello"), val("l")), 2))
    # !(test (string-index-of "hello" "z") -1)
    yield m.eval(S.test(S["string-index-of"](val("hello"), val("z")), -1))

    # replace changes every occurrence.
    # !(test (string-replace "banana" "a" "X") "bXnXnX")
    yield m.eval(
        S.test(
            S["string-replace"](val("banana"), val("a"), val("X")),
            val("bXnXnX"),
        )
    )

    # chars are one-character STRINGS, not char symbols, so the pieces are the
    # same kind of thing as the whole and feed straight back in.
    # !(test (string-chars "abc") ("a" "b" "c"))
    yield m.eval(
        S.test(
            S["string-chars"](val("abc")), (val("a"), val("b"), val("c"))
        )
    )
    # !(test (string-from-chars ("a" "b" "c")) "abc")
    yield m.eval(
        S.test(
            S["string-from-chars"]((val("a"), val("b"), val("c"))),
            val("abc"),
        )
    )
    # !(test (string-repeat "ab" 3) "ababab")
    yield m.eval(
        S.test(S["string-repeat"](val("ab"), 3), val("ababab"))
    )
    # !(test (string-pad-left "7" 3 "0") "007")
    yield m.eval(
        S.test(
            S["string-pad-left"](val("7"), 3, val("0")), val("007")
        )
    )
    # !(test (string-pad-right "7" 3 ".") "7..")
    yield m.eval(
        S.test(
            S["string-pad-right"](val("7"), 3, val(".")), val("7..")
        )
    )

    # format-args is MeTTa HE's spelling, and this is HE's own example.
    # !(test (format-args "Probability of {} is {}%" (head 50))
    #        "Probability of head is 50%")
    yield m.eval(
        S.test(
            S["format-args"](
                val("Probability of {} is {}%"), (S.head, 50)
            ),
            val("Probability of head is 50%"),
        )
    )
    # A short argument list produces NOTHING for the placeholders it cannot
    # fill, which is the dyn_fmt formatter upstream interpolates through.
    # !(test (format-args "{} and {}" (only)) "only and ")
    yield m.eval(
        S.test(
            S["format-args"](val("{} and {}"), (S.only,)),
            val("only and "),
        )
    )

    # !(test (sort-strings ("pear" "apple" "fig")) ("apple" "fig" "pear"))
    yield m.eval(
        S.test(
            S["sort-strings"]((val("pear"), val("apple"), val("fig"))),
            (val("apple"), val("fig"), val("pear")),
        )
    )
    # !(test (parse-number "42") 42)
    yield m.eval(S.test(S["parse-number"](val("42")), 42))
    # !(test (number-to-string 42) "42")
    yield m.eval(S.test(S["number-to-string"](42), val("42")))

    # Text operations accept a Symbol or a Number where a String is wanted,
    # because a symbol arriving where a string was meant is ordinary in MeTTa.
    # !(test (string-length hello) 5)
    yield m.eval(S.test(S["string-length"](S.hello), 5))
    # !(test (string-upper hello) "HELLO")
    yield m.eval(S.test(S["string-upper"](S.hello), val("HELLO")))

    # Files.
    # !(test (write-file! "/tmp/petta-text-example.txt" "one\ntwo\nthree\n") True)
    yield m.eval(
        S.test(S["write-file!"](PATH, val("one\ntwo\nthree\n")), TRUE)
    )
    # !(test (read-file! "/tmp/petta-text-example.txt") "one\ntwo\nthree\n")
    yield m.eval(
        S.test(S["read-file!"](PATH), val("one\ntwo\nthree\n"))
    )
    # file-lines! drops the trailing empty line a final newline would produce.
    # !(test (file-lines! "/tmp/petta-text-example.txt") ("one" "two" "three"))
    yield m.eval(
        S.test(
            S["file-lines!"](PATH),
            (val("one"), val("two"), val("three")),
        )
    )
    # !(test (append-file! "/tmp/petta-text-example.txt" "four\n") True)
    yield m.eval(S.test(S["append-file!"](PATH, val("four\n")), TRUE))
    # !(test (file-lines! "/tmp/petta-text-example.txt") ("one" "two" "three" "four"))
    yield m.eval(
        S.test(
            S["file-lines!"](PATH),
            (val("one"), val("two"), val("three"), val("four")),
        )
    )

    # The handle surface is MeTTa HE's exactly: r read, w write, c create,
    # a append, t truncate.
    # !(test (let $h (file-open! "/tmp/petta-text-example.txt" "r")
    #          (let $head (file-read-exact! $h 3)
    #            (let $_ (file-close! $h) $head)))
    #        "one")
    yield m.eval(
        S.test(
            S.let(
                V.h,
                S["file-open!"](PATH, val("r")),
                S.let(
                    V.head,
                    S["file-read-exact!"](V.h, 3),
                    S.let(V._, S["file-close!"](V.h), V.head),
                ),
            ),
            val("one"),
        )
    )

    # file-space! is the mettafied reading of reading a file: its lines become
    # (line Number Text) atoms in a space, so the file is QUERYABLE with match
    # rather than being one long string. The line number is kept because a
    # space is unordered.
    # !(test (let $log (file-space! "/tmp/petta-text-example.txt")
    #          (collapse (match $log (line $n $t) ($n $t))))
    #        ((1 "one") (2 "two") (3 "three") (4 "four")))
    yield m.eval(
        S.test(
            S.let(
                V.log,
                S["file-space!"](PATH),
                S.collapse(S.match(V.log, S.line(V.n, V.t), (V.n, V.t))),
            ),
            (
                (1, val("one")),
                (2, val("two")),
                (3, val("three")),
                (4, val("four")),
            ),
        )
    )
    # Asking for one line is a match, not a scan.
    # !(test (let $log (file-space! "/tmp/petta-text-example.txt")
    #          (collapse (match $log (line 2 $t) $t)))
    #        ("two"))
    yield m.eval(
        S.test(
            S.let(
                V.log,
                S["file-space!"](PATH),
                S.collapse(S.match(V.log, S.line(2, V.t), V.t)),
            ),
            (val("two"),),
        )
    )

    # !(test (delete-file! "/tmp/petta-text-example.txt") True)
    yield m.eval(S.test(S["delete-file!"](PATH), TRUE))
