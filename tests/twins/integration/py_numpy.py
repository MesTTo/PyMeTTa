"""The Python twin of examples/integration/py_numpy.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

import numpy as np

from petta import S, expr, sym, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6801 to 6803, +2, by the current NumPy crossing
#: floor rather than a merged semantic path: twelve fresh processes on
#: de61495's branch tree, 7932219's authoring-surface tree and the merged
#: worktree all cost 6803. No Defined call or space drop occurs here.
BUDGET = 6803


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(bind! np-abs (py-atom numpy.absolute))
    np_abs = val(np.absolute)
    yield [expr()]

    # !(test (py-dot (py-dot (np-abs -5) __class__) __name__) "int64")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["py-dot"], expr(S["py-dot"], expr(np_abs, -5), sym("__class__")), sym("__name__")
            ),
            val("int64"),
        )
    )

    # !(test ((py-dot (np-abs -5) item)) 5)
    yield m.eval(expr(S["test"], expr(expr(S["py-dot"], expr(np_abs, -5), S["item"])), 5))

    # !(bind! np-array (py-atom numpy.array))
    np_array = val(np.array)
    yield [expr()]

    # !(test (py-dot (py-dot (np-array (py-atom "[1, 2, 3]")) __class__) __name__)
    #        "ndarray")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["py-dot"],
                expr(
                    S["py-dot"],
                    expr(np_array, val([1, 2, 3])),
                    sym("__class__"),
                ),
                sym("__name__"),
            ),
            val("ndarray"),
        )
    )

    # !(bind! np-arange (py-atom numpy.arange))
    np_arange = val(np.arange)
    yield [expr()]

    # !(test (collapse (py-iter ((py-dot (np-arange 4) tolist)))) (0 1 2 3))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["py-iter"], expr(expr(S["py-dot"], expr(np_arange, 4), S["tolist"]))),
            ),
            expr(0, 1, 2, 3),
        )
    )

    # !(test (collapse (py-iter ((py-dot (np-arange (Kwargs (step 2) (stop 8))) tolist))))
    #        (0 2 4 6))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["py-iter"],
                    expr(
                        expr(
                            S["py-dot"],
                            expr(
                                np_arange,
                                expr(S["Kwargs"], expr(S["step"], 2), expr(S["stop"], 8)),
                            ),
                            S["tolist"],
                        )
                    ),
                ),
            ),
            expr(0, 2, 4, 6),
        )
    )

    # !(test (collapse (py-iter ((py-dot (np-arange (Kwargs (start 2) (stop 10) (step 3)))
    #                                    tolist))))
    #        (2 5 8))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["py-iter"],
                    expr(
                        expr(
                            S["py-dot"],
                            expr(
                                np_arange,
                                expr(
                                    S["Kwargs"],
                                    expr(S["start"], 2),
                                    expr(S["stop"], 10),
                                    expr(S["step"], 3),
                                ),
                            ),
                            S["tolist"],
                        )
                    ),
                ),
            ),
            expr(2, 5, 8),
        )
    )

    # !(bind! np-random (py-atom numpy.random))
    np_random = val(np.random)
    yield [expr()]

    # !(test (py-dot (py-dot ((py-dot np-random randint) 25) __class__) __name__) "int")
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["py-dot"],
                expr(
                    S["py-dot"],
                    expr(expr(S["py-dot"], np_random, S["randint"]), 25),
                    sym("__class__"),
                ),
                sym("__name__"),
            ),
            val("int"),
        )
    )

    yield from ()
