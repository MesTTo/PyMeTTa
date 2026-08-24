"""examples/functions/specialize_recursive_wrap.metta in Python: a compile-time regression.

A recursive call that WRAPS its own higher-order argument used to build a
bigger specialization key at every step and never terminate. Re-specializing a
function already being specialized is refused now, so the inner call compiles
unspecialized and translation ends.

All three definitions are ordinary Python. `twice` applies its first parameter
to its own result, which is variable-head application (`r(r(g))` compiles to
`($r ($r $g))`), and `evolve` is a Python conditional expression whose
recursive call passes `twice(r)`, a PARTIAL application of a two-parameter
function. Neither needs a MeTTa spelling: the subset already reads both.

Python's `n == 0` is the source-faithful spelling: compiled-body equality
lowers to the engine's `==` relation rather than host structural comparison.
"""

from metta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1


def twin(m):
    """Wrap a function twice and evolve it, without diverging at compile time."""

    @m.define
    def derive(g):
        # (= (derive $g) $g)
        return g

    @m.define
    def twice(r, g):
        # (= (twice $r $g) ($r ($r $g)))
        return r(r(g))

    @m.define
    def evolve(r, n, g):
        # (= (evolve $r $n $g) (if (== $n 0) $g (evolve (twice $r) (- $n 1) $g)))
        return g if n == 0 else evolve(twice(r), n - 1, g)

    assert evolve(S.derive, 2, S.stmt) == [S.stmt]
