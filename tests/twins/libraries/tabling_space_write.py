"""The Python twin of examples/libraries/tabling_space_write.metta.

A table over a space stays fresh when the space changes: the engine declares the
storage predicates the function reads incremental, so SWI invalidates and
re-evaluates the table on the next call by itself.

`reach` is written by `@m.define`, whose compiled `match(...)` names the space
as a literal and the pattern structurally, which is exactly the source's own
shape. `twohop` and `bypattern` stay at the container door, both recorded
against P14.4: a conjunction pattern `(, p q)` has no compiled spelling, since a
Python tuple of patterns builds `(p q)` and `,` is not a name Python can put in
head position; and `bypattern` takes its pattern as a PARAMETER, which the
compiled `match(...)` refuses because it reads its pattern as syntax.
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 85285 to 86854, +1569 (+1.84%), by the P14
#: twin-style rewrite: reach's equation is now compiled from Python syntax by
#: @m.define; twohop and bypattern stay container-door atoms, so one compile
#: of 1,569 inferences is the whole of the move. Prior: ADDED 2026-08-22 at
#: 85285 by the wave-3 libraries baseline, which recorded no cause.
BUDGET = 86854


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_tabling))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_tabling)))

    # !(add-atom &self (edge a b))
    yield m.eval(S["add-atom"](S["&self"], S.edge(S.a, S.b)))
    # !(add-atom &self (edge b c))
    yield m.eval(S["add-atom"](S["&self"], S.edge(S.b, S.c)))

    @m.define
    def reach(x, y):
        # (= (reach $x $y) (match &self (edge $x $y) $y))
        return match("&self", edge(x, y), y)  # noqa: F821  -- match reads its pattern as syntax: `edge` is the relation symbol and `x`, `y` are the parameters

    # (= (twohop $x $z) (match &self (, (edge $x $y) (edge $y $z)) $z))
    m += equation(S.twohop(V.x, V.z)).to(
        S.match(S["&self"], S[","](S.edge(V.x, V.y), S.edge(V.y, V.z)), V.z)
    )

    # !(tabled (reach $x $y))
    yield m.eval(S.tabled(S.reach(V.x, V.y)))
    # !(tabled (twohop $x $z))
    yield m.eval(S.tabled(S.twohop(V.x, V.z)))

    # !(test (collapse (reach a $y)) (b))
    yield m.eval(S.test(S.collapse(S.reach(S.a, V.y)), (S.b,)))
    # !(test (collapse (twohop a $z)) (c))
    yield m.eval(S.test(S.collapse(S.twohop(S.a, V.z)), (S.c,)))

    # Adding an atom the table read. sort-atom for the same reason as
    # tabling_equation_change: a tabled function answers from its trie, not in
    # clause order, so only the answer SET is stable.
    # !(add-atom &self (edge a c))
    yield m.eval(S["add-atom"](S["&self"], S.edge(S.a, S.c)))
    # !(test (sort-atom (collapse (reach a $y))) (b c))
    yield m.eval(
        S.test(S["sort-atom"](S.collapse(S.reach(S.a, V.y))), (S.b, S.c))
    )

    # Removing one.
    # !(remove-atom &self (edge a b))
    yield m.eval(S["remove-atom"](S["&self"], S.edge(S.a, S.b)))
    # !(test (collapse (reach a $y)) (c))
    yield m.eval(S.test(S.collapse(S.reach(S.a, V.y)), (S.c,)))

    # A conjunction reads each of its patterns, so it tracks them all.
    # !(add-atom &self (edge c d))
    yield m.eval(S["add-atom"](S["&self"], S.edge(S.c, S.d)))
    # !(test (collapse (twohop b $z)) (d))
    yield m.eval(S.test(S.collapse(S.twohop(S.b, V.z)), (S.d,)))

    # A read the engine cannot resolve to one space predicate is refused
    # rather than tabled without the guarantee.
    # (= (bypattern $p) (match &self $p $p))
    m += equation(S.bypattern(V.p)).to(S.match(S["&self"], V.p, V.p))

    # !(test (repr (catch (tabled (bypattern $p))))
    #        "(Error (petta_tabling_unresolved_read match $_0) none)")
    yield m.eval(
        S.test(
            S.repr(S.catch(S.tabled(S.bypattern(V.p)))),
            val("(Error (petta_tabling_unresolved_read match $_0) none)"),
        )
    )
