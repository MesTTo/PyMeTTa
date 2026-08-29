"""examples/ch03-atoms-and-expressions/02-string.metta in Python: a string is a value, not structure.

The parentheses in the text are characters, which is the whole point of the
original: evaluating a string literal answers that same string. `ground(text)`
carries the Python string whole, which is how a MeTTa string literal is
written from Python.
"""

from metta import ground

#: The text under test. Its parentheses and its spaces are DATA, and `ground`
#: is what says so: every other string in a twin would be program text.
TEXT = ground("a test (with newlines and parentheses)")


def twin(m):
    """Reduce a string literal, and get the same string back."""
    assert m.eval(TEXT) == [TEXT]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 140 to 141, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
BUDGET = 141
