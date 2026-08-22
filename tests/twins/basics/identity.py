"""The Python twin of examples/basics/identity.metta: one equation, one call.

The equation is written at the container door, `m += S["="](head, body)`,
the cheapest of the two pure-Python spellings: `@m.define` reads a body as
syntax and pays a fixed registration cost (measured +1,561 inferences per
definition) that dominates an example this small, while the bare equation
lands the identical atom for the identical compiled clauses. The ladder
documents both rungs; a twin picks the one the original's size calls for.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1251 to 1249, -2, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 1214 to 1251, +37 (+3.05%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
BUDGET = 1249


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (f $x) (* $x $x))
    m += S["="](S.f(V.x), V.x * V.x)

    # !(test (f 1) 1)
    yield m.eval(S.test(S.f(1), 1))
