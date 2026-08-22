"""examples/syntax/parse.metta in Python: reading text back into an atom.

`parse` is the reader, and its input is MeTTa source. The first five forms hand
it source written into the program (`"A"`, `"(R A B)"`, and three more), which
is exactly what a twin may not carry, so those five are declined and the
residue table records each against P14.1.

The last three are different, and they are the ones a Python program can state:
each starts from ordinary string DATA and lets the program itself print that
data before reading it back. `str(val(text))` is the printing half, the same
`str` that answers `repr`'s text in syntax/repr.py, and `m.fn("parse")` reads
it, so the claim is that printing and reading are inverse over a string with
backslashes, one with embedded quotes, and one whose backslash-n is two
characters rather than a newline.
"""

from petta import val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2238 to 406, -1832 (-81.9%), by the twin contract
#: change: three `(test (parse (repr X)) X)` terms became three Python
#: `assert`s over `m.fn("parse")(str(val(X)))`, so the `test` wrapper and the
#: three `repr` calls left the engine and only the three reads are left.
#: Against the example's 9005 the ratio is 0.0451, and the example is paying
#: for the five forms this twin declines.
#: Prior: 2238, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 406


def twin(m):
    """Print three awkward strings, and read each of them back."""
    read = m.fn("parse")

    # A Windows path: every backslash is a backslash, doubled on the way out
    # and single again on the way back.
    assert read(str(val("C:\\Users\\bob"))) == val("C:\\Users\\bob")
    # Quotes inside the string, escaped by the printer and unescaped by
    # the reader.
    assert read(str(val('say "hi"'))) == val('say "hi"')
    # Backslash-n as two characters, which survives because the printer
    # escapes the backslash rather than the n.
    assert read(str(val("a\\nb"))) == val("a\\nb")
