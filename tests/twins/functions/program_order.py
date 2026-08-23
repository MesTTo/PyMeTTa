"""examples/functions/program_order.metta in Python: source order counts.

The call comes before its equation and stays unreduced; the same call after
the equation reduces. A Python twin reads the same way for the same reason,
because statements run in order.

The equation is written at the container door, one rung below the decorator,
because its head fixes a SYMBOL: `(p121-example-respond me)` matches the atom
`me` and nothing else. A stacked `@m.define` clause fixes a head position with
a literal DEFAULT (`def g(n=1)` writes `(= (g 1) 1)`), and a literal is a
bool, int, float or str, never a symbol. The residue table records that
against P14.4.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Call before the definition, then after it."""
    respond = S["p121-example-respond"]

    # Nothing defines it yet, so the call answers ITSELF.
    assert m.eval(respond(S.me)) == [respond(S.me)]

    # (= (p121-example-respond me) hello)
    m += equation(respond(S.me)).to(S.hello)  # rung: the head fixes a SYMBOL

    assert m.eval(respond(S.me)) == [S.hello]
