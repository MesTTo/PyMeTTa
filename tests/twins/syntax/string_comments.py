"""Purpose: examples/syntax/string_comments.metta in Python: `;` inside a string.

The original is a READER test: a semicolon inside a string starts no comment, a
lone `(` or `)` is a string rather than a paren, and a backslash escape
survives. No Python program can re-run that reader, because it never hands the
engine any text to read, and the residue table records the gap against P14.1
where syntax/parse.metta records it.

What a Python program CAN say is the other half, and it is the half the reader
exists to protect: each of these values crosses into the engine and comes back
as itself, which is the same round trip the original's `!(test "x" "x")` forms
make.

The last form is an ordinary definition whose body is the lowercase symbol
`result`, and `S.result` says that inside a compiled body: a factory mention is
data there, where a bare `result` would be read as a call.
"""

from metta import S, fn, ground

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Send nine awkward strings through the engine, then define a function."""
    # A lone paren is a string, not punctuation.
    # !(test ")" ")")
    # !(test "(" "(")
    close, open_ = ground(")"), ground("(")
    assert m.eval(close) == [close]
    assert m.eval(open_) == [open_]

    # A lone semicolon is a string, not the start of a comment.
    # !(test ";" ";")
    semicolon = ground(";")
    assert m.eval(semicolon) == [semicolon]

    # `quote` holds its argument rather than reducing it, so the semicolon
    # survives one level in as well.
    # !(test (quote ";") (quote ";"))
    quoted = fn.quote(semicolon)
    assert m.eval(quoted) == [quoted]

    # A semicolon in the middle, three of them, one at each end.
    # !(test "foo;bar" "foo;bar")
    # !(test ";;;" ";;;")
    middle, three = ground("foo;bar"), ground(";;;")
    assert m.eval(middle) == [middle]
    assert m.eval(three) == [three]
    # !(test ";start" ";start")
    # !(test "end;" "end;")
    first, last = ground(";start"), ground("end;")
    assert m.eval(first) == [first]
    assert m.eval(last) == [last]

    # An escaped quote, and a backslash.
    # !(test "quote: \"" "quote: \"")
    # !(test "path\\file" "path\\file")
    escaped, backslash = ground('quote: "'), ground("path\\file")
    assert m.eval(escaped) == [escaped]
    assert m.eval(backslash) == [backslash]

    @m.define
    def test_func():
        """(= (test-func) result), whose body is one lowercase symbol."""
        return S.result

    # !(test (test-func) result)
    assert test_func() == [S.result]
