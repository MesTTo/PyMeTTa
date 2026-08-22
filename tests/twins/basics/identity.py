"""examples/basics/identity.metta in Python: square a number, check the answer.

The example defines `(= (f $x) (* $x $x))` and asserts `(f 1)` is 1. Here the
definition is an ordinary Python function the engine compiles, and the claim
is Python's own `assert`.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-23, 2289 to 2226, -63, by two changes with separate
#: causes that partly cancel. The lane now hands the child a BUILT measurement
#: environment rather than inheriting the caller's, which is worth -91 to any
#: twin that compiles a definition and nothing to one that does not; and the
#: startup-perf merge's type-system work is worth +28 here. Against the
#: example's 2577 the ratio is 0.8638 [measured 2026-08-23 min-of-3]. NOTE that
#: the other 203 budgets in this corpus are stale by the same arithmetic and
#: are re-pinned in the one pass scheduled after the surface tracks land; this
#: twin and spaces3 are re-pinned now because the gate checks them end to end.
#: Prior: RE-PINNED 2026-08-22 at 2289 by the twin contract change, when the
#: definition moved to `@m.define`; the figure before that priced a different
#: program.
BUDGET = 2226


def twin(m):
    """Define the square, then check it."""
    @m.define
    def f(x):
        return x * x

    assert f(1) == [1]
