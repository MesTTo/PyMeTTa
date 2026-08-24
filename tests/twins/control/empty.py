"""Purpose: examples/control/empty.metta in Python: a function that answers nothing.

Answering nothing is not answering `()`: `collapse` over no answers is the
empty expression, and that is what the original asserts.

`empty()` is the form itself, one of the names a compiled body reads as MeTTa,
and it stores `(= (y) (empty))` exactly. The two Python spellings beside it are
sugar over it and store `(superpose ())` instead: `superpose()` with no
alternatives, and a generator that yields nothing, which prunes its branch. All
three answer the same and only this one stores the original's own equation. The
package exports the name nowhere, so the line carries the suppression the
residue entry against P14.4 would delete.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Define a function with no answers, and count them."""
    @m.define
    def y():
        # (= (y) (empty))
        return empty()  # noqa: F821  -- `empty` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)

    # !(test (collapse (y)) ())
    assert y() == []
