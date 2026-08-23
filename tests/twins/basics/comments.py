"""examples/basics/comments.metta in Python: a definition with comments in it.

The original is about MeTTa's comment syntax, and the definition it comments,
`(= (f) 42)`, is what survives translation: Python has comments too, so this
file puts them where the original puts them and says the same thing with them.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Define a function of no arguments, then check what it answers."""
    # let's comment
    @m.define
    def f():  # with a comment
        # this is a line with just a comment
        return 42  # overall we tested systematically several comments

    assert f() == [42]  # and added an evil comment for fun
    # anything else to comment?
