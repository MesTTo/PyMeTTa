"""The Python twin of examples/functions/functionremoval.metta: equations move.

An equation is an atom, so it can be taken out of the space and put back, and
the function answers differently while it is gone. When both clauses are gone
`(f g)` matches nothing and answers itself.

Two definitional doors, one per shape. `g` is a computation, so it is a
decorated Python function. `f`'s two clauses are ALTERNATIVES that both answer,
which stacked `@m.define` clauses cannot mean (stacking reads as first-match,
and two clauses fixing no literal head are a redefinition of one clause), so
they come from `@rules`: the generator's parameter IS the equation's variable
and each `yield` is one equation.

The point of the file then writes itself, because the two equations are Python
VALUES: `call` and `const` are named once and handed to `remove-atom` and
`add-atom` as the atoms they are.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10071 to 11719, +1648 (+16.36%), and ALL of it is
#: definition installation: the eight runnable forms cost 1228, 1535, 1280,
#: 666, 788, 793 and 546 either way, unchanged to the inference, because both
#: doors land the same three equations. Installing them costs 1432 as atoms,
#: 3061 once `g` is decorated and 3080 once the pair goes in through
#: `m.add`. So +1629 is `@m.define`, nearly all of it the one-time setup the
#: FIRST decorated definition in a process pays (2244 against the atom door's
#: 600 for one equation, where every later one costs 793 against 600), and
#: +19 is the fixed cost of the many-wire add over two single ones. The
#: lane's parity reads 0.82 of the original. Prior: ADDED 2026-08-22 at 10071
#: by 7f15dc1's wave-3 baseline.
BUDGET = 11719


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def g(x):
        # (= (g $x) (+ $x 1))
        return x + 1

    @rules
    def clauses(g):
        # (= (f $g) ($g 1))
        yield equation(S.f(g)).to((g, 1))
        # (= (f $g) 42)
        yield equation(S.f(g)).to(42)

    call, const = clauses
    m.add(call, const)

    # !(test (collapse (f g)) (2 42))
    yield m.eval(S.test(S.collapse(S.f(S.g)), (2, 42)))

    # !(remove-atom &self (= (f $g) 42))
    yield m.eval(S["remove-atom"](S["&self"], const))

    # !(test (collapse (f g)) (2))
    yield m.eval(S.test(S.collapse(S.f(S.g)), (2,)))

    # !(add-atom &self (= (f $g) 42))
    yield m.eval(S["add-atom"](S["&self"], const))

    # !(remove-atom &self (= (f $g) ($g 1)))
    yield m.eval(S["remove-atom"](S["&self"], call))

    # !(test (collapse (f g)) (42))
    yield m.eval(S.test(S.collapse(S.f(S.g)), (42,)))

    # !(remove-atom &self (= (f $g) 42))
    yield m.eval(S["remove-atom"](S["&self"], const))

    # !(test (collapse (f g)) ((f g)))
    yield m.eval(S.test(S.collapse(S.f(S.g)), (S.f(S.g),)))
