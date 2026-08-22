"""The Python twin of examples/functions/functionremovalspec.metta.

`f` applies its argument, so a call `(f g)` SPECIALIZES on `g`; removing one of
`f`'s two clauses must leave the specialized call working over the clause that
remains, and putting the clause back must bring its answer back.

`g` is a computation, so it is a decorated Python function. `f`'s two clauses
are ALTERNATIVES that both answer, which stacked `@m.define` clauses cannot
mean (stacking reads as first-match, and two clauses fixing no literal head are
a redefinition of one clause), so they come from `@rules`, whose parameter IS
the equation's variable. Naming the two equations is what lets `remove-atom`
and `add-atom` take them as the atoms they are.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10048 to 11696, +1648 (+16.40%), and ALL of it is
#: definition installation: the five runnable forms cost 1272, 1427, 1446 and
#: 2126 either way, unchanged to the inference, because both doors land the
#: same three equations. Installing them costs 1568 as atoms, 3197 once `g`
#: is decorated and 3216 once the pair goes in through `m.add`. So +1629 is
#: `@m.define`, nearly all of it the one-time setup the FIRST decorated
#: definition in a process pays (2244 against the atom door's 600 for one
#: equation, where every later one costs 793 against 600), and +19 is the
#: fixed cost of the many-wire add over two single ones. The lane's parity
#: reads 0.86 of the original. Prior: ADDED 2026-08-22 at 10048 by 7f15dc1's
#: wave-3 baseline.
BUDGET = 11696


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def g(x):
        # (= (g $x) (+ $x 1))
        return x + 1

    # rung: below the function shape: the two clauses are ALTERNATIVES that both
    #   answer, which stacked @m.define clauses read as first-match (residue,
    #   P14.4; the design is P14.3's own note)
    @rules
    def clauses(g):
        # (= (f $g) ($g 1))
        yield equation(S.f(g)).to((g, 1))
        # (= (f $g) ($g 2))
        yield equation(S.f(g)).to((g, 2))

    one, two = clauses
    m.add(one, two)

    # !(test (collapse (f g)) (2 3))
    yield m.eval(S.test(S.collapse(S.f(S.g)), (2, 3)))

    # !(remove-atom &self (= (f $g) ($g 1)))
    yield m.eval(S["remove-atom"](S["&self"], one))

    # The specialized call still runs, over the one clause left.
    # !(test (f g) 3)
    yield m.eval(S.test(S.f(S.g), 3))

    # !(add-atom &self (= (f $g) ($g 1)))
    yield m.eval(S["add-atom"](S["&self"], one))

    # !(test (f g) (3 2))
    yield m.eval(S.test(S.f(S.g), (3, 2)))
