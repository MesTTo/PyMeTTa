"""The Python twin of examples/control/chain.metta: `chain` names its result.

`(chain expr $n body)` runs `expr`, binds the answer to the VARIABLE written
in its second position, and runs `body`. The variable is part of the form, so
it is spelled as one: `V.n`, not a Python name.

Inside a compiled body the same shape is written `n = 2 + 4` and lowers to
`let*`; at the top level, with no definition to hold statements, the form is
built as the term it is.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
BUDGET = 2073


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (chain (+ 2 4) $n (* 3 $n)) 18)
    yield m.eval(
        S.test(S["chain"](S["+"](2, 4), V.n, S["*"](3, V.n)), 18)
    )

    # Chains nest, and the inner one still sees the outer binding.
    # !(test (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m))) 12)
    yield m.eval(
        S.test(
            S["chain"](
                S["+"](1, 3),
                V.n,
                S["chain"](S["*"](2, V.n), V.m, S["+"](V.n, V.m)),
            ),
            12,
        )
    )
