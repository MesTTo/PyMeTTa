"""examples/control/case2.metta in Python: a branch may fork.

One branch, whose pattern is the key itself so everything reaches it, and
whose VALUE is a superposition: a `case` answers whatever its branch answers,
which is two things here. The `case` therefore decides nothing, and what is
left is the fork, which a generator's two yields say directly.

The two tags are capitalised where the original writes them lowercase.
A compiled body reads a lowercase free name as a FUNCTION and a capitalised
one as a data constructor, so `what` raises where `What` is data; the ledger's
own worked example writes `yield S.red`, which does not compile either. Filed
as residue against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1546 to 2244, +698 (+45.1%), by the twin contract
#: change: the equation ENTERED the engine as `@m.define`, whose fixed
#: registration is the whole of the increase, while the `test` wrapper and
#: the collapse LEFT for `assert` and a list. Measured min-of-3 over fresh
#: processes with the MORK backend linked in, which the artefact-free
#: worktree omits and which moves a compiled twin by about 10 inferences per
#: definition; against the example's 3736 the ratio is 0.6006. Prior: 1546,
#: the transliterated twin this replaces.
BUDGET = 2244


def twin(m):
    """One head, one branch, two answers."""
    @m.define(name="compile")
    def compiled(_stmt):
        # (= (compile $stmt) (case $stmt (($stmt (superpose (what what2))))))
        yield What  # noqa: F821  -- a capitalised free name in a compiled body IS a data constructor, and MeTTa data has no Python value to bind
        yield What2  # noqa: F821  -- the second tag, the same way

    # !(test (collapse (compile wat)) (what what2))
    assert compiled(S.wat) == [S.What, S.What2]
