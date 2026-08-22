"""The Python twin of examples/basics/xor.metta: `xor` inside an equation.

Python's `^` would be the operator: on a built term it lowers to `(xor ...)`,
and inside a compiled body it is REFUSED ("the operator BitXor has no MeTTa
function"). The two doors disagree, which the residue table records against
P14.4. So the body names `xor` instead, which compiles because the engine
knows that name. `m.fn("xor")` binds it so the Python is valid to read and to
run: `check_xor.py(2, 2)` still answers, which is the twin `@m.define`
promises.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5492 to 5500, +8, and this one is
#: UNATTRIBUTED: it reproduces byte-stably across three runs and survives an
#: A/B of both candidate causes (the lib_json/lib_file/lib_thread counter
#: change and this file's own comment block each measure identically either
#: way), and engine/metta.pl is byte-identical to the tree the earlier figure
#: was taken on. Ten of the eighteen twins moved by exactly eight and
#: constraint_domains by forty-eight, which is the shape of the +/-8
#: instruction-layout floor this tree records elsewhere rather than a cost.
#: Pinned at the reproducible reading. Prior: #: RE-PINNED 2026-08-22, 5495 to 5492, -3, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 4882 to 5495, +613 (+12.56%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
#: RE-PINNED 2026-08-22, 5500 to 5763, at P14.17 automatic tabling: the
#: isolated check_xor equation now publishes its RHS call heads and crosses
#: the SCC decision; +263, re-measured min-of-three fresh-process.
#: RE-PINNED 2026-08-22, 5763 to 5799, at P14.17 per-function invalidation:
#: its indexed ground event clause replaces the shared guarded handler and
#: adds 36 inferences; re-measured min-of-three fresh-process.
BUDGET = 5799


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    xor = m.fn("xor")

    @m.define
    def check_xor(source, destination):
        # (= (check_xor $source $destination)
        #    (if (xor (== $source $destination) (> $source $destination)) 42 0))
        return 42 if xor(source == destination, source > destination) else 0

    # !(test (check_xor 2 2) 42)
    yield m.eval(S.test(check_xor(2, 2), 42))
    # !(test (check_xor 4 2) 42)
    yield m.eval(S.test(check_xor(4, 2), 42))
