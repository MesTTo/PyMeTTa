"""Purpose: examples/spaces/match_snapshot.metta in Python: the query is a snapshot.

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

`visit` is one compiled definition where the original writes two equations, and
the door picked the form: two literal heads at one arity would overlap if they
were written as bare coexisting equations, so a Python `match` statement is the
spelling and it lowers to MeTTa's own case tower, exclusivity structural inside
one equation. The removals inside it are the engine's own `remove-atom` through
the mention door, with the snapshot space itself as the operand, because a
compiled body carries a handle the way a term does.
"""

from collections import Counter

import metta
from metta import S, V, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1

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
    snapshot = metta.space(S.snapshot)
    snapshot += S.item(S.alpha)
    snapshot += S.item(S.beta)

    # (= (visit alpha) (let () (remove-atom &snapshot (item beta)) alpha))
    # (= (visit beta)  (let () (remove-atom &snapshot (item alpha)) beta))
    @m.define
    def visit(item):
        match item:
            case S.alpha:
                _gone = fn.remove_atom(snapshot, S.item(S.beta))
                return S.alpha
            case S.beta:
                _gone = fn.remove_atom(snapshot, S.item(S.alpha))
                return S.beta

    assert [visit(row.x).one() for row in snapshot[S.item(V.x)]] == [S.alpha, S.beta]

    # Both removals happened, so the space is empty: each row's template ran,
    # and ran against the space the other row's template had written to.
    assert not list(snapshot)
