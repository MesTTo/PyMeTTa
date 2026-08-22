"""The Python twin of examples/functions/specialize_recursive_wrap.metta.

The original is a compile-time regression: a recursive call that WRAPS its own
higher-order argument used to build a bigger specialization key at every step
and never terminate. Re-specializing a function already being specialized is
refused now, so the inner call compiles unspecialized and translation ends.

All three definitions are ordinary Python. `twice` applies its first parameter
to its own result, which is variable-head application (`r(r(g))` compiles to
`($r ($r $g))`), and `evolve` is a Python conditional expression whose
recursive call passes `twice(r)`, a PARTIAL application of a two-parameter
function. Neither needs a MeTTa spelling: the subset already reads both.

One divergence to know about, since it is five of this twin's inferences:
`n == 0` compiles to `(py-eq $n 0)`, Python's own equality through the
prelude, where the original writes MeTTa's `(== $n 0)`. Both answer True here
and the residue table records the lowering against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9800 to 11864, +2064 (+21.06%), by the rewrite onto
#: the decorator, and the whole move splits into two measured causes. The
#: definitions cost 6310 as equation atoms and 8369 through `@m.define` in
#: this file's own nesting, +2059: a decorated definition compiles Python
#: syntax where the atom door stores a term, the FIRST one in a process pays
#: a one-time setup (2244 against the atom door's 600 for the same equation,
#: where every later one costs 793 against 600), and a callee reached through
#: a closure cell rather than a module global costs 147 more across these
#: three. The runnable form costs 3500 against 3495, +5, because `n == 0`
#: compiles to `(py-eq $n 0)` where the original writes `(== $n 0)`; the
#: residue table records that lowering against P14.4. 2059 + 5 = 2064, the
#: whole of it. The lane's parity reads 0.88 of the original. Prior: ADDED
#: 2026-08-22 at 9800 by 7f15dc1's wave-3 baseline.
BUDGET = 11864


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

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
        # (= (evolve $r $n $g)
        #    (if (== $n 0) $g (evolve (twice $r) (- $n 1) $g)))
        return g if n == 0 else evolve(twice(r), n - 1, g)

    # !(test (evolve derive 2 stmt) stmt)
    yield m.eval(S.test(S.evolve(S.derive, 2, S.stmt), S.stmt))
