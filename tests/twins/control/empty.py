"""examples/control/empty.metta in Python: a function that answers nothing.

Answering nothing is not answering `()`: `collapse` over no answers is the
empty expression, and that is what the original asserts. Python says it
without a name for it, because a generator that yields nothing prunes its
branch, and `yield from ()` is a generator with nothing to yield.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2745 to 2036, -709 (-25.8%), by the twin contract
#: change: the `test` wrapper and the `collapse` LEFT for `assert` and an
#: empty list; the definition is still `@m.define` and its fixed registration
#: is what remains. Measured min-of-3 over fresh processes with the MORK
#: backend linked in, which the artefact-free worktree omits and which moves
#: a compiled twin by about 10 inferences per definition; against the
#: example's 2508 the ratio is 0.8118. Prior: 2745, the transliterated twin
#: this replaces.
BUDGET = 2036


def twin(m):
    """Define a function with no answers, and count them."""
    @m.define
    def y():
        # (= (y) (empty))
        yield from ()

    # !(test (collapse (y)) ())
    assert y() == []
