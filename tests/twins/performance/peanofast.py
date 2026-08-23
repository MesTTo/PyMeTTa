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
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1


def twin(m):
    """Build 2500 Peano successors, then count them."""

    # `expandK` is camelCase, which the naming ladder's underscore map does
    # not produce from any Python identifier, so this one door states the
    # exact name while the Python side stays snake_case.
    @m.define(name="expandK")
    def expand_k(expression, n):
        if n == 0:
            return S.done
        _written = fn.add_atom(fn.context_space(), S.num(expression))
        return expand_k(S.S(expression), n - 1)

    @m.define
    def demo_peano(k):
        """Expand from zero, k times."""
        # One rule at both call sites: a compiled body naming a bound
        # `Defined` sibling emits the MeTTa name that object was installed
        # under, so this stores `(expandK Z $k)`.
        return expand_k(S.Z, k)

    assert demo_peano(2500) == [S.done]
    assert len(m[S.num(V.stored)]) == 2500
