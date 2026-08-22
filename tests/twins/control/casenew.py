"""examples/control/casenew.metta in Python: a branch that answers nothing.

`wu` superposes two calls; one of them answers nothing at all, so the whole
form answers only the other. That is the file's subject, and it is where a
Python generator says exactly what MeTTa says: each `yield` is one answer,
which is what `superpose` spells, and a yielded CALL contributes that call's
own answers rather than a generator object.

`(full)` is written `(Full,)`, a one-element tuple holding a data constructor,
because a compiled body reads a lowercase free name as a function; the same
spelling gap case2 records against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4695 to 4205, -490 (-10.4%), by the twin contract
#: change: `wu2` ENTERED as a third `@m.define` where it was a container-door
#: equation, and the `test` wrapper LEFT for `assert`; the second outweighs
#: the first because `wu1` and `wu` were already compiled. Measured min-of-3
#: over fresh processes with the MORK backend linked in, which the artefact-
#: free worktree omits and which moves a compiled twin by about 10 inferences
#: per definition; against the example's 5092 the ratio is 0.8258. Prior:
#: 4695, the transliterated twin this replaces.
BUDGET = 4205


def twin(m):
    """Fork over two calls, one of which has nothing to say."""
    @m.define
    def wu1():
        # (= (wu1) (empty))
        yield from ()

    @m.define
    def wu2():
        # (= (wu2) (full))
        return (Full,)  # noqa: F821  -- a capitalised free name in a compiled body IS a data constructor

    @m.define
    def wu():
        # (= (wu) (superpose ((wu1) (wu2))))
        yield wu1()
        yield wu2()

    # !(test (wu) (full))
    assert wu() == [S.Full()]
