"""examples/basics/comments.metta in Python: a definition with comments in it.

The original is about MeTTa's comment syntax, and the definition it comments,
`(= (f) 42)`, is what survives translation: Python has comments too, so this
file puts them where the original puts them and says the same thing with them.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-23, 2003 to 1911, -92, by the p14-tabling merge, the sole
#: change between the two readings: the define-path saving seen corpus-wide.
#: Ratio 1911/2807 = 0.6808 [measured 2026-08-23 min-of-3 via
#: tools/twin_coverage.py --measure]. Prior:
#: RE-PINNED 2026-08-22, 2543 to 2003, -540 (-21.2%), by the twin contract
#: change: the `test` wrapper and the `m.eval` around it left the engine
#: for `assert` and the call door, so what is left is the definition and
#: the one call over it. Against the example's 2771 the ratio is 0.7228
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 1911


def twin(m):
    """Define a function of no arguments, then check what it answers."""
    # let's comment
    @m.define
    def f():  # with a comment
        # this is a line with just a comment
        return 42  # overall we tested systematically several comments

    assert f() == [42]  # and added an evil comment for fun
    # anything else to comment?
