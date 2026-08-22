"""The Python twin of examples/basics/fib.metta: the exponential fib, budgeted.

The deliberately exponential tree exceeds the evaluator's default fuel, so
the original scopes a larger `max-stack-depth` to the one expression with
`with-pragma!`. That form takes its settings UNEVALUATED, which is why it is
built at the term door rather than called.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 33664261 to 28278972, -5385289 (-16.00%), by
#: INLINING the fuel charge into the compiled clause instead of calling a
#: shared petta_fuel_step/2. The cost of a charged reduction is a
#: compile-time constant, so the charge is BUILT where the call used to be
#: emitted and the constant lands as a literal in the subtraction: six
#: inferences per charged reduction become four, and the drop tracks each
#: twin's charged-reduction count rather than its size. Prior: #: RE-PINNED 2026-08-22, 33664253 to 33664261, +8, and this one is
#: UNATTRIBUTED: it reproduces byte-stably across three runs and survives an
#: A/B of both candidate causes (the lib_json/lib_file/lib_thread counter
#: change and this file's own comment block each measure identically either
#: way), and engine/metta.pl is byte-identical to the tree the earlier figure
#: was taken on. Ten of the eighteen twins moved by exactly eight and
#: constraint_domains by forty-eight, which is the shape of the +/-8
#: instruction-layout floor this tree records elsewhere rather than a cost.
#: Pinned at the reproducible reading. Prior: #: RE-PINNED 2026-08-22, 33664255 to 33664253, -2, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 25585424 to 33664255, +8078831 (+31.58%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
BUDGET = 28278972


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def fib(n):
        # (= (fib $N) (if (< $N 2) $N (+ (fib (- $N 1)) (fib (- $N 2)))))
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    # !(test (with-pragma! ((max-stack-depth 100000000)) (fib 30)) 832040)
    yield m.eval(
        S.test(
            S["with-pragma!"](((S["max-stack-depth"], 100000000),), S.fib(30)),
            832040,
        )
    )
