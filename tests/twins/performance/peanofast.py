"""Purpose: examples/performance/peanofast.metta in Python: 2500 successors, and how to count them.

`expandK` writes `(num Z)`, `(num (S Z))`, and so on down 2500 levels;
`demo-peano` starts it from `Z`. Then the space is asked how many `num` atoms
it holds.

Both equations are ordinary Python functions under the decorator. `expandK`
writes with the engine's own `add-atom`, spelled through the mention door
because a hyphen is not a Python identifier, and answers the lowercase symbol
`S.done` in its base case; the mention door reads both as syntax, so the whole
body compiles. `demo-peano` calls it by name and starts it from the data
constructor `S.Z`.

The count is Python's: `len(space[pattern])` is what `(length (collapse
(match ...)))` dissolves into, and this is the file where that dissolution is
expensive rather than free. Every answer here is a term of depth O(K), and the
query door builds a Python atom for each one, so counting costs Theta(K^2)
against the engine's linear collapse-and-length: 251,831 inferences at K=250,
1,003,611 at 500, 4,007,233 at 1000 and 16,014,711 at 2000, quadrupling per
doubling, against 1,308 / 2,058 / 3,558 / 6,558 [measured 2026-08-22,
ai-tmp/probe/f_query_scaling.py]. The missing door is a query that projects or
aggregates BEFORE it crosses, the way MeTTa's own `match` template does; the
count below is the spelling the surface rules, and the cost is the library's
to close (residue, P14.7).
"""

from petta import S, V, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Build 2500 Peano successors, then count them."""

    # The define door does not apply rung 4's underscore-to-hyphen map, so
    # every MeTTa name that is not a Python identifier states itself through
    # `name=`; the Python side stays snake_case, which is what PEP 8 and the
    # linter both want [measured 2026-08-23: `def find_divisor` lands as
    # `find_divisor`, not `find-divisor`; commit=WORKTREE].
    @m.define(name="expandK")
    def expand_k(expression, n):
        if n == 0:
            return S.done
        _written = fn.add_atom(fn.context_space(), S.num(expression))
        return expand_k(S.S(expression), n - 1)

    @m.define(name="demo-peano")
    def demo_peano(k):
        """Expand from zero, k times."""
        # A SELF-recursive call delegates through `name=`, which is why the
        # body above says `expand_k`. A call to ANOTHER definition resolves
        # the Python name against the engine instead, so it has to say the
        # MeTTa name through the mention door: a bare `expand_k(...)` here is
        # refused with "'expand_k' is not a parameter of demo-peano, not a
        # function the engine knows" [measured 2026-08-23; commit=WORKTREE].
        # PERFECT: one rule at both call sites, the way `name=` already binds
        # the two names together.
        return fn.expandK(S.Z, k)

    assert demo_peano(2500) == [S.done]
    assert len(m[S.num(V.stored)]) == 2500
