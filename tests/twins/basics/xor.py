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
BUDGET = 4882


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
