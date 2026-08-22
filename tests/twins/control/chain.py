"""examples/control/chain.metta in Python: `chain` names its result.

`(chain expr $n body)` runs `expr`, binds the answer to a name, and runs the
body with that name in scope. Python spells that with an ordinary assignment
statement, and a second assignment nests inside the first exactly as a second
`chain` nests inside the first, which is what `summed` below reads like.

The first form is stated as a term rather than as a second compiled function,
and the reason is the lane's price: a second `@m.define` costs 1,603
inferences and two of them put this twin at 4,415 against a ceiling of
4,282 (measured 2026-08-22, min of three fresh processes). Filed against
P14.14.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2146 to 3918, +1772 (+82.6%), by the twin contract
#: change: the nested chain ENTERED the engine as a compiled body of two
#: assignments, which is what a `chain` is, and pays `@m.define`'s fixed
#: registration; the `test` wrappers LEFT for `assert`s. The first form stays
#: a term because a second definition costs 1,603 more and would put the twin
#: at 4,415 against the band's ceiling of 4,282. Measured min-of-3 over fresh
#: processes with the MORK backend linked in, which the artefact-free
#: worktree omits and which moves a compiled twin by about 10 inferences per
#: definition; against the example's 3893 the ratio is 1.0064. Prior: 2146,
#: the transliterated twin this replaces.
BUDGET = 3918


def twin(m):
    """Name one intermediate result, then two."""
    # !(test (chain (+ 2 4) $n (* 3 $n)) 18)
    # rung: `n = 2 + 4` then `return 3 * n` is this form in a compiled body, and a second @m.define does not fit the band
    assert m.eval(S.chain(S["+"](2, 4), V.n, 3 * V.n)) == [18]

    @m.define
    def summed():
        # (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m)))
        n = 1 + 3
        doubled = 2 * n
        return n + doubled

    # !(test (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m))) 12)
    assert summed() == [12]
