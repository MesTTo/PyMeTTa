"""Purpose: examples/syntax/test_string_comments.metta in Python: `;` inside a string.

The original is a READER test: a semicolon inside a string starts no comment, a
lone `(` or `)` is a string rather than a paren, and a backslash escape
survives. No Python program can re-run that reader, because it never hands the
engine any text to read, and the residue table records the gap against P14.1
where syntax/parse.metta records it.

What a Python program CAN say is the other half, and it is the half the reader
exists to protect: each of these values crosses into the engine and comes back
as itself, which is the same round trip the original's `!(test "x" "x")` forms
make.

The last form is an ordinary definition, written at the container door one rung
below `@m.define`: its body is the lowercase symbol `result`, and a compiled
body reads a lowercase free name as a CALL, so the symbol has no decorator
spelling (residue, P14.4).

The file keeps its example-derived name, `test_string_comments.py`, because the
lane derives a twin's path from its example's; the pytest collection it invites
is the integrator's to configure, not this file's to rename around.
"""

from petta import S, equation, fn, ground

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Send nine awkward strings through the engine, then define a function."""
    # A lone paren is a string, not punctuation.
    close, open_ = ground(")"), ground("(")
    assert m.eval(close) == [close]
    assert m.eval(open_) == [open_]
    # A lone semicolon is a string, not the start of a comment.
    semicolon = ground(";")
    assert m.eval(semicolon) == [semicolon]

    # `quote` holds its argument rather than reducing it, so the semicolon
    # survives one level in as well.
    quoted = fn.quote(semicolon)
    assert m.eval(quoted) == [quoted]

    # A semicolon in the middle, three of them, one at each end.
    middle, three = ground("foo;bar"), ground(";;;")
    assert m.eval(middle) == [middle]
    assert m.eval(three) == [three]
    first, last = ground(";start"), ground("end;")
    assert m.eval(first) == [first]
    assert m.eval(last) == [last]

    # An escaped quote, and a backslash.
    escaped, backslash = ground('quote: "'), ground("path\\file")
    assert m.eval(escaped) == [escaped]
    assert m.eval(backslash) == [backslash]

    # (= (test-func) result)
    m += equation(S["test-func"]()).to(S.result)
    assert m.fn.test_func() == [S.result]
