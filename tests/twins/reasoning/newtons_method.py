"""examples/reasoning/newtons_method.metta in Python: memoised double recursion.

`energy` calls itself twice on the same smaller argument, so without a cache it
doubles at every level. The example imports lib_memo, sets a cache policy, and
memoises the function by name; then two claims read it.

`energy` is an ordinary Python function. The `if` is MeTTa's `if`, the
arithmetic is Python's own operators over the compiled parameters, and the two
recursive calls are the calls the equation makes, so `@m.define` lands the
example's own equation up to variable naming and `memoize` reaches it by name
like any other definition. Calling it evaluates, which is why the claims read
`energy(2.0, 0)` and not a rebuilt term.

The three directives stay terms: each names an engine service rather than a
computation, and lib_memo has no Python face.

The definition is written FIRST, where the example writes it fourth. A file
loader registers a file's function names before it runs the file's `!` forms,
so `!(memoize energy)` finds `energy` there; a Python program has no such
pre-pass and `memoize` on an unknown name is a domain error. The residue
records the missing batch door against P14.4.
"""

from petta import S

#: The space the import writes.
SELF = S["&self"]  # rung: no import door hangs off the space handle

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 146888 to 144836, -2052 (-1.40%), by the twin contract
#: change: two `test` wrappers left the engine for Python's own `assert` and the
#: two calls under them became calls on the `Defined` object, which is all that
#: could move here; the memoised recursion is the example. `energy` was already
#: compiled at the previous pin, so `@m.define`'s per-name admission is inside
#: both figures: three reflection facts the container door never writes
#: (`(defined &self energy)`, `(effect energy immutable)` and
#: `(source-span &self energy ...)`), measured on this tree at 1629 inferences
#: for this clause and 1629 for a one-line `def f(x): return x`, so the charge
#: is per decorated NAME rather than per clause size. Against the example's
#: 139949 the ratio is 1.0349, the one twin in these three folders that costs
#: MORE than its example, and that decoration is why [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure
#: examples/reasoning/newtons_method.metta`]. Prior: RE-PINNED at 146888, +1729,
#: when `energy` gained the decorator; ADDED 2026-08-22 at 145159 by the wave-3
#: twin baseline.
BUDGET = 144836


def twin(m):
    """Define the recursion, memoise it, then read two of its values."""
    m.eval(S["import!"](SELF, S.library(S.lib_memo)))

    @m.define
    def energy(x, n):
        """Halve, shift, and add the same branch to itself."""
        if n <= 0:
            return x * x
        return energy(0.5 * x + 0.4, n - 1) + energy(0.5 * x + 0.4, n - 1)

    m.eval(S["config-memoize"](S.strategy(S.wtinylfu), S["unique-limit"](100)))
    m.eval(S.memoize(S.energy))

    # Base case: x*x.
    assert energy(2.0, 0) == [4.0]
    # One level down: 1.4*1.4 twice.
    assert energy(2.0, 1) == [3.9199999999999995]
