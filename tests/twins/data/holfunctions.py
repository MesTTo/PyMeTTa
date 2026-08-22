"""The Python twin of examples/data/holfunctions.metta: higher-order folds.

Each of `foldl-atom`, `map-atom` and `filter-atom` takes its step either as an
inline TEMPLATE, naming the variables it binds, or as a FUNCTION passed by
name. The example writes both and checks they agree.

`foldfun`, `mapfun`, `filterfun` and `foldfun2` are computations and are
written as ones; `foldfun2` shows that a body may name an engine function the
engine knows under a Python-spellable name, which `append` is.

The six `f...` definitions stay at the container door. Their bodies name
`foldl-atom`, `map-atom` and `filter-atom`, and a compiled body resolves a
free name EXACTLY, so a hyphenated engine function cannot be reached from one;
the template forms additionally bind `$acc` and `$x` inside the call, which is
not a Python binding position at all. Both are recorded against P14.4.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 14069 to 16462, +2393 (+17.01%), by the wave-4 idiom
#: rewrite moving `foldfun`, `mapfun`, `filterfun` and `foldfun2` onto
#: @m.define.
#: COMPILING a definition costs more than STORING one, and the difference is
#: paid once per process plus a little per definition, never per call: four
#: trivial one-parameter definitions in a fresh process measured
#: 2221 / 2986 / 3751 / 4516 inferences through @m.define against
#: 592 / 1164 / 1736 / 2308 through `m += equation(...).to(...)`, so the first
#: compiled definition costs 1,629 more and each one after it 193 more.
#: Four definitions here measured 16362 against 14069 for the same four at the
#: container door, the whole of the move; the 85 above 1629 + 3*193 is these
#: bodies being larger than the trivial ones the rate was taken on.
#: A second, smaller cause is in this figure: binding an engine function with
#: `m.fn(...)` makes its name PYTHON-RESOLVABLE, so @m.define records no
#: hazard and builds a RUNNABLE Python twin where it would otherwise build one
#: that refuses. Measured by deleting only that binding line: 16362 against
#: 16462, and with it `foldfun2.py((1, 2), (3,))` answers `(1 2 3)` where without it the twin raises
#: "its body uses the engine function ..., which exist only in the engine".
BUDGET = 16462


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    the last form says its own answer in the comment above it.
    """
    # The engine's own `append`, bound so the Python below stays valid. A
    # compiled body resolves the NAME through the engine's registry rather
    # than through this object, so the binding changes nothing it emits.
    append = m.fn("append")
    # (= (f1a) (foldl-atom (1 2 3 4) 0 $acc $x (+ $acc $x)))
    m += equation(S.f1a()).to(
        S["foldl-atom"]((1, 2, 3, 4), 0, V.acc, V.x, V.acc + V.x)
    )
    # (= (f2a) (map-atom (1 2 3) $x (+ $x 1)))
    m += equation(S.f2a()).to(S["map-atom"]((1, 2, 3), V.x, V.x + 1))
    # (= (f3a) (filter-atom (1 2 3 4 5) $x (> $x 3)))
    m += equation(S.f3a()).to(S["filter-atom"]((1, 2, 3, 4, 5), V.x, V.x > 3))

    @m.define
    def foldfun(a, b):
        # (= (foldfun $a $b) (+ $a $b))
        return a + b

    @m.define
    def mapfun(a):
        # (= (mapfun $a) (+ $a 1))
        return a + 1

    @m.define
    def filterfun(x):
        # (= (filterfun $x) (> $x 3))
        return x > 3

    # (= (f1b) (foldl-atom (1 2 3 4) 0 foldfun))
    m += equation(S.f1b()).to(S["foldl-atom"]((1, 2, 3, 4), 0, S.foldfun))
    # (= (f2b) (map-atom (1 2 3) mapfun))
    m += equation(S.f2b()).to(S["map-atom"]((1, 2, 3), S.mapfun))
    # (= (f3b) (filter-atom (1 2 3 4 5) filterfun))
    m += equation(S.f3b()).to(S["filter-atom"]((1, 2, 3, 4, 5), S.filterfun))

    # !(test (f1a) 10)
    yield m.eval(S.test(S.f1a(), 10))
    # !(test (f2a) (2 3 4))
    yield m.eval(S.test(S.f2a(), (2, 3, 4)))
    # !(test (f3a) (4 5))
    yield m.eval(S.test(S.f3a(), (4, 5)))

    # !(test (f1b) 10)
    yield m.eval(S.test(S.f1b(), 10))
    # !(test (f2b) (2 3 4))
    yield m.eval(S.test(S.f2b(), (2, 3, 4)))
    # !(test (f3b) (4 5))
    yield m.eval(S.test(S.f3b(), (4, 5)))

    @m.define
    def foldfun2(a, b):
        # (= (foldfun2 $a $b) (append $a $b))
        return append(a, b)

    # A fold that builds an expression rather than a number; answers (1 2 3 4 5 6)
    # !(foldl-atom ((1 2) (3 4) (5 6)) () $acc $x (append $acc $x))
    yield m.eval(
        S["foldl-atom"](
            ((1, 2), (3, 4), (5, 6)), (), V.acc, V.x, S.append(V.acc, V.x)
        )
    )
