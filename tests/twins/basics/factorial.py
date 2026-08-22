"""The Python twin of examples/basics/factorial.metta: recursion over if.

`@m.define` reads the function as syntax and writes the equation, so the
Python `if`/`else` expression IS MeTTa's `if` and the recursive call is the
same call the equation makes.

One thing the stored equation does NOT match. A compiled body's `==` lowers to
`(py-eq $n 0)`, the prelude's Python equality, where the original writes
`(== $n 0)`; the operator table calls `==` taken for exactly that reason, and
the method form `a.eq(b)` that builds `(== a b)` is a term-door spelling with
no body equivalent. The two answer alike on every input this example has, and
the residue table records the divergence against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5122 to 5101, -21 (-0.41%), by
#: INLINING the fuel charge into the compiled clause instead of calling a
#: shared petta_fuel_step/2. The cost of a charged reduction is a
#: compile-time constant, so the charge is BUILT where the call used to be
#: emitted and the constant lands as a literal in the subtraction: six
#: inferences per charged reduction become four, and the drop tracks each
#: twin's charged-reduction count rather than its size. Prior: #: RE-PINNED 2026-08-22, 5114 to 5122, +8, and this one is
#: UNATTRIBUTED: it reproduces byte-stably across three runs and survives an
#: A/B of both candidate causes (the lib_json/lib_file/lib_thread counter
#: change and this file's own comment block each measure identically either
#: way), and engine/metta.pl is byte-identical to the tree the earlier figure
#: was taken on. Ten of the eighteen twins moved by exactly eight and
#: constraint_domains by forty-eight, which is the shape of the +/-8
#: instruction-layout floor this tree records elsewhere rather than a cost.
#: Pinned at the reproducible reading. Prior: #: RE-PINNED 2026-08-22, 5116 to 5114, -2, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 4495 to 5116, +621 (+13.82%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
BUDGET = 5101


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define(name="facF")
    def fac_f(n):
        # (= (facF $n) (if (== $n 0) 1 (* $n (facF (- $n 1)))))
        return 1 if n == 0 else n * fac_f(n - 1)

    # !(test (facF 10) 3628800)
    yield m.eval(S.test(S.facF(10), 3628800))
