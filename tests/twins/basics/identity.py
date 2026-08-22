"""The Python twin of examples/basics/identity.metta: one equation, one call.

The equation is written at the container door, `equation(head).to(body)`,
and the reason is a measurement rather than a preference. `@m.define` reads
the body as syntax and pays a fixed registration cost; re-measured 2026-08-22
the decorated twin costs 2,878 inferences against the original's 2,577, past
the lane's 10% ceiling of 2,835 by 43. The bare equation lands the identical
atom for the identical compiled clauses and costs 1,249. `control/empty.metta`
is the same shape and now DOES fit, at 1.0945, so this is a 43-inference call
rather than a rule about small examples; both files re-measure it rather than
citing the other.
"""

from petta import S, V, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check
#: reads. `@m.define` is the top rung for a definition; here it costs 2,878
#: against a ceiling of 2,835.
RUNG = "@m.define costs 2878 against the band ceiling of 2835 on this one-form example"

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
    m += equation(S.f(V.x)).to(V.x * V.x)

    # !(test (f 1) 1)
    yield m.eval(S.test(S.f(1), 1))
