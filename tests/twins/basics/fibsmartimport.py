"""The Python twin of examples/basics/fibsmartimport.metta: importing a module.

`import!` is a directive in a `.metta` file and has no dedicated Python door,
so it is built as the term it is. A bare module name resolves relative to the
IMPORTING FILE, and a Python-authored program has no file, so the twin names
the path instead; the residue table records that against P14.13.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10969 to 10566, -403 (-3.67%), by
#: INLINING the fuel charge into the compiled clause instead of calling a
#: shared petta_fuel_step/2. The cost of a charged reduction is a
#: compile-time constant, so the charge is BUILT where the call used to be
#: emitted and the constant lands as a literal in the subtraction: six
#: inferences per charged reduction become four, and the drop tracks each
#: twin's charged-reduction count rather than its size. Prior: #: RE-PINNED 2026-08-22, 10971 to 10969, -2, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 10033 to 10971, +938 (+9.35%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
#: RE-PINNED 2026-08-22, 10566 to 11227, at P14.17 automatic tabling:
#: importing fibsmart now publishes its equation call heads and declines its
#: single-tail SCC; +661, re-measured min-of-three fresh-process.
#: RE-PINNED 2026-08-22, 11227 to 11269, at P14.17 per-function invalidation:
#: the imported indexed ground event clause replaces the shared guarded
#: handler and adds 42 inferences; min-of-three fresh-process.
BUDGET = 11269


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self fibsmart) answers (())
    yield m.eval(S["import!"](S["&self"], S["examples/basics/fibsmart"]))
    # !(test (fib 100) 354224848179261915075)
    yield m.eval(S.test(S.fib(100), 354224848179261915075))
