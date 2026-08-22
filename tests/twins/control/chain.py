"""The Python twin of examples/control/chain.metta: `chain` names its result.

`(chain expr $n body)` runs `expr`, binds the answer to the VARIABLE written
in its second position, and runs `body`. The variable is part of the form, so
it is spelled as one: `V.n`, not a Python name.

Inside a compiled body the same shape is written `n = 2 + 4` and lowers to
`let*`; at the top level, with no definition to hold statements, the form is
built as the term it is.
"""

from petta import S, V

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `(+ 2 4)` and `(+ 1 3)` reach `chain` as unevaluated DATA and have two GROUND operands
#: each, where Python's `+` computes the sum instead of building the term. The `(* 3 $n)` and
#: `(+ $n $m)` bodies do have a variable operand and are ordinary operators.
RUNG = "ground operands: the sums chain is handed as data have two, where Python's + computes"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2073 to 2146, +73, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 2073 by 47554fc's control/types twin baseline.
BUDGET = 2146


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (chain (+ 2 4) $n (* 3 $n)) 18)
    yield m.eval(S.test(S.chain(S["+"](2, 4), V.n, 3 * V.n), 18))

    # Chains nest, and the inner one still sees the outer binding.
    # !(test (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m))) 12)
    yield m.eval(
        S.test(
            S.chain(
                S["+"](1, 3),
                V.n,
                S.chain(2 * V.n, V.m, V.n + V.m),
            ),
            12,
        )
    )
