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
#: RE-PINNED 2026-08-22, 224 to 3289, by the band's authoring allowance: this
#: twin now DEFINES `keep` rather than building `(if True 42)` at the term
#: door, so it pays the per-name admission the old figure was avoiding.
#: Against the example's 1308 the ceiling is 1308 * 1.10 + 1456 + 765 = 3660,
#: so it fits with 374 to spare [measured 2026-08-22 min-of-3]. Prior:
#: RE-PINNED at 224 by the twin contract change, when the `test` wrapper left
#: the engine for `assert`; the figure before that priced a different program.
BUDGET = 3289

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
