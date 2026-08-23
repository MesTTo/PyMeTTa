"""Purpose: examples/types/parametric_types.metta in Python: an arrow with variables.

`apply` takes a function and an argument and applies it, and its type says so
with two type variables: `(-> (-> $tx $ty) $tx $ty)`. That arrow is what
`Callable[[X], Y]` and `-> Y` mean, so the annotation IS the declaration, and
mypy checks the Python half of the same claim the engine checks at run time.
The type parameters are written in Python's own syntax for them, which needs no
name to be spelled as a string.

The example's last claim instantiates the arrow at `(-> Bool Bool)` and `Bool`
and reads the result type off it, which is a `let` whose PATTERN carries the
answer variable. `solve` says that directly, because its answer template takes
the variables the pattern introduces as well as the subject's.
"""

from collections.abc import Callable

from petta import FALSE, S, V, arrow, fn

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Apply a function through a parametrically typed applier."""

    @m.define
    def apply[X, Y](f: Callable[[X], Y], x: X) -> Y:
        return f(x)

    assert apply(S["not"], FALSE) == [True]

    # The example's last claim instantiates the arrow at `(-> Bool Bool)` and
    # `Bool` and reads the result type off it, a `let` whose PATTERN carries
    # the answer variable.
    assert m.solve(arrow(arrow(bool, bool), bool, V.result),
                   fn.get_type(S.apply)).result == S.Bool
