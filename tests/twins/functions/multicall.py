"""examples/functions/multicall.metta in Python: one head, two answers.

Both equations answer, so `mycalc(1, 2)` is `[3, -1]` rather than either of
them. Stacked `@m.define` clauses will not say that: stacking reads as
first-match, so a later clause is guarded against every earlier literal head,
and two clauses fixing no literal are a REDEFINITION rather than an
alternative. `@rules` is the other shape of the definitional door and says it
directly: the generator's parameters ARE the equations' variables.

One wall here, filed as residue: `@m.rules` does not exist, so writing the
rules and landing them in the space are two acts where the ledger's own
examples spell one. Calling is fine: `m.fn(name)` is cardinality-aware, and
`.all()` is the door for a function that answers more than once.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2314 to 1441, -873 (-37.7%), by the twin contract
#: change: `collapse` and the `test` wrapper left the engine for Python's own
#: list comparison and `assert`, and the two equations plus the one call that
#: runs over them are all that is left. Against the example's 4460 the ratio is
#: 0.3231 [measured 2026-08-22 min-of-3].
BUDGET = 1441


def twin(m):
    """Two alternatives for one head, and the answers both of them give."""
    @rules
    def mycalc(x, y):
        yield equation(S.mycalc(x, y)).to(x + y)
        yield equation(S.mycalc(x, y)).to(x - y)

    m.add(*mycalc)

    assert m.fn("mycalc").all(1, 2) == [3, -1]
