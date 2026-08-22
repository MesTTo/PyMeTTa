"""The Python twin of examples/libraries/tabling_equation_change.metta.

A table answers from the equations compiled when it was built, so changing an
equation makes it stale. The engine's own change funnel drops the tables, and
the next call rebuilds them.

Both equations are written at the container door and both reasons are recorded
against P14.4: a compiled body reads a bare lowercase name as neither a
parameter nor a constructor nor a known function, so the answers `one` and `two`
have no spelling in one; and the two clauses share a head, where a second
`@m.define` REPLACES the earlier clause instead of stacking beside it, which is
the opposite of what this example needs since it removes one of the two by hand
at the end.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 77656 to 77656, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: the lowercase answers and the two clauses sharing
#: a head keep both equations at the container door, and
#: equation(...).to(...) builds the same atoms S["="](...) built. Prior:
#: ADDED 2026-08-22 at 77656 by the wave-3 libraries baseline, which recorded
#: no cause.
BUDGET = 77656


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_tabling))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_tabling)))

    # (= (pick $x) one)
    m += equation(S.pick(V.x)).to(S.one)

    # !(tabled (pick $x))
    yield m.eval(S.tabled(S.pick(V.x)))

    # !(test (collapse (pick a)) (one))
    yield m.eval(S.test(S.collapse(S.pick(S.a)), (S.one,)))
    # !(test (collapse (pick a)) (one))
    yield m.eval(S.test(S.collapse(S.pick(S.a)), (S.one,)))

    # A second equation for the same function. Without invalidation the table
    # keeps answering (one).
    # (= (pick $x) two)
    m += equation(S.pick(V.x)).to(S.two)

    # sort-atom, because a TABLED function does not answer in clause order.
    # !(test (sort-atom (collapse (pick a))) (one two))
    yield m.eval(
        S.test(S["sort-atom"](S.collapse(S.pick(S.a))), (S.one, S.two))
    )

    # Removing one again.
    # !(remove-atom &self (= (pick $x) one))
    yield m.eval(S["remove-atom"](S["&self"], equation(S.pick(V.x)).to(S.one)))

    # !(test (collapse (pick a)) (two))
    yield m.eval(S.test(S.collapse(S.pick(S.a)), (S.two,)))
