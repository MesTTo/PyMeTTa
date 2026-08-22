"""The Python twin of examples/data/iter.metta: an iterator that is a number.

`iter-next` answers a PAIR of the current value and the next state, so the
whole iterator protocol is one equation over a number. Both definitions are
computations and are written as ones: assignment in a compiled body IS
MeTTa's `let`, so `x = n` and `nxt = n + 1` are the two bindings the
original's `let*` writes, compiled as nested one-pair `let*`s, and the
returned Python tuple `(x, nxt)` is the expression `($X $Next)`.

The runnable form stays at the container door because its `let*` pairs
DESTRUCTURE: `(($x1 $it1) (iter-next $it))` binds two names from one answer,
and a compiled body binds plain names only, which the residue table already
records against P14.4.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3922 to 5783, +1861 (+47.45%), by the wave-4 idiom
#: rewrite moving both definitions onto @m.define, in two separable parts.
#: COMPILING a definition costs more than STORING one, and the difference is
#: paid once per process plus a little per definition, never per call: four
#: trivial one-parameter definitions in a fresh process measured
#: 2221 / 2986 / 3751 / 4516 inferences through @m.define against
#: 592 / 1164 / 1736 / 2308 through `m += equation(...).to(...)`, so the first
#: compiled definition costs 1,629 more and each one after it 193 more.
#: Two definitions here is 1629 + 193 = 1822 of it. The other 39 is the BODY
#: SHAPE: two assignments compile to nested one-pair `let*`s where the
#: original writes one `let*` with two pairs, measured 3961 against 3922 by
#: storing the nested shape at the container door.
BUDGET = 5783


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """

    @m.define(name="make-nat-iter")
    def make_nat_iter():
        # iterator state is just a number
        # (= (make-nat-iter) 0)
        return 0

    @m.define(name="iter-next")
    def iter_next(n):
        # (= (iter-next $N) (let* (($X $N) ($Next (+ $N 1))) ($X $Next)))
        x = n
        nxt = n + 1
        return (x, nxt)

    # !(test (let* (($it (make-nat-iter))
    #               (($x1 $it1) (iter-next $it))
    #               (($x2 $it2) (iter-next $it1))
    #               (($x3 $it3) (iter-next $it2)))
    #              ($x1 $x2 $x3))
    #        (0 1 2))
    yield m.eval(
        S.test(
            S["let*"](
                (
                    (V.it, S["make-nat-iter"]()),
                    ((V.x1, V.it1), S["iter-next"](V.it)),
                    ((V.x2, V.it2), S["iter-next"](V.it1)),
                    ((V.x3, V.it3), S["iter-next"](V.it2)),
                ),
                (V.x1, V.x2, V.x3),
            ),
            (0, 1, 2),
        )
    )
