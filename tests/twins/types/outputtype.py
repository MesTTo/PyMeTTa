"""examples/types/outputtype.metta in Python: the output type decides.

One body, `x + 42`, three declarations, three answers. `Any` is `%Undefined%`
and lets the sum run, so `f` answers 44. `Atom` on the OUTPUT stops the result
being evaluated, so `g` answers the term `(+ 2 42)`. `Atom` on the input as
well stops the argument evaluating too, so `h` answers `(+ (+ 1 1) 42)`.

All three are ordinary annotated functions: `@m.define` publishes the arrow the
annotations name before it stores the equation, so the output type governs that
equation as soon as it lands.
"""

from typing import Any

from petta import Atom, S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 7006 to 6175, -831 (-11.86%), by the twin-shape
#: rewrite: the three `test` wrappers and their `noeval` expectations left
#: the engine; the three annotated definitions and the calls over them are
#: unchanged. Against the example's 9589 the ratio is 0.6440 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/outputtype.metta`]. Prior: RE-PINNED at 7006 by P14.8's
#: m.eval fuel-scope alignment.
BUDGET = 6175


def twin(m):
    """One body, three signatures, three answers."""

    @m.define
    def f(x: int) -> Any:
        return x + 42

    @m.define
    def g(x: int) -> Atom:
        return x + 42

    @m.define
    def h(x: Atom) -> Atom:
        return x + 42

    assert f(S["+"](1, 1)) == [44]
    assert g(S["+"](1, 1)) == [S["+"](2, 42)]
    assert h(S["+"](1, 1)) == [S["+"](S["+"](1, 1), 42)]
