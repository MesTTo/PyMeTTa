"""The Python twin of examples/types/outputtype.metta: the output type decides.

One body, `(+ $x 42)`, three declarations, three answers. `%Undefined%` lets
the sum run and answers 44; `Atom` on the OUTPUT stops the result being
evaluated, so `g` answers the term `(+ 2 42)`; and `Atom` on the input as well
stops the argument evaluating too, so `h` answers `(+ (+ 1 1) 42)`.

The declarations use Python annotations. `@m.define` publishes the derived
`(: name (-> ...))` atom before its equation, so the output annotation governs
that equation as soon as it lands. This twin used to write each declaration
by hand to work around P14.9's late-publication defect; the retired residue
entry records the old spelling and its correction.
"""

from typing import Any

from petta import Atom, S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6895 to 7006, +111, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 6895 by 47554fc's control/types twin baseline.
BUDGET = 7006


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    @m.define
    def f(x: int) -> Any:
        # (= (f $x) (+ $x 42))
        return x + 42

    @m.define
    def g(x: int) -> Atom:
        # (= (g $x) (+ $x 42))
        return x + 42

    @m.define
    def h(x: Atom) -> Atom:
        # (= (h $x) (+ $x 42))
        return x + 42

    # !(test (f (+ 1 1)) 44)
    yield m.eval(S.test(S.f(S["+"](1, 1)), 44))
    # quote retains its wrapper in LeaTTa; noeval is the payload-preserving
    # form these expected expressions require.
    # !(test (g (+ 1 1)) (noeval (+ 2 42)))
    yield m.eval(
        S.test(S.g(S["+"](1, 1)), S.noeval(S["+"](2, 42)))
    )
    # !(test (h (+ 1 1)) (noeval (+ (+ 1 1) 42)))
    yield m.eval(
        S.test(
            S.h(S["+"](1, 1)),
            S.noeval(S["+"](S["+"](1, 1), 42)),
        )
    )
