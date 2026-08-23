"""examples/basics/ifsimple.metta in Python: `if` with no else branch.

MeTTa's two-argument `if` answers nothing when its condition is false, and
Python's conditional expression cannot mean that, because it always has an
else. What does mean it is a GENERATOR: a compiled body that yields nothing
prunes its branch, so `keep` below says exactly this form, and the second
claim proves the half the example does not state, that a false condition
answers nothing rather than a falsy value.

This file used to build the term instead, and said so, because the band
priced a decorated definition against an example that defines nothing. The
band now allows the measured cost of authoring one, so the spelling the
ladder wants is affordable and the residue entry that recorded the block is
retired.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1

#: The two conditions, named rather than written inline: a bare boolean in an
#: argument list reads as a Python FLAG, and these are the example's data.
HOLDS, FAILS = True, False


def twin(m):
    """Answer under a condition that holds, and nothing under one that does not."""
    @m.define
    def keep(condition, value):
        # (if $condition $value), the two-argument form: yielding nothing is
        # what "no else branch" means.
        if condition:
            yield value

    assert keep(HOLDS, 42) == [42]
    assert keep(FAILS, 42) == []
