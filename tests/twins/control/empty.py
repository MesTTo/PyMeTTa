"""Purpose: examples/control/empty.metta in Python: a function that answers nothing.

Answering nothing is not answering `()`: `collapse` over no answers is the
empty expression, and that is what the original asserts. Python says it
without a name for it, because a generator that yields nothing prunes its
branch, and `yield from ()` is a generator with nothing to yield.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Define a function with no answers, and count them."""
    @m.define
    def y():
        # (= (y) (empty))
        yield from ()

    # !(test (collapse (y)) ())
    assert y() == []
