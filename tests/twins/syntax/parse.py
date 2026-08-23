"""Purpose: examples/syntax/parse.metta in Python: reading text back into an atom.

`parse` is the reader, and its input is MeTTa source. The first five forms hand
it source written into the program (`"A"`, `"(R A B)"`, and three more), which
is exactly what a twin may not carry, so those five are declined and the
residue table records each against P14.1.

The last three are different, and they are the ones a Python program can state:
each starts from ordinary string DATA and lets the program itself print that
data before reading it back. `str(ground(text))` is the printing half, the same
`str` that answers `repr`'s text in syntax/repr.py, and the engine's own
`parse` reads it, so the claim is that printing and reading are inverse over a
string with backslashes, one with embedded quotes, and one whose backslash-n is
two characters rather than a newline.
"""

from metta import ground

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Print three awkward strings, and read each of them back."""
    read = m.fn.parse

    # A Windows path: every backslash is a backslash, doubled on the way out
    # and single again on the way back.
    # !(test (parse (repr "C:\\Users\\bob")) "C:\\Users\\bob")
    assert read(str(ground("C:\\Users\\bob"))).one() == "C:\\Users\\bob"

    # Quotes inside the string, escaped by the printer and unescaped by
    # the reader.
    # !(test (parse (repr "say \"hi\"")) "say \"hi\"")
    assert read(str(ground('say "hi"'))).one() == 'say "hi"'

    # Backslash-n as two characters, which survives because the printer
    # escapes the backslash rather than the n.
    # !(test (parse (repr "a\\nb")) "a\\nb")
    assert read(str(ground("a\\nb"))).one() == "a\\nb"
