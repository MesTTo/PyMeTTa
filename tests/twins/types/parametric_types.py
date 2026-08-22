"""examples/types/parametric_types.metta in Python: an arrow with variables.

`apply` takes a function and an argument and applies it, and its type says so
with two type variables: `(-> (-> $tx $ty) $tx $ty)`. That arrow is what
`Callable[[X], Y]` and `-> Y` mean, so the annotation IS the declaration, and
mypy checks the Python half of the same claim the engine checks at run time.

The example's last claim instantiates the arrow at `(-> Bool Bool)` and `Bool`
and reads the result type off it. `petta.unify` is one-way matching, so it
cannot bind through the arrow's own variables from the pattern side (filed as
friction); asking the type of the APPLICATION answers the same question, and
it is the example's own second form.
"""

from collections.abc import Callable
from typing import TypeVar

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5543 to 4583, -960 (-17.32%), by the twin-shape
#: rewrite: the `test` wrapper left the engine for `assert`, and the arrow-
#: instantiation claim became a `get-type` of the APPLICATION rather than a
#: `let` unifying against the declared arrow. Against the example's 6723 the
#: ratio is 0.6817 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/parametric_types.metta`]. Prior: RE-PINNED at 5543 by
#: P14.9's declaration-order correction.
BUDGET = 4583

X = TypeVar(name="X")
Y = TypeVar(name="Y")


def twin(m):
    """Apply a function through a parametrically typed applier."""

    @m.define
    def apply(f: Callable[[X], Y], x: X) -> Y:
        return f(x)

    assert apply(S["not"], False) == [True]  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert m.fn("get-type").all(S.apply(S["not"], False)) == [S.Bool]  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
