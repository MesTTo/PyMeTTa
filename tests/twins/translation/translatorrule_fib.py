"""The Python twin of examples/translation/translatorrule_fib.metta.

A translator rule on `compilefib` makes `(compilefib 10)` expand at COMPILE
time, so `smartfun`'s equation is stored already holding 55 and the tenth
Fibonacci number is never computed at run time.

`compilefib` and `smartfun` are computations and are written as ones, and
their order matters: the rule is registered between them, which is what lets
`smartfun`'s body be expanded as it compiles.

`fib-tr` and `fib` stay at the container door, each for its own reason.
`fib-tr`'s condition is `(== $n 0)`, and Python's `==` in a compiled body does
not lower to MeTTa's `==`: it lowers to `py-eq`, a registered Python operation
that crosses the host boundary on every comparison, which inside a
tail-recursive loop is the callback-lane cliff the design authority names.
`V.n.eq(0)` builds the engine's own `==` at the term door, so the equation
stored is the equation the example stores. `fib`'s body then names `fib-tr`,
and a compiled body resolves a free name EXACTLY, so a hyphenated engine
function cannot be reached from one. Both are recorded against P14.4.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6199 to 8119, +1920 (+30.97%), by the wave-4 idiom
#: rewrite moving `compilefib` and `smartfun` onto @m.define. COMPILING a
#: definition costs more than STORING one, and the difference is paid once per
#: process plus a little per definition, never per call: four trivial
#: one-parameter definitions in a fresh process measured
#: 2221 / 2986 / 3751 / 4516 inferences through @m.define against
#: 592 / 1164 / 1736 / 2308 through `m += equation(...).to(...)`, so the first
#: compiled definition costs 1,629 more and each one after it 193 more. The
#: 6199 this twin was pinned at is the same four equations stored, so the
#: whole move is those two definitions, 51 above 1629 + 193.
#: A second, smaller cause is in this figure: binding an engine function with
#: `m.fn(...)` makes its name PYTHON-RESOLVABLE, so @m.define records no
#: hazard and builds a RUNNABLE Python twin where it would otherwise build one
#: that refuses. Measured by deleting only that binding line: 8072 against
#: 8119, and with it `compilefib.py(10)` answers where without it the twin raises
#: "its body uses the engine function ..., which exist only in the engine".
BUDGET = 8119


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    the `add-translator-rule!` form answers the rule it registered.
    """
    # `fib`, whose equation is stored below, bound so the Python stays valid.
    # A compiled body resolves the NAME through the engine's registry rather
    # than through this object, so the binding changes nothing it emits.
    fib = m.fn("fib")
    # (= (fib-tr $n $a $b) (if (== $n 0) $a (fib-tr (- $n 1) $b (+ $a $b))))
    m += equation(S["fib-tr"](V.n, V.a, V.b)).to(
        S["if"](
            V.n.eq(0), V.a, S["fib-tr"](V.n - 1, V.b, V.a + V.b)
        )
    )

    # (= (fib $n) (fib-tr $n 0 1))
    m += equation(S.fib(V.n)).to(S["fib-tr"](V.n, 0, 1))

    @m.define
    def compilefib(n):
        # (= (compilefib $n) (fib $n))
        return fib(n)

    # can be commented out but then the following will be slower:
    # !(add-translator-rule! compilefib)
    yield m.eval(S["add-translator-rule!"](S.compilefib))

    @m.define
    def smartfun(b):
        # (= (smartfun $b) (* (compilefib 10) $b))
        return compilefib(10) * b

    # !(test (smartfun 42) 2310)
    yield m.eval(S.test(S.smartfun(42), 2310))
