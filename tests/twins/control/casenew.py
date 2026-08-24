"""Purpose: examples/control/casenew.metta in Python: a branch that answers nothing.

`wu` superposes two calls; one of them answers nothing at all, so the whole
form answers only the other. That is the file's subject, and the three
equations it compiles to are the original's own, term for term.

The fork is `superpose(wu1(), wu2())` rather than two yields, because the two
are different knowledge: yields store one equation each where the example
stores ONE whose body superposes. `empty()` is a second name a compiled body
reads as MeTTa, and it stores `(empty)` exactly where `superpose()` would store
`(superpose ())`; the package exports it nowhere, so the line carries the
suppression the residue entry against P14.4 would delete.

`(full)` is a one-tuple over `S.full`, the lowercase symbol reached through
the factory, which is how a compiled body writes data whose name would
otherwise read as a function to call.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Fork over two calls, one of which has nothing to say."""
    @m.define
    def wu1():
        # (= (wu1) (empty))
        return empty()  # noqa: F821  -- `empty` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)

    @m.define
    def wu2():
        # (= (wu2) (full))
        return (S.full,)

    @m.define
    def wu():
        # (= (wu) (superpose ((wu1) (wu2))))
        return superpose(wu1(), wu2())

    # !(test (wu) (full))
    assert wu() == [S.full()]
