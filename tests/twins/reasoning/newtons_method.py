"""Purpose: examples/reasoning/newtons_method.metta in Python: memoised double recursion.

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
computation, and lib_memo has no Python face. The import takes the space
HANDLE, because a space crosses a term position as itself.

The definition is written FIRST, where the example writes it fourth. A file
loader registers a file's function names before it runs the file's `!` forms,
so `!(memoize energy)` finds `energy` there; a Python program has no such
pre-pass and `memoize` on an unknown name is a domain error. The residue
records the missing batch door against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Define the recursion, memoise it, then read two of its values."""
    # The library's file name is `lib_memo.metta`, and the factory attribute
    # door maps every underscore to a hyphen, so the name takes the bracket.
    m.fn["import!"](m, S.library(S["lib_memo"]))

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
