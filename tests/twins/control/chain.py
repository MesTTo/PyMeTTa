"""examples/control/chain.metta in Python: `chain` names its result.

`(chain expr $n body)` runs `expr`, binds the answer to a name, and runs the
body with that name in scope. Python spells that with an ordinary assignment
statement, and a second assignment nests inside the first exactly as a second
`chain` nests inside the first, which is what `summed` below reads like.

Both forms are compiled now. The first was written as a term while the band
priced two definitions against an example that authors none; with the
authoring allowance in place the two definitions cost 4,415 against a ceiling
of 7,268, so the file says in Python what it had been describing in a comment.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3918 to 4415, +497 (+12.7%), by lifting this twin to
#: the definitional door now that the band pays for authoring: the first
#: chain ENTERED the engine as a second compiled definition, so both forms
#: are now assignments rather than one being a term. The increase is one
#: decoration's marginal cost and nothing else. Measured min-of-3 over fresh
#: processes with the MORK backend linked in; against the example's 3893 the
#: ratio is 1.1341, and the ceiling is 7268, the example plus 10% plus 2986
#: to author 2 definitions. Prior: 3918, the term-door twin the old band
#: forced.
BUDGET = 4415


def twin(m):
    """Name one intermediate result, then two."""
    @m.define
    def scaled():
        # (chain (+ 2 4) $n (* 3 $n))
        n = 2 + 4
        return 3 * n

    # !(test (chain (+ 2 4) $n (* 3 $n)) 18)
    assert scaled() == [18]

    @m.define
    def summed():
        # (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m)))
        n = 1 + 3
        doubled = 2 * n
        return n + doubled

    # !(test (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m))) 12)
    assert summed() == [12]
