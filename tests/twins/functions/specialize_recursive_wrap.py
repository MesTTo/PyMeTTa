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

One divergence to know about: `n == 0` compiles to `(py-eq $n 0)`, Python's
own equality through the prelude, where the original writes MeTTa's
`(== $n 0)`. Both answer True here and the residue table records the lowering
against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11864 to 11737, -127 (-1.1%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`; the three
#: definitions and the compile-time specialization they exist for are all
#: of the rest. Against the example's 13464 the ratio is 0.8717 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 11737


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
