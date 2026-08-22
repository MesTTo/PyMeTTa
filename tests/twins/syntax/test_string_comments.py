"""examples/syntax/test_string_comments.metta in Python: `;` inside a string.

The original is a READER test: a semicolon inside a string starts no comment, a
lone `(` or `)` is a string rather than a paren, and a backslash escape
survives. No Python program can re-run that reader, because it never hands the
engine any text to read, and the residue table records the gap against P14.1
where syntax/parse.metta records it.

What a Python program CAN say is the other half, and it is the half the reader
exists to protect: each of these values crosses into the engine and comes back
as itself. `m.one(val(text))` is that crossing, one answer out, and it is the
same round trip the original's `!(test "x" "x")` forms make.

The last form is an ordinary definition, written at the container door one rung
below `@m.define`: its body is the lowercase symbol `result`, and a compiled
body reads a lowercase free name as a CALL, so the symbol has no decorator
spelling (residue, P14.4).
"""

from petta import S, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3883 to 1680, -2203 (-56.7%), by the twin contract
#: change: eleven `(test X X)` terms became eleven Python `assert`s, so the
#: `test` wrapper left the engine and the ten crossings plus one definition are
#: what remains. Against the example's 8232 the ratio is 0.2041.
#: Prior: 3883, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 1680


def twin(m):
    """Send nine awkward strings through the engine, then define a function."""
    # A lone paren is a string, not punctuation.
    assert m.one(val(")")) == val(")")
    assert m.one(val("(")) == val("(")
    # A lone semicolon is a string, not the start of a comment.
    assert m.one(val(";")) == val(";")

    # `quote` holds its argument rather than reducing it, so the semicolon
    # survives one level in as well.
    assert m.one(S.quote(val(";"))) == S.quote(val(";"))

    # A semicolon in the middle, three of them, one at each end.
    assert m.one(val("foo;bar")) == val("foo;bar")
    assert m.one(val(";;;")) == val(";;;")
    assert m.one(val(";start")) == val(";start")
    assert m.one(val("end;")) == val("end;")

    # An escaped quote, and a backslash.
    assert m.one(val('quote: "')) == val('quote: "')
    assert m.one(val("path\\file")) == val("path\\file")

    # (= (test-func) result)
    m += equation(S["test-func"]()).to(S.result)
    assert m.one(S["test-func"]()) == S.result
