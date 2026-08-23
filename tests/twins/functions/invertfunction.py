"""Purpose: examples/functions/invertfunction.metta in Python: functions run backwards.

Unifying a pattern with what a call PRODUCES makes the call run backwards and
its variables come out bound, so destructuring a list with `cons` and
destructuring it with an ordinary user function are the same act. The last
form does it through arithmetic, where `#+` is the constraint path, so
`(g $X $Y 35)` solves `$X + 35 = 42`.

Both definitions are ordinary Python functions. `f` is `(append ($X) $Y)`,
where the one-element Python tuple is the one-element expression; `g` names
`#+`, which no Python identifier spells, and `fn["#+"]` is the function
namespace's exact spelling for that head.

`m.solve(pattern, subject)` is the inversion door: the known list on `let`'s
pattern side, the call on its subject side, and the answer template derived
from the subject's own variables, so each solution is a row keyed by the
variable that solved it. The subject is a BUILT term rather than a Python
call, because solve must receive the call unevaluated; `S.f` and `S.g` name
the two definitions and `fn.cons` names the constructor.
"""

from petta import Expression, S, V, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1

#: The list every claim destructures, and the head and tail it splits into.
ITEMS = (1, 2, 3, 4, 5, 6)
SPLIT = (1, Expression((2, 3, 4, 5, 6)))


def twin(m):
    """Destructure a list three ways, one of them through arithmetic."""

    @m.define
    def f(x, y):
        # (= (f $X $Y) (append ($X) $Y))
        return fn.append((x,), y)

    @m.define
    def g(x, y, z):
        # (= (g $X $Y $Z) (append ((#+ $X $Z)) $Y))
        return fn.append((fn["#+"](x, z),), y)

    # List destructuring, through the cons constructor.
    assert tuple(m.solve(ITEMS, fn.cons(V.Head, V.Tail)).one()) == SPLIT
    # And through an ordinary user function, which is the point.
    assert tuple(m.solve(ITEMS, S.f(V.Head, V.Tail)).one()) == SPLIT
    # A more complex case: the constraint solves 42 = $X + 35.
    assert tuple(m.solve((42, 2, 3), S.g(V.X, V.Y, 35)).one()) == (7, Expression((2, 3)))
