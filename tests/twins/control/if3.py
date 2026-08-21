"""The Python twin of examples/control/if3.metta: an unbound variable IS one.

The companion of if2: there the argument was a symbol and `is-var` answered
False, here it is `$A` and the then arm runs. `V.A` is that variable, and the
lane compares answers up to consistent renaming, so the letter carries no
weight.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 915


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (is-var $A) (if True 42 lol) (+ 2 2)) 42)
    yield m.eval(
        S.test(
            S["if"](
                S["is-var"](V.A),
                S["if"](TRUE, 42, S.lol),
                S["+"](2, 2),
            ),
            42,
        )
    )
