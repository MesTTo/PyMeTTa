"""examples/spaces/match_snapshot.metta in Python: the query is a snapshot.

`match` finds every row BEFORE any output template runs, so a template that
writes to the space cannot change what the match still has to answer. The
language specifies this rather than leaving it open, and the graph-rewriting
example is why: reversing links one at a time as they are found would break the
cycle after the first rewrite.

The Python door says the same thing by being an ordinary sequence.
`space[pattern]` answers a materialised view, so the three loop links are all
found before the first `-=` runs, and the comprehension at the bottom pulls
both `item` rows before the first `visit` call removes the other one. Nothing
about that is special pleading: it is what `for row in rows` means.

The two `visit` equations are at the container door. Each head fixes a literal
symbol, `(visit alpha)`, where a compiled head pattern is a literal DEFAULT and
reaches neither a structure nor a symbol, and each body writes with a
hyphenated head no compiled body can spell (residue, P14.4).
"""

from collections import Counter

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6003 to 2531, -3472 (-57.8%), by the twin contract
#: change: four `(test (collapse ...) ...)` terms became four Python `assert`s,
#: so `test` and `collapse` left the engine four times and the first form's
#: match-with-a-writing-template became a Python loop over the same match. The
#: rewriting, the two equations and both visits stayed in the engine. Against
#: the example's 18311 the ratio is 0.1382.
#: Prior: 6003, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 2531

#: Upstream's own example, verbatim: three links form a loop, the fourth does
#: not.
LINKS = [(S.A, S.B), (S.B, S.C), (S.C, S.A), (S.C, S.E)]


def twin(m):
    """Reverse every link of a cycle, then watch two templates delete each other."""
    for tail, head in LINKS:
        m += S.link(tail, head)

    # All three rows are found before the first reversal breaks the cycle, so
    # all three are reverted and (link C E) is left alone.
    loop = m[S.link(V.x, V.y), S.link(V.y, V.z), S.link(V.z, V.x)]
    assert len(loop) == 3
    for row in loop:
        m -= S.link(row.x, row.y)
        m += S.link(row.y, row.x)

    assert Counter(S.link(row.x, row.y) for row in m[S.link(V.x, V.y)]) == Counter(
        [S.link(S.C, S.E), S.link(S.B, S.A), S.link(S.C, S.B), S.link(S.A, S.C)]
    )

    # The single-pattern case, reduced to its detector: two rows, and each
    # template removes the OTHER one. A lazy query would lose the row it had
    # not reached yet and answer once.
    snapshot = m.space("&snapshot")
    at_snapshot = S[snapshot.space_name]
    snapshot += S.item(S.alpha)
    snapshot += S.item(S.beta)

    def visit(removed, answered):
        """`(= (visit X) (let () (remove-atom &snapshot (item Y)) X))`."""
        drop = S["remove-atom"](at_snapshot, S.item(removed))  # rung: an equation body is one term, where the container doors are Python statements
        return S.let((), drop, answered)  # rung: as above

    m += equation(S.visit(S.alpha)).to(visit(S.beta, S.alpha))
    m += equation(S.visit(S.beta)).to(visit(S.alpha, S.beta))

    assert [m.one(S.visit(row.x)) for row in snapshot[S.item(V.x)]] == [S.alpha, S.beta]

    # Both removals happened, so the space is empty: each row's template ran,
    # and ran against the space the other row's template had written to.
    assert not list(snapshot)
