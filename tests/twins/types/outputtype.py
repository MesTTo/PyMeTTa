"""Purpose: examples/types/outputtype.metta in Python: the output type decides.

One body, `x + 42`, three declarations, three answers. `Any` is `%Undefined%`
and lets the sum run, so `f` answers 44. `Atom` on the OUTPUT stops the result
being evaluated, so `g` answers the term `(+ 2 42)`. `Atom` on the input as
well stops the argument evaluating too, so `h` answers `(+ (+ 1 1) 42)`.

All three are ordinary annotated functions: `@m.define` publishes the arrow the
annotations name before it stores the equation, so the output type governs that
equation as soon as it lands, and calling one IS evaluating it.
"""

from typing import Any

from metta import Atom, S

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
BUDGET = 1


def twin(m):
    """One body, three signatures, three answers."""

    @m.define
    def f(x: int) -> Any:
        """(: f (-> Number %Undefined%)), (= (f $x) (+ $x 42))."""
        return x + 42

    @m.define
    def g(x: int) -> Atom:
        """(: g (-> Number Atom)), the same body under a lazy OUTPUT."""
        return x + 42

    @m.define
    def h(x: Atom) -> Atom:
        """(: h (-> Atom Atom)), lazy on both sides."""
        return x + 42

    # !(test (f (+ 1 1)) 44)
    assert f(S.add(1, 1)) == [44]
    # !(test (g (+ 1 1)) (noeval (+ 2 42)))
    assert g(S.add(1, 1)) == [S.add(2, 42)]
    # !(test (h (+ 1 1)) (noeval (+ (+ 1 1) 42)))
    assert h(S.add(1, 1)) == [S.add(S.add(1, 1), 42)]
