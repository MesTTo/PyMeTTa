"""The Python twin of examples/integration/py_numpy.metta: numpy through the seam.

Every `!(bind! np-abs (py-atom numpy.absolute))` is a PYTHON NAME BINDING here,
which is the design authority's own lowering for `bind!`: a token existed so a
MeTTa program could name a Python object, and a Python program names it with
`=`. So `np_abs = val(np.absolute)` IS the form, `numpy.absolute` is reached as
the object rather than by parsing its dotted path, and the form answers the unit
because there is nothing left to evaluate. The residue records the token half
against P14.15: a `bind!` token does not survive from one `m.eval` to the next,
so a twin cannot use the MeTTa spelling across forms even if it wanted to.

`__class__` and `__name__` come from `sym(...)` rather than `S`: the factory
refuses every name beginning with `__`, and its subscript door forwards to the
same guard. That is filed as residue against P14.5.
"""

import numpy as np

from petta import S, expr, sym, val

#: What a `bind!` form answers. The Python name binding above it IS the
#: lowering, so the form has nothing left to evaluate and answers the unit.
BOUND = [expr()]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6801 to 6803, +2, by the current NumPy crossing
#: floor rather than a merged semantic path: twelve fresh processes on
#: de61495's branch tree, 7932219's authoring-surface tree and the merged
#: worktree all cost 6803. No Defined call or space drop occurs here.
BUDGET = 6803


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(bind! np-abs (py-atom numpy.absolute))
    np_abs = val(np.absolute)
    yield BOUND

    # !(test (py-dot (py-dot (np-abs -5) __class__) __name__) "int64")
    yield m.eval(
        S.test(S["py-dot"](S["py-dot"]((np_abs, -5), sym("__class__")), sym("__name__")),
            val("int64"))
    )

    # !(test ((py-dot (np-abs -5) item)) 5)
    yield m.eval(S.test((S["py-dot"]((np_abs, -5), S.item),), 5))

    # !(bind! np-array (py-atom numpy.array))
    np_array = val(np.array)
    yield BOUND

    # !(test (py-dot (py-dot (np-array (py-atom "[1, 2, 3]")) __class__) __name__)
    #        "ndarray")
    yield m.eval(
        S.test(S["py-dot"](S["py-dot"]((np_array, val([1, 2, 3])),
                    sym("__class__")),
                sym("__name__")),
            val("ndarray"))
    )

    # !(bind! np-arange (py-atom numpy.arange))
    np_arange = val(np.arange)
    yield BOUND

    # !(test (collapse (py-iter ((py-dot (np-arange 4) tolist)))) (0 1 2 3))
    yield m.eval(
        S.test(S.collapse(S["py-iter"]((S["py-dot"]((np_arange, 4), S.tolist),))),
            (0, 1, 2, 3))
    )

    # !(test (collapse (py-iter ((py-dot (np-arange (Kwargs (step 2) (stop 8))) tolist))))
    #        (0 2 4 6))
    yield m.eval(
        S.test(S.collapse(S["py-iter"]((S["py-dot"]((np_arange,
                                S.Kwargs(S.step(2), S.stop(8))),
                            S.tolist),))),
            (0, 2, 4, 6))
    )

    # !(test (collapse (py-iter ((py-dot (np-arange (Kwargs (start 2) (stop 10) (step 3)))
    #                                    tolist))))
    #        (2 5 8))
    yield m.eval(
        S.test(S.collapse(S["py-iter"]((S["py-dot"]((np_arange,
                                S.Kwargs(S.start(2),
                                    S.stop(10),
                                    S.step(3))),
                            S.tolist),))),
            (2, 5, 8))
    )

    # !(bind! np-random (py-atom numpy.random))
    np_random = val(np.random)
    yield BOUND

    # !(test (py-dot (py-dot ((py-dot np-random randint) 25) __class__) __name__) "int")
    yield m.eval(
        S.test(S["py-dot"](S["py-dot"]((S["py-dot"](np_random, S.randint), 25),
                    sym("__class__")),
                sym("__name__")),
            val("int"))
    )
