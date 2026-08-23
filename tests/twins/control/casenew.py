"""Purpose: examples/control/casenew.metta in Python: a branch that answers nothing.

`wu` superposes two calls; one of them answers nothing at all, so the whole
form answers only the other. That is the file's subject, and it is where a
Python generator says exactly what MeTTa says: each `yield` is one answer,
which is what `superpose` spells, and a yielded CALL contributes that call's
own answers rather than a generator object.

`(full)` is a one-tuple over `S.full`, the lowercase symbol reached through
the factory, which is how a compiled body writes data whose name would
otherwise read as a function to call.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Fork over two calls, one of which has nothing to say."""
    @m.define
    def wu1():
        # (= (wu1) (empty))
        yield from ()

    @m.define
    def wu2():
        # (= (wu2) (full))
        return (S.full,)

    @m.define
    def wu():
        # (= (wu) (superpose ((wu1) (wu2))))
        yield wu1()
        yield wu2()

    # !(test (wu) (full))
    assert wu() == [S.full()]
