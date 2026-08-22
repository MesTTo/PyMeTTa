"""examples/libraries/text_lib.metta in Python: lib_string and lib_file.

Both libraries are the subject, so every function here is named. What Python
takes over is the plumbing around them: the `let` chain that threads a file
handle through three calls is three statements, the file space is queried
through the handle's own subscript door, and every answer is compared as
ordinary Python data.

Two heads keep their MeTTa spelling with a stated reason rather than
dissolving. `format-args` is MeTTa HE's own formatter and this file is HE's
example of it, including what it does with too few arguments, which an f-string
cannot reproduce; `sort-strings` is the library function under test, not a
request to sort a Python list.

The file this writes is named for the twin rather than for the example, so the
two can never meet on one path.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 117079 to 101616, -15463 (-13.21%), by the idiomatic
#: rewrite: thirty-seven `test` wrappers left the engine for `assert`, the
#: file-handle `let` chain became three statements, and the two `file-space!`
#: matches became subscripts on the space the file decodes into. Measured
#: min-of-three with the MORK backend linked into this worktree, which the
#: earlier figure may not have been. Prior: 117079 was the last figure for
#: the generator twin that yielded `m.eval(S.test(...))` once per runnable
#: form.
BUDGET = 101616

#: Written, appended to, read back four ways, then removed.
SCRATCH = val("/tmp/petta-text-twin.txt")


def twin(m):
    """Walk lib_string's measuring, slicing, testing and padding, then lib_file."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_string)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes
    m.eval(S["import!"](S["&self"], S.library(S.lib_file)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one, as above

    # Measuring and slicing. string-slice is half-open, From included, To not.
    assert m.fn("string-length")(val("hello")) == 5
    slice_ = m.fn("string-slice")
    assert slice_(val("hello world"), 0, 5) == val("hello")
    # An over-long end clamps instead of erroring, as slicing does everywhere.
    assert slice_(val("hello"), 3, 999) == val("lo")
    assert slice_(val("hello"), 99, 120) == val("")

    # Splitting and joining are inverses.
    assert list(m.fn("string-split")(val(","), val("a,b,c"))) == [val("a"), val("b"), val("c")]
    assert m.fn("string-join")(val(", "), (val("a"), val("b"), val("c"))) == val("a, b, c")
    assert m.fn("string-trim")(val("  padded  ")) == val("padded")
    assert m.fn("string-upper")(val("shout")) == val("SHOUT")
    assert m.fn("string-lower")(val("QUIET")) == val("quiet")

    # The tests answer True or False, so they guard a query.
    assert m.fn("string-starts-with")(val("hello"), val("he")) is True
    assert m.fn("string-ends-with")(val("hello"), val("lo")) is True
    contains = m.fn("string-contains")
    assert contains(val("hello"), val("ell")) is True
    assert contains(val("hello"), val("zzz")) is False

    # index-of answers -1 rather than failing: asking "where is it" deserves an
    # answer either way.
    index_of = m.fn("string-index-of")
    assert index_of(val("hello"), val("l")) == 2
    assert index_of(val("hello"), val("z")) == -1

    # replace changes every occurrence.
    assert m.fn("string-replace")(val("banana"), val("a"), val("X")) == val("bXnXnX")

    # chars are one-character STRINGS, not char symbols, so the pieces are the
    # same kind of thing as the whole and feed straight back in.
    chars = m.fn("string-chars")(val("abc"))
    assert list(chars) == [val("a"), val("b"), val("c")]
    assert m.fn("string-from-chars")(chars) == val("abc")
    assert m.fn("string-repeat")(val("ab"), 3) == val("ababab")
    assert m.fn("string-pad-left")(val("7"), 3, val("0")) == val("007")
    assert m.fn("string-pad-right")(val("7"), 3, val(".")) == val("7..")

    # rung: format-args is MeTTa HE's own formatter and this is HE's example of
    # it; an f-string cannot show what it does with too few arguments, which is
    # the second claim.
    format_args = m.fn("format-args")
    assert format_args(val("Probability of {} is {}%"), (S.head, 50)) == val("Probability of head is 50%")
    # A short argument list produces NOTHING for the placeholders it cannot
    # fill, which is the dyn_fmt formatter upstream interpolates through.
    assert format_args(val("{} and {}"), (S.only,)) == val("only and ")

    # rung: sort-strings is the library function under test, not a request to
    # sort a Python list.
    sorted_strings = m.fn("sort-strings")((val("pear"), val("apple"), val("fig")))
    assert list(sorted_strings) == [val("apple"), val("fig"), val("pear")]
    assert m.fn("parse-number")(val("42")) == 42
    assert m.fn("number-to-string")(42) == val("42")

    # Text operations accept a Symbol or a Number where a String is wanted,
    # because a symbol arriving where a string was meant is ordinary in MeTTa.
    assert m.fn("string-length")(S.hello) == 5
    assert m.fn("string-upper")(S.hello) == val("HELLO")

    # Files.
    assert m.fn("write-file!")(SCRATCH, val("one\ntwo\nthree\n")) is True
    assert m.fn("read-file!")(SCRATCH) == val("one\ntwo\nthree\n")
    # file-lines! drops the trailing empty line a final newline would produce.
    assert list(m.fn("file-lines!")(SCRATCH)) == [val("one"), val("two"), val("three")]
    assert m.fn("append-file!")(SCRATCH, val("four\n")) is True
    assert list(m.fn("file-lines!")(SCRATCH)) == [val("one"), val("two"), val("three"), val("four")]

    # The handle surface is MeTTa HE's exactly: r read, w write, c create,
    # a append, t truncate. The example's `let` chain is three statements.
    handle = m.fn("file-open!")(SCRATCH, val("r"))
    head = m.fn("file-read-exact!")(handle, 3)
    m.fn("file-close!")(handle)
    assert head == val("one")

    # file-space! is the mettafied reading of reading a file: its lines become
    # (line Number Text) atoms in a space, so the file is QUERYABLE rather than
    # one long string you then have to take apart. The line number is kept
    # because a space is unordered.
    log = m.space(str(m.fn("file-space!")(SCRATCH)))
    assert [(row.n, row.t) for row in log.query(S.line(V.n, V.t))] == [
        (1, val("one")), (2, val("two")), (3, val("three")), (4, val("four")),
    ]
    # Asking for one line is a match, not a scan.
    assert log.query(S.line(2, V.t))["t"] == [val("two")]

    assert m.fn("delete-file!")(SCRATCH) is True
