"""The Python twin of examples/functions/smartdispatch.metta: which heads run.

One form asks five questions at once. `(f 21)` reduces, `(g f 2)` keeps `f` as
DATA inside `(justdata f 2)`, `(h f 2)` applies it, `((notjustdata 42) 21)`
computes the head first and then applies it, and
`(datawithnondatacomponent)` answers data with a call nested inside it, which
reduces where it sits.

Three definitions are ordinary Python functions, including the two that make
the point: `h` applies its parameter (`f(x)` compiles to `($f $x)`) and
`notjustdata` ANSWERS one (a free name the engine knows compiles to that
symbol, so `return f` writes `f`).

The other two are equations, because their bodies are lowercase symbols used
as DATA: `justdata` and `lol` name nothing the engine defines, and a compiled
body reads a lowercase free name as a call it cannot resolve, since
capitalisation is what marks a data constructor there. `g` has a variable in
its head, so it takes the `@rules` shape of the definitional decorator, where the
generator's parameters ARE the equation's variables;
`datawithnondatacomponent` has none, so it is one `equation(...).to(...)` and
a generator around it would say nothing. The residue table records the gap
against P14.4.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6852 to 9049, +2197 (+32.06%), and ALL of it is
#: definition installation: the five definitions cost 2620 as equation atoms
#: and 4817 with `f`, `h` and `notjustdata` decorated, +2197, which is the
#: whole move. The one runnable form is unchanged, because both doors land
#: the same five equations. Nearly all of the +2197 is per-definition rather
#: than one-time: three decorated bodies here, where the FIRST decorated
#: definition in a process costs 2244 against the atom door's 600 for one
#: equation and every later one costs 793 against 600. The lane's parity
#: reads 0.80 of the original. Prior: ADDED 2026-08-22 at 6852 by 7f15dc1's
#: wave-3 baseline.
BUDGET = 9049


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def f(x):
        # (= (f $x) (* $x 2))
        return x * 2

    @rules
    def data_heads(f, x):
        # (= (g $f $x) (justdata $f $x))
        yield equation(S.g(f, x)).to(S.justdata(f, x))

    m.add(*data_heads)

    @m.define
    def h(f, x):
        # (= (h $f $x) ($f $x))
        return f(x)

    @m.define
    def notjustdata(_x):
        # (= (notjustdata $x) f)
        return f

    # (= (datawithnondatacomponent) ((lol (f 42))))
    m += equation(S.datawithnondatacomponent()).to((S.lol(S.f(42)),))

    # !(test ((f 21) (g f 2) (h f 2) ((notjustdata 42) 21) (datawithnondatacomponent))
    #        (42 (justdata f 2) 4 42 ((lol 84))))
    yield m.eval(
        S.test(
            (
                S.f(21),
                S.g(S.f, 2),
                S.h(S.f, 2),
                (S.notjustdata(42), 21),
                S.datawithnondatacomponent(),
            ),
            (42, S.justdata(S.f, 2), 4, 42, (S.lol(84),)),
        )
    )
