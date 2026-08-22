"""The Python twin of examples/reasoning/newtons_method.metta: memoised recursion.

`energy` is an ordinary Python function: the `if` is MeTTa's `if`, the
arithmetic is Python's own operators over the compiled parameters, and the two
recursive calls are the same call the equation makes. `@m.define` reads it as
syntax, so what lands in the space is the example's equation up to variable
naming, and `!(memoize energy)` reaches it by name like any other definition.

The three directive forms stay terms because each names an engine service
rather than a computation: `import!` loads a library, `config-memoize` and
`memoize` set the cache's policy.

The definition is written FIRST, where the example writes it fourth. The file
loader registers a file's function names before it runs the file's `!` forms,
so `!(memoize energy)` finds `energy` there; a Python program has no such
pre-pass, and `m.eval(S.memoize(S.energy))` on an undefined name is a domain
error. The residue records the missing batch door against P14.4, beside
examples/libraries/test_memo_aggregate.metta, which is the same friction.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 145159 to 146888, +1729 (+1.19%), by the definitional
#: decorator replacing the hand-built equation. The compiled clause is the same
#: clause; what @m.define adds is its per-name ADMISSION, three reflection facts
#: the container door never writes, `(defined &self energy)`,
#: `(effect energy immutable)` and `(source-span &self energy ...)`. Measured
#: on this tree at 1629 inferences for this clause and 1629 for a one-line
#: `def f(x): return x`, so the charge is per decorated NAME rather than per
#: clause size, paid once at decoration and never per reduction. Prior: ADDED
#: 2026-08-22 at 145159 by the wave-3 twin baseline.
BUDGET = 146888


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def energy(x, n):
        # (= (energy $x $n)
        #    (if (<= $n 0)
        #        (* $x $x)
        #        (+ (energy (+ (* 0.5 $x) 0.4) (- $n 1))
        #           (energy (+ (* 0.5 $x) 0.4) (- $n 1)))))
        if n <= 0:
            return x * x
        return energy(0.5 * x + 0.4, n - 1) + energy(0.5 * x + 0.4, n - 1)

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # !(config-memoize (strategy wtinylfu) (unique-limit 100))
    yield m.eval(S["config-memoize"](S.strategy(S.wtinylfu), S["unique-limit"](100)))

    # !(memoize energy)
    yield m.eval(S.memoize(S.energy))

    # Base case: n=0 returns x*x = 4.0
    # !(test (energy 2.0 0) 4.0)
    yield m.eval(S.test(S.energy(2.0, 0), 4.0))

    # Recursive case: energy(2.0, 1) = 1.4*1.4 + 1.4*1.4 = 1.96 + 1.96 = 3.92
    # !(test (energy 2.0 1) 3.9199999999999995)
    yield m.eval(S.test(S.energy(2.0, 1), 3.9199999999999995))
