"""The Python twin of examples/data/foldallspacecount.metta: counting a space.

`countitem` answers 1 once per match, so folding it with `merge` counts the
matches. `merge` is a computation and is written as one.

`countitem` and `spacecount` stay at the container door, each for its own
reason. A compiled `match(space, pattern, template)` reads its PATTERN in a
scope where a lowercase name is a fresh variable, but it reads its TEMPLATE
with the ordinary expression compiler, which resolves a lowercase free name
as a FUNCTION, so the template `(foo $1)` raises a refusal saying `foo` is
not a parameter of `countitem`, not a function the engine knows, and not a
capitalized data constructor. A relation that is data on both sides of a
match has no compiled spelling, and the residue table records that against
P14.4. `spacecount`'s body names `foldall`, which is not a function
the engine knows either, so a body cannot reach it.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3263 to 4892, +1629 (+49.92%), by the wave-4 idiom
#: rewrite moving `merge` onto @m.define.
#: COMPILING a definition costs more than STORING one, and the difference is
#: paid once per process plus a little per definition, never per call: four
#: trivial one-parameter definitions in a fresh process measured
#: 2221 / 2986 / 3751 / 4516 inferences through @m.define against
#: 592 / 1164 / 1736 / 2308 through `m += equation(...).to(...)`, so the first
#: compiled definition costs 1,629 more and each one after it 193 more.
#: One compiled definition here, so the move is exactly that first 1,629.
BUDGET = 4892


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # (foo 1) (foo 2) (foo 3)
    m += (S.foo, 1)
    m += (S.foo, 2)
    m += (S.foo, 3)

    # (= (countitem) (let $x (match &self (foo $1) (foo $1)) 1))
    m += equation(S.countitem()).to(
        S.let(V.x, S.match(S["&self"], S.foo(V["1"]), S.foo(V["1"])), 1)
    )

    @m.define
    def merge(a, b):
        # (= (merge $a $b) (+ $a $b))
        return a + b

    # (= (spacecount $x) (foldall merge (countitem) 0))
    m += equation(S.spacecount(V.x)).to(S.foldall(S.merge, S.countitem(), 0))

    # !(test (foldall merge (countitem) 0) 3)
    yield m.eval(S.test(S.foldall(S.merge, S.countitem(), 0), 3))
